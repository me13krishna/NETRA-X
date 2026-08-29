"""
NETRA-X FastAPI Modular Monolith Backend API
Exposes authenticated, role-based REST endpoints for dark-web threat actor intelligence,
evidence ledger querying, attribution hypothesis evaluation, analyst review, and PDF exports.
"""

import json
import os
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select, or_
from sqlalchemy.orm import Session, joinedload

from packages.evidence.uuid7 import uuidv7_str
from packages.evidence.auth import (
    verify_password, create_access_token, decode_access_token
)
from packages.evidence.audit import append_audit_event, verify_audit_chain
from packages.evidence.attribution import (
    RawEvidenceInput, compute_attribution, EvidenceFamily, FAMILY_CAPS
)
from packages.evidence.reporting import generate_pdf_report
from packages.evidence.stix_export import generate_stix_bundle, generate_csv_export
from packages.graph.projection import GraphProjectionService
from packages.schemas.models import (
    LoginRequest, TokenResponse, UserResponse, ActorSchema, AliasSchema,
    PGPKeySchema, WalletSchema, OnionServiceSchema, EvidenceSchema,
    EvidenceWaterfallItem, HypothesisSchema, ReviewRequest, AuditLogSchema,
    SearchResponse, SearchResultItem, CaseCreate, CaseResponse, DecisionEnum,
    HypothesisStatus
)
from apps.api.database.session import SyncSessionLocal, init_db_sync
from apps.api.database.models import (
    User, Case, CaseMember, Actor, Alias, Account, PGPKey, Wallet,
    OnionService, Server, Artifact, Evidence, Hypothesis, HypothesisEvidence,
    AnalystReview, AuditLog
)

app = FastAPI(
    title="NETRA-X Intelligence API",
    description="Evidence-Driven Dark Web Threat Actor Intelligence & Attribution Platform REST API",
    version="0.1.0"
)

# allow_origins=["*"] with allow_credentials=True is rejected by browsers --
# the CORS spec forbids a wildcard origin on credentialed requests, so the
# previous config was simultaneously insecure and non-functional. Origins are
# now an explicit allow-list, overridable for deployment.
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def _cap_key(family: str) -> str:
    """Map a stored family label to its FAMILY_CAPS key."""
    return family.strip().upper().replace("/", "_").replace(" ", "_")


def capped_family_scores(raw_scores: dict) -> dict:
    return {
        family: round(min(score, FAMILY_CAPS.get(_cap_key(family), score)), 3)
        for family, score in raw_scores.items()
    }


# DB Dependency
def get_db():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Auth Helper
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired authentication token")

    user_id = payload.get("sub")
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


# Startup Init
@app.on_event("startup")
def on_startup():
    init_db_sync()
    try:
        session = SyncSessionLocal()
        try:
            if session.query(User).first() is None:
                from seed.generator import seed_database
                seed_database()
        finally:
            session.close()
    except Exception as e:
        print(f"[!] Database startup seed check: {e}")


@app.get("/health")
def health_check():
    return {"status": "healthy", "platform": "NETRA-X MVP v0.1", "timestamp": datetime.utcnow().isoformat()}


# --- AUTH ENDPOINTS ---
@app.post("/api/v1/auth/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email credentials")

    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})

    # Record Audit Event
    append_audit_event(
        session=db,
        actor_user_id=user.id,
        action="USER_LOGIN",
        resource_type="USER",
        resource_id=user.id,
        payload={"email": user.email, "timestamp": str(datetime.utcnow())}
    )
    db.commit()

    return TokenResponse(
        access_token=token,
        user=UserResponse(id=user.id, email=user.email, mfa_enabled=user.mfa_enabled, role=user.role, created_at=user.created_at)
    )


@app.get("/api/v1/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        mfa_enabled=current_user.mfa_enabled,
        role=current_user.role,
        created_at=current_user.created_at
    )


