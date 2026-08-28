"""
NETRA-X Bayesian Attribution Engine & Contradiction Subsystem
Implements Log-Likelihood Ratio (LLR) fusion, dependence discounting, evidence family caps,
first-class contradiction penalties, and isotonic calibration.
"""

import math
from typing import Dict, List, Tuple
from packages.schemas.models import EvidenceFamily

# Configuration-driven default family caps
FAMILY_CAPS: Dict[str, float] = {
    EvidenceFamily.EXACT_IDENTITY.value: 10.0,
    EvidenceFamily.FINANCIAL.value: 7.5,
    EvidenceFamily.INFRASTRUCTURE.value: 5.0,
    EvidenceFamily.CONTENT_NLP.value: 5.0,
    EvidenceFamily.STYLOMETRY.value: 3.0,
    EvidenceFamily.TEMPORAL.value: 2.0,
    EvidenceFamily.SEMANTIC_HANDLE.value: 2.0,
}

# Contradiction Penalty Weights (Uncapped subtractions)
CONTRADICTION_PENALTIES: Dict[str, float] = {
    "PGP Key Identity Conflict": 12.0,
    "Temporal Impossibility": 15.0,
    "Infrastructure Ownership Conflict": 8.0,
    "Mutually Exclusive Identity": 10.0,
    "Wallet Contradiction": 8.0,
}

# Operational default dependence discount parameter lambda
DEFAULT_LAMBDA = 0.15


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
        contradiction_type: str = ""
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

        # Calculate item LLR: llr = ln(m / u)
        if u_prob <= 0:
            u_prob = 1e-6
        if m_prob <= 0:
            m_prob = 1e-6
        self.raw_llr = math.log(m_prob / u_prob)


class AttributionResult:
    def __init__(
        self,
        raw_log_lr: float,
        calibrated_prob: float,
        confidence_tier: str,
        family_scores: Dict[str, float],
        supporting_items: List[Dict],
        contradiction_items: List[Dict],
        total_contradiction_penalty: float
    ):
        self.raw_log_lr = raw_log_lr
        self.calibrated_prob = calibrated_prob
        self.confidence_tier = confidence_tier
        self.family_scores = family_scores
        self.supporting_items = supporting_items
        self.contradiction_items = contradiction_items
        self.total_contradiction_penalty = total_contradiction_penalty


def calibrate_probability(raw_llr: float, beta0: float = -0.5, beta1: float = 0.35) -> float:
    """Map raw LLR to calibrated posterior probability P(H1 | E) via Sigmoid/IsotonicStub."""
    exponent = -(beta0 + beta1 * raw_llr)
    # Clip exponent to avoid overflow
    exponent = max(-50.0, min(50.0, exponent))
    prob = 1.0 / (1.0 + math.exp(exponent))
    return round(prob, 4)


def determine_confidence_tier(prob: float) -> str:
    """Classify calibrated probability into decision tiers."""
    if prob >= 0.85:
        return "High Confidence"
    elif prob >= 0.60:
        return "Medium Confidence"
    elif prob >= 0.35:
        return "Low Confidence"
    else:
        return "Insufficient Evidence"


def compute_attribution(
    evidence_items: List[RawEvidenceInput],
    discount_lambda: float = DEFAULT_LAMBDA,
    custom_family_caps: Dict[str, float] = None
) -> AttributionResult:
    """
    Core Log-Likelihood Ratio (LLR) Attribution Algorithm with Dependence Discounting,
    Family Caps, and Contradiction Subtraction.
    """
    caps = custom_family_caps or FAMILY_CAPS

    supporting_inputs = [item for item in evidence_items if not item.is_contradiction]
    contradiction_inputs = [item for item in evidence_items if item.is_contradiction]

    # Step 1: Group supporting evidence by family and dependence_group
    family_groups: Dict[str, Dict[str, List[RawEvidenceInput]]] = {}
    for item in supporting_inputs:
        fam = item.family
        dep = item.dependence_group
        if fam not in family_groups:
            family_groups[fam] = {}
        if dep not in family_groups[fam]:
            family_groups[fam][dep] = []
        family_groups[fam][dep].append(item)

    # Step 2: Calculate discounted scores per group, capped per family
    family_final_scores: Dict[str, float] = {}
    supporting_output_items: List[Dict] = []

    for fam, dep_dict in family_groups.items():
        fam_uncapped_score = 0.0
        for dep_group, items in dep_dict.items():
            if not items:
                continue
            # Sort items in group by raw_llr descending
            items_sorted = sorted(items, key=lambda x: x.raw_llr, reverse=True)
            max_item = items_sorted[0]
            remaining_items = items_sorted[1:]

            # Group Score: max(LLR) + lambda * sum(remaining LLRs)
            group_score = max_item.raw_llr + discount_lambda * sum(x.raw_llr for x in remaining_items)
            fam_uncapped_score += group_score

            # Record item contribution details
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

        # Apply Family Cap
        cap = caps.get(fam, 5.0)
        family_final_scores[fam] = round(min(fam_uncapped_score, cap), 3)

    llr_pos = sum(family_final_scores.values())

    # Step 3: Evaluate Contradiction Penalties (Uncapped)
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

    # Step 4: Final Raw LLR Score & Calibration
    raw_log_lr = round(llr_pos - total_penalty, 3)
    calibrated_prob = calibrate_probability(raw_log_lr)
    confidence_tier = determine_confidence_tier(calibrated_prob)

    return AttributionResult(
        raw_log_lr=raw_log_lr,
        calibrated_prob=calibrated_prob,
        confidence_tier=confidence_tier,
        family_scores=family_final_scores,
        supporting_items=supporting_output_items,
        contradiction_items=contradiction_output_items,
        total_contradiction_penalty=total_penalty
    )
