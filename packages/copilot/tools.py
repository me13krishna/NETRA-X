"""
Ledger access tools for the investigation copilot.

Every function here is a read-only query against the authoritative ledger. They
exist as small, individually-callable units for two reasons: the deterministic
answerer composes them directly, and they double as the tool surface handed to
Claude when an API key is configured. One implementation, two consumers -- so
the LLM path can never report something the deterministic path cannot also
derive from the same rows.

Nothing here invents a value. If the ledger does not contain the answer, the
tool returns an empty result and the caller is expected to say so. That is the
same discipline the fusion engine applies when it abstains below threshold.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from apps.api.database.models import (
    Actor, Alias, Account, PGPKey, Wallet, OnionService, Server,
    Artifact, Evidence, Hypothesis, HypothesisEvidence, AnalystReview,
    AuditLog, Source, Observation, Case,
)


# --------------------------------------------------------------------------
# Entity resolution
# --------------------------------------------------------------------------

def resolve_entity(db: Session, term: str) -> List[Dict[str, Any]]:
    """Find actors whose primary alias, any alias, or category matches `term`.

    Matching an alias matters as much as matching the primary name: the whole
    premise is that one operator wears several handles, so an analyst asking
    about 'nightowl99' is asking about whichever actors used it.
    """
    if not term or not term.strip():
        return []

    like = f"%{term.strip()}%"
    direct = db.query(Actor).filter(
        or_(Actor.primary_alias.ilike(like), Actor.category.ilike(like))
    ).all()

    via_alias = (
        db.query(Actor)
        .join(Alias, Alias.actor_id == Actor.id)
        .filter(Alias.value.ilike(like))
        .all()
    )

    seen, out = set(), []
    for a in list(direct) + list(via_alias):
        if a.id in seen:
            continue
        seen.add(a.id)
        matched = [al.value for al in a.aliases if term.strip().lower() in al.value.lower()]
        out.append({
            "actor_id": a.id,
            "primary_alias": a.primary_alias,
            "category": a.category,
            "confidence": round(a.confidence, 4),
            "matched_aliases": matched,
        })
    return out


# --------------------------------------------------------------------------
# Actor detail
# --------------------------------------------------------------------------

def get_actor_profile(db: Session, actor_id: str) -> Optional[Dict[str, Any]]:
    """Everything the ledger holds about one actor."""
    a = db.query(Actor).filter_by(id=actor_id).first()
    if a is None:
        return None
    return {
        "actor_id": a.id,
        "primary_alias": a.primary_alias,
        "category": a.category,
        "confidence": round(a.confidence, 4),
        "last_seen": a.last_seen.isoformat() if a.last_seen else None,
        "is_synthetic": bool(a.is_synthetic),
        "aliases": [
            {"value": al.value, "platform": al.platform,
             "source": al.source, "confidence": round(al.confidence, 4)}
            for al in a.aliases
        ],
        "pgp_keys": [{"key_id": k.key_id, "fingerprint": k.fingerprint} for k in a.pgp_keys],
        "wallets": [
            {"address": w.address, "chain": w.chain, "cluster_id": w.cluster_id}
            for w in a.wallets
        ],
        "accounts": [
            {"platform": ac.platform, "handle": ac.handle}
            for ac in db.query(Account).filter_by(actor_id=a.id).all()
        ],
    }


def get_actor_links(db: Session, actor_id: str) -> List[Dict[str, Any]]:
    """Scored attribution hypotheses connecting this actor to others."""
    rows = db.query(Hypothesis).filter(
        or_(Hypothesis.subject_entity_id == actor_id,
            Hypothesis.object_entity_id == actor_id)
    ).order_by(Hypothesis.calibrated_prob.desc()).all()

    out = []
    for h in rows:
        other_id = h.object_entity_id if h.subject_entity_id == actor_id else h.subject_entity_id
        other = db.query(Actor).filter_by(id=other_id).first()
        out.append({
            "hypothesis_id": h.id,
            "counterpart_id": other_id,
            "counterpart": other.primary_alias if other else other_id,
            "calibrated_prob": round(h.calibrated_prob, 4),
            "raw_log_lr": round(h.raw_log_lr, 4),
            "status": h.status,
            "model_version": h.model_version,
        })
    return out


def get_hypothesis_evidence(db: Session, hypothesis_id: str) -> Dict[str, Any]:
    """The per-family evidence breakdown behind one hypothesis.

    This is the waterfall the UI renders, in data form -- the answer to
    "why do you believe that", which is the only question that matters.
    """
    h = db.query(Hypothesis).filter_by(id=hypothesis_id).first()
    if h is None:
        return {}

    items = db.query(HypothesisEvidence).filter_by(hypothesis_id=hypothesis_id).all()
    contributions, contradictions, evidence_ids = [], [], []
    for it in items:
        evidence_ids.append(it.evidence_id)
        row = {
            "evidence_id": it.evidence_id,
            "family": it.family,
            "raw_llr": round(it.raw_llr, 4),
            "contribution": round(it.contribution, 4),
            "reliability_weight": round(it.reliability_weight, 4),
        }
        (contradictions if it.is_contradiction else contributions).append(row)

    by_family: Dict[str, float] = {}
    for c in contributions:
        by_family[c["family"]] = round(by_family.get(c["family"], 0.0) + c["contribution"], 4)

    return {
        "hypothesis_id": h.id,
        "calibrated_prob": round(h.calibrated_prob, 4),
        "raw_log_lr": round(h.raw_log_lr, 4),
        "status": h.status,
        "family_totals": by_family,
        "independent_families": len(by_family),
        "supporting_items": contributions,
        "contradictions": contradictions,
        "evidence_ids": evidence_ids,
    }


# --------------------------------------------------------------------------
# Cross-actor structure -- the reuse the product exists to surface
# --------------------------------------------------------------------------

def find_shared_identifiers(db: Session, actor_id: Optional[str] = None) -> Dict[str, Any]:
    """Identifiers touched by more than one actor.

    A handle or wallet cluster used by two differently-named personas is the
    finding; a handle used by one is just a handle.
    """
    shared_handles = []
    counts = (
        db.query(func.lower(Alias.value).label("v"),
                 func.count(func.distinct(Alias.actor_id)).label("n"))
        .group_by(func.lower(Alias.value))
        .having(func.count(func.distinct(Alias.actor_id)) > 1)
        .all()
    )
    for value, n in counts:
        rows = db.query(Alias).filter(func.lower(Alias.value) == value).all()
        owners = {r.actor_id for r in rows}
        names = [
            (db.query(Actor).filter_by(id=o).first().primary_alias
             if db.query(Actor).filter_by(id=o).first() else o)
            for o in owners
        ]
        if actor_id and actor_id not in owners:
            continue
        shared_handles.append({"handle": rows[0].value, "actor_count": n, "actors": names})

    shared_wallets = []
    wcounts = (
        db.query(Wallet.cluster_id, func.count(func.distinct(Wallet.actor_id)).label("n"))
        .filter(Wallet.cluster_id.isnot(None))
        .group_by(Wallet.cluster_id)
        .having(func.count(func.distinct(Wallet.actor_id)) > 1)
        .all()
    )
    for cluster_id, n in wcounts:
        rows = db.query(Wallet).filter_by(cluster_id=cluster_id).all()
        owners = {r.actor_id for r in rows}
        if actor_id and actor_id not in owners:
            continue
        names = [
            (db.query(Actor).filter_by(id=o).first().primary_alias
             if db.query(Actor).filter_by(id=o).first() else o)
            for o in owners
        ]
        shared_wallets.append({
            "cluster_id": cluster_id, "actor_count": n, "actors": names,
            "addresses": len(rows),
            "chains": sorted({r.chain for r in rows}),
        })

    return {"shared_handles": shared_handles, "shared_wallet_clusters": shared_wallets}


# --------------------------------------------------------------------------
# Provenance and integrity
# --------------------------------------------------------------------------

def get_evidence_provenance(db: Session, limit: int = 10,
                            kind: Optional[str] = None) -> List[Dict[str, Any]]:
    """Recent evidence rows with the artifact digest they came from."""
    q = db.query(Evidence)
    if kind:
        q = q.filter(Evidence.extraction_method.ilike(f"%{kind}%"))
    rows = q.order_by(Evidence.created_at.desc()).limit(limit).all()

    out = []
    for e in rows:
        art = db.query(Artifact).filter_by(id=e.artifact_id).first()
        out.append({
            "evidence_id": e.id,
            "value": e.value,
            "extraction_method": e.extraction_method,
            "dependence_group": e.dependence_group,
            "confidence": round(e.confidence, 4),
            "source_uri": e.source_uri,
            "artifact_sha256": art.sha256 if art else None,
        })
    return out


def get_ledger_stats(db: Session) -> Dict[str, Any]:
    """Counts across the ledger, plus the audit chain's verification state."""
    from packages.evidence.audit import verify_audit_chain

    try:
        chain_valid, records, err = verify_audit_chain(db)
    except Exception as exc:  # pragma: no cover - defensive
        chain_valid, records, err = False, 0, str(exc)

    return {
        "actors": db.query(Actor).count(),
        "aliases": db.query(Alias).count(),
        "pgp_keys": db.query(PGPKey).count(),
        "wallets": db.query(Wallet).count(),
        "onion_services": db.query(OnionService).count(),
        "evidence": db.query(Evidence).count(),
        "artifacts": db.query(Artifact).count(),
        "observations": db.query(Observation).count(),
        "sources": db.query(Source).count(),
        "hypotheses": db.query(Hypothesis).count(),
        "hypotheses_awaiting_review": db.query(Hypothesis).filter_by(status="PROPOSED").count(),
        "cases": db.query(Case).count(),
        "audit_records": records,
        "audit_chain_valid": bool(chain_valid),
        "audit_chain_error": err,
    }


