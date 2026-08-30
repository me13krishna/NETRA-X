"""
test_fusion.py — Unit tests for Bayesian Log-Likelihood Ratio evidence fusion engine & waterfall contributions.
"""

import math
import pytest
from packages.common.types import (
    EvidenceItem,
    EvidenceFamily,
    FAMILY_CAPS,
    AttributionDecision,
)
from packages.attribution.fusion import LLRFusionEngine
from packages.attribution.decide import evaluate_attribution, compute_attribution
from packages.attribution.calibration import sigmoid_llr_to_prob


def test_effective_llr_calculation():
    """
    Test basic LLR calculation and multiplier scaling.
    """
    item = EvidenceItem(
        id="item1",
        feature_name="test_feat",
        family=EvidenceFamily.EXACT_IDENTITY,
        dependence_group="grp1",
        m_i=0.99,
        u_i=0.01,
        source_reliability=1.0,
        credibility_multiplier=1.0,
    )
    expected_llr = math.log(0.99 / 0.01)  # ln(99) ~ 4.595
    assert math.isclose(item.get_effective_llr(), expected_llr, rel_tol=1e-3)

    # Test with 50% credibility scaling
    item.credibility_multiplier = 0.5
    assert math.isclose(item.get_effective_llr(), expected_llr * 0.5, rel_tol=1e-3)


def test_dependence_group_discounting():
    """
    Test dependence discounting parameter lambda = 0.25 across co-dependent items.
    Formula: max(LLR) + 0.25 * sum(remaining LLRs)
    """
    engine = LLRFusionEngine(lambda_discount=0.25)
    
    item1 = EvidenceItem(id="1", feature_name="f1", family=EvidenceFamily.FINANCIAL, dependence_group="wallet", llr=4.0)
    item2 = EvidenceItem(id="2", feature_name="f2", family=EvidenceFamily.FINANCIAL, dependence_group="wallet", llr=2.0)
    item3 = EvidenceItem(id="3", feature_name="f3", family=EvidenceFamily.FINANCIAL, dependence_group="wallet", llr=1.0)

    final_llr, family_breakdown, _, _, contributions, _, _ = engine.fuse_evidence([item1, item2, item3])
    
    # Expected total uncapped: 4.0 + 0.25 * 2.0 + 0.25 * 1.0 = 4.75
    # FINANCIAL cap is 7.5, so uncapped 4.75 is under cap.
    assert math.isclose(family_breakdown[EvidenceFamily.FINANCIAL.value], 4.75, rel_tol=1e-3)

    # Verify per-item contribution flags
    contrib_map = {c["evidence_id"]: c for c in contributions}
    assert contrib_map["1"]["is_discounted"] is False
    assert math.isclose(contrib_map["1"]["llr_contrib"], 4.0, rel_tol=1e-3)
    assert contrib_map["2"]["is_discounted"] is True
    assert math.isclose(contrib_map["2"]["llr_contrib"], 0.5, rel_tol=1e-3)
    assert contrib_map["3"]["is_discounted"] is True
    assert math.isclose(contrib_map["3"]["llr_contrib"], 0.25, rel_tol=1e-3)


def test_waterfall_contribution_mathematical_identity():
    """
    Test that sum(llr_contrib) across non-contradictions minus sum(W_c) EXACTLY equals final_llr.
    Guarantees Evidence Waterfall consistency for frontend bar chart!
    """
    items = [
        # Family EXACT_IDENTITY (Cap 10.0) -> Uncapped 15.0 -> Capped to 10.0 (Scale = 10/15 = 2/3)
        EvidenceItem(id="pgp1", feature_name="pgp1", family=EvidenceFamily.EXACT_IDENTITY, dependence_group="g1", llr=9.0),
        EvidenceItem(id="pgp2", feature_name="pgp2", family=EvidenceFamily.EXACT_IDENTITY, dependence_group="g2", llr=6.0),
        # Family FINANCIAL (Cap 7.5) -> Uncapped 4.0 -> No cap scaling
        EvidenceItem(id="btc1", feature_name="btc1", family=EvidenceFamily.FINANCIAL, dependence_group="g3", llr=4.0),
        # Contradiction
        EvidenceItem(id="c1", feature_name="contra1", family=EvidenceFamily.TEMPORAL, dependence_group="cg", is_contradiction=True, contradiction_weight=5.0),
    ]

    engine = LLRFusionEngine()
    final_llr, family_scores, total_penalty, _, contributions, ind_count, fams_pres = engine.fuse_evidence(items)

    positive_contribs = sum(c["llr_contrib"] for c in contributions if not c["is_contradiction"])
    negative_penalties = sum(abs(c["llr_contrib"]) for c in contributions if c["is_contradiction"])

    assert math.isclose(positive_contribs, sum(family_scores.values()), rel_tol=1e-4)
    assert math.isclose(negative_penalties, total_penalty, rel_tol=1e-4)
    assert math.isclose(positive_contribs - negative_penalties, final_llr, rel_tol=1e-4)
    assert ind_count == 2
    assert sorted(fams_pres) == ["EXACT_IDENTITY", "FINANCIAL"]


