# netra-x-krishna — Bayesian Attribution Engine, Stylometry & Synthetic Benchmarks

> **SEE BEYOND. UNMASK THE REAL.**  
> *Krishna's Personal Implementation Repository for NETRA-X Cyber Threat Intelligence Attribution Engine*

---

## 📌 Repository Overview

This repository contains Krishna's complete ownership deliverables for Phase 1 and Phase 2 of NETRA-X:
1. **Bayesian Attribution Engine** (`packages/attribution/`): Dependence-aware Log-Likelihood Ratio ($LLR_i = \ln(m_i / u_i)$) fusion ($\lambda = 0.25$), family capping, source reliability/credibility scaling, uncapped contradiction penalties ($W_c$), isotonic probability calibration, candidate decision evaluation, and per-item waterfall contribution calculation.
2. **Stylometry Verification Module** (`packages/stylometry/`): Character n-grams, function word frequency extraction, Burrows' Delta / Cosine Distance same-author verifier, and **mandatory short-text abstention rule** ($< 50$ words $\to$ `abstain = True`, $0.0$ score weight).
3. **Synthetic Benchmark Suite** (`bench/synthetic/`): Ground-truth scenarios for **Actor A** (multi-family true positive match), **Actor B** (coincidence non-match), **Actor C** (adversarial imposter clone with temporal contradiction), and short-text abstention test cases.
4. **Evaluation & Metrics Suite** (`bench/metrics.py`, `bench/report.py`): Quantitative evaluation of Brier Score, Expected Calibration Error (ECE $< 0.15$), False-Attribution Rate (FAR $= 0.0\%$), and Stylometry Abstention Rate.

---

## 📁 Repository Structure

```
netra-x-krishna/
├── README.md                   # Repository overview & setup instructions
├── pyproject.toml              # Standalone package setup & dependencies
├── packages/
│   ├── attribution/            # Bayesian LLR Evidence Fusion Engine
│   │   ├── __init__.py
│   │   ├── fusion.py           # Dependence-aware LLR fusion (lambda=0.25), family caps, waterfall contribs
│   │   ├── calibration.py      # Isotonic Regression & Sigmoid calibrators
│   │   ├── decide.py           # compute_attribution public API & candidate decision evaluator
│   │   └── mu_table.yaml       # Base frequency priors (u_i) and match probabilities (m_i)
│   ├── stylometry/             # Stylometric Feature Extraction & Verifier
│   │   ├── __init__.py
│   │   ├── features.py         # Character n-grams, function words, POS & punctuation ratios
│   │   ├── episodes.py         # SYSML-style text episode container & abstention rule (<50 words)
│   │   └── verify.py           # Burrows' Delta & Cosine Distance author verifier
│   └── common/
│       ├── __init__.py
│       └── types.py            # EvidenceFamily, EvidenceItem, ItemContributionBreakdown, AttributionResult
├── bench/
│   ├── __init__.py
│   ├── synthetic/              # Benchmark generator and scenario definitions
│   │   ├── __init__.py
│   │   ├── generator.py        # Benchmark suite generator
│   │   └── scenarios.py        # Actor A, B, C and short-text scenarios
│   ├── report.py               # Benchmark CLI report generator (python -m bench.report)
│   └── metrics.py              # ECE, Brier Score, FAR, Recall@10 metrics
├── tests/
│   ├── __init__.py
│   ├── test_fusion.py          # Pytest suite for LLR fusion, family caps & API contract
│   ├── test_stylometry.py      # Pytest suite for stylometry & <50 words abstention
│   └── test_synthetic.py       # Pytest suite for Actor A, B, C benchmark outcomes
└── docs/
    └── KRISHNA_NOTES.md        # Technical specifications & frozen API contract for Vivek
```

---

## 🛠️ How Vivek Will Integrate This

Vivek can integrate Krishna's engine into the main FastAPI backend (`apps/api/`) or worker handlers using the frozen `compute_attribution` API contract.

### Step 1: Install or Add Path
Install in editable mode or import package:
```bash
pip install -e netra-x-krishna
```

### Step 2: Call `compute_attribution` in Backend Handlers

```python
from packages.attribution import compute_attribution

# Vivek passes raw evidence rows fetched from PostgreSQL
evidence_rows = [
    {
        "id": "ev_101",
        "feature_name": "pgp_fingerprint_exact", # Priors auto-loaded from mu_table.yaml
    },
    {
        "id": "ev_102",
        "feature_name": "btc_address_reuse",
        "dependence_group": "wallet_cluster_alpha",
    },
    {
        "id": "ev_103",
        "feature_name": "temporal_impossible_overlap",
        "is_contradiction": True,
    }
]

# Run Bayesian Attribution Engine
result_dict = compute_attribution(evidence_rows)

print(result_dict["decision"])                # "HIGH_CONFIDENCE_LINK" | "CONTRADICTION_REJECTED" | etc.
print(result_dict["calibrated_prob"])         # Posterior probability P(H1|E) in [0, 1]
print(result_dict["final_llr"])               # Capped LLR minus contradiction penalties
print(result_dict["contributions"])           # Detailed list for Sahil's Evidence Waterfall chart!
```

---

## ⚡ Running Tests & Benchmark Reports

### Running Unit Tests
```bash
python -m pytest tests -v
```

### Running Benchmark Evaluation Report
```bash
python -m bench.report
```
Target Quality Metrics:
- **ECE**: $< 0.15$ (PASSED)
- **FAR**: $0.0\%$ (PASSED)
- **Actor A**: `HIGH_CONFIDENCE_LINK`
- **Actor B**: `INSUFFICIENT_EVIDENCE`
- **Actor C**: `CONTRADICTION_REJECTED`
