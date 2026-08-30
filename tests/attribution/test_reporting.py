"""
test_reporting.py — Unit tests for Automated Evidence Waterfall & Attribution Report Formatting module.
"""

import pytest
from bench.synthetic.scenarios import generate_actor_a_scenario, generate_actor_c_scenario
from packages.attribution.decide import evaluate_attribution
from packages.attribution.reporting import (
    AttributionReportFormatter,
    build_waterfall_breakdown,
    format_ascii_waterfall,
    format_markdown_report,
)


def test_build_waterfall_breakdown_positive_case():
    """
    Test waterfall breakdown accounting for Actor A (true match across multiple families).
    """
    case_a = generate_actor_a_scenario()
    res = evaluate_attribution(case_a.evidence_items)
    breakdown = build_waterfall_breakdown(res)

    assert breakdown["base_prior_llr"] == 0.0
    assert len(breakdown["family_contributions"]) > 0
    assert breakdown["total_positive_capped_llr"] > 10.0
    assert breakdown["contradiction_penalty"] == 0.0
    assert breakdown["final_net_llr"] == res.final_llr
    assert breakdown["decision"] == "HIGH_CONFIDENCE_LINK"


def test_build_waterfall_breakdown_contradiction_case():
    """
    Test waterfall breakdown accounting for Actor C (imposter with contradiction penalty).
    """
    case_c = generate_actor_c_scenario()
    res = evaluate_attribution(case_c.evidence_items)
    breakdown = build_waterfall_breakdown(res)

    assert breakdown["contradiction_penalty"] == 15.0
    assert len(breakdown["contradictions"]) == 1
    assert breakdown["contradictions"][0]["feature_name"] == "temporal_impossible_overlap"
    assert breakdown["decision"] == "CONTRADICTION_REJECTED"


def test_format_ascii_waterfall():
    """
    Test format_ascii_waterfall CLI diagram string rendering.
    """
    case_a = generate_actor_a_scenario()
    res = evaluate_attribution(case_a.evidence_items)
    ascii_str = format_ascii_waterfall(res)

    assert "NETRA-X EVIDENCE WATERFALL LLR CONTRIBUTION DIAGRAM" in ascii_str
    assert "[Base Prior H1]" in ascii_str
    assert "P(H1|E) =" in ascii_str


def test_format_markdown_report():
    """
    Test format_markdown_report GitHub Markdown output.
    """
    case_a = generate_actor_a_scenario()
    res = evaluate_attribution(case_a.evidence_items)
    md_report = format_markdown_report("nstar_7", "ShadowByte", res)

    assert "# NETRA-X Attribution Report — nstar_7 &harr; ShadowByte" in md_report
    assert "## Executive Summary" in md_report
    assert "## Evidence Waterfall Family Breakdown" in md_report
    assert "`HIGH_CONFIDENCE_LINK`" in md_report


def test_export_summary_json():
    """
    Test export_summary_json structured dictionary output.
    """
    case_a = generate_actor_a_scenario()
    res = evaluate_attribution(case_a.evidence_items)
    summary_json = AttributionReportFormatter.export_summary_json("nstar_7", "ShadowByte", res)

    assert summary_json["target_actor"] == "nstar_7"
    assert summary_json["candidate_actor"] == "ShadowByte"
    assert summary_json["decision"] == "HIGH_CONFIDENCE_LINK"
    assert "waterfall" in summary_json
