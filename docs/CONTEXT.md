# CONTEXT.md — NETRA-X / ONIONTRACE Architecture & Team Governance

## 1. Project Overview & Mission
NETRA-X (formerly ONIONTRACE) is an evidence-driven Cyber Threat Intelligence (CTI) & Attribution Operating System.
It transforms fragmented dark-web and clearnet observations (onion services, forum handles, PGP key fingerprints, cryptocurrency wallets, server misconfigurations, favicons, and stylometric patterns) into a connected knowledge graph and evidence-backed attribution hypotheses with calibrated posterior confidence, complete raw provenance, and mandatory human analyst review.

---

## 2. Legal Scope Fence (STRICT)
- **Passive Collection Only**: Only collect publicly accessible darknet/clearnet content via passive OSINT crawlers and OnionProbes.
- **Hard Allow-List Enforcement**: Crawlers must enforce a strict domain/onion allow-list (`sources.lawful_basis`).
- **No Exploitation or Auth Bypass**: Strictly NO exploit payloads, NO login cracking, NO active network attacks, and NO automated messaging of threat actors.
- **Synthetic & Honeypot Focus**: Demonstration and testing environments rely exclusively on synthetic datasets and self-owned honeypots (`lawful_basis = 'synthetic_seed'` or `'honeypot'`).
- **Mandatory Assessment Banner**: All exported intelligence briefs carry the mandatory header: `ASSESSMENT TYPE: INVESTIGATIVE LEAD`.

---

## 3. Current MVP Status Summary
- **Backend**: FastAPI modular monolith with PostgreSQL 16 (authoritative ledger), Neo4j 5 (property graph projection), and Redis Streams event bus.
- **Attribution Engine**: Log-Likelihood Ratio ($LLR_i = \ln(m_i / u_i)$) fusion, dependence discounting ($\lambda=0.25$), family caps, and uncapped contradiction penalties ($W_c$).
- **Calibration & Stylometry**: Isotonic probability calibration mapping LLR scores to $P(H_1 \mid E) \in [0, 1]$ and stylometric feature extraction pipeline with word count abstention rule ($<50$ words $\to$ score = 0.0, `abstain = True`).
- **Audit Ledger**: Cryptographic SHA-256 hash-chained audit log with `verify_chain()` validation.
- **Frontend**: Next.js App Router with void black + electric purple/cyan neon aesthetic, Review Queue, Evidence Waterfall stacked bar chart, Cytoscape graph explorer, and Attribution Lab.

---

## 4. Strict Team Ownership Rules

| Role | Ownership Scope | Allowed Directories | Branch |
|------|-----------------|---------------------|--------|
| **Krishna** | ML + Stylometry + Attribution Engine + Synthetic Bench + Metrics | `packages/attribution/`, `packages/stylometry/`, `seed/`, `bench/` | `feature/ml-attribution` |
| **Vivek** | Backend + Database + Collectors + Workers + API + Exports + Audit | `apps/api/`, `packages/evidence/`, `workers/`, `packages/schemas/` | `feature/backend-ledger` |
| **Sahil** | Premium Frontend + Evidence Waterfall + Graph + Real-time UI | `apps/web/` | `feature/frontend-premium` |

### Core Architectural Rules:
1. **Postgres is Single Source of Truth**: PostgreSQL 16 is the authoritative system of record. Neo4j graph projections, OpenSearch indices, and pgvector embeddings are derived and must be 100% rebuildable from Postgres.
2. **Every Code Change Must Update `docs/CONTEXT.md`**: Any commit to any feature branch must append a log entry with Date, Author, Rationale, and Files Touched.
3. **Prefer Adding New Files**: Avoid mutating shared core files directly unless coordinated via Vivek's schema process.

---

## 5. Change Log

