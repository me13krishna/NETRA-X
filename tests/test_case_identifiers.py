"""Attaching an identifier to a case must persist it.

The Cases view raised an "identifier added" toast and called no API at all:
the value was never sent, never stored, and gone on the next render. A demo
that shows a confirmation for work the system did not do is worse than a
missing feature, because nothing signals the gap.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.database.session import SyncSessionLocal
from apps.api.database.models import Case, CaseIdentifier


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth(client):
    r = client.post("/api/v1/auth/login", json={
        "email": "analyst@netra-x.local", "password": "AnalystPass2026!"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def case_id():
    db = SyncSessionLocal()
    c = db.query(Case).first()
    if c is None:
        db.close()
        pytest.skip("no case in the ledger")
    cid = c.id
    db.close()
    return cid


def test_identifier_is_persisted_and_readable(client, auth, case_id):
    value = "bc1q" + uuid.uuid4().hex[:20]
    r = client.post(f"/api/v1/investigations/{case_id}/identifiers",
                    json={"id_type": "wallet", "value": value}, headers=auth)
    assert r.status_code == 201, r.text

    # The failure being guarded: a success response with nothing written.
    db = SyncSessionLocal()
    row = db.query(CaseIdentifier).filter_by(case_id=case_id, value=value).first()
    db.close()
    assert row is not None, "endpoint reported success but stored nothing"

    listed = client.get(f"/api/v1/investigations/{case_id}/identifiers",
                        headers=auth).json()
    assert value in [i["value"] for i in listed]


def test_duplicate_identifier_is_rejected(client, auth, case_id):
    value = "handle_" + uuid.uuid4().hex[:10]
    body = {"id_type": "handle", "value": value}
    assert client.post(f"/api/v1/investigations/{case_id}/identifiers",
                       json=body, headers=auth).status_code == 201
    assert client.post(f"/api/v1/investigations/{case_id}/identifiers",
                       json=body, headers=auth).status_code == 409


def test_unknown_case_is_rejected(client, auth):
    r = client.post("/api/v1/investigations/not-a-real-case/identifiers",
                    json={"id_type": "handle", "value": "x"}, headers=auth)
    assert r.status_code == 404


def test_identifier_requires_authentication(client, case_id):
    r = client.post(f"/api/v1/investigations/{case_id}/identifiers",
                    json={"id_type": "handle", "value": "x"})
    assert r.status_code in (401, 403)


def test_adding_an_identifier_is_audited(client, auth, case_id):
    from apps.api.database.models import AuditLog

    value = "pgp_" + uuid.uuid4().hex[:10]
    client.post(f"/api/v1/investigations/{case_id}/identifiers",
                json={"id_type": "pgp", "value": value}, headers=auth)

    db = SyncSessionLocal()
    hit = (db.query(AuditLog)
           .filter_by(action="CASE_IDENTIFIER_ADDED", resource_id=case_id)
           .order_by(AuditLog.seq.desc()).first())
    db.close()
    assert hit is not None, "identifier was added without an audit entry"
