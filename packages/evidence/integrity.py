"""
Referential integrity for the evidence ledger.

The ledger claims to be an append-only chain of custody, but nothing enforced
it. A hard-delete endpoint removed Evidence rows while the HypothesisEvidence
join rows that cited them stayed behind, so hypotheses kept scores computed
from rows that no longer existed. On the working database that had reached
36 of 69 cited evidence rows missing, across 13 of 14 hypotheses -- the
evidence waterfall, the screen whose entire job is answering "why do you
believe this", was rendering placeholders for most links.

Deletion is now retraction (see the DELETE endpoint), so the rot cannot
recur. This module reports what is already broken and repairs it, and the
check is cheap enough to run at startup.

A dangling citation is never silently dropped: dropping it would quietly
change a hypothesis's score to match whatever survived. It is reported, and
repair is an explicit call.
"""

from typing import Any, Dict, List

from sqlalchemy.orm import Session


def check(db: Session) -> Dict[str, Any]:
    """Report dangling references without changing anything."""
    from apps.api.database.models import Evidence, Hypothesis, HypothesisEvidence

    evidence_ids = {e.id for e in db.query(Evidence.id).all()}
    hypothesis_ids = {h.id for h in db.query(Hypothesis.id).all()}

    missing_evidence: List[str] = []
    missing_hypothesis: List[str] = []
    affected: Dict[str, int] = {}

    for he in db.query(HypothesisEvidence).all():
        if he.evidence_id not in evidence_ids:
            missing_evidence.append(he.id)
            affected[he.hypothesis_id] = affected.get(he.hypothesis_id, 0) + 1
        if he.hypothesis_id not in hypothesis_ids:
            missing_hypothesis.append(he.id)

    return {
        "ok": not missing_evidence and not missing_hypothesis,
        "dangling_evidence_citations": len(missing_evidence),
        "orphaned_join_rows": len(missing_hypothesis),
        "affected_hypotheses": len(affected),
        "total_hypotheses": len(hypothesis_ids),
        "_missing_evidence_ids": missing_evidence,
        "_missing_hypothesis_ids": missing_hypothesis,
    }


def repair(db: Session) -> Dict[str, Any]:
    """Remove join rows whose evidence or hypothesis no longer exists.

    Only the dangling join rows go. Evidence and hypotheses are never touched:
    the point of the exercise is that ledger rows do not disappear.
    """
    from apps.api.database.models import HypothesisEvidence

    report = check(db)
    doomed = set(report["_missing_evidence_ids"]) | set(report["_missing_hypothesis_ids"])
    if not doomed:
        return {"repaired": 0, **{k: v for k, v in report.items() if not k.startswith("_")}}

    removed = 0
    for he in db.query(HypothesisEvidence).filter(HypothesisEvidence.id.in_(doomed)).all():
        db.delete(he)
        removed += 1
    db.commit()

    after = check(db)
    return {"repaired": removed, **{k: v for k, v in after.items() if not k.startswith("_")}}


def rescore_hypothesis(db: Session, hypothesis_id: str) -> Dict[str, Any]:
    """Recompute a hypothesis from the evidence that still counts.

    Retracting evidence has to move the score. Otherwise the headline keeps
    asserting a confidence derived from a claim that has since been withdrawn,
    and the waterfall shows rows that no longer sum to the number above them --
    which is the exact inconsistency the hard-delete endpoint used to create.

    The stored per-item contributions are reused rather than re-running fusion:
    they are the engine's own post-discount, post-cap output, so summing the
    surviving ones is the same arithmetic the engine performed.
    """
    from apps.api.database.models import Hypothesis
    from packages.attribution.calibration import sigmoid_llr_to_prob

    h = db.query(Hypothesis).filter_by(id=hypothesis_id).first()
    if h is None:
        return {}

    active = active_evidence_items(db, hypothesis_id)
    new_llr = round(sum(i.contribution for i in active), 4)
    new_prob = round(sigmoid_llr_to_prob(new_llr), 4)

    before = {"raw_log_lr": h.raw_log_lr, "calibrated_prob": h.calibrated_prob}
    h.raw_log_lr = new_llr
    h.calibrated_prob = new_prob

    # A hypothesis an analyst already ruled on does not silently revert to the
    # queue; the decision stands until a human revisits it.
    if h.status == "PROPOSED" and new_llr < 2.0:
        h.status = "INSUFFICIENT"

    db.commit()
    return {
        "hypothesis_id": hypothesis_id,
        "before": before,
        "after": {"raw_log_lr": new_llr, "calibrated_prob": new_prob},
        "active_items": len(active),
        "status": h.status,
    }


def active_evidence_items(db: Session, hypothesis_id: str) -> List[Any]:
    """Join rows for a hypothesis whose evidence exists and is not retracted.

    Retracted evidence stays visible in the vault but must stop contributing to
    a score -- that is the difference between withdrawing a claim and pretending
    it was never made.
    """
    from apps.api.database.models import Evidence, HypothesisEvidence

    rows = db.query(HypothesisEvidence).filter_by(hypothesis_id=hypothesis_id).all()
    out = []
    for he in rows:
        ev = db.query(Evidence).filter_by(id=he.evidence_id).first()
        if ev is None or ev.retracted_at is not None:
            continue
        out.append(he)
    return out
