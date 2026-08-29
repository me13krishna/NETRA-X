# KRISHNA_NOTES.md — ML, Stylometry & Bayesian Attribution Engine Implementation & Integration Guide

## 👤 Author: Krishna
- **Module Repository**: `netra-x-krishna`
- **Ownership**: Bayesian Attribution Engine (`packages/attribution/`), Stylometry Verification (`packages/stylometry/`), Synthetic Benchmark Generator (`bench/synthetic/`), Evaluation Metrics (`bench/metrics.py`, `bench/report.py`).

---

## 📐 Methodological & Mathematical Specifications Implemented

### 1. Item-Level Log-Likelihood Ratio (LLR)
Every evidence observation calculates effective LLR:
$$LLR_i = \text{source\_reliability} \times \text{credibility\_multiplier} \times \ln\left(\frac{m_i}{u_i}\right)$$
- $m_i = P(E_i \mid H_1)$: Probability of observing evidence given true identity match.
- $u_i = P(E_i \mid H_0)$: Base frequency / random occurrence probability in darknet/clearnet population.

### 2. Dependence-Aware Group Discounting ($\lambda = 0.25$)
Co-dependent evidence items sharing the same `dependence_group` (e.g., multiple addresses in the same Bitcoin wallet cluster, multiple domain certificates from the same server host) undergo dependence discounting to prevent double-counting:
$$S_{\text{group}} = LLR_{(1)} + \lambda \sum_{k=2}^{N} LLR_{(k)} \quad (\text{where } \lambda = 0.25)$$

### 3. Family-Level LLR Capping (`FAMILY_CAPS`)
Evidence group scores are summed within each evidence family and capped to avoid single-vector over-dominance:
- `EXACT_IDENTITY`: **10.0** (PGP fingerprints, SSH host keys)
- `FINANCIAL`: **7.5** (Bitcoin/Monero wallet clusters)
- `INFRASTRUCTURE`: **5.0** (Favicon MurmurHash3, TLS cert serials)
- `CONTENT_NLP`: **5.0** (Near-duplicate SimHash >= 95%, distinctive jargon)
- `STYLOMETRY`: **3.0** (Burrows' Delta, function word distributions)
- `TEMPORAL`: **2.0** (Diurnal activity window overlaps)
- `SEMANTIC_HANDLE`: **2.0** (Trigram handle similarity)

### 4. Uncapped Contradiction Penalties ($W_c$)
Mutually exclusive evidence items (e.g. Temporal Impossibility, conflicting PGP keys) subtract uncapped penalties directly without damping or capping:
$$LLR_{\text{raw}} = \sum S_{\text{family}} - \sum W_c$$

### 5. Proportional Item Contribution for Evidence Waterfall
To drive Sahil's Evidence Waterfall stacked bar chart in the frontend:
- Each item's contribution `llr_contrib` is calculated taking dependence discounting and family cap scaling into account.
- Mathematical Identity: $\sum \text{llr\_contrib}_i - \sum W_c = \text{final\_llr}$.

### 6. Isotonic Posterior Probability Calibration
Maps final LLR score to empirical posterior probability $P(H_1 \mid E) \in [0, 1]$ via `IsotonicRegression` with fallback sigmoid curve:
$$P(H_1 \mid E) = \frac{1}{1 + e^{-(\text{LLR} - 2.0)}}$$

### 7. Stylometry Short-Text Abstention Rule
- **HARD RULE**: If total word count $< 50$ words $\to$ sets `abstain = True` and emits $0.0$ score weight contribution.

---

## 🔌 Frozen Public API Contract for Vivek

Vivek can import `compute_attribution` directly from `packages.attribution`.

### Function Signature

```python
def compute_attribution(
    evidence_rows: list[dict | EvidenceItem],
    calibrator: Optional[IsotonicCalibrator] = None,
    fusion_engine: Optional[LLRFusionEngine] = None,
) -> dict:
    ...
```

### Example Input (`evidence_rows`)

```python
evidence_rows = [
    {
        "id": "ev_pgp_1",
        "feature_name": "pgp_fingerprint_exact", # Auto-loads m_i, u_i, family from mu_table
    },
    {
        "id": "ev_btc_1",
        "feature_name": "btc_address_reuse",
        "dependence_group": "wallet_cluster_btc",
    },
    {
        "id": "ev_custom_1",
        "family": "INFRASTRUCTURE",
        "dependence_group": "web_server",
        "m_i": 0.92,
        "u_i": 0.0001,
    },
    {
        "id": "ev_contra_1",
        "feature_name": "temporal_impossible_overlap", # Auto-loads contradiction weight W_c = 15.0
        "is_contradiction": True,
    }
]
```

### Example Output (`dict`)

```json
{
  "raw_llr": 38.99,
  "family_scores": {
    "EXACT_IDENTITY": 10.0,
    "FINANCIAL": 7.5,
    "INFRASTRUCTURE": 5.0,
    "CONTENT_NLP": 0.0,
    "STYLOMETRY": 0.0,
    "TEMPORAL": 0.0,
    "SEMANTIC_HANDLE": 0.0
  },
  "total_capped_llr": 22.5,
  "contradiction_penalty": 15.0,
  "final_llr": 7.5,
  "calibrated_prob": 0.9959,
  "decision": "HIGH_CONFIDENCE_LINK",
  "independent_family_count": 3,
  "families_present": ["EXACT_IDENTITY", "FINANCIAL", "INFRASTRUCTURE"],
  "abstained_items_count": 0,
  "explanation": "High confidence evidence-backed identity attribution (posterior P = 0.9959, final LLR = 7.50, independent families = 3).",
  "contributions": [
    {
      "evidence_id": "ev_pgp_1",
      "feature_name": "pgp_fingerprint_exact",
      "family": "EXACT_IDENTITY",
      "dependence_group": "pgp_identity",
      "raw_llr": 18.42,
      "llr_contrib": 10.0,
      "is_discounted": false,
      "is_capped": true,
      "is_contradiction": false,
      "abstain": false,
      "metadata": {}
    },
    {
      "evidence_id": "ev_contra_1",
      "feature_name": "temporal_impossible_overlap",
      "family": "TEMPORAL",
      "dependence_group": "temporal_contradiction",
      "raw_llr": 0.0,
      "llr_contrib": -15.0,
      "is_discounted": false,
      "is_capped": false,
      "is_contradiction": true,
      "abstain": false,
      "metadata": {}
    }
  ]
}
```

---

## 🧪 Verification & Benchmark Execution

To run unit tests:
```bash
python -m pytest tests -v
```

To run the full synthetic benchmark evaluation suite:
```bash
python -m bench.report
```

Target Quality Metrics Verified:
- Expected Calibration Error (ECE) $< 0.15$
- False-Attribution Rate (FAR) $= 0.0\%$
- Actor A $\to$ `HIGH_CONFIDENCE_LINK` ($P \ge 0.85$)
- Actor B $\to$ `INSUFFICIENT_EVIDENCE` ($P < 0.50$)
- Actor C $\to$ `CONTRADICTION_REJECTED`
