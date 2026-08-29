"""
NETRA-X Bayesian Fusion & Contradiction Subsystem
Implements Log-Likelihood Ratio (LLR) multi-evidence fusion, dependence discounting (lambda=0.25),
family contribution caps, uncapped contradiction subtractions, and decision policy.
"""

import math
from typing import Dict, List, Optional
from enum import Enum

FAMILY_CAPS: Dict[str, float] = {
    "EXACT_IDENTITY": 10.0,
    "FINANCIAL": 7.5,
    "INFRASTRUCTURE": 5.0,
    "CONTENT_NLP": 5.0,
    "STYLOMETRY": 3.0,
    "TEMPORAL": 2.0,
    "SEMANTIC_HANDLE": 2.0,
}

CONTRADICTION_PENALTIES: Dict[str, float] = {
    "PGP Key Identity Conflict": 12.0,
    "Temporal Impossibility": 15.0,
    "Infrastructure Ownership Conflict": 8.0,
    "Mutually Exclusive Identity": 10.0,
    "Wallet Contradiction": 8.0,
}

DEFAULT_LAMBDA = 0.25


class DecisionOutcome(str, Enum):
    HIGH_CONFIDENCE_LINK = "HIGH_CONFIDENCE_LINK"
    MEDIUM_CONFIDENCE_LINK = "MEDIUM_CONFIDENCE_LINK"
    LOW_CONFIDENCE_LINK = "LOW_CONFIDENCE_LINK"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONTRADICTION_REJECTED = "CONTRADICTION_REJECTED"


class RawEvidenceInput:
    def __init__(
        self,
        evidence_id: str,
        family: str,
        value: str,
        m_prob: float,  # P(E | H1)
        u_prob: float,  # P(E | H0)
        dependence_group: str,
        source_uri: str,
        extraction_method: str,
        timestamp: str,
        sha256: str,
        is_contradiction: bool = False,
        contradiction_type: str = "",
        abstain: bool = False
    ):
        self.evidence_id = evidence_id
        self.family = family
        self.value = value
        self.m_prob = m_prob
        self.u_prob = u_prob
        self.dependence_group = dependence_group
        self.source_uri = source_uri
        self.extraction_method = extraction_method
        self.timestamp = timestamp
        self.sha256 = sha256
        self.is_contradiction = is_contradiction
        self.contradiction_type = contradiction_type
        self.abstain = abstain

        # Calculate item LLR: llr = ln(m / u)
        if abstain:
            self.raw_llr = 0.0
        else:
            safe_u = max(u_prob, 1e-6)
            safe_m = max(m_prob, 1e-6)
            self.raw_llr = math.log(safe_m / safe_u)


class AttributionResult:
    def __init__(
        self,
        raw_log_lr: float,
        calibrated_prob: float,
        confidence_tier: str,
        family_scores: Dict[str, float],
        supporting_items: List[Dict],
        contradiction_items: List[Dict],
        total_contradiction_penalty: float,
        decision: DecisionOutcome,
        family_count: int
    ):
        self.raw_log_lr = raw_log_lr
        self.calibrated_prob = calibrated_prob
        self.confidence_tier = confidence_tier
        self.family_scores = family_scores
        self.supporting_items = supporting_items
        self.contradiction_items = contradiction_items
        self.total_contradiction_penalty = total_contradiction_penalty
        self.decision = decision
        self.family_count = family_count


