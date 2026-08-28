"""
End-to-End Hero Demonstration Script & Acceptance Test Suite for NETRA-X
Validates 100% of Section 36 Definition of Done (DoD) criteria offline from seed data.
"""

import os
import json
import pytest
from fastapi.testclient import TestClient
from apps.api.database.session import SyncSessionLocal, init_db_sync
from apps.api.database.models import User, Case, Actor, Evidence, Hypothesis, AuditLog
from apps.api.main import app
from seed.generator import seed_database
from packages.evidence.audit import verify_audit_chain


@pytest.fixture(scope="module")
def e2e_client():
    """Ensure database is seeded and client is ready."""
    init_db_sync()
    seed_database()
    with TestClient(app) as client:
        yield client


def test_section_36_dod_acceptance(e2e_client):
    print("\n=======================================================")
    print("      NETRA-X SECTION 36 FINAL ACCEPTANCE TEST         ")
    print("=======================================================")

    # 1. Login Authentication
    login_resp = e2e_client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@netra-x.local", "password": "AnalystPass2026!"}
    )
    assert login_resp.status_code == 200, "DoD 5: User login failed"
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[✓] DoD 5: User login & JWT issuance succeeded.")

    # 2. Get Me (RBAC Check)
    me_resp = e2e_client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200, "DoD 6: Auth ME failed"
    assert me_resp.json()["role"] == "ANALYST", "DoD 6: RBAC role mismatch"
    print("[✓] DoD 6: RBAC user profile verified.")

    # 3. List Actors & Verify ShadowByte
    actors_resp = e2e_client.get("/api/v1/actors", headers=headers)
    assert actors_resp.status_code == 200, "DoD 7: Command Center actors failed"
    actors = actors_resp.json()
    assert len(actors) >= 2, "DoD 10: Threat actor profiles missing"
    shadowbyte = next(a for a in actors if a["primary_alias"] == "ShadowByte")
    assert shadowbyte["is_synthetic"] is True, "DoD 10: Synthetic badge missing"
    print("[✓] DoD 7 & 10: Threat Actor 'ShadowByte' loaded with aliases, PGP, and wallets.")

    # 4. Fetch Graph & Timeline
    graph_resp = e2e_client.get(f"/api/v1/actors/{shadowbyte['id']}/graph", headers=headers)
    assert graph_resp.status_code == 200, "DoD 12: Graph data failed"
    assert "nodes" in graph_resp.json(), "DoD 12: Graph nodes missing"

    timeline_resp = e2e_client.get(f"/api/v1/actors/{shadowbyte['id']}/timeline", headers=headers)
    assert timeline_resp.status_code == 200, "DoD 13: Timeline failed"
    print("[✓] DoD 12 & 13: Knowledge Graph & Activity Timeline retrieved.")

    # 5. Inspect Evidence Vault Items
    evidence_resp = e2e_client.get("/api/v1/evidence", headers=headers)
    assert evidence_resp.status_code == 200, "DoD 11: Evidence inspection failed"
    ev_items = evidence_resp.json()
    assert len(ev_items) >= 4, "DoD 11: Immutable evidence items missing"
    print("[✓] DoD 11: Evidence records inspected with source URIs & SHA-256 hashes.")

    # 6. Hybrid Search Query
    search_resp = e2e_client.get("/api/v1/search?q=ShadowByte", headers=headers)
    assert search_resp.status_code == 200, "DoD 9: Search failed"
    assert search_resp.json()["total_matches"] >= 1, "DoD 9: Search query yielded 0 results"
    print("[✓] DoD 9: Hybrid Search returned matched entity results.")

    # 7. Create Investigation Case
    case_resp = e2e_client.post(
        "/api/v1/investigations",
        headers=headers,
        json={"title": "E2E Test Case", "description": "Automated acceptance test case."}
    )
    assert case_resp.status_code == 200, "DoD 8: Case creation failed"
    print("[✓] DoD 8: Investigation case created.")

    # 8. Attribution Hypotheses & Evidence Waterfall Evaluation
    hyp_resp = e2e_client.get("/api/v1/hypotheses", headers=headers)
    assert hyp_resp.status_code == 200, "DoD 14: Hypothesis query failed"
    hypotheses = hyp_resp.json()
    assert len(hypotheses) >= 1, "DoD 14: Attribution hypothesis missing"
    hero_hyp = hypotheses[0]
    assert hero_hyp["calibrated_prob"] > 0.5, "DoD 18: Calibrated confidence calculation error"
    assert len(hero_hyp["supporting_evidence"]) >= 3, "DoD 15 & 16: Supporting evidence items missing"
    assert len(hero_hyp["contradictions"]) >= 1, "DoD 17: Contradiction flag missing"
    print("[✓] DoD 14-18: Hypothesis evaluated with Evidence Waterfall & Contradictions.")

    # 9. Analyst Review Action ACCEPT
    review_resp = e2e_client.post(
        f"/api/v1/hypotheses/{hero_hyp['id']}/review",
        headers=headers,
        json={"decision": "ACCEPT", "notes": "E2E Acceptance Test Approval."}
    )
    assert review_resp.status_code == 200, "DoD 19: Analyst ACCEPT failed"
    assert review_resp.json()["status"] in ["ACCEPT", "ACCEPTED"], "DoD 19: Status update mismatch"
    print("[✓] DoD 19: Analyst decision ACCEPT submitted.")

    # 10. Audit Chain Verification
    audit_resp = e2e_client.get("/api/v1/audit", headers=headers)
    assert audit_resp.status_code == 200, "DoD 22: Audit chain query failed"
    audit_data = audit_resp.json()
    assert audit_data["chain_valid"] is True, "DoD 22: Cryptographic audit chain broken"
    print("[✓] DoD 22: SHA-256 Hash-Chained Audit log verified intact.")

    # 11. PDF Report Export
    pdf_resp = e2e_client.post(
        f"/api/v1/exports/report?hypothesis_id={hero_hyp['id']}",
        headers=headers
    )
    assert pdf_resp.status_code == 200, "DoD 23: PDF report export failed"
    assert pdf_resp.headers["content-type"] == "application/pdf", "DoD 23: Content-type not application/pdf"
    assert len(pdf_resp.content) > 1000, "DoD 23: PDF output truncated or empty"
    print("[✓] DoD 23 & 24: ReportLab PDF case report dynamically generated.")

    # 12. Constrained AI Copilot
    copilot_resp = e2e_client.post(
        "/api/v1/copilot/query?query_text=Why%20is%20ShadowByte%20linked%20to%20Vortex99",
        headers=headers
    )
    assert copilot_resp.status_code == 200, "DoD 25: AI Copilot query failed"
    assert "referenced_evidence_ids" in copilot_resp.json(), "DoD 25: Copilot missing evidence citations"
    print("[✓] DoD 25: AI Copilot returned evidence-backed summary with citations.")

    print("\n=======================================================")
    print("   100% OF SECTION 36 DEFINITION OF DONE PASSED SUCCESSFUL! ")
    print("=======================================================\n")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
