"""Tests for the evidence ingestion path.

The ledger previously had no write path: evidence existed only because a seed
script put it there. These cover the properties that make ingested evidence
usable as evidence -- an unbroken provenance chain, a stated lawful basis, and
idempotency on the artifact digest.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.database.session import SyncSessionLocal
from apps.api.database.models import Source, Observation, Artifact, Evidence, AuditLog
from packages.evidence.audit import verify_audit_chain


# Ingest is idempotent on the SHA-256 of the content, and the suite runs against
# a persistent database. A fixed fixture string would therefore be a duplicate of
# itself on the second run of the suite, so each run gets its own nonce.
NONCE = uuid.uuid4().hex

POST = (
    "Vendor @nightowl99 back after the exit. PGP "
    "9F2B7C1D4E6A8035B1C2D3E4F5061728394A5B6C. "
    "BTC bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh. "
    "Mirror abcdefghijklmnopqrstuvwxyz234567abcdefghijklmnopqrstuvwx.onion. "
    "Contact relay@protonmail.com."
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth(client):
    r = client.post("/api/v1/auth/login", json={
        "email": "analyst@netra-x.local", "password": "AnalystPass2026!"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _ingest(client, auth, content, name="pytest-forum"):
    return client.post("/api/v1/evidence", headers=auth, json={
        "raw_content": content,
        "source_name": name,
        "source_type": "FORUM_CRAWL",
        "lawful_basis": "passive_osint",
        "source_uri": "netrax://test/forum",
    })


def test_ingest_extracts_and_returns_evidence(client, auth):
    r = _ingest(client, auth, POST + f" nonce-{NONCE}-A")
    assert r.status_code == 201, r.text
    body = r.json()

    assert body["duplicate"] is False
    assert body["lawful_basis"] == "passive_osint"
    assert len(body["artifact_sha256"]) == 64
    assert body["extracted_count"] >= 5

    kinds = {e["kind"] for e in body["evidence"]}
    assert {"PGP_FINGERPRINT", "BTC_ADDRESS", "ONION_SERVICE", "EMAIL", "HANDLE"} <= kinds


def test_provenance_chain_is_unbroken(client, auth):
    """Every Evidence row must trace back to the bytes it came from."""
    r = _ingest(client, auth, POST + f" nonce-{NONCE}-B")
    body = r.json()

    s = SyncSessionLocal()
    try:
        obs = s.query(Observation).filter_by(id=body["observation_id"]).one()
        artifact = s.query(Artifact).filter_by(sha256=body["artifact_sha256"]).one()
        source = s.query(Source).filter_by(id=body["source_id"]).one()

        # observation -> source -> lawful basis
        assert obs.source_id == source.id
        assert source.lawful_basis == "passive_osint"
        # observation -> artifact bytes
        assert obs.content_hash == artifact.sha256
        # evidence -> artifact
        ev = s.query(Evidence).filter_by(artifact_id=artifact.id).all()
        assert len(ev) == body["extracted_count"]
        assert all(e.dependence_group for e in ev)
    finally:
        s.close()


def test_reposting_identical_content_does_not_duplicate(client, auth):
    content = POST + f" nonce-{NONCE}-C"
    first = _ingest(client, auth, content).json()
    second = _ingest(client, auth, content).json()

    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert second["artifact_sha256"] == first["artifact_sha256"]
    assert second["extracted_count"] == 0

    s = SyncSessionLocal()
    try:
        n = s.query(Artifact).filter_by(sha256=first["artifact_sha256"]).count()
        assert n == 1
    finally:
        s.close()


def test_ingest_appends_to_the_audit_chain_and_chain_stays_valid(client, auth):
    s = SyncSessionLocal()
    try:
        before = s.query(AuditLog).count()
    finally:
        s.close()

    _ingest(client, auth, POST + f" nonce-{NONCE}-D")

    s = SyncSessionLocal()
    try:
        assert s.query(AuditLog).count() == before + 1
        entry = s.query(AuditLog).order_by(AuditLog.seq.desc()).first()
        assert entry.action == "EVIDENCE_INGESTED"
        valid, _, err = verify_audit_chain(s)
        assert valid is True, err
    finally:
        s.close()


def test_monero_is_recorded_but_flagged_for_abstention(client, auth):
    xmr = "4" + "B" * 94
    r = _ingest(client, auth, f"XMR only {xmr} nonce-{NONCE}-E")
    body = r.json()
    assert body["xmr_abstain"] is True
    xmr_rows = [e for e in body["evidence"] if e["kind"] == "XMR_ADDRESS"]
    assert xmr_rows and xmr_rows[0]["confidence"] <= 0.5


def test_lawful_basis_is_required_and_closed(client, auth):
    r = client.post("/api/v1/evidence", headers=auth, json={
        "raw_content": "anything", "source_name": "x", "lawful_basis": "because_i_felt_like_it"})
    assert r.status_code == 422


def test_ingest_requires_authentication(client):
    r = client.post("/api/v1/evidence", json={
        "raw_content": "anything", "source_name": "x"})
    assert r.status_code in (401, 403)