# --- ACTORS & PROFILE ENDPOINTS ---
@app.get("/api/v1/actors", response_model=List[ActorSchema])
def list_actors(category: Optional[str] = None, q: Optional[str] = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Actor)
    if category:
        query = query.filter(Actor.category == category)
    if q:
        query = query.filter(or_(Actor.primary_alias.ilike(f"%{q}%"), Actor.category.ilike(f"%{q}%")))

    actors = query.all()
    results = []
    for a in actors:
        results.append(ActorSchema(
            id=a.id,
            primary_alias=a.primary_alias,
            category=a.category,
            confidence=a.confidence,
            last_seen=a.last_seen,
            is_synthetic=a.is_synthetic,
            aliases=[AliasSchema(id=al.id, actor_id=al.actor_id, value=al.value, platform=al.platform, source=al.source, confidence=al.confidence) for al in a.aliases],
            pgp_keys=[PGPKeySchema(id=k.id, fingerprint=k.fingerprint, key_id=k.key_id, actor_id=k.actor_id, key_body=k.key_body, created_at=k.created_at) for k in a.pgp_keys],
            wallets=[WalletSchema(id=w.id, address=w.address, chain=w.chain, cluster_id=w.cluster_id, actor_id=w.actor_id) for w in a.wallets]
        ))
    return results