def test_frozen_compute_attribution_api_contract():
    """
    Test compute_attribution function accepting raw Python dictionaries for Vivek's integration.
    """
    raw_dict_rows = [
        {
            "id": "ev_pgp",
            "feature_name": "pgp_fingerprint_exact",  # Prior populated from mu_table
        },
        {
            "id": "ev_custom",
            "family": "INFRASTRUCTURE",
            "dependence_group": "web_server",
            "llr": 4.5,
        },
    ]

    out = compute_attribution(raw_dict_rows)

    assert "raw_llr" in out
    assert "calibrated_prob" in out
    assert "decision" in out
    assert "contributions" in out
    assert len(out["contributions"]) == 2
    assert out["independent_family_count"] == 2
    assert "EXACT_IDENTITY" in out["families_present"]
    assert "INFRASTRUCTURE" in out["families_present"]


def test_edge_case_empty_evidence():
    """
    Test attribution engine behavior with empty evidence list.
    """
    out = compute_attribution([])
    assert out["final_llr"] == 0.0
    assert out["decision"] == AttributionDecision.INSUFFICIENT_EVIDENCE.value
    assert out["independent_family_count"] == 0
    assert len(out["contributions"]) == 0


def test_edge_case_pure_contradiction():
    """
    Test attribution engine with only contradiction items.
    """
    raw_dict_rows = [
        {
            "id": "c1",
            "feature_name": "temporal_impossible_overlap",
            "is_contradiction": True,
            "contradiction_weight": 20.0,
        }
    ]
    out = compute_attribution(raw_dict_rows)
    assert out["contradiction_penalty"] == 20.0
    assert out["final_llr"] == -20.0
    assert out["decision"] == AttributionDecision.CONTRADICTION_REJECTED.value


def test_candidate_generator_temporal_overlap_score():
    """
    Test CandidateGenerator.temporal_overlap_score with valid, invalid, overlapping, and distant timestamps.
    """
    from packages.attribution.candidate_gen import CandidateGenerator

    # Case 1: Empty / invalid inputs
    res_empty = CandidateGenerator.temporal_overlap_score([], [])
    assert res_empty["overlap_detected"] is False
    assert res_empty["min_proximity_minutes"] is None
    assert res_empty["contradiction"] is False
    assert res_empty["num_events_a"] == 0

    # Case 2: Overlapping within 60 minutes
    events_a = ["2026-08-20T10:00:00Z", "2026-08-20T12:00:00Z"]
    events_b = ["2026-08-20T10:15:00Z"]  # 15 min gap
    res_overlap = CandidateGenerator.temporal_overlap_score(events_a, events_b)
    assert res_overlap["overlap_detected"] is True
    assert res_overlap["min_proximity_minutes"] == 15.0
    assert res_overlap["contradiction"] is False
    assert res_overlap["num_events_a"] == 2
    assert res_overlap["num_events_b"] == 1

    # Case 3: Extreme gap > 30 days -> contradiction
    events_distant = ["2026-10-01T10:00:00Z"]
    res_contradiction = CandidateGenerator.temporal_overlap_score(events_a, events_distant)
    assert res_contradiction["overlap_detected"] is False
    assert res_contradiction["contradiction"] is True
    assert res_contradiction["min_proximity_minutes"] > 40000

