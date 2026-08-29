"""
fusion.py — Dependence-aware Log-Likelihood Ratio (LLR) Bayesian Evidence Fusion Engine.

Implements:
1. Item-level LLR calculation: LLR_i = reliability * credibility * ln(m_i / u_i)
2. Dependence discounting (lambda = 0.25) across co-dependent evidence items in the same dependence_group.
3. Family-level Score Capping (EXACT_IDENTITY, FINANCIAL, INFRASTRUCTURE, etc.).
4. Uncapped Contradiction Penalties subtraction (W_c).
5. Per-item contribution tracking for Evidence Waterfall visualization.
"""

import math
import os
from typing import List, Dict, Tuple, Any, Optional
import yaml

from packages.common.types import (
    EvidenceItem,
    EvidenceFamily,
    FAMILY_CAPS,
    ItemContributionBreakdown,
)


def load_mu_table(path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load base frequency priors (u_i) and match probabilities (m_i) from YAML.
    """
    if path is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(current_dir, "mu_table.yaml")
    
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {"features": {}, "contradictions": {}}


class LLRFusionEngine:
    """
    Core Evidence Fusion Engine implementing dependence-aware LLR fusion.
    """

    def __init__(self, lambda_discount: float = 0.25, family_caps: Optional[Dict[EvidenceFamily, float]] = None):
        """
        Initialize fusion engine with dependence discount factor lambda (default 0.25).
        """
        self.lambda_discount = lambda_discount
        self.family_caps = family_caps or FAMILY_CAPS
        self.mu_table = load_mu_table()

    def create_item_from_prior(
        self,
        item_id: str,
        feature_name: str,
        dependence_group: Optional[str] = None,
        source_reliability: float = 1.0,
        credibility_multiplier: float = 1.0,
        abstain: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EvidenceItem:
        """
        Helper factory to instantiate an EvidenceItem using default priors from mu_table.yaml.
        """
        features_dict = self.mu_table.get("features", {})
        contradictions_dict = self.mu_table.get("contradictions", {})

        if feature_name in features_dict:
            f_info = features_dict[feature_name]
            fam = EvidenceFamily(f_info.get("family", "CONTENT_NLP"))
            dep_grp = dependence_group or f_info.get("dependence_group", feature_name)
            return EvidenceItem(
                id=item_id,
                feature_name=feature_name,
                family=fam,
                dependence_group=dep_grp,
                m_i=f_info.get("m_i", 0.90),
                u_i=f_info.get("u_i", 0.01),
                is_contradiction=False,
                abstain=abstain,
                source_reliability=source_reliability,
                credibility_multiplier=credibility_multiplier,
                metadata=metadata or {},
            )
        elif feature_name in contradictions_dict:
            c_info = contradictions_dict[feature_name]
            return EvidenceItem(
                id=item_id,
                feature_name=feature_name,
                family=EvidenceFamily.TEMPORAL,  # Default fallback family
                dependence_group=dependence_group or "contradiction",
                is_contradiction=True,
                contradiction_weight=c_info.get("contradiction_weight", 10.0),
                abstain=abstain,
                metadata=metadata or {},
            )
        else:
            # Fallback item creation
            return EvidenceItem(
                id=item_id,
                feature_name=feature_name,
                family=EvidenceFamily.CONTENT_NLP,
                dependence_group=dependence_group or feature_name,
                m_i=0.80,
                u_i=0.05,
                abstain=abstain,
                source_reliability=source_reliability,
                credibility_multiplier=credibility_multiplier,
                metadata=metadata or {},
            )

    def fuse_evidence(
        self, items: List[EvidenceItem]
    ) -> Tuple[float, Dict[str, float], float, int, List[Dict[str, Any]], int, List[str]]:
        """
        Performs full dependence-aware LLR fusion across all evidence items.
        
        Returns:
            final_llr: float (total capped LLR minus contradiction penalties)
            family_breakdown: Dict[str, float] (capped scores per family)
            total_contradiction_penalty: float
            abstained_count: int
            contributions: List[Dict[str, Any]] (waterfall contributions)
            independent_family_count: int
            families_present: List[str]
        """
        abstained_count = sum(1 for it in items if it.abstain)
        family_breakdown: Dict[str, float] = {fam.value: 0.0 for fam in EvidenceFamily}
        contributions: List[Dict[str, Any]] = []

        families_present_set = set()
        for it in items:
            if not it.abstain and not it.is_contradiction:
                families_present_set.add(it.family.value)

        # Process non-contradiction items per family
        for fam in EvidenceFamily:
            fam_items = [it for it in items if it.family == fam and not it.abstain and not it.is_contradiction]
            if not fam_items:
                continue

            # Group items by dependence_group
            dep_groups: Dict[str, List[EvidenceItem]] = {}
            for it in fam_items:
                dep_groups.setdefault(it.dependence_group, []).append(it)

            # Step 1: Calculate discounted contributions per dependence group
            group_item_contribs: List[Tuple[EvidenceItem, float, bool]] = []
            uncapped_family_sum = 0.0

            for grp_id, grp_items in dep_groups.items():
                # Sort group items by effective LLR descending
                sorted_grp = sorted(grp_items, key=lambda x: x.get_effective_llr(), reverse=True)
                for idx, grp_item in enumerate(sorted_grp):
                    eff_llr = grp_item.get_effective_llr()
                    if idx == 0:
                        contrib = eff_llr
                        is_disc = False
                    else:
                        contrib = self.lambda_discount * eff_llr
                        is_disc = True
                    group_item_contribs.append((grp_item, contrib, is_disc))
                    uncapped_family_sum += contrib

            # Step 2: Apply family caps
            cap = self.family_caps.get(fam, 10.0)
            if uncapped_family_sum > cap and uncapped_family_sum > 0.0:
                scale = cap / uncapped_family_sum
                capped_family_score = cap
                is_capped_flag = True
            else:
                scale = 1.0
                capped_family_score = uncapped_family_sum
                is_capped_flag = False

            family_breakdown[fam.value] = capped_family_score

            # Step 3: Record item contributions
            for item_ref, base_contrib, is_disc in group_item_contribs:
                final_contrib = base_contrib * scale
                brk = ItemContributionBreakdown(
                    evidence_id=item_ref.id,
                    feature_name=item_ref.feature_name,
                    family=fam.value,
                    dependence_group=item_ref.dependence_group,
                    raw_llr=item_ref.get_effective_llr(),
                    llr_contrib=final_contrib,
                    is_discounted=is_disc,
                    is_capped=is_capped_flag,
                    is_contradiction=False,
                    abstain=False,
                    metadata=item_ref.metadata,
                )
                contributions.append(brk.to_dict())

        # Process contradiction items
        total_contradiction_penalty = 0.0
        for it in items:
            if it.is_contradiction:
                if not it.abstain:
                    total_contradiction_penalty += it.contradiction_weight
                brk = ItemContributionBreakdown(
                    evidence_id=it.id,
                    feature_name=it.feature_name,
                    family=it.family.value if isinstance(it.family, EvidenceFamily) else str(it.family),
                    dependence_group=it.dependence_group,
                    raw_llr=0.0,
                    llr_contrib=-it.contradiction_weight if not it.abstain else 0.0,
                    is_discounted=False,
                    is_capped=False,
                    is_contradiction=True,
                    abstain=it.abstain,
                    metadata=it.metadata,
                )
                contributions.append(brk.to_dict())

        # Process abstained non-contradiction items
        for it in items:
            if it.abstain and not it.is_contradiction:
                brk = ItemContributionBreakdown(
                    evidence_id=it.id,
                    feature_name=it.feature_name,
                    family=it.family.value if isinstance(it.family, EvidenceFamily) else str(it.family),
                    dependence_group=it.dependence_group,
                    raw_llr=0.0,
                    llr_contrib=0.0,
                    is_discounted=False,
                    is_capped=False,
                    is_contradiction=False,
                    abstain=True,
                    metadata=it.metadata,
                )
                contributions.append(brk.to_dict())

        total_capped_llr = sum(family_breakdown.values())
        final_llr = total_capped_llr - total_contradiction_penalty

        independent_family_count = sum(1 for v in family_breakdown.values() if v > 0.0)
        families_present = sorted(list(families_present_set))

        return (
            final_llr,
            family_breakdown,
            total_contradiction_penalty,
            abstained_count,
            contributions,
            independent_family_count,
            families_present,
        )