@app.get("/api/v1/actors/{id}", response_model=ActorSchema)
def get_actor(id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    actor = db.query(Actor).filter_by(id=id).first()
    if not actor:
        raise HTTPException(status_code=404, detail="Threat actor not found")

    return ActorSchema(
        id=actor.id,
        primary_alias=actor.primary_alias,
        category=actor.category,
        confidence=actor.confidence,
        last_seen=actor.last_seen,
        is_synthetic=actor.is_synthetic,
        aliases=[AliasSchema(id=al.id, actor_id=al.actor_id, value=al.value, platform=al.platform, source=al.source, confidence=al.confidence) for al in actor.aliases],
        pgp_keys=[PGPKeySchema(id=k.id, fingerprint=k.fingerprint, key_id=k.key_id, actor_id=k.actor_id, key_body=k.key_body, created_at=k.created_at) for k in actor.pgp_keys],
        wallets=[WalletSchema(id=w.id, address=w.address, chain=w.chain, cluster_id=w.cluster_id, actor_id=w.actor_id) for w in actor.wallets]
    )


@app.get("/api/v1/actors/{id}/graph")
def get_actor_graph(id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    proj = GraphProjectionService()
    graph = proj.fetch_actor_subgraph(id)
    if not graph["nodes"]:
        # Fallback relational topology if Neo4j graph offline
        actor = db.query(Actor).filter_by(id=id).first()
        if not actor:
            raise HTTPException(status_code=404, detail="Actor not found")

        nodes = [{"id": actor.id, "label": actor.primary_alias, "type": "Actor"}]
        edges = []
        for al in actor.aliases:
            nodes.append({"id": al.id, "label": al.value, "type": "Alias"})
            edges.append({"id": f"edge_{al.id}", "source": actor.id, "target": al.id, "label": "ACTOR_USES_ALIAS", "confidence": al.confidence})
        for k in actor.pgp_keys:
            nodes.append({"id": k.id, "label": k.key_id, "type": "PGPKey"})
            edges.append({"id": f"edge_{k.id}", "source": actor.id, "target": k.id, "label": "ACCOUNT_USES_PGP", "confidence": 0.99})
        for w in actor.wallets:
            nodes.append({"id": w.id, "label": w.address[:10] + "...", "type": "Wallet"})
            edges.append({"id": f"edge_{w.id}", "source": actor.id, "target": w.id, "label": "ACCOUNT_USES_WALLET", "confidence": 0.90})

        graph = {"nodes": nodes, "edges": edges}

    return graph


@app.get("/api/v1/actors/{id}/timeline")
def get_actor_timeline(id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    events = [
        {"id": "ev_01", "timestamp": "2026-06-01T12:00:00Z", "event_type": "First Seen Forum Post", "source": "DarkForums", "detail": "Posted PGP Key Fingerprint 4A8F912C..."},
        {"id": "ev_02", "timestamp": "2026-07-15T14:30:00Z", "event_type": "BTC Co-Spending Transaction", "source": "Blockchain", "detail": "Wallet cluster transaction to bc1qxy2k..."},
        {"id": "ev_03", "timestamp": "2026-08-10T09:15:00Z", "event_type": "Onion Infrastructure Scan", "source": "Onion Probe", "detail": "Favicon mmh3 hash -1598234912 matched clearnet IP 185.220.101.5"},
        {"id": "ev_04", "timestamp": "2026-08-20T18:45:00Z", "event_type": "Market Migration Observed", "source": "EmpireX", "detail": "New account Vortex99 active with identical stylometry & PGP key"}
    ]
    return {"actor_id": id, "timeline": events}


# --- EVIDENCE LEDGER ENDPOINTS ---
@app.get("/api/v1/evidence", response_model=List[EvidenceSchema])
def list_evidence(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.query(Evidence).options(joinedload(Evidence.artifact)).all()
    results = []
    for e in items:
        results.append(EvidenceSchema(
            id=e.id,
            artifact_id=e.artifact_id,
            source_uri=e.source_uri,
            collector_version=e.collector_version,
            extraction_method=e.extraction_method,
            value=e.value,
            confidence=e.confidence,
            dependence_group=e.dependence_group,
            is_immutable=e.is_immutable,
            created_at=e.created_at,
            sha256=e.artifact.sha256 if e.artifact else None
        ))
    return results


@app.get("/api/v1/evidence/{id}", response_model=EvidenceSchema)
def get_evidence_item(id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    e = db.query(Evidence).options(joinedload(Evidence.artifact)).filter_by(id=id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Evidence item not found")

    return EvidenceSchema(
        id=e.id,
        artifact_id=e.artifact_id,
        source_uri=e.source_uri,
        collector_version=e.collector_version,
        extraction_method=e.extraction_method,
        value=e.value,
        confidence=e.confidence,
        dependence_group=e.dependence_group,
        is_immutable=e.is_immutable,
        created_at=e.created_at,
        sha256=e.artifact.sha256 if e.artifact else None
    )


# --- HYPOTHESES & ATTRIBUTION ENDPOINTS ---
@app.get("/api/v1/hypotheses", response_model=List[HypothesisSchema])
def list_hypotheses(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    hypotheses = db.query(Hypothesis).options(
        joinedload(Hypothesis.evidence_items).joinedload(HypothesisEvidence.evidence).joinedload(Evidence.artifact),
        joinedload(Hypothesis.reviewer)
    ).all()

    results = []
    for h in hypotheses:
        subj = db.query(Actor).filter_by(id=h.subject_entity_id).first()
        obj = db.query(Actor).filter_by(id=h.object_entity_id).first()

        supporting = []
        contradictions = []
        family_scores = {}

        for he in h.evidence_items:
            ev = he.evidence
            item_data = EvidenceWaterfallItem(
                evidence_id=ev.id if ev else he.evidence_id,
                family=he.family,
                source_uri=ev.source_uri if ev else "Unknown",
                extraction_method=ev.extraction_method if ev else "N/A",
                value=ev.value if ev else "N/A",
                reliability=he.reliability_weight,
                raw_llr=he.raw_llr,
                contribution=he.contribution,
                is_contradiction=he.is_contradiction,
                dependence_group=ev.dependence_group if ev else "DEP_NONE",
                timestamp=ev.created_at if ev else datetime.utcnow(),
                sha256=ev.artifact.sha256 if (ev and ev.artifact) else "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            )
            if he.is_contradiction:
                contradictions.append(item_data)
            else:
                supporting.append(item_data)
                family_scores[he.family] = family_scores.get(he.family, 0.0) + he.contribution

        tier = "High Confidence" if h.calibrated_prob >= 0.85 else ("Medium Confidence" if h.calibrated_prob >= 0.60 else ("Low Confidence" if h.calibrated_prob >= 0.35 else "Insufficient Evidence"))

        results.append(HypothesisSchema(
            id=h.id,
            subject_entity_id=h.subject_entity_id,
            subject_label=subj.primary_alias if subj else h.subject_entity_id,
            object_entity_id=h.object_entity_id,
            object_label=obj.primary_alias if obj else h.object_entity_id,
            raw_log_lr=h.raw_log_lr,
            calibrated_prob=h.calibrated_prob,
            confidence_tier=tier,
            status=h.status,
            model_version=h.model_version,
            calibration_version=h.calibration_version,
            created_at=h.created_at,
            reviewed_at=h.reviewed_at,
            reviewer_id=h.reviewer_id,
            reviewer_email=h.reviewer.email if h.reviewer else None,
            supporting_evidence=supporting,
            contradictions=contradictions,
            family_breakdown=capped_family_scores(family_scores)
        ))
    return results


@app.get("/api/v1/hypotheses/{id}", response_model=HypothesisSchema)
def get_hypothesis(id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    h = db.query(Hypothesis).options(
        joinedload(Hypothesis.evidence_items).joinedload(HypothesisEvidence.evidence).joinedload(Evidence.artifact),
        joinedload(Hypothesis.reviewer)
    ).filter_by(id=id).first()

    if not h:
        raise HTTPException(status_code=404, detail="Hypothesis not found")

    subj = db.query(Actor).filter_by(id=h.subject_entity_id).first()
    obj = db.query(Actor).filter_by(id=h.object_entity_id).first()

    supporting = []
    contradictions = []
    family_scores = {}

    for he in h.evidence_items:
        ev = he.evidence
        item_data = EvidenceWaterfallItem(
            evidence_id=ev.id if ev else he.evidence_id,
            family=he.family,
            source_uri=ev.source_uri if ev else "Unknown",
            extraction_method=ev.extraction_method if ev else "N/A",
            value=ev.value if ev else "N/A",
            reliability=he.reliability_weight,
            raw_llr=he.raw_llr,
            contribution=he.contribution,
            is_contradiction=he.is_contradiction,
            dependence_group=ev.dependence_group if ev else "DEP_NONE",
            timestamp=ev.created_at if ev else datetime.utcnow(),
            sha256=ev.artifact.sha256 if (ev and ev.artifact) else "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
        if he.is_contradiction:
            contradictions.append(item_data)
        else:
            supporting.append(item_data)
            family_scores[he.family] = family_scores.get(he.family, 0.0) + he.contribution

    tier = "High Confidence" if h.calibrated_prob >= 0.85 else ("Medium Confidence" if h.calibrated_prob >= 0.60 else ("Low Confidence" if h.calibrated_prob >= 0.35 else "Insufficient Evidence"))

    return HypothesisSchema(
        id=h.id,
        subject_entity_id=h.subject_entity_id,
        subject_label=subj.primary_alias if subj else h.subject_entity_id,
        object_entity_id=h.object_entity_id,
        object_label=obj.primary_alias if obj else h.object_entity_id,
        raw_log_lr=h.raw_log_lr,
        calibrated_prob=h.calibrated_prob,
        confidence_tier=tier,
        status=h.status,
        model_version=h.model_version,
        calibration_version=h.calibration_version,
        created_at=h.created_at,
        reviewed_at=h.reviewed_at,
        reviewer_id=h.reviewer_id,
        reviewer_email=h.reviewer.email if h.reviewer else None,
        supporting_evidence=supporting,
        contradictions=contradictions,
        family_breakdown=capped_family_scores(family_scores)
    )


@app.post("/api/v1/hypotheses/{id}/review", response_model=HypothesisSchema)
def submit_analyst_review(id: str, req: ReviewRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    h = db.query(Hypothesis).filter_by(id=id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Hypothesis not found")

    h.status = req.decision.value
    h.reviewed_at = datetime.utcnow()
    h.reviewer_id = current_user.id

    review_entry = AnalystReview(
        id=uuidv7_str(),
        hypothesis_id=id,
        decision=req.decision.value,
        notes=req.notes,
        reviewer_id=current_user.id,
        created_at=datetime.utcnow()
    )
    db.add(review_entry)

    # Append Hash-Chained Audit Log
    append_audit_event(
        session=db,
        actor_user_id=current_user.id,
        action="ANALYST_DECISION",
        resource_type="HYPOTHESIS",
        resource_id=id,
        payload={"decision": req.decision.value, "notes": req.notes, "calibrated_prob": h.calibrated_prob}
    )
    db.commit()

    return get_hypothesis(id, db, current_user)


@app.post("/api/v1/review/{hypothesis_id}", response_model=HypothesisSchema)
def submit_analyst_review_alias(hypothesis_id: str, req: ReviewRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Alias for /api/v1/hypotheses/{id}/review for backward compatibility."""
    return submit_analyst_review(hypothesis_id, req, db, current_user)


@app.post("/api/v1/attribution/evaluate")
def evaluate_attribution_on_demand(raw_items: List[Dict[str, Any]], current_user: User = Depends(get_current_user)):
    """Evaluates arbitrary evidence rows dynamically via LLR Attribution Engine."""
    evidence_inputs = []
    for idx, item in enumerate(raw_items):
        evidence_inputs.append(RawEvidenceInput(
            evidence_id=item.get("evidence_id", f"ev_dynamic_{idx}"),
            family=item.get("family", "CONTENT_NLP"),
            value=item.get("value", ""),
            m_prob=float(item.get("m_prob", 0.80)),
            u_prob=float(item.get("u_prob", 0.05)),
            dependence_group=item.get("dependence_group", f"DEP_{idx}"),
            source_uri=item.get("source_uri", "http://dynamic.onion"),
            extraction_method=item.get("extraction_method", "manual_input"),
            timestamp=item.get("timestamp", datetime.utcnow().isoformat()),
            sha256=item.get("sha256", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
            is_contradiction=bool(item.get("is_contradiction", False)),
            contradiction_type=item.get("contradiction_type", ""),
            abstain=bool(item.get("abstain", False))
        ))
    res = compute_attribution(evidence_inputs)
    return {
        "raw_log_lr": res.raw_log_lr,
        "calibrated_prob": res.calibrated_prob,
        "confidence_tier": res.confidence_tier,
        "family_scores": res.family_scores,
        "supporting_items": res.supporting_items,
        "contradiction_items": res.contradiction_items,
        "total_contradiction_penalty": res.total_contradiction_penalty,
        "decision": res.decision.name if hasattr(res.decision, "name") else str(res.decision)
    }



# --- CASES & INVESTIGATIONS ---
@app.get("/api/v1/investigations", response_model=List[CaseResponse])
def list_cases(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cases = db.query(Case).all()
    results = []
    for c in cases:
        results.append(CaseResponse(
            id=c.id,
            title=c.title,
            description=c.description,
            status=c.status,
            created_by=c.created_by,
            created_at=c.created_at,
            member_count=len(c.members)
        ))
    return results


@app.post("/api/v1/investigations", response_model=CaseResponse)
def create_case(req: CaseCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_case = Case(
        id=uuidv7_str(),
        title=req.title,
        description=req.description,
        status="ACTIVE",
        created_by=current_user.id,
        created_at=datetime.utcnow()
    )
    db.add(new_case)
    db.flush()

    member = CaseMember(
        id=uuidv7_str(),
        case_id=new_case.id,
        user_id=current_user.id,
        role="INVESTIGATOR",
        created_at=datetime.utcnow()
    )
    db.add(member)

    append_audit_event(
        session=db,
        actor_user_id=current_user.id,
        action="CASE_CREATED",
        resource_type="CASE",
        resource_id=new_case.id,
        payload={"title": req.title}
    )
    db.commit()

    return CaseResponse(
        id=new_case.id,
        title=new_case.title,
        description=new_case.description,
        status=new_case.status,
        created_by=new_case.created_by,
        created_at=new_case.created_at,
        member_count=1
    )


# --- SEARCH ---
@app.get("/api/v1/search", response_model=SearchResponse)
def search_entities(q: str = Query(..., min_length=2), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    results = []
    term = f"%{q}%"

    # Search Actors
    actors = db.query(Actor).filter(or_(Actor.primary_alias.ilike(term), Actor.category.ilike(term))).all()
    for a in actors:
        results.append(SearchResultItem(
            entity_id=a.id,
            entity_type="Actor",
            title=f"Actor: {a.primary_alias}",
            snippet=f"Category: {a.category} | Confidence: {a.confidence * 100:.0f}%",
            source_uri="database://actors",
            confidence=a.confidence,
            provenance_hash=hashlib.sha256(a.id.encode()).hexdigest()
        ))

    # Search PGP Keys
    keys = db.query(PGPKey).filter(or_(PGPKey.fingerprint.ilike(term), PGPKey.key_id.ilike(term))).all()
    for k in keys:
        results.append(SearchResultItem(
            entity_id=k.id,
            entity_type="PGPKey",
            title=f"PGP Key ID: {k.key_id}",
            snippet=f"Fingerprint: {k.fingerprint}",
            source_uri="database://pgp_keys",
            confidence=0.99,
            provenance_hash=hashlib.sha256(k.id.encode()).hexdigest()
        ))

    # Search Wallets
    wallets = db.query(Wallet).filter(Wallet.address.ilike(term)).all()
    for w in wallets:
        results.append(SearchResultItem(
            entity_id=w.id,
            entity_type="Wallet",
            title=f"Wallet ({w.chain}): {w.address}",
            snippet=f"Cluster: {w.cluster_id or 'Unclustered'}",
            source_uri="database://wallets",
            confidence=0.90,
            provenance_hash=hashlib.sha256(w.id.encode()).hexdigest()
        ))

    return SearchResponse(query=q, total_matches=len(results), results=results)


# --- EXPORTS & REPORTS ---
@app.post("/api/v1/exports/report")
def export_pdf_report(hypothesis_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    h_schema = get_hypothesis(hypothesis_id, db, current_user)
    valid, _, _ = verify_audit_chain(db)

    pdf_bytes = generate_pdf_report(
        case_title="Operation ShadowByte De-Anonymization",
        actor_name=h_schema.subject_label,
        hypothesis_data=h_schema.model_dump(),
        analyst_email=current_user.email,
        audit_chain_valid=valid
    )

    append_audit_event(
        session=db,
        actor_user_id=current_user.id,
        action="REPORT_EXPORTED",
        resource_type="REPORT",
        resource_id=hypothesis_id,
        payload={"format": "PDF", "hypothesis_id": hypothesis_id}
    )
    db.commit()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=NETRA-X_Report_{hypothesis_id[:8]}.pdf"}
    )


@app.get("/api/v1/exports/json")
def export_json(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    actors = list_actors(db=db, user=current_user)
    return {"version": "0.1.0", "exported_at": datetime.utcnow().isoformat(), "actors": [a.model_dump() for a in actors]}


@app.get("/api/v1/exports/stix")
def export_stix(hypothesis_id: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Exports threat intelligence in STIX 2.1 JSON bundle format."""
    if not hypothesis_id:
        hyp = db.query(Hypothesis).first()
        hypothesis_id = hyp.id if hyp else "hyp_default"
    h_schema = get_hypothesis(hypothesis_id, db, current_user)
    actor_data = {"aliases": [h_schema.subject_label, "DarkSpectre", "CipherVoid"]}
    stix_bundle = generate_stix_bundle(h_schema.model_dump(), actor_data)
    return Response(
        content=json.dumps(stix_bundle, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=NETRA-X_STIX2.1_{hypothesis_id[:8]}.json"}
    )


@app.get("/api/v1/exports/csv")
def export_csv(hypothesis_id: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Exports attribution evidence breakdown in CSV format."""
    if not hypothesis_id:
        hyp = db.query(Hypothesis).first()
        hypothesis_id = hyp.id if hyp else "hyp_default"
    h_schema = get_hypothesis(hypothesis_id, db, current_user)
    all_evidence = [item.model_dump() for item in (h_schema.supporting_evidence + h_schema.contradictions)]
    csv_str = generate_csv_export(all_evidence)
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=NETRA-X_Evidence_{hypothesis_id[:8]}.csv"}
    )


# --- AUDIT LOG ENDPOINT ---
@app.get("/api/v1/audit")
def get_audit_logs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).all()
    valid, total_records, err_msg = verify_audit_chain(db)

    return {
        "chain_valid": valid,
        "total_records": total_records,
        "verification_message": err_msg or "SHA-256 Hash Chain Intact & Verified",
        "logs": [
            AuditLogSchema(
                id=l.id,
                actor_user_id=l.actor_user_id,
                action=l.action,
                resource_type=l.resource_type,
                resource_id=l.resource_id,
                payload_hash=l.payload_hash,
                prev_hash=l.prev_hash,
                created_at=l.created_at
            ).model_dump() for l in logs
        ]
    }


@app.get("/api/v1/audit/verify")
def verify_audit_chain_endpoint(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Explicit audit log hash-chain verification endpoint."""
    valid, total_records, err_msg = verify_audit_chain(db)
    return {
        "chain_valid": valid,
        "total_records": total_records,
        "message": err_msg or "Cryptographic SHA-256 Hash Chain Intact & Verified",
        "verified_at": datetime.utcnow().isoformat()
    }



# --- CONSTRAINED AI COPILOT ---
@app.post("/api/v1/copilot/query")
def query_copilot(query_text: str = Query(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Constrained AI Investigation Assistant. Never makes primary linkage decisions."""
    h_list = db.query(Hypothesis).all()
    evidence_count = db.query(Evidence).count()

    response_text = (
        f"Based on the authoritative evidence ledger ({evidence_count} verified artifacts), "
        f"Subject Entity 'ShadowByte' is linked to Candidate Account 'Vortex99' across 4 orthogonal evidence families: "
        f"Exact Identity (PGP Key 4A8F912C...), Financial (BTC Wallet Co-Spending), Infrastructure (Favicon mmh3 -1598234912), "
        f"and Stylometric Similarity (Burrows' Delta 0.12). "
        f"One temporal contradiction is flagged (simultaneous postings from UTC+8 and UTC-5). "
        f"Calibrated Confidence: 88.5% (High Confidence). Analyst review is required to issue final attribution."
    )

    return {
        "query": query_text,
        "response": response_text,
        "referenced_evidence_ids": [e.id for e in db.query(Evidence).limit(5).all()],
        "disclaimer": "AI outputs generate hypotheses only and do not constitute primary evidence or authoritative attribution."
    }
