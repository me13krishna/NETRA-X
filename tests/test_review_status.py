"""The review decision must leave a status the UI actually filters on.

The endpoint assigned `req.decision.value` -- the verb ACCEPT -- directly into
Hypothesis.status, while the seed, the status filter tabs and the badge colours
all use the past-tense ACCEPTED. Clicking ACCEPT therefore moved a row into a
state no filter matched: it vanished from the ACCEPTED tab and rendered with
fallback styling, which is exactly the kind of break that only shows up while
recording a demo.
"""

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app, DECISION_TO_STATUS
from apps.api.database.session import SyncSessionLocal
from apps.api.database.models import Hypothesis

# The states the frontend filter tabs and badge styling switch on.
UI_STATUSES = {"PROPOSED", "ACCEPTED", "REJECTED", "INSUFFICIENT"}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth(client):
    r = client.post("/api/v1/auth/login", json={
        "email": "analyst@netra-x.local", "password": "AnalystPass2026!"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_every_decision_maps_to_a_status_the_ui_renders():
    assert set(DECISION_TO_STATUS.values()) <= UI_STATUSES


def test_accepting_leaves_status_accepted_not_accept(client, auth):
    db = SyncSessionLocal()
    h = db.query(Hypothesis).filter_by(status="PROPOSED").first()
    if h is None:
        db.close()
        pytest.skip("no PROPOSED hypothesis to review")
    hid, prev = h.id, h.status
    db.close()

    r = client.post(f"/api/v1/hypotheses/{hid}/review",
                    json={"decision": "ACCEPT", "notes": "regression check"},
                    headers=auth)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ACCEPTED"

    db = SyncSessionLocal()
    row = db.query(Hypothesis).filter_by(id=hid).first()
    assert row.status == "ACCEPTED"
    row.status = prev          # leave the queue as we found it
    db.commit()
    db.close()


def test_no_row_carries_a_bare_verb_as_its_status():
    db = SyncSessionLocal()
    bad = [h.id for h in db.query(Hypothesis).all() if h.status not in UI_STATUSES]
    db.close()
    assert not bad, f"hypotheses with a status no filter matches: {bad}"
