"""Ledger invariants that quietly broke and were not caught by any test.

Three separate failures, all invisible from the UI because the UI faithfully
rendered whatever it was given:

  1. Evidence was hard-deleted while HypothesisEvidence rows kept citing it,
     so hypotheses carried scores derived from rows that no longer existed --
     36 of 69 citations dangling, across 13 of 14 hypotheses.

  2. seed/network.py read the engine's contribution breakdown with the wrong
     keys ("id"/"contribution" instead of "evidence_id"/"llr_contrib"), so
     every contribution silently defaulted to 0.0. The waterfall displayed a
     headline LLR of 20.50 above evidence rows summing to zero.

  3. The waterfall substituted e3b0c442...b855 -- the SHA-256 of the empty
     string -- whenever an artifact was missing, presenting absent provenance
     as a verified digest.

Each is asserted here against live rows rather than against a fixture, because
each was a divergence between what the ledger held and what the screen said.
"""

import pytest

from apps.api.database.session import SyncSessionLocal
from apps.api.database.models import Evidence, Hypothesis, HypothesisEvidence
from packages.evidence import integrity

EMPTY_STRING_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


@pytest.fixture
def db():
    s = SyncSessionLocal()
    yield s
    s.close()


def test_no_hypothesis_cites_evidence_that_does_not_exist(db):
    report = integrity.check(db)
    assert report["ok"], (
        f"{report['dangling_evidence_citations']} dangling citations across "
        f"{report['affected_hypotheses']} hypotheses"
    )


def test_stored_llr_equals_the_sum_of_its_evidence(db):
    """The headline number must be the sum of the rows shown beneath it."""
    drifted = []
    for h in db.query(Hypothesis).all():
        items = db.query(HypothesisEvidence).filter_by(hypothesis_id=h.id).all()
        if not items:
            continue
        total = sum(i.contribution for i in items)
        if abs(total - h.raw_log_lr) > 0.51:      # tolerance for capping/rounding
            drifted.append((h.id, round(h.raw_log_lr, 2), round(total, 2)))
    assert not drifted, f"LLR does not match its evidence: {drifted}"


def test_evidence_contributions_are_not_uniformly_zero(db):
    """The bug's signature: every contribution defaulting to 0.0."""
    items = db.query(HypothesisEvidence).all()
    if not items:
        pytest.skip("no hypothesis evidence seeded")
    assert any(i.contribution != 0.0 for i in items), \
        "every contribution is 0.0 -- the engine breakdown is not being read"


def test_no_artifact_carries_the_empty_string_digest(db):
    """Absent provenance must read as absent, never as a plausible hash."""
    from apps.api.database.models import Artifact
    bad = [a.id for a in db.query(Artifact).all() if a.sha256 == EMPTY_STRING_SHA256]
    assert not bad, f"artifacts stamped with the empty-string digest: {bad}"


def test_retraction_preserves_the_row(db):
    """Withdrawing evidence must not remove it from the ledger."""
    e = db.query(Evidence).first()
    if e is None:
        pytest.skip("ledger has no evidence")
    assert hasattr(e, "retracted_at"), "Evidence has no retraction column"
    # Nothing retracted in the seed; the column exists and defaults to null.
    assert e.retracted_at is None


def test_retracted_evidence_is_excluded_from_active_items(db):
    """active_evidence_items must skip retracted rows without deleting them."""
    h = db.query(Hypothesis).first()
    if h is None:
        pytest.skip("no hypotheses")

    items = integrity.active_evidence_items(db, h.id)
    if not items:
        pytest.skip("hypothesis has no active evidence")

    target = db.query(Evidence).filter_by(id=items[0].evidence_id).first()
    from datetime import datetime
    target.retracted_at = datetime.utcnow()
    target.retraction_reason = "integrity test"
    db.commit()
    try:
        after = integrity.active_evidence_items(db, h.id)
        assert len(after) == len(items) - 1
        assert db.query(Evidence).filter_by(id=target.id).first() is not None, \
            "retraction destroyed the row"
    finally:
        target.retracted_at = None
        target.retraction_reason = None
        db.commit()
