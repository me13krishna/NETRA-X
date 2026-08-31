"""
types.py — Shared domain data types, enums, and result contracts for NETRA-X Krishna module.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional
import math


class EvidenceFamily(str, Enum):
    """
    Evidence categories mapped to upper bound LLR caps.
    """
    EXACT_IDENTITY = "EXACT_IDENTITY"
    FINANCIAL = "FINANCIAL"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    CONTENT_NLP = "CONTENT_NLP"
    STYLOMETRY = "STYLOMETRY"
    TEMPORAL = "TEMPORAL"
    SEMANTIC_HANDLE = "SEMANTIC_HANDLE"


FAMILY_CAPS: Dict[EvidenceFamily, float] = {
    EvidenceFamily.EXACT_IDENTITY: 10.0,
    EvidenceFamily.FINANCIAL: 7.5,
    EvidenceFamily.INFRASTRUCTURE: 5.0,
    EvidenceFamily.CONTENT_NLP: 5.0,
    EvidenceFamily.STYLOMETRY: 3.0,
    EvidenceFamily.TEMPORAL: 2.0,
    EvidenceFamily.SEMANTIC_HANDLE: 2.0,
}


@dataclass
class EvidenceItem:
    """
    Individual evidence observation passed into the attribution engine.
    """
    id: str
    feature_name: str
    family: EvidenceFamily
    dependence_group: str
    m_i: float = 0.90  # P(E_i | H_1)
    u_i: float = 0.01  # P(E_i | H_0)
    llr: Optional[float] = None  # Computed if None
    is_contradiction: bool = False
    contradiction_weight: float = 0.0  # W_c penalty
    abstain: bool = False  # If True, emits 0.0 score weight
    source_reliability: float = 1.0  # Multiplier in [0, 1]
    credibility_multiplier: float = 1.0  # Multiplier in [0, 1]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_effective_llr(self) -> float:
        """
        Calculate effective LLR with source reliability and credibility multipliers.
        """
        if self.abstain:
            return 0.0
        if self.is_contradiction:
            return 0.0
        if self.llr is not None:
            base_llr = self.llr
        else:
            u_safe = max(self.u_i, 1e-12)
            m_safe = max(self.m_i, 1e-12)
            base_llr = math.log(m_safe / u_safe)
        
        effective_mult = max(0.0, min(1.0, self.source_reliability * self.credibility_multiplier))
        return base_llr * effective_mult

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert EvidenceItem into clean serializable JSON dictionary for API.
        """
        fam_str = self.family.value if hasattr(self.family, "value") else str(self.family)
        return {
            "id": self.id,
            "feature_name": self.feature_name,
            "family": fam_str,
            "dependence_group": self.dependence_group,
            "m_i": self.m_i,
            "u_i": self.u_i,
            "raw_llr": round(self.get_effective_llr(), 4),
            "is_contradiction": self.is_contradiction,
            "contradiction_weight": self.contradiction_weight,
            "abstain": self.abstain,
            "source_reliability": self.source_reliability,
            "credibility_multiplier": self.credibility_multiplier,
            "metadata": self.metadata,
        }



@dataclass
class ItemContributionBreakdown:
    """
    Per-evidence item contribution detail for Evidence Waterfall chart.
    """
    evidence_id: str
    feature_name: str
    family: str
    dependence_group: str
    raw_llr: float
    llr_contrib: float
    is_discounted: bool
    is_capped: bool
    is_contradiction: bool
    abstain: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "feature_name": self.feature_name,
            "family": self.family,
            "dependence_group": self.dependence_group,
            "raw_llr": round(self.raw_llr, 4),
            "llr_contrib": round(self.llr_contrib, 4),
            "is_discounted": self.is_discounted,
            "is_capped": self.is_capped,
            "is_contradiction": self.is_contradiction,
            "abstain": self.abstain,
            "metadata": self.metadata,
        }


class AttributionDecision(str, Enum):
    """
    Final system attribution recommendation.
    """
    HIGH_CONFIDENCE_LINK = "HIGH_CONFIDENCE_LINK"     # P >= 0.85
    LOW_CONFIDENCE_LINK = "LOW_CONFIDENCE_LINK"       # 0.50 <= P < 0.85
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"   # P < 0.50 or high abstention
    CONTRADICTION_REJECTED = "CONTRADICTION_REJECTED" # Active contradiction penalty subtracted


@dataclass
class AttributionResult:
    """
    Complete output of the Bayesian Attribution Engine.
    """
    raw_llr: float
    family_scores: Dict[str, float]
    total_capped_llr: float
    contradiction_penalty: float
    final_llr: float
    posterior_probability: float
    decision: AttributionDecision
    independent_family_count: int
    families_present: List[str]
    abstained_items_count: int
    explanation: str
    contributions: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert AttributionResult into clean serializable JSON dictionary for API.
        """
        return {
            "raw_llr": round(self.raw_llr, 4),
            "family_scores": {k: round(v, 4) for k, v in self.family_scores.items()},
            "total_capped_llr": round(self.total_capped_llr, 4),
            "contradiction_penalty": round(self.contradiction_penalty, 4),
            "final_llr": round(self.final_llr, 4),
            "calibrated_prob": round(self.posterior_probability, 4),
            "decision": self.decision.value,
            "independent_family_count": self.independent_family_count,
            "families_present": self.families_present,
            "abstained_items_count": self.abstained_items_count,
            "explanation": self.explanation,
            "contributions": self.contributions,
            "metadata": self.metadata,
        }
