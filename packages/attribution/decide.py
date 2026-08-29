"""
decide.py — Candidate decision logic and unified API entry point for NETRA-X Attribution Engine.
"""

from typing import List, Dict, Any, Union, Optional
from packages.common.types import (
    EvidenceItem,
    EvidenceFamily,
    AttributionDecision,
    AttributionResult,
)
from packages.attribution.fusion import LLRFusionEngine
from packages.attribution.calibration import IsotonicCalibrator


def parse_evidence_row(row: Union[Dict[str, Any], EvidenceItem], engine: LLRFusionEngine) -> EvidenceItem:
    """
    Parses a dictionary row or EvidenceItem object into a validated EvidenceItem instance.
    """
    if isinstance(row, EvidenceItem):
        return row

    if not isinstance(row, dict):
        raise ValueError(f"Invalid evidence row type: {type(row)}. Expected dict or EvidenceItem.")

    item_id = str(row.get("id", "ev_unknown"))
    feature_name = str(row.get("feature_name", ""))

    # If feature_name is in mu_table, use create_item_from_prior helper
    if feature_name and (
        feature_name in engine.mu_table.get("features", {})
        or feature_name in engine.mu_table.get("contradictions", {})
    ):
        item = engine.create_item_from_prior(
            item_id=item_id,
            feature_name=feature_name,
            dependence_group=row.get("dependence_group"),
            source_reliability=float(row.get("source_reliability", 1.0)),
            credibility_multiplier=float(row.get("credibility_multiplier", 1.0)),
            abstain=bool(row.get("abstain", False)),
            metadata=row.get("metadata", {}),
        )
        # Override fields if explicitly provided in row
        if "llr" in row and row["llr"] is not None:
            item.llr = float(row["llr"])
        if "is_contradiction" in row:
            item.is_contradiction = bool(row["is_contradiction"])
        if "contradiction_weight" in row:
            item.contradiction_weight = float(row["contradiction_weight"])
        return item

    # Direct dictionary parsing fallback
    fam_str = str(row.get("family", "CONTENT_NLP"))
    try:
        family = EvidenceFamily(fam_str)
    except ValueError:
        family = EvidenceFamily.CONTENT_NLP

    return EvidenceItem(
        id=item_id,
        feature_name=feature_name or "custom_evidence",
        family=family,
        dependence_group=str(row.get("dependence_group", item_id)),
        m_i=float(row.get("m_i", 0.90)),
        u_i=float(row.get("u_i", 0.01)),
        llr=float(row["llr"]) if "llr" in row and row["llr"] is not None else None,
        is_contradiction=bool(row.get("is_contradiction", False)),
        contradiction_weight=float(row.get("contradiction_weight", 0.0)),
        abstain=bool(row.get("abstain", False)),
        source_reliability=float(row.get("source_reliability", 1.0)),
        credibility_multiplier=float(row.get("credibility_multiplier", 1.0)),
        metadata=row.get("metadata", {}),
    )


def evaluate_attribution(
    items: List[EvidenceItem],
    calibrator: Optional[IsotonicCalibrator] = None,
    fusion_engine: Optional[LLRFusionEngine] = None,
) -> AttributionResult:
    """
    Main evaluation pipeline:
    1. Fuses evidence items using LLRFusionEngine.
    2. Calibrates final LLR into posterior probability P(H_1 | E).
    3. Categorizes decision into HIGH_CONFIDENCE_LINK, LOW_CONFIDENCE_LINK, INSUFFICIENT_EVIDENCE, or CONTRADICTION_REJECTED.
    """
    engine = fusion_engine or LLRFusionEngine()
    calib = calibrator or IsotonicCalibrator()

    (
        final_llr,
        family_scores,
        contradiction_penalty,
        abstained_count,
        contributions,
        independent_family_count,
        families_present,
    ) = engine.fuse_evidence(items)

    raw_llr = sum(it.get_effective_llr() for it in items if not it.abstain and not it.is_contradiction)
    total_capped_llr = sum(family_scores.values())

    posterior_prob = calib.predict_proba(final_llr)

    # Decision Categorization
    if contradiction_penalty > 0.0 or final_llr < 0.0:
        decision = AttributionDecision.CONTRADICTION_REJECTED
        explanation = (
            f"Linkage rejected due to active contradiction penalties (-{contradiction_penalty:.2f} LLR) "
            f"or overall negative evidence ratio (final LLR = {final_llr:.2f})."
        )
    elif posterior_prob >= 0.85:
        decision = AttributionDecision.HIGH_CONFIDENCE_LINK
        explanation = (
            f"High confidence evidence-backed identity attribution (posterior P = {posterior_prob:.4f}, "
            f"final LLR = {final_llr:.2f}, independent families = {independent_family_count})."
        )
    elif posterior_prob >= 0.50:
        decision = AttributionDecision.LOW_CONFIDENCE_LINK
        explanation = (
            f"Low confidence identity correlation (posterior P = {posterior_prob:.4f}, "
            f"final LLR = {final_llr:.2f}). Requires human analyst review."
        )
    else:
        decision = AttributionDecision.INSUFFICIENT_EVIDENCE
        explanation = (
            f"Insufficient evidence to establish identity linkage (posterior P = {posterior_prob:.4f}, "
            f"final LLR = {final_llr:.2f})."
        )

    return AttributionResult(
        raw_llr=raw_llr,
        family_scores=family_scores,
        total_capped_llr=total_capped_llr,
        contradiction_penalty=contradiction_penalty,
        final_llr=final_llr,
        posterior_probability=posterior_prob,
        decision=decision,
        independent_family_count=independent_family_count,
        families_present=families_present,
        abstained_items_count=abstained_count,
        explanation=explanation,
        contributions=contributions,
        metadata={"total_items": len(items)},
    )


def compute_attribution(
    evidence_rows: List[Union[Dict[str, Any], EvidenceItem]],
    calibrator: Optional[IsotonicCalibrator] = None,
    fusion_engine: Optional[LLRFusionEngine] = None,
) -> Dict[str, Any]:
    """
    FROZEN PUBLIC API CONTRACT FOR VIVEK / BACKEND INTEGRATION.
    
    Accepts raw evidence dictionaries or EvidenceItem instances and returns
    a clean, JSON-serializable dictionary with calibrated probability, decision,
    family breakdown, and per-evidence waterfall contributions.
    """
    engine = fusion_engine or LLRFusionEngine()
    parsed_items = [parse_evidence_row(row, engine) for row in evidence_rows]
    result = evaluate_attribution(parsed_items, calibrator=calibrator, fusion_engine=engine)
    return result.to_dict()
