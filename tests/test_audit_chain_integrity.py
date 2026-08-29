"""
Audit Chain Tamper-Detection Suite

Asserts that editing or deleting history is *detected*. A tamper-evidence
claim is worth nothing without tests that actually mutate stored rows and
check the verifier notices -- the previous implementation passed its own
integrity test while being blind to every field edit, because verification
never recomputed anything from the row.

Runs against an isolated in-memory database. Corrupting the shared netrax.db
would break every other test in the suite.
"""

import json

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from apps.api.database.models import AuditLog, Base
from packages.evidence.audit import (
    GENESIS_HASH,
    append_audit_event,
    chain_head,
    compute_payload_hash,
    verify_audit_chain,
)


@pytest.fixture()
def session():
    """Fresh in-memory schema per test.

    One shared connection: SQLite drops an in-memory database when its last
    connection closes, so a pooled engine would lose the schema between
    statements.
    """
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    s = factory()
    try:
        yield s
    finally:
        s.close()
        engine.dispose()


def _seed(session, n=5):
    for i in range(n):
        append_audit_event(
            session,
            actor_user_id=f"user-{i % 2}",
            action="EVIDENCE_CREATED",
            resource_type="EVIDENCE",
            resource_id=f"evidence-{i}",
            payload={"index": i, "note": f"entry {i}"},
        )
    session.commit()


def test_first_entry_is_genesis(session):
    append_audit_event(
        session, actor_user_id="u1", action="USER_LOGIN",
        resource_type="USER", resource_id="u1", payload={},
    )
    session.commit()

    entry = session.execute(select(AuditLog)).scalar_one()
    assert entry.seq == 0
    assert entry.prev_hash == GENESIS_HASH
    assert len(entry.entry_hash) == 64


def test_each_entry_chains_to_its_predecessor(session):
    _seed(session, 5)
    rows = session.execute(select(AuditLog).order_by(AuditLog.seq)).scalars().all()

    assert [r.seq for r in rows] == [0, 1, 2, 3, 4]
    for prev, cur in zip(rows, rows[1:]):
        assert cur.prev_hash == prev.entry_hash


def test_clean_chain_verifies(session):
    _seed(session, 8)
    valid, count, err = verify_audit_chain(session)

    assert valid is True
    assert count == 8
    assert err is None


def test_empty_chain_is_valid(session):
    valid, count, err = verify_audit_chain(session)
    assert (valid, count, err) == (True, 0, None)


def test_payload_is_retained_and_readable(session):
    """An audit log that discards its payload cannot be audited."""
    append_audit_event(
        session, actor_user_id="u1", action="HYPOTHESIS_REVIEWED",
        resource_type="HYPOTHESIS", resource_id="h1",
        payload={"decision": "ACCEPT", "notes": "corroborated across families"},
    )
    session.commit()

    entry = session.execute(select(AuditLog)).scalar_one()
    assert json.loads(entry.payload)["decision"] == "ACCEPT"


def test_edited_payload_is_detected(session):
    _seed(session, 5)
    row = session.execute(select(AuditLog).where(AuditLog.seq == 2)).scalar_one()
    row.payload = json.dumps({"index": 2, "note": "tampered"})
    session.commit()

    valid, _, err = verify_audit_chain(session)
    assert valid is False
    assert "payload" in err


def test_edited_payload_with_recomputed_hash_is_still_detected(session):
    """A careful attacker also updates payload_hash. entry_hash still breaks."""
    _seed(session, 5)
    row = session.execute(select(AuditLog).where(AuditLog.seq == 2)).scalar_one()
    tampered = {"index": 2, "note": "tampered"}
    row.payload = json.dumps(tampered)
    row.payload_hash = compute_payload_hash(tampered)
    session.commit()

    valid, _, err = verify_audit_chain(session)
    assert valid is False
    assert "entry_hash" in err


def test_edited_actor_is_detected(session):
    """Reassigning who performed an action -- the previous implementation
    could not see this at all."""
    _seed(session, 4)
    row = session.execute(select(AuditLog).where(AuditLog.seq == 1)).scalar_one()
    row.actor_user_id = "someone-else"
    session.commit()

    valid, _, err = verify_audit_chain(session)
    assert valid is False
    assert "entry_hash" in err


def test_edited_action_is_detected(session):
    _seed(session, 4)
    row = session.execute(select(AuditLog).where(AuditLog.seq == 2)).scalar_one()
    row.action = "HYPOTHESIS_REVIEWED"
    session.commit()

    valid, _, err = verify_audit_chain(session)
    assert valid is False


def test_edited_timestamp_is_detected(session):
    """Backdating an action. Undetectable before -- created_at was not hashed."""
    from datetime import timedelta

    _seed(session, 4)
    row = session.execute(select(AuditLog).where(AuditLog.seq == 2)).scalar_one()
    row.created_at = row.created_at - timedelta(days=30)
    session.commit()

    valid, _, err = verify_audit_chain(session)
    assert valid is False


def test_deleted_entry_is_detected_as_a_gap(session):
    _seed(session, 6)
    row = session.execute(select(AuditLog).where(AuditLog.seq == 3)).scalar_one()
    session.delete(row)
    session.commit()

    valid, _, err = verify_audit_chain(session)
    assert valid is False
    assert "seq" in err


def test_tail_truncation_needs_an_external_anchor(session):
    """A limitation, asserted rather than hidden.

    Deleting from the end leaves a shorter but internally consistent chain, so
    verify_audit_chain() cannot catch it. Comparing against a previously
    published chain_head() can. This is why chain_head() exists.
    """
    _seed(session, 6)
    published_head = chain_head(session)

    for seq in (5, 4):
        row = session.execute(select(AuditLog).where(AuditLog.seq == seq)).scalar_one()
        session.delete(row)
    session.commit()

    valid, _, _ = verify_audit_chain(session)
    assert valid is True                      # chain alone still verifies
    assert chain_head(session) != published_head   # the anchor catches it


def test_payload_hash_is_key_order_independent(session):
    """Canonical JSON. Without stable ordering the same payload hashes
    differently between runs and verification fails on clean data."""
    assert compute_payload_hash({"a": 1, "b": 2}) == compute_payload_hash({"b": 2, "a": 1})