def get_infrastructure(db: Session, limit: int = 10) -> Dict[str, Any]:
    """Onion services and hosting, including favicon/TLS values shared by more
    than one service -- the misconfiguration pivot."""
    services = db.query(OnionService).limit(limit).all()
    rows = [{
        "onion_address": s.onion_address,
        "title": s.title,
        "favicon_mmh3": s.favicon_mmh3,
        "tls_cert_fingerprint": s.tls_cert_fingerprint,
    } for s in services]

    fav_shared = (
        db.query(OnionService.favicon_mmh3, func.count(OnionService.id).label("n"))
        .filter(OnionService.favicon_mmh3.isnot(None))
        .group_by(OnionService.favicon_mmh3)
        .having(func.count(OnionService.id) > 1).all()
    )
    tls_shared = (
        db.query(OnionService.tls_cert_fingerprint, func.count(OnionService.id).label("n"))
        .filter(OnionService.tls_cert_fingerprint.isnot(None))
        .group_by(OnionService.tls_cert_fingerprint)
        .having(func.count(OnionService.id) > 1).all()
    )

    return {
        "services": rows,
        "shared_favicon_hashes": [{"favicon_mmh3": f, "service_count": n} for f, n in fav_shared],
        "shared_tls_fingerprints": [{"fingerprint": t, "service_count": n} for t, n in tls_shared],
        "servers": [
            {"ip_address": s.ip_address, "asn": s.asn, "provider": s.provider}
            for s in db.query(Server).limit(limit).all()
        ],
    }


