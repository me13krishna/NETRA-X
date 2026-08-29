"""
NETRA-X Synthetic Benchmark Generator & Dataset Suite
Generates deterministic multi-actor benchmark scenario:
  - Actor A ("nstar_7"): Strong multi-family evidence -> High Calibrated Probability (0.85+)
  - Actor B ("coincidence_user"): Coincidence-only weak evidence -> Low / Insufficient (0.30)
  - Actor C ("clone_imposter"): Adversarial clone with copied handle & planted Temporal Impossibility contradiction
"""

from typing import List, Dict, Any, Tuple
# Import through the bridge, not the engine directly. packages/evidence/
# attribution.py is the single seam between application code and the
# attribution engine -- importing packages.attribution here bypassed it and
# broke the moment the engine's public names changed.
from packages.evidence.attribution import RawEvidenceInput, compute_attribution, EvidenceFamily


class SyntheticBenchmarkSuite:
    """Generates ground-truth labeled scenarios for calibration & evaluation."""

    def __init__(self):
        self.scenarios = []

    def build_dataset(self) -> List[Dict[str, Any]]:
        dataset = []

        # --- SCENARIO 1: Actor A ("nstar_7" / ShadowByte) ---
        # Strong independent evidence across Exact Identity, Financial, Infrastructure, Stylometry
        ev_a = [
            RawEvidenceInput(
                evidence_id="ev_a_pgp",
                family="EXACT_IDENTITY",
                value="PGP Fingerprint 4A8F 912C B301 772E B19C 80A5 D810 23EF 44A9 1876",
                m_prob=0.99,
                u_prob=0.0001,
                dependence_group="DEP_PGP_01",
                source_uri="http://darkforums777.onion/thread/10928",
                extraction_method="pgp_parser",
                timestamp="2026-08-20T10:00:00Z",
                sha256="a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890"
            ),
            RawEvidenceInput(
                evidence_id="ev_a_wallet",
                family="FINANCIAL",
                value="BTC Co-spending wallet bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
                m_prob=0.90,
                u_prob=0.001,
                dependence_group="DEP_WALLET_01",
                source_uri="http://blockchain.info/tx/123",
                extraction_method="blockchain_cluster",
                timestamp="2026-08-21T12:00:00Z",
                sha256="b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1"
            ),
            RawEvidenceInput(
                evidence_id="ev_a_favicon",
                family="INFRASTRUCTURE",
                value="Favicon mmh3 -1598234912 -> Clearnet 185.220.101.5",
                m_prob=0.85,
                u_prob=0.005,
                dependence_group="DEP_INFRA_01",
                source_uri="http://shadowmarket7x4k2.onion/favicon.ico",
                extraction_method="shodan_favicon_matcher",
                timestamp="2026-08-22T14:00:00Z",
                sha256="c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2"
            ),
            RawEvidenceInput(
                evidence_id="ev_a_style",
                family="STYLOMETRY",
                value="Burrows Delta 0.12 (Calibrated author probability 0.88)",
                m_prob=0.75,
                u_prob=0.02,
                dependence_group="DEP_STYLE_01",
                source_uri="http://empirex.onion/seller/nstar_7",
                extraction_method="stylometry_pipeline",
                timestamp="2026-08-23T16:00:00Z",
                sha256="d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3"
            )
        ]
        res_a = compute_attribution(ev_a)
        dataset.append({
            "pair_id": "Actor_A_nstar_7",
            "subject": "nstar_7",
            "candidate": "ShadowByte",
            "ground_truth": 1,
            "evidence_items": ev_a,
            "result": res_a
        })

        # --- SCENARIO 2: Actor B ("coincidence_user") ---
        # Weak coincidence signal (similar handle + single generic post term)
        ev_b = [
            RawEvidenceInput(
                evidence_id="ev_b_handle",
                family="SEMANTIC_HANDLE",
                value="Fuzzy handle match (coincidence_user ~ nstar_7 similarity 0.35)",
                m_prob=0.40,
                u_prob=0.20,
                dependence_group="DEP_HANDLE_01",
                source_uri="http://dreadmirror.onion/u/coincidence_user",
                extraction_method="fuzzy_handle_trigram",
                timestamp="2026-08-24T10:00:00Z",
                sha256="e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4"
            )
        ]
        res_b = compute_attribution(ev_b)
        dataset.append({
            "pair_id": "Actor_B_coincidence",
            "subject": "nstar_7",
            "candidate": "coincidence_user",
            "ground_truth": 0,
            "evidence_items": ev_b,
            "result": res_b
        })

        # --- SCENARIO 3: Actor C ("clone_imposter") ---
        # Adversarial clone (copied listing + similar handle + shared hosting + planted Temporal Impossibility contradiction)
        ev_c = [
            RawEvidenceInput(
                evidence_id="ev_c_handle",
                family="SEMANTIC_HANDLE",
                value="Similar handle nstar_7_store (imposter clone)",
                m_prob=0.60,
                u_prob=0.05,
                dependence_group="DEP_CLONE_01",
                source_uri="http://alphabay2.onion/vendor/nstar_7_store",
                extraction_method="fuzzy_handle_trigram",
                timestamp="2026-08-25T11:00:00Z",
                sha256="f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5"
            ),
            RawEvidenceInput(
                evidence_id="ev_c_temporal_conflict",
                family="TEMPORAL",
                value="Simultaneous high-frequency postings from UTC+8 and UTC-5 within 1-minute window",
                m_prob=0.01,
                u_prob=0.98,
                dependence_group="DEP_TEMP_CONFLICT",
                source_uri="http://alphabay2.onion/logs",
                extraction_method="temporal_overlap_analyzer",
                timestamp="2026-08-25T11:01:00Z",
                sha256="7890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f6",
                is_contradiction=True,
                contradiction_type="Temporal Impossibility"
            )
        ]
        res_c = compute_attribution(ev_c)
        dataset.append({
            "pair_id": "Actor_C_clone",
            "subject": "nstar_7",
            "candidate": "clone_imposter",
            "ground_truth": 0,
            "evidence_items": ev_c,
            "result": res_c
        })

        return dataset