def compute_attribution(
    evidence_items: List[RawEvidenceInput],
    discount_lambda: float = DEFAULT_LAMBDA,
    custom_family_caps: Optional[Dict[str, float]] = None
) -> AttributionResult:
    """
    Core Log-Likelihood Ratio (LLR) Attribution Algorithm.
    Applies dependence discounting, family caps, and uncapped contradiction penalties.
    """
    caps = custom_family_caps or FAMILY_CAPS

    # Filter active supporting and contradiction items (ignore abstained evidence)
    supporting_inputs = [item for item in evidence_items if not item.is_contradiction and not item.abstain]
    contradiction_inputs = [item for item in evidence_items if item.is_contradiction and not item.abstain]

    # Group supporting evidence by family -> dependence_group
    family_groups: Dict[str, Dict[str, List[RawEvidenceInput]]] = {}
    for item in supporting_inputs:
        fam = item.family
        dep = item.dependence_group
        if fam not in family_groups:
            family_groups[fam] = {}
        if dep not in family_groups[fam]:
            family_groups[fam][dep] = []
        family_groups[fam][dep].append(item)

    family_final_scores: Dict[str, float] = {}
    supporting_output_items: List[Dict] = []

    for fam, dep_dict in family_groups.items():
        fam_uncapped_score = 0.0
        for dep_group, items in dep_dict.items():
            if not items:
                continue
            items_sorted = sorted(items, key=lambda x: x.raw_llr, reverse=True)
            max_item = items_sorted[0]
            remaining_items = items_sorted[1:]

            # Group Score: max(LLR) + lambda * sum(remaining LLRs)
            group_score = max_item.raw_llr + discount_lambda * sum(x.raw_llr for x in remaining_items)
            fam_uncapped_score += group_score

            for idx, item in enumerate(items_sorted):
                contrib = item.raw_llr if idx == 0 else item.raw_llr * discount_lambda
                supporting_output_items.append({
                    "evidence_id": item.evidence_id,
                    "family": item.family,
                    "source_uri": item.source_uri,
                    "extraction_method": item.extraction_method,
                    "value": item.value,
                    "reliability": round(item.m_prob, 2),
                    "raw_llr": round(item.raw_llr, 3),
                    "contribution": round(contrib, 3),
                    "is_contradiction": False,
                    "dependence_group": item.dependence_group,
                    "timestamp": item.timestamp,
                    "sha256": item.sha256
                })

        cap = caps.get(fam, 5.0)
        family_final_scores[fam] = round(min(fam_uncapped_score, cap), 3)

    llr_pos = sum(family_final_scores.values())

    # Contradiction Penalties (Uncapped)
    contradiction_output_items: List[Dict] = []
    total_penalty = 0.0

    for item in contradiction_inputs:
        penalty = CONTRADICTION_PENALTIES.get(item.contradiction_type, 10.0)
        total_penalty += penalty
        contradiction_output_items.append({
            "evidence_id": item.evidence_id,
            "family": item.family,
            "source_uri": item.source_uri,
            "extraction_method": item.extraction_method,
            "value": f"CONTRADICTION: {item.contradiction_type} - {item.value}",
            "reliability": 0.0,
            "raw_llr": -penalty,
            "contribution": -penalty,
            "is_contradiction": True,
            "dependence_group": item.dependence_group,
            "timestamp": item.timestamp,
            "sha256": item.sha256
        })

    raw_log_lr = round(llr_pos - total_penalty, 3)

    from .calibration import calibrate_probability, determine_confidence_tier
    calibrated_prob = calibrate_probability(raw_log_lr)
    confidence_tier = determine_confidence_tier(calibrated_prob)
    num_families = len(family_final_scores)

    decision = decide(calibrated_prob, total_penalty, num_families)

    return AttributionResult(
        raw_log_lr=raw_log_lr,
        calibrated_prob=calibrated_prob,
        confidence_tier=confidence_tier,
        family_scores=family_final_scores,
        supporting_items=supporting_output_items,
        contradiction_items=contradiction_output_items,
        total_contradiction_penalty=total_penalty,
        decision=decision,
        family_count=num_families
    )


def decide(calibrated_prob: float, total_contradiction_penalty: float, family_count: int) -> DecisionOutcome:
    """Automated decision policy based on probability, family independence, and contradictions."""
    if total_contradiction_penalty >= 15.0:
        return DecisionOutcome.CONTRADICTION_REJECTED
    
    if calibrated_prob >= 0.85 and family_count >= 2:
        return DecisionOutcome.HIGH_CONFIDENCE_LINK
    elif calibrated_prob >= 0.60:
        return DecisionOutcome.MEDIUM_CONFIDENCE_LINK
    elif calibrated_prob >= 0.35:
        return DecisionOutcome.LOW_CONFIDENCE_LINK
    else:
        return DecisionOutcome.INSUFFICIENT_EVIDENCE