def get_review_queue(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
    """Hypotheses awaiting an analyst decision, most confident first."""
    rows = (
        db.query(Hypothesis)
        .filter(Hypothesis.status == "PROPOSED")
        .order_by(Hypothesis.calibrated_prob.desc())
        .limit(limit).all()
    )
    out = []
    for h in rows:
        s = db.query(Actor).filter_by(id=h.subject_entity_id).first()
        o = db.query(Actor).filter_by(id=h.object_entity_id).first()
        out.append({
            "hypothesis_id": h.id,
            "subject": s.primary_alias if s else h.subject_entity_id,
            "object": o.primary_alias if o else h.object_entity_id,
            "calibrated_prob": round(h.calibrated_prob, 4),
            "raw_log_lr": round(h.raw_log_lr, 4),
        })
    return out


# --------------------------------------------------------------------------
# Universal search
#
# resolve_entity only knows actors and aliases, so pasting a wallet address, a
# PGP fingerprint, an onion host or a cluster id -- the identifiers an analyst
# actually has in hand mid-investigation -- fell straight through to a refusal.
# This searches every identifier table the ledger holds and reports which actor
# each hit belongs to.
# --------------------------------------------------------------------------

def universal_search(db: Session, term: str, limit: int = 8) -> List[Dict[str, Any]]:
    """Search every identifier table for `term`.

    Returns typed hits: each carries `kind`, the matched `value`, and the
    owning actor where the ledger records one.
    """
    t = (term or "").strip()
    if len(t) < 3:
        return []
    like = f"%{t}%"
    hits: List[Dict[str, Any]] = []

    def owner(actor_id: Optional[str]) -> Optional[str]:
        if not actor_id:
            return None
        a = db.query(Actor).filter_by(id=actor_id).first()
        return a.primary_alias if a else None

    for a in db.query(Actor).filter(
            or_(Actor.primary_alias.ilike(like), Actor.category.ilike(like))).limit(limit):
        hits.append({"kind": "actor", "value": a.primary_alias, "actor": a.primary_alias,
                     "actor_id": a.id, "detail": a.category})

    for al in db.query(Alias).filter(Alias.value.ilike(like)).limit(limit):
        hits.append({"kind": "alias", "value": al.value, "actor": owner(al.actor_id),
                     "actor_id": al.actor_id, "detail": al.platform})

    for ac in db.query(Account).filter(
            or_(Account.handle.ilike(like), Account.platform.ilike(like))).limit(limit):
        hits.append({"kind": "account", "value": ac.handle, "actor": owner(ac.actor_id),
                     "actor_id": ac.actor_id, "detail": ac.platform})

    for w in db.query(Wallet).filter(
            or_(Wallet.address.ilike(like), Wallet.cluster_id.ilike(like),
                Wallet.chain.ilike(like))).limit(limit):
        hits.append({"kind": "wallet", "value": w.address, "actor": owner(w.actor_id),
                     "actor_id": w.actor_id,
                     "detail": f"{w.chain}, cluster {w.cluster_id or 'unclustered'}"})

    for k in db.query(PGPKey).filter(
            or_(PGPKey.key_id.ilike(like), PGPKey.fingerprint.ilike(like))).limit(limit):
        hits.append({"kind": "pgp_key", "value": k.key_id, "actor": owner(k.actor_id),
                     "actor_id": k.actor_id, "detail": k.fingerprint})

    for s in db.query(OnionService).filter(
            or_(OnionService.onion_address.ilike(like),
                OnionService.title.ilike(like))).limit(limit):
        hits.append({"kind": "onion_service", "value": s.onion_address, "actor": None,
                     "actor_id": None, "detail": s.title})

    for sv in db.query(Server).filter(
            or_(Server.ip_address.ilike(like), Server.asn.ilike(like),
                Server.provider.ilike(like))).limit(limit):
        hits.append({"kind": "server", "value": sv.ip_address, "actor": None,
                     "actor_id": None, "detail": f"{sv.asn} / {sv.provider}"})

    for e in db.query(Evidence).filter(
            or_(Evidence.value.ilike(like),
                Evidence.extraction_method.ilike(like))).limit(limit):
        hits.append({"kind": "evidence", "value": e.value[:120], "actor": None,
                     "actor_id": None, "detail": e.extraction_method})

    for c in db.query(Case).filter(
            or_(Case.title.ilike(like), Case.description.ilike(like))).limit(limit):
        hits.append({"kind": "case", "value": c.title, "actor": None,
                     "actor_id": None, "detail": c.status})

    seen, out = set(), []
    for h in hits:
        key = (h["kind"], h["value"])
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
    return out


def list_actors(db: Session, limit: int = 100) -> List[Dict[str, Any]]:
    """The full roster, so "who is in here" is answerable."""
    return [{
        "actor_id": a.id,
        "primary_alias": a.primary_alias,
        "category": a.category,
        "confidence": round(a.confidence, 4),
        "alias_count": len(a.aliases),
    } for a in db.query(Actor).order_by(Actor.confidence.desc()).limit(limit).all()]


def get_actor_evidence(db: Session, actor_id: str, limit: int = 12) -> List[Dict[str, Any]]:
    """Evidence rows cited by any hypothesis touching this actor."""
    hyp_ids = [h.id for h in db.query(Hypothesis).filter(
        or_(Hypothesis.subject_entity_id == actor_id,
            Hypothesis.object_entity_id == actor_id)).all()]
    if not hyp_ids:
        return []
    items = (db.query(HypothesisEvidence)
             .filter(HypothesisEvidence.hypothesis_id.in_(hyp_ids)).all())
    out, seen = [], set()
    for it in items:
        if it.evidence_id in seen:
            continue
        seen.add(it.evidence_id)
        e = db.query(Evidence).filter_by(id=it.evidence_id).first()
        if e is None:
            continue
        art = db.query(Artifact).filter_by(id=e.artifact_id).first()
        out.append({
            "evidence_id": e.id,
            "family": it.family,
            "value": e.value,
            "extraction_method": e.extraction_method,
            "contribution": round(it.contribution, 4),
            "is_contradiction": bool(it.is_contradiction),
            "artifact_sha256": art.sha256 if art else None,
        })
        if len(out) >= limit:
            break
    return sorted(out, key=lambda r: -abs(r["contribution"]))


def get_cases(db: Session, limit: int = 20) -> List[Dict[str, Any]]:
    """Investigations on record."""
    return [{
        "case_id": c.id,
        "title": c.title,
        "status": c.status,
        "description": c.description,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    } for c in db.query(Case).order_by(Case.created_at.desc()).limit(limit).all()]


def get_decisions(db: Session, limit: int = 15) -> List[Dict[str, Any]]:
    """Analyst decisions already recorded against hypotheses."""
    out = []
    rows = (db.query(AnalystReview)
            .order_by(AnalystReview.created_at.desc()).limit(limit).all())
    for r in rows:
        h = db.query(Hypothesis).filter_by(id=r.hypothesis_id).first()
        pair = None
        if h is not None:
            s = db.query(Actor).filter_by(id=h.subject_entity_id).first()
            o = db.query(Actor).filter_by(id=h.object_entity_id).first()
            pair = (f"{s.primary_alias if s else h.subject_entity_id} <-> "
                    f"{o.primary_alias if o else h.object_entity_id}")
        out.append({
            "review_id": r.id,
            "decision": r.decision,
            "notes": r.notes,
            "hypothesis_id": r.hypothesis_id,
            "pair": pair,
            "calibrated_prob": round(h.calibrated_prob, 4) if h else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return out


def get_timeline(db: Session, limit: int = 15) -> List[Dict[str, Any]]:
    """Recent recorded activity, from the audit chain.

    Answers "what has happened here lately" -- and unlike a UI activity feed it
    reads the same rows the tamper-evidence check verifies.
    """
    rows = db.query(AuditLog).order_by(AuditLog.seq.desc()).limit(limit).all()
    return [{
        "seq": r.seq,
        "action": r.action,
        "resource_type": r.resource_type,
        "resource_id": r.resource_id,
        "at": r.created_at.isoformat() if r.created_at else None,
        "entry_hash": r.entry_hash[:16] if r.entry_hash else None,
    } for r in rows]


def get_sources(db: Session, limit: int = 20) -> List[Dict[str, Any]]:
    """Collection sources and the lawful basis recorded for each."""
    return [{
        "source_id": s.id,
        "name": s.name,
        "source_type": s.source_type,
        "lawful_basis": s.lawful_basis,
        "base_uri": s.base_uri,
        "is_active": bool(s.is_active),
    } for s in db.query(Source).limit(limit).all()]


# Registry consumed by both the deterministic answerer and the Claude tool
# surface, so the two can never drift apart.
TOOL_REGISTRY = {
    "resolve_entity": resolve_entity,
    "universal_search": universal_search,
    "list_actors": list_actors,
    "get_actor_profile": get_actor_profile,
    "get_actor_links": get_actor_links,
    "get_actor_evidence": get_actor_evidence,
    "get_hypothesis_evidence": get_hypothesis_evidence,
    "find_shared_identifiers": find_shared_identifiers,
    "get_evidence_provenance": get_evidence_provenance,
    "get_ledger_stats": get_ledger_stats,
    "get_infrastructure": get_infrastructure,
    "get_review_queue": get_review_queue,
    "get_cases": get_cases,
    "get_decisions": get_decisions,
    "get_timeline": get_timeline,
    "get_sources": get_sources,
}
