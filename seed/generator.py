"""
Deterministic Synthetic Intelligence Seed Pipeline for NETRA-X
Populates the authoritative PostgreSQL ledger with the Hero Scenario dataset (Actor A "ShadowByte").
"""

import sys
import hashlib
from datetime import datetime, timedelta
from packages.evidence.auth import hash_password
from packages.evidence.uuid7 import uuidv7_str
from packages.evidence.audit import append_audit_event
from packages.evidence.attribution import (
    RawEvidenceInput, compute_attribution, EvidenceFamily
)
from packages.graph.projection import GraphProjectionService
from apps.api.database.session import SyncSessionLocal, init_db_sync
from apps.api.database.models import (
    User, Case, CaseMember, Actor, Alias, Account, PGPKey, Wallet,
    OnionService, Server, Artifact, Evidence, Hypothesis, HypothesisEvidence,
    AuditLog
)


def seed_database():
    """Populate database with deterministic synthetic dataset."""
    print("[+] Initializing database tables...")
    init_db_sync()

    session = SyncSessionLocal()

    try:
        # Check if already seeded
        existing_admin = session.query(User).filter_by(email="admin@netra-x.local").first()
        if existing_admin:
            print("[!] Database already contains seed data. Re-running graph projection...")
            GraphProjectionService().rebuild_graph_from_postgres(session)
            print("[+] Graph projection complete.")
            return

        print("[+] Creating default system users...")
        admin_user = User(
            id=uuidv7_str(),
            email="admin@netra-x.local",
            password_hash=hash_password("AdminPass2026!"),
            mfa_enabled=True,
            role="ADMIN",
            created_at=datetime.utcnow()
        )
        analyst_user = User(
            id=uuidv7_str(),
            email="analyst@netra-x.local",
            password_hash=hash_password("AnalystPass2026!"),
            mfa_enabled=False,
            role="ANALYST",
            created_at=datetime.utcnow()
        )
        session.add_all([admin_user, analyst_user])
        session.flush()

        print("[+] Creating Investigation Case...")
        case_id = uuidv7_str()
        hero_case = Case(
            id=case_id,
            title="Operation ShadowByte De-Anonymization",
            description="Investigating cross-platform migration of threat actor ShadowByte / DarkSpectre across darknet forums.",
            status="ACTIVE",
            created_by=analyst_user.id,
            created_at=datetime.utcnow()
        )
        session.add(hero_case)
        session.flush()

        case_member = CaseMember(
            id=uuidv7_str(),
            case_id=case_id,
            user_id=analyst_user.id,
            role="ANALYST",
            created_at=datetime.utcnow()
        )
        session.add(case_member)

        print("[+] Creating Synthetic Threat Actor A (ShadowByte)...")
        actor_id = uuidv7_str()
        actor_a = Actor(
            id=actor_id,
            primary_alias="ShadowByte",
            category="Ransomware Operator",
            confidence=0.95,
            last_seen=datetime.utcnow(),
            is_synthetic=True
        )
        session.add(actor_a)
        session.flush()

        # Aliases
        alias_1 = Alias(id=uuidv7_str(), actor_id=actor_id, value="ShadowByte", platform="DarkForums", source="forum_post", confidence=0.99)
        alias_2 = Alias(id=uuidv7_str(), actor_id=actor_id, value="DarkSpectre", platform="DreadMirror", source="profile_bio", confidence=0.90)
        alias_3 = Alias(id=uuidv7_str(), actor_id=actor_id, value="CipherVoid", platform="Telegram", source="chat_dump", confidence=0.75)
        session.add_all([alias_1, alias_2, alias_3])

        # Accounts
        acc_1 = Account(id=uuidv7_str(), actor_id=actor_id, platform="DarkForums", handle="ShadowByte")
        acc_2 = Account(id=uuidv7_str(), actor_id=actor_id, platform="DreadMirror", handle="DarkSpectre")
        session.add_all([acc_1, acc_2])

        # PGP Key
        pgp_fingerprint = "4A8F912CB301772EB19C80A5D81023EF44A91876"
        pgp_key = PGPKey(
            id=uuidv7_str(),
            fingerprint=pgp_fingerprint,
            key_id="D81023EF",
            actor_id=actor_id,
            key_body="-----BEGIN PGP PUBLIC KEY BLOCK-----\nVersion: GnuPG v2\nmQENBF5...\n-----END PGP PUBLIC KEY BLOCK-----",
            created_at=datetime.utcnow()
        )
        session.add(pgp_key)

        # Wallets
        wallet_1 = Wallet(id=uuidv7_str(), address="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh", chain="BTC", cluster_id="CLUSTER_SB_01", actor_id=actor_id)
        wallet_2 = Wallet(id=uuidv7_str(), address="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", chain="BTC", cluster_id="CLUSTER_SB_01", actor_id=actor_id)
        session.add_all([wallet_1, wallet_2])

        # Onion Service & Server
        onion_srv = OnionService(
            id=uuidv7_str(),
            onion_address="shadowmarket7x4k2.onion",
            title="Shadow Market Official",
            favicon_mmh3=-1598234912,
            tls_cert_fingerprint="04:a1:b2:c3:d4:e5:f6:78",
            first_seen=datetime.utcnow() - timedelta(days=90),
            last_seen=datetime.utcnow()
        )
        session.add(onion_srv)

        clearnet_server = Server(
            id=uuidv7_str(),
            ip_address="185.220.101.5",
            asn="AS60729",
            provider="ZettaHosting Ltd",
            created_at=datetime.utcnow()
        )
        session.add(clearnet_server)
        session.flush()

        print("[+] Creating Candidate Target Entity B (Unlinked Alias Vortex99)...")
        target_actor_id = uuidv7_str()
        target_actor = Actor(
            id=target_actor_id,
            primary_alias="Vortex99",
            category="Suspect Migration Account",
            confidence=0.60,
            last_seen=datetime.utcnow(),
            is_synthetic=True
        )
        session.add(target_actor)
        session.flush()

        target_alias = Alias(id=uuidv7_str(), actor_id=target_actor_id, value="Vortex99", platform="EmpireX", source="marketplace_seller", confidence=0.80)
        session.add(target_alias)

        print("[+] Creating Raw Immutable Artifacts & Evidence Ledger Items...")
        raw_text_1 = "Contact me at ShadowByte PGP Key: 4A8F 912C B301 772E B19C 80A5 D810 23EF 44A9 1876 for ransom decryption."
        raw_hash_1 = hashlib.sha256(raw_text_1.encode("utf-8")).hexdigest()

        artifact_1 = Artifact(
            id=uuidv7_str(),
            sha256=raw_hash_1,
            storage_uri=f"s3://netra-artifacts/sha256/{raw_hash_1}",
            content_type="text/plain",
            size=len(raw_text_1),
            collected_at=datetime.utcnow()
        )
        session.add(artifact_1)
        session.flush()

        # Evidence Items linking Actor A (ShadowByte) to Candidate B (Vortex99)
        ev_1 = Evidence(
            id=uuidv7_str(),
            artifact_id=artifact_1.id,
            source_uri="http://darkforums777.onion/thread/10928",
            collector_version="v0.1.0-synthetic",
            extraction_method="pgp_fingerprint_parser",
            value=f"Shared PGP Fingerprint Match: {pgp_fingerprint}",
            confidence=0.99,
            dependence_group="DEP_GRP_PGP_01",
            is_immutable=True,
            created_at=datetime.utcnow()
        )

        ev_2 = Evidence(
            id=uuidv7_str(),
            artifact_id=artifact_1.id,
            source_uri="http://dreadmirror44.onion/post/5512",
            collector_version="v0.1.0-synthetic",
            extraction_method="blockchain_cluster_analyzer",
            value="Co-spending BTC Wallet Address: bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            confidence=0.90,
            dependence_group="DEP_GRP_WALLET_01",
            is_immutable=True,
            created_at=datetime.utcnow()
        )

        ev_3 = Evidence(
            id=uuidv7_str(),
            artifact_id=artifact_1.id,
            source_uri="http://shadowmarket7x4k2.onion/favicon.ico",
            collector_version="v0.1.0-synthetic",
            extraction_method="favicon_mmh3_shodan_matcher",
            value="Shared Favicon mmh3 Hash -1598234912 -> Clearnet Server 185.220.101.5",
            confidence=0.85,
            dependence_group="DEP_GRP_INFRA_01",
            is_immutable=True,
            created_at=datetime.utcnow()
        )

        ev_4 = Evidence(
            id=uuidv7_str(),
            artifact_id=artifact_1.id,
            source_uri="http://empirex999.onion/seller/Vortex99",
            collector_version="v0.1.0-synthetic",
            extraction_method="faststylometry_burrows_delta",
            value="Burrows Delta Distance 0.12 (Calibrated Same-Author Prob 0.88)",
            confidence=0.75,
            dependence_group="DEP_GRP_STYLE_01",
            is_immutable=True,
            created_at=datetime.utcnow()
        )

        # Planted Contradiction Evidence (e.g. Timezone Conflict)
        ev_contradiction = Evidence(
            id=uuidv7_str(),
            artifact_id=artifact_1.id,
            source_uri="http://empirex999.onion/logs/activity",
            collector_version="v0.1.0-synthetic",
            extraction_method="temporal_activity_overlap",
            value="Simultaneous high-frequency forum posting recorded from UTC+8 and UTC-5 within 2-minute window",
            confidence=0.95,
            dependence_group="DEP_GRP_TEMP_CONFLICT",
            is_immutable=True,
            created_at=datetime.utcnow()
        )

        session.add_all([ev_1, ev_2, ev_3, ev_4, ev_contradiction])
        session.flush()

        print("[+] Evaluating LLR Attribution Engine for Hero Hypothesis...")
        raw_evidence_list = [
            RawEvidenceInput(
                evidence_id=ev_1.id,
                family=EvidenceFamily.EXACT_IDENTITY.value,
                value=ev_1.value,
                m_prob=0.99,
                u_prob=0.0001,
                dependence_group=ev_1.dependence_group,
                source_uri=ev_1.source_uri,
                extraction_method=ev_1.extraction_method,
                timestamp=str(ev_1.created_at),
                sha256=raw_hash_1
            ),
            RawEvidenceInput(
                evidence_id=ev_2.id,
                family=EvidenceFamily.FINANCIAL.value,
                value=ev_2.value,
                m_prob=0.90,
                u_prob=0.001,
                dependence_group=ev_2.dependence_group,
                source_uri=ev_2.source_uri,
                extraction_method=ev_2.extraction_method,
                timestamp=str(ev_2.created_at),
                sha256=raw_hash_1
            ),
            RawEvidenceInput(
                evidence_id=ev_3.id,
                family=EvidenceFamily.INFRASTRUCTURE.value,
                value=ev_3.value,
                m_prob=0.85,
                u_prob=0.005,
                dependence_group=ev_3.dependence_group,
                source_uri=ev_3.source_uri,
                extraction_method=ev_3.extraction_method,
                timestamp=str(ev_3.created_at),
                sha256=raw_hash_1
            ),
            RawEvidenceInput(
                evidence_id=ev_4.id,
                family=EvidenceFamily.STYLOMETRY.value,
                value=ev_4.value,
                m_prob=0.75,
                u_prob=0.02,
                dependence_group=ev_4.dependence_group,
                source_uri=ev_4.source_uri,
                extraction_method=ev_4.extraction_method,
                timestamp=str(ev_4.created_at),
                sha256=raw_hash_1
            ),
            RawEvidenceInput(
                evidence_id=ev_contradiction.id,
                family=EvidenceFamily.TEMPORAL.value,
                value=ev_contradiction.value,
                m_prob=0.01,
                u_prob=0.95,
                dependence_group=ev_contradiction.dependence_group,
                source_uri=ev_contradiction.source_uri,
                extraction_method=ev_contradiction.extraction_method,
                timestamp=str(ev_contradiction.created_at),
                sha256=raw_hash_1,
                is_contradiction=True,
                contradiction_type="Temporal Impossibility"
            )
        ]

        attribution_res = compute_attribution(raw_evidence_list)

        hypothesis_id = uuidv7_str()
        hero_hypothesis = Hypothesis(
            id=hypothesis_id,
            subject_entity_id=actor_id,
            object_entity_id=target_actor_id,
            raw_log_lr=attribution_res.raw_log_lr,
            calibrated_prob=attribution_res.calibrated_prob,
            status="PROPOSED",
            model_version="v1.0-LLR",
            calibration_version="v1.0-Isotonic",
            created_at=datetime.utcnow()
        )
        session.add(hero_hypothesis)
        session.flush()

        # Link Hypothesis to Evidence Items
        for item_dict in attribution_res.supporting_items:
            session.add(HypothesisEvidence(
                id=uuidv7_str(),
                hypothesis_id=hypothesis_id,
                evidence_id=item_dict["evidence_id"],
                family=item_dict["family"],
                reliability_weight=item_dict["reliability"],
                raw_llr=item_dict["raw_llr"],
                contribution=item_dict["contribution"],
                is_contradiction=False
            ))

        for item_dict in attribution_res.contradiction_items:
            session.add(HypothesisEvidence(
                id=uuidv7_str(),
                hypothesis_id=hypothesis_id,
                evidence_id=item_dict["evidence_id"],
                family=item_dict["family"],
                reliability_weight=item_dict["reliability"],
                raw_llr=item_dict["raw_llr"],
                contribution=item_dict["contribution"],
                is_contradiction=True
            ))

        session.flush()

        print("[+] Generating Hash-Chained Audit Log Entries...")
        append_audit_event(
            session=session,
            actor_user_id=admin_user.id,
            action="SYSTEM_INIT_SEED",
            resource_type="SYSTEM",
            resource_id="NETRA_SEED_01",
            payload={"event": "Deterministic synthetic seed dataset initialized", "actor": "ShadowByte"}
        )

        append_audit_event(
            session=session,
            actor_user_id=analyst_user.id,
            action="HYPOTHESIS_CREATED",
            resource_type="HYPOTHESIS",
            resource_id=hypothesis_id,
            payload={
                "subject": "ShadowByte",
                "object": "Vortex99",
                "calibrated_prob": attribution_res.calibrated_prob,
                "confidence_tier": attribution_res.confidence_tier
            }
        )

        session.commit()
        print("[+] PostgreSQL Seeding Succeeded.")

        print("[+] Rebuilding Neo4j Knowledge Graph...")
        proj_service = GraphProjectionService()
        graph_stats = proj_service.rebuild_graph_from_postgres(session)
        print(f"[+] Neo4j Graph Projection Complete: {graph_stats}")

    except Exception as e:
        session.rollback()
        print(f"[-] Error seeding database: {e}")
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
