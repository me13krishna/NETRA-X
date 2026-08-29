"""
scenarios.py — Synthetic benchmark scenario definitions for Actors A, B, and C.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from packages.common.types import EvidenceItem, EvidenceFamily
from packages.stylometry.episodes import StylometryEpisode
from packages.stylometry.verify import verify_author_stylometry


@dataclass
class SyntheticBenchmarkCase:
    """
    TestCase container for a synthetic benchmark run.
    """
    case_id: str
    target_actor: str
    candidate_actor: str
    ground_truth_match: int  # 1 for True Match, 0 for Non-Match / Imposter
    evidence_items: List[EvidenceItem] = field(default_factory=list)
    expected_decision: str = ""  # Expected AttributionDecision string name
    description: str = ""


# Sample text paragraphs for stylometry testing
LONG_AUTHOR_TEXT_A1 = """
We have upgraded our operational deployment scripts for darknet hidden service nodes. 
All servers MUST implement strict firewall rules and disable directory indexing immediately. 
If you observe any suspicious latency spikes on our Tor onions, report them to the PGP key fingerprint listed in our header. 
Security is paramount when operating defensive CTI monitoring nodes across untrusted infrastructure networks. 
Ensure that PostgreSQL database connections are encrypted using TLS 1.3 and authentication tokens are rotated daily.
"""

LONG_AUTHOR_TEXT_A2 = """
Regarding the recent infrastructure updates, we confirmed that all favicons and static assets have been re-indexed. 
Our automated OSINT crawlers continue passive observation without executing active exploits or authenticating. 
Always verify PGP signatures on all administrative announcements before proceeding with system updates. 
Maintain complete hash-chained audit logs for all evidentiary extractions to ensure court-admissible chain of custody.
"""

SHORT_TEXT_ABSTAIN = "Quick update on the forum post."  # <50 words


def generate_actor_a_scenario() -> SyntheticBenchmarkCase:
    """
    Actor A (nstar_7 / ShadowByte) — True Positive Ground Truth = 1.
    
    Multi-family evidence spanning 5 independent evidence families:
    1. EXACT_IDENTITY: PGP Key Fingerprint exact match
    2. FINANCIAL: Bitcoin Address Reuse in wallet cluster
    3. INFRASTRUCTURE: Favicon MurmurHash3 digest match
    4. CONTENT_NLP: Near-duplicate website SimHash content match (>=95%)
    5. STYLOMETRY: Burrows' Delta same-author text match (>50 words)
    
    Expected Outcome: HIGH_CONFIDENCE_LINK (P >= 0.85).
    """
    items = [
        # Family 1: EXACT_IDENTITY
        EvidenceItem(
            id="ev_a_pgp",
            feature_name="pgp_fingerprint_exact",
            family=EvidenceFamily.EXACT_IDENTITY,
            dependence_group="pgp_identity",
            m_i=0.9999,
            u_i=0.00000001,  # Raw LLR ~ 18.42 (Capped at 10.0)
        ),
        # Family 2: FINANCIAL
        EvidenceItem(
            id="ev_a_btc",
            feature_name="btc_address_reuse",
            family=EvidenceFamily.FINANCIAL,
            dependence_group="wallet_cluster_btc",
            m_i=0.95,
            u_i=0.00001,  # Raw LLR ~ 11.46 (Capped at 7.5)
        ),
        # Family 3: INFRASTRUCTURE
        EvidenceItem(
            id="ev_a_favicon",
            feature_name="favicon_mmh3_hash",
            family=EvidenceFamily.INFRASTRUCTURE,
            dependence_group="web_server_fingerprint",
            m_i=0.92,
            u_i=0.0001,  # Raw LLR ~ 9.12 (Capped at 5.0)
        ),
        # Family 4: CONTENT_NLP
        EvidenceItem(
            id="ev_a_simhash",
            feature_name="simhash_clone_95",
            family=EvidenceFamily.CONTENT_NLP,
            dependence_group="site_content_nlp",
            m_i=0.85,
            u_i=0.001,  # Raw LLR ~ 6.74 (Capped at 5.0)
        ),
    ]

    # Family 5: STYLOMETRY (>50 words text match)
    ep1 = StylometryEpisode.from_single_text("actor_a", "ep1", LONG_AUTHOR_TEXT_A1)
    ep2 = StylometryEpisode.from_single_text("actor_a", "ep2", LONG_AUTHOR_TEXT_A2)
    sty_item = verify_author_stylometry(ep1, ep2, item_id="ev_a_stylometry")
    items.append(sty_item)

    return SyntheticBenchmarkCase(
        case_id="case_actor_a_true_match",
        target_actor="nstar_7",
        candidate_actor="ShadowByte",
        ground_truth_match=1,
        evidence_items=items,
        expected_decision="HIGH_CONFIDENCE_LINK",
        description="True match across 5 independent evidence families (PGP, BTC, Favicon, SimHash, Stylometry).",
    )


def generate_actor_b_scenario() -> SyntheticBenchmarkCase:
    """
    Actor B (coincidence_user) — Ground Truth = 0.
    
    Weak single-family coincidence (fuzzy handle trigram overlap).
    
    Expected Outcome: INSUFFICIENT_EVIDENCE (P < 0.50).
    """
    items = [
        EvidenceItem(
            id="ev_b_handle",
            feature_name="handle_trigram_fuzzy",
            family=EvidenceFamily.SEMANTIC_HANDLE,
            dependence_group="handle_alias",
            m_i=0.60,
            u_i=0.15,  # Weak LLR ~ 1.38
        )
    ]

    return SyntheticBenchmarkCase(
        case_id="case_actor_b_coincidence",
        target_actor="nstar_7",
        candidate_actor="coincidence_user",
        ground_truth_match=0,
        evidence_items=items,
        expected_decision="INSUFFICIENT_EVIDENCE",
        description="Weak single-family handle coincidence without supporting corroborating evidence.",
    )


def generate_actor_c_scenario() -> SyntheticBenchmarkCase:
    """
    Actor C (clone_imposter) — Ground Truth = 0.
    
    Adversarial clone imposter attempting to frame/impersonate target:
    - High handle similarity (copied handle)
    - Copied site content (high SimHash content score)
    - Shared server favicon
    BUT contains a planted Temporal Impossibility contradiction penalty W_c = 15.0
    (e.g., physically impossible simultaneous forum posts from opposite sides of the world).
    
    Expected Outcome: CONTRADICTION_REJECTED (Suppressed despite superficial positive signals).
    """
    items = [
        # Copied Handle (SEMANTIC_HANDLE)
        EvidenceItem(
            id="ev_c_handle",
            feature_name="handle_trigram_fuzzy",
            family=EvidenceFamily.SEMANTIC_HANDLE,
            dependence_group="handle_alias",
            m_i=0.85,
            u_i=0.05,  # LLR ~ 2.83
        ),
        # Copied Content (CONTENT_NLP)
        EvidenceItem(
            id="ev_c_content",
            feature_name="simhash_clone_95",
            family=EvidenceFamily.CONTENT_NLP,
            dependence_group="site_content_nlp",
            m_i=0.85,
            u_i=0.001,  # LLR ~ 6.74
        ),
        # Planted Temporal Impossibility Contradiction
        EvidenceItem(
            id="ev_c_contradiction",
            feature_name="temporal_impossible_overlap",
            family=EvidenceFamily.TEMPORAL,
            dependence_group="temporal_contradiction",
            is_contradiction=True,
            contradiction_weight=15.0,  # W_c = 15.0 penalty
            metadata={"detail": "Physically impossible simultaneous login timestamps from Tokyo and Berlin"},
        ),
    ]

    return SyntheticBenchmarkCase(
        case_id="case_actor_c_adversarial_clone",
        target_actor="nstar_7",
        candidate_actor="clone_imposter",
        ground_truth_match=0,
        evidence_items=items,
        expected_decision="CONTRADICTION_REJECTED",
        description="Adversarial imposter copying profile & content, suppressed by Temporal Impossibility contradiction.",
    )


def generate_short_text_abstention_scenario() -> SyntheticBenchmarkCase:
    """
    Short Text Sample (<50 words) — Demonstrates clean stylometry abstention.
    """
    ep1 = StylometryEpisode.from_single_text("actor_a", "ep1", LONG_AUTHOR_TEXT_A1)
    ep_short = StylometryEpisode.from_single_text("actor_a", "ep_short", SHORT_TEXT_ABSTAIN)
    sty_item = verify_author_stylometry(ep1, ep_short, item_id="ev_short_stylometry")

    return SyntheticBenchmarkCase(
        case_id="case_short_text_abstention",
        target_actor="nstar_7",
        candidate_actor="nstar_7_mobile",
        ground_truth_match=1,
        evidence_items=[sty_item],
        expected_decision="INSUFFICIENT_EVIDENCE",
        description="Short text sample (<50 words) triggers stylometry abstention rule.",
    )
