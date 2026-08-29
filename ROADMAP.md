# ROADMAP.md — NETRA-X / ONIONTRACE Product & Technical Roadmap

Comprehensive multi-phase roadmap outlining the transition from functional MVP to competition-ready production threat intelligence platform.

---

## Phase 0: Stabilize Current MVP (Completed)
- **Goals**: Establish reliable baseline, fix dependencies, enforce UUIDv7 time-ordered PKs, and verify end-to-end hero test suite.
- **Main Deliverables**:
  - FastAPI modular monolith backend + Next.js App Router frontend.
  - Basic synthetic seed script for Actor A (`ShadowByte`).
  - Cryptographic SHA-256 hash-chained audit log with `verify_chain()`.
  - Docker Compose service mesh (Postgres 16 + pgvector, Neo4j 5, Redis 7, MinIO, OpenSearch).
- **Definition of Done**: `pytest tests/test_backend.py` and `pytest tests/test_e2e_hero.py` pass 100%.

---

## Phase 1: Core Attribution Engine & Synthetic Excellence (Completed / Active)
- **Goals**: Refine mathematical LLR fusion, introduce dependence discounting ($\lambda=0.25$), family caps, isotonic calibration, and stylometric same-author verification.
- **Main Deliverables**:
  - `packages/attribution/`: Log-Likelihood Ratio engine, `mu_table.yaml` priors, isotonic regressor, candidate generators.
  - `packages/stylometry/`: Feature extraction pipeline (char n-grams, POS ratios, function words) with $<50$ word abstention rule.
  - `seed/synthetic_bench.py`: Ground-truth synthetic dataset (Actor A `nstar_7`, Actor B coincidence, Actor C clone imposter with planted contradiction).
  - `bench/report.py`: Automated calibration reporting (ECE, Brier Score, FAR, Recall@10, Stylometry ROC-AUC).
- **Definition of Done**: Benchmark report outputs ECE $< 0.15$, Brier Score $< 0.08$, FAR $0.0\%$, and Recall@10 $100\%$.

---

## Phase 2: Real-Time Passive Collection Pipeline (Active)
- **Goals**: Build passive OSINT ingestion workers with WARC storage, OnionProbes, and Redis Streams event bus.
- **Main Deliverables**:
  - `workers/collection/warc_writer.py`: ISO 28500 immutable WARC response record generator with SHA-256 payload digest.
  - `workers/collection/onion_probe.py`: Favicon mmh3 Shodan matcher, Apache/Nginx status page detector, TLS cert fingerprinting.
  - `workers/collection/event_bus.py`: Redis Streams topic coordinator (`PAGE_COLLECTED` $\to$ extraction $\to$ `RELATIONSHIP_DISCOVERED` $\to$ graph projection).
  - `workers/extraction/extractor.py`: PGP, BTC, ETH, Monero (XMR hard abstention rule), handle, and email parsers.
  - `workers/extraction/clone_detector.py`: SimHash 64-bit structural clone detector ($\ge 95\% \to \text{phishing\_clone}$).
- **Definition of Done**: Crawler writes WARC artifacts to MinIO, triggers Redis stream, extracts identifiers, and updates PostgreSQL database idempotently.

---

## Phase 3: Premium Real-Time Frontend & Evidence Waterfall (Active)
- **Goals**: Deliver a cinematic CTI user interface matching the NETRA-X dark void black / neon cyan / electric purple theme.
- **Main Deliverables**:
  - `apps/web/src/components/ReviewQueue.tsx`: Prioritized hypothesis queue sorted by calibrated probability with family badges and status filters.
  - `apps/web/src/components/EvidenceWaterfall.tsx`: Stacked family contribution bar chart, dependence group shading, left-pulling red contradiction bars, raw provenance drill-down modal.
  - `apps/web/src/components/AttributionLab.tsx`: Interactive decision panel (ACCEPT / REJECT / INSUFFICIENT) and multi-format exports (Signed PDF, STIX 2.1 JSON, CSV).
  - `apps/web/src/components/GraphExplorer.tsx`: Cytoscape.js interactive graph visualization with edge thickness proportional to LLR contribution score.
- **Definition of Done**: Analyst can complete the entire review workflow from queue $\to$ waterfall detail $\to$ review decision $\to$ export report.

---

## Phase 4: Production Hardening & Observability (Upcoming)
- **Goals**: High-concurrency performance, zero-trust RBAC, OpenSearch full-text search indexing, and real-time WebSocket activity stream.
- **Main Deliverables**:
  - Case-level and object-level fine-grained RBAC middleware.
  - OpenSearch full-text search integration for raw artifacts and forum threads.
  - Prometheus & Grafana dashboard tracking pipeline throughput and engine latency.
  - Automated continuous database backup and graph re-projection worker.
- **Definition of Done**: System handles 10,000+ evidence items per minute with $< 200\text{ms}$ query latency.

---

## Phase 5: Advanced Features & Machine Learning (Future Expansion)
- **Goals**: Advanced neural stylometry (Transformer-based author verification), cross-ledger financial clustering, and AI Copilot fine-tuning.
- **Main Deliverables**:
  - Fine-tuned RoBERTa / DeBERTa stylometric embeddings for short text blocks.
  - UTXO multi-input co-spending heuristic cluster builder for Monero / Bitcoin mixer tracing.
  - Retrieval-Augmented Generation (RAG) AI Copilot drawer with strict evidence citation bounds.
- **Definition of Done**: Multi-modal attribution accuracy exceeds $98\%$ ROC-AUC on real-world OSINT benchmarks.