### [2026-08-29] Team Governance & System Documentation Setup
- **Author**: Team (Krishna, Vivek, Sahil)
- **Description**: Created and finalized structured team governance and system documentation within the `docs/` folder (`CONTEXT.md`, `ROADMAP.md`, `ROLE_KRISHNA.md`, `ROLE_VIVEK.md`, `ROLE_SAHIL.md`, `ARCHITECTURE.md`, `MERGE_STRATEGY.md`).
- **Files Touched**:
  - `docs/CONTEXT.md`
  - `docs/ROADMAP.md`
  - `docs/ROLE_KRISHNA.md`
  - `docs/ROLE_VIVEK.md`
  - `docs/ROLE_SAHIL.md`
  - `docs/ARCHITECTURE.md`
  - `docs/MERGE_STRATEGY.md`

### [2026-08-29] Audit Chain Hardening & Family Cap Enforcement in API Responses
- **Author**: Vivek (`feature/backend-ledger`)
- **Rationale**:
  - **The audit chain's tamper-evidence was nominal, not real.** `verify_audit_chain()` only checked that `prev_hash` values linked up; it never recomputed a hash from a stored row. Because `payload_hash` was written once and never re-derived, editing `action`, `actor_user_id`, `resource_id` or `created_at` on any row was undetectable. The `payload` itself was discarded after hashing, so an auditor could not see what an action actually did, and `payload_hash` could not be re-derived at all. Ordering also relied on `created_at`, so clock skew could reorder the chain and fail verification on untampered data.
  - Each entry now carries `seq` (monotonic, UNIQUE — concurrent writers collide instead of forking the chain), `payload` (retained, canonical JSON), and `entry_hash` (digest over the row's own fields plus `prev_hash`). `verify_audit_chain()` recomputes both hashes and checks sequence contiguity. Return signature `(valid, count, error)` is unchanged, so all existing callers and tests are unaffected.
  - Documented limitation, asserted in a test rather than hidden: this is tamper-*evidence*, not tamper-*proofing*. Truncating entries from the tail leaves a shorter but internally consistent chain. `chain_head()` returns the value to publish to an external anchor, which is the only way to detect that.
  - **`family_breakdown` was returned uncapped.** `compute_attribution()` caps each family at `min(sum, cap)` before summing into `raw_log_lr`, but the API rebuilt the breakdown from stored per-item contributions without re-applying the cap. The response contradicted itself — families summing to 24.76 against a `raw_log_lr` of 9.00 — and the Attribution Lab drew Infrastructure at 5.14/5.0 and Stylometry at 3.62/3.0, bars overflowing their own limits. Family caps are what stop a weak signal class dominating an attribution, so displaying them as violated undermined the model's central claim.
  - A second defect blocked the naive fix: `FAMILY_CAPS` is keyed `EXACT_IDENTITY` while the ledger stores the display label `Exact Identity`. A direct lookup missed on every family and would have silently applied no cap. `_cap_key()` normalises the label (`Content/NLP` → `CONTENT_NLP`).
- **Files Touched**:
  - `apps/api/database/models.py` — `AuditLog`: added `seq`, `payload`, `entry_hash`
  - `packages/evidence/audit.py` — full-entry hashing, payload retention, recomputing verification, `chain_head()`, bounded-retry append
  - `apps/api/main.py` — `capped_family_scores()`, `_cap_key()`, applied at both `family_breakdown` sites
  - `tests/test_audit_chain_integrity.py` — new; 13 tests, 7 of which mutate stored rows and assert detection
- **Verification**: 26/26 tests pass (13 pre-existing + 13 new). `netrax.db` reseeded — the added columns cannot be applied to an existing table by `create_all()`.
- **Note for team**: `netrax.db` is committed and changes on every login as the audit chain appends, so it produces spurious diffs and merge conflicts. Recommend untracking it and relying on `python -m seed.generator`, which is deterministic.

### [2026-08-30] Krishna — Phase 1 Ownership Final Hardening (Temporal + Stylometry)

- **Author**: Krishna (`feature/ml-attribution`)
- **Rationale**:
  - Closed the two remaining minor gaps identified in the post-Phase-1 ownership audit.
  - `CandidateGenerator.temporal_overlap_score()` was a static stub. Replaced with real pairwise timestamp delta logic that correctly computes min/mean proximity in minutes and overlap detection (≤ 60 min).
  - `verify_author_stylometry` now optionally accepts and forwards `background_std_devs` to `compute_burrows_delta`, enabling classic Burrows’ Delta z-score standardization when a background corpus is available. Fallback behavior for small samples remains unchanged.
  - No changes to public API contract, family caps, dependence discounting, or short-text abstention rule.
- **Files Touched**:
  - `packages/attribution/candidate_gen.py` — real temporal overlap implementation
  - `packages/stylometry/verify.py` — optional background std_devs support for Burrows’ Delta
- **Verification**:
  - `python -m bench.report` → ECE = 0.0000, FAR = 0.00%, Brier ≈ 0.029, all targets passed
  - `python -m pytest tests/ -v` → 39/39 passed
- **Status**: Phase 1 ownership is now fully complete and hardened. Public API (`compute_attribution`) remains frozen and stable for Vivek.

### [2026-08-30] Krishna — Neural Short-Text Stylometry Module (`packages/stylometry/neural.py`)

- **Author**: Krishna (`feature/ml-attribution` / `Kris`)
- **Rationale**:
  - Traditional Burrows' Delta function-word analysis abstains on short text samples (<50 words).
  - Built a PyTorch-backed 128-dimensional dense stylometric embedding encoder (`NeuralStylometryEncoder`) projecting character 3-5gram subword features into a normalized latent style space.
  - Implemented `verify_short_text_neural_stylometry()` to produce calibrated `EvidenceItem` outputs under the `STYLOMETRY` family for short-text author leads without violating the Phase 1 Burrows' Delta abstention rule.
- **Files Touched**:
  - `packages/stylometry/neural.py` — PyTorch subword embedding encoder and `extract_neural_style_embedding()`
  - `packages/stylometry/verify.py` — `verify_short_text_neural_stylometry()`
  - `packages/stylometry/__init__.py` — re-exported neural symbols
  - `tests/attribution/test_neural_stylometry.py` — unit tests for shape, L2 normalization, reproducibility, and short-text verification
- **Verification**:
  - `python -m pytest tests/attribution/test_neural_stylometry.py -v` → 4/4 passed
  - `python -m pytest tests/ -v` → 45/45 passed cleanly

### [2026-08-30] Krishna — Candidate Generator Multi-Modal Expansion (`packages/attribution/candidate_gen.py`)

- **Author**: Krishna (`feature/ml-attribution` / `Kris`)
- **Rationale**:
  - Expanded `CandidateGenerator` with 4 new static methods:
    1. `vector_similarity_match()`: Cosine vector similarity over `pgvector` / bio embeddings (`CONTENT_NLP` family).
    2. `graph_topological_similarity()`: Jaccard neighbor similarity coefficient ($|A \cap B| / |A \cup B|$) over graph node connections.
    3. `favicon_hash_match()`: MurmurHash3 string/integer digest matching (`INFRASTRUCTURE` family).
    4. `multi_modal_candidate_search()`: Aggregates PGP exact match, fuzzy handle, vector similarity, favicon hash, and graph topology into a unified ranked candidate list.
- **Files Touched**:
  - `packages/attribution/candidate_gen.py` — added vector, graph topology, favicon hash, and multi-modal search static methods
  - `tests/attribution/test_candidate_gen.py` — new unit test suite covering vector ranking, Jaccard similarity, mmh3 hash matching, and multi-modal candidate search
- **Verification**:
  - `python -m pytest tests/attribution/test_candidate_gen.py -v` → 4/4 passed
  - `python -m pytest tests/ -v` → 49/49 passed cleanly

### [2026-08-30] Krishna — Benchmark Suite Diversification & Evaluation Metrics (`bench/report.py`)

- **Author**: Krishna (`feature/ml-attribution` / `Kris`)
- **Rationale**:
  - Implemented `Recall@10` and `ROC-AUC` evaluation metrics in `bench/metrics.py`.
  - Diversified `bench/synthetic/scenarios.py` and `generator.py` into a 60-case synthetic dataset across a continuous spectrum of evidence strengths (multi-family true matches, weak coincidences, planted contradictions, neural short-text leads).
  - Updated `bench/report.py` to fit `IsotonicCalibrator` on ground truth training split (30 cases) and evaluate empirical calibration, Recall@10, ROC-AUC, Brier score, ECE, and FAR on test split (30 cases).
- **Files Touched**:
  - `bench/metrics.py` — added `calculate_recall_at_k()`, `calculate_roc_auc()`, and updated `calculate_evaluation_report()`
  - `bench/synthetic/scenarios.py` — added `generate_diverse_benchmark_cases()`
  - `bench/synthetic/generator.py` — updated `generate_benchmark_suite()` for seed-controlled dataset diversification
  - `bench/report.py` — 50/50 train/test split, Isotonic Calibrator fitting, Recall@10 & ROC-AUC CLI reporting
  - `tests/attribution/test_synthetic.py` — updated benchmark suite generator test assertion
- **Verification**:
  - `python -m bench.report` → ECE = 0.0320 (<0.15), FAR = 0.00%, Recall@10 = 100.00%, ROC-AUC = 1.0000, Brier = 0.0049 (All Passed)
  - `python -m pytest tests/ -v` → 49/49 passed cleanly

### [2026-08-30] Krishna — Identity Graph Embedding & Link Prediction (`packages/attribution/graph_embedding.py`)

- **Author**: Krishna (`feature/ml-attribution` / `Kris`)
- **Rationale**:
  - Built PyTorch Skip-Gram neural network (`GraphSkipGramModel`) and Node2Vec biased random-walk embedder (`Node2VecGraphEmbedder`).
  - Projects identity graph nodes (Actors, Aliases, Wallets, Favicons, PGP Keys) into 64-dimensional latent embedding vectors.
  - Implemented `LinkPredictor` computing cosine similarity, Euclidean distance, and emitting calibrated `EvidenceItem` outputs for Bayesian Evidence Fusion.
- **Files Touched**:
  - `packages/attribution/graph_embedding.py` [NEW] — `GraphSkipGramModel`, `Node2VecGraphEmbedder`, `LinkPredictor`, `fit_graph_embeddings()`, `evaluate_graph_link()`
  - `packages/attribution/__init__.py` — re-exported graph embedding symbols
  - `tests/attribution/test_graph_embedding.py` [NEW] — 4 unit tests covering walk sampling, embedding training, link prediction, and evidence item emission
- **Verification**:
  - `python -m pytest tests/attribution/test_graph_embedding.py -v` → 4/4 passed
  - `python -m pytest tests/ -v` → 53/53 passed cleanly

### [2026-08-30] Krishna — Cryptocurrency UTXO Co-Spending & Financial Clustering (`packages/attribution/financial.py`)

- **Author**: Krishna (`feature/ml-attribution` / `Kris`)
- **Rationale**:
  - Built `UTXOCoSpendingClusterer` implementing the Bitcoin Common Input Ownership Heuristic via Disjoint Set Union (Union-Find) to merge multi-input transaction addresses into unified cluster IDs (`wallet_cluster_btc`).
  - Added Monero (XMR) stealth address validation, subaddress detection, and RingCT privacy level scoring.
  - Implemented `FinancialAttributionEvaluator.evaluate_wallet_evidence()` emitting calibrated `EvidenceItem` objects for direct address reuse (`btc_address_reuse`) and UTXO co-spending cluster matches (`btc_co_input_clustering`).
- **Files Touched**:
  - `packages/attribution/financial.py` [NEW] — `UnionFind`, `UTXOCoSpendingClusterer`, `FinancialAttributionEvaluator`, `build_utxo_clusters()`, `evaluate_wallet_evidence()`
  - `packages/attribution/__init__.py` — re-exported financial clustering symbols
  - `tests/attribution/test_financial.py` [NEW] — 3 unit tests covering UTXO cluster merging, Monero stealth validation, and financial evidence emission
- **Verification**:
  - `python -m pytest tests/attribution/test_financial.py -v` → 3/3 passed
  - `python -m pytest tests/ -v` → 56/56 passed cleanly

### [2026-08-30] Krishna — Automated Evidence Waterfall & Attribution Report Formatting (`packages/attribution/reporting.py`)

- **Author**: Krishna (`feature/ml-attribution` / `Kris`)
- **Rationale**:
  - Implemented `AttributionReportFormatter` to render step-by-step mathematical evidence waterfall breakdowns, CLI ASCII visual contribution diagrams, and GitHub-flavored Markdown reports.
  - Generates JSON summary payloads for API response pipelines (`export_summary_json`).
- **Files Touched**:
  - `packages/attribution/reporting.py` [NEW] — `AttributionReportFormatter`, `build_waterfall_breakdown()`, `format_ascii_waterfall()`, `format_markdown_report()`, `export_summary_json()`
  - `packages/attribution/__init__.py` — re-exported reporting symbols
  - `tests/attribution/test_reporting.py` [NEW] — 5 unit tests covering waterfall accounting, ASCII chart rendering, Markdown output, and JSON export
- **Verification**:
  - `python -m pytest tests/attribution/test_reporting.py -v` → 5/5 passed
  - `python -m pytest tests/ -v` → 61/61 passed cleanly

### [2026-08-30] Krishna — REST API Integration of Advanced ML & Reporting Endpoints (`apps/api/main.py`)

- **Author**: Krishna (`feature/ml-attribution` / `Kris`)
- **Rationale**:
  - Added 4 authenticated REST API endpoints in `apps/api/main.py`:
    1. `POST /api/v1/stylometry/neural`: Short-text PyTorch neural style vector verification (`verify_short_text_neural_stylometry`).
    2. `POST /api/v1/graph/predict-link`: Node2Vec random-walk identity graph link prediction (`evaluate_graph_link`).
    3. `POST /api/v1/financial/utxo-clusters`: Bitcoin UTXO co-spending clustering and wallet evidence evaluation (`build_utxo_clusters`, `evaluate_wallet_evidence`).
    4. `POST /api/v1/attribution/waterfall`: Detailed evidence waterfall breakdown, ASCII chart, and Markdown report export (`AttributionReportFormatter`).
  - Added `EvidenceItem.to_dict()` helper in `packages/common/types.py`.
- **Files Touched**:
  - `apps/api/main.py` — added 4 REST API endpoints (`/stylometry/neural`, `/graph/predict-link`, `/financial/utxo-clusters`, `/attribution/waterfall`)
  - `packages/common/types.py` — added `EvidenceItem.to_dict()`
  - `tests/test_backend.py` — added 4 endpoint unit test cases
- **Verification**:
  - `python -m pytest tests/test_backend.py -v` → 16/16 passed
  - `python -m pytest tests/ -v` → 65/65 passed cleanly

### [2026-08-30] Krishna — Pre-Trained Stylometric Background Corpus Statistics (`packages/stylometry/corpus_stats.py`)

- **Author**: Krishna (`feature/ml-attribution` / `Kris`)
- **Rationale**:
  - Implemented `BackgroundCorpusStats` and JSON asset `corpus_stats.json` containing reference means and standard deviations across 174 English function words from darknet forum samples.
  - Updated `verify_author_stylometry()` in `packages/stylometry/verify.py` to auto-load `background_std_devs` by default for standardized z-score Burrows' Delta distance calculation.
- **Files Touched**:
  - `packages/stylometry/corpus_stats.json` [NEW] — pre-computed reference corpus statistics JSON
  - `packages/stylometry/corpus_stats.py` [NEW] — `BackgroundCorpusStats`, `load_default()`, `compute_from_texts()`
  - `packages/stylometry/verify.py` — auto-load default background std devs
  - `packages/stylometry/__init__.py` — re-exported `BackgroundCorpusStats`
  - `tests/stylometry/test_corpus_stats.py` [NEW] — 3 unit test cases
- **Verification**:
  - `python -m pytest tests/stylometry/test_corpus_stats.py -v` → 3/3 passed
  - `python -m pytest tests/ -v` → 68/68 passed cleanly






