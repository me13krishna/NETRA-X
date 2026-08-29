"""
test_synthetic.py — Unit tests for synthetic benchmark generator and Actor A, B, C scenarios.
"""

import pytest
from bench.synthetic.scenarios import (
    generate_actor_a_scenario,
    generate_actor_b_scenario,
    generate_actor_c_scenario,
    generate_short_text_abstention_scenario,
)
from bench.synthetic.generator import generate_benchmark_suite
from packages.attribution.decide import evaluate_attribution
from packages.common.types import AttributionDecision


def test_actor_a_high_confidence():
    """
    Actor A (nstar_7 / ShadowByte) must produce HIGH_CONFIDENCE_LINK (P >= 0.85).
    """
    case_a = generate_actor_a_scenario()
    result = evaluate_attribution(case_a.evidence_items)
    assert result.decision == AttributionDecision.HIGH_CONFIDENCE_LINK
    assert result.posterior_probability >= 0.85
    assert result.total_capped_llr > 10.0


def test_actor_b_coincidence_insufficient():
    """
    Actor B (coincidence_user) must produce INSUFFICIENT_EVIDENCE (P < 0.50).
    """
    case_b = generate_actor_b_scenario()
    result = evaluate_attribution(case_b.evidence_items)
    assert result.decision == AttributionDecision.INSUFFICIENT_EVIDENCE
    assert result.posterior_probability < 0.50


def test_actor_c_adversarial_clone_contradiction():
    """
    Actor C (clone_imposter) must produce CONTRADICTION_REJECTED due to temporal contradiction.
    """
    case_c = generate_actor_c_scenario()
    result = evaluate_attribution(case_c.evidence_items)
    assert result.decision == AttributionDecision.CONTRADICTION_REJECTED
    assert result.contradiction_penalty > 0.0


def test_benchmark_suite_generation():
    """
    Test generating benchmark dataset with multiple replications.
    """
    suite = generate_benchmark_suite(num_replications=5)
    assert len(suite) == 5 * 3 + 1  # 3 scenarios * 5 + 1 short text scenario
