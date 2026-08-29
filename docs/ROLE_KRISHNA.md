# ROLE_KRISHNA.md — ML, Stylometry & Attribution Engine Ownership

## 👤 Owner: Krishna
- **Branch**: `feature/ml-attribution`
- **Ownership Scope**: `packages/attribution/`, `packages/stylometry/`, `seed/`, `bench/`
- **Core Goal**: Make the mathematical heart of the system correct, calibrated, robust, and demo-ready.

---

## 🎯 Detailed Task Breakdown & Priority Order

### 1. Bayesian Attribution Engine (`packages/attribution/`)
- **Deliverables**:
  - `fusion.py`: Log-Likelihood Ratio ($LLR_i = \ln(m_i / u_i)$) fusion algorithm.
  - Dependence discounting ($\lambda = 0.25$) applied across items sharing the same `dependence_group`:
    $$S_{\text{group}} = \text{max}(LLR) + \lambda \sum \text{remaining } LLRs$$
  - Family caps (`EXACT_IDENTITY`: 10.0, `FINANCIAL`: 7.5, `INFRASTRUCTURE`: 5.0, `CONTENT_NLP`: 5.0, `STYLOMETRY`: 3.0, `TEMPORAL`: 2.0, `SEMANTIC_HANDLE`: 2.0).
  - Uncapped direct contradiction penalty subtractions ($W_c$).
  - `mu_table.yaml`: Base frequency priors ($u_i$) and match probabilities ($m_i$).
  - `calibration.py`: Isotonic Regression wrapper (`sklearn.isotonic.IsotonicRegression`) mapping LLR scores to posterior probabilities $P(H_1 \mid E) \in [0, 1]$.
  - `candidate_gen.py`: Exact PGP match, trigram fuzzy handle, graph topological distance, pgvector cosine similarity.

### 2. Stylometry Module (`packages/stylometry/`)
- **Deliverables**:
  - `pipeline.py`: Feature extraction (char 3-5grams, function words, punctuation ratios, POS patterns, sentence length distributions).
  - `pipeline.py`: SYSML-style episode aggregation (`StylometryEpisode`).
  - `verifier.py`: Burrows' Delta / Cosine Distance same-author verifier.
  - **MANDATORY HARD RULE**: If text $< 50$ words $\to$ return `abstain = True` with $0.0$ score contribution.

### 3. Synthetic Benchmark Generator (`seed/synthetic_bench.py`)
- **Deliverables**:
  - **Actor A (`nstar_7` / `ShadowByte`)**: Ground Truth = 1. Multi-family evidence (PGP exact, wallet cluster, Favicon mmh3, stylometry). Outcome: `HIGH_CONFIDENCE_LINK` ($P \ge 0.85$).
  - **Actor B (`coincidence_user`)**: Ground Truth = 0. Weak single-family coincidence. Outcome: `LOW_CONFIDENCE_LINK` / `INSUFFICIENT_EVIDENCE`.
  - **Actor C (`clone_imposter`)**: Ground Truth = 0. Copied handle + planted Temporal Impossibility contradiction. Outcome: `CONTRADICTION_REJECTED`.

### 4. Evaluation & Metrics Script (`bench/report.py`)
- **Deliverables**:
  - Automated benchmark reporter outputting: Brier Score, Expected Calibration Error (ECE), False-Attribution Rate (FAR), Recall@10, Stylometry ROC-AUC, and Stylometry Short-Text Abstention Rate.

---

## 📋 Immediate Action Items for Krishna
1. Keep unit tests in `tests/test_backend.py` passing.
2. Run `python -m bench.report` after modifying attribution logic to ensure ECE $< 0.15$ and FAR $0.0\%$.
3. Maintain API contract signature for Vivek: `compute_attribution(evidence_items) -> AttributionResult`.
4. Update `docs/CONTEXT.md` change log on every commit to `feature/ml-attribution`.
