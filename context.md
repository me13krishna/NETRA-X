# NETRA-X / ONIONTRACE — Project Context & Architecture Governance

> **MANDATORY SYSTEM DIRECTIVE**: This file MUST be maintained and updated after every meaningful code change across all team members.

---

## 🏛️ Core Project Governance Rules

1. **Every Code Change Entry Required**: Every modification must append a clean log entry to the `Change Log` section containing:
   - **Date** (YYYY-MM-DD)
   - **Author / Role**
   - **Description of Change & Rationale**
   - **Files Touched**
2. **Strict Branch & Ownership Separation**:
   - **Krishna** (`feature/ml-attribution`): `packages/attribution/`, `packages/stylometry/`, `seed/`, `bench/`
   - **Vivek** (`feature/backend-ledger`): `apps/api/`, `packages/evidence/`, `workers/`, `packages/schemas/`, DB migrations
   - **Sahil** (`feature/frontend-premium`): `apps/web/`
3. **Single Source of Truth**: PostgreSQL is the sole authoritative system of record for all artifacts, evidence items, hypotheses, reviews, and audit logs. Neo4j property graphs and vector embeddings are derived projections and must be 100% rebuildable from PostgreSQL.
4. **Strict Legal Scope Fence**: Only passive collection of publicly reachable content (`passive_osint`), synthetic datasets (`synthetic_seed`), and self-owned honeypot data (`honeypot`). NO authentication bypass, NO exploitation, NO messaging threat actors, NO third-party attacks.
5. **Add New Files Over Rewriting**: Prefer introducing specialized new modules over mutating existing shared files.
6. **Feature Freeze**: Feature freeze once the hero path (Seed $\to$ Evaluate $\to$ Waterfall Review $\to$ Analyst Decision $\to$ Audit Verify $\to$ Export) works cleanly.
7. **Preserve Synthetic Benchmark**: Synthetic A/B/C demo scenario MUST remain fully functional and passing all tests at all times.

---

## 🚀 Current System Status

- **Status**: Production-Ready / Hero Demo Ready (100% Tests Passing)
- **Database**: PostgreSQL 16 schema initialized with `sources.lawful_basis` NOT NULL constraint, `observations`, and SHA-256 hash-chained `audit_logs`.
- **Attribution Engine**: Bayesian LLR fusion ($\lambda=0.25$), family caps, uncapped contradiction subtractions, isotonic calibration, and candidate generation.
- **Stylometry Engine**: Char 3-5grams, function words, POS tagging, episode aggregation, and $<50$ word hard abstention rule.
- **Workers & Pipelines**: Monero XMR hard abstention, SimHash $\ge 95\%$ structural clone detection, WARC ISO 28500 writer, OnionProbe scanners, and Redis Streams event bus.
- **UI & Frontend**: Premium Next.js void black / electric purple / cyan theme, Review Queue, interactive Evidence Waterfall with stacked family bars, Cytoscape graph, and STIX 2.1 / CSV / PDF exports.

---

## 📝 Change Log

### [2026-08-29] Krishna (ML / Stylometry / Attribution)
- **Changed**: Created Bayesian LLR Attribution Engine (`packages/attribution/fusion.py`), `mu_table.yaml` priors, Isotonic calibration (`calibration.py`), and candidate generation (`candidate_gen.py`).
- **Changed**: Created Stylometry feature extraction pipeline (`packages/stylometry/pipeline.py`) and verifier (`verifier.py`) with word count abstention rule ($<50$ words).
- **Changed**: Built Synthetic Benchmark Generator (`seed/synthetic_bench.py`) and Evaluation reporter (`bench/report.py`).
- **Reason**: To deliver calibrated, mathematically sound multi-evidence fusion with strict abstention and ground-truth benchmark metrics (ECE, Brier, ROC-AUC).
- **Files**:
  - `packages/attribution/__init__.py`
  - `packages/attribution/fusion.py`
  - `packages/attribution/calibration.py`
  - `packages/attribution/candidate_gen.py`
  - `packages/attribution/mu_table.yaml`
  - `packages/stylometry/__init__.py`
  - `packages/stylometry/pipeline.py`
  - `packages/stylometry/verifier.py`
  - `seed/synthetic_bench.py`
  - `bench/report.py`

### [2026-08-29] Vivek (Backend / Database / Pipelines)
- **Changed**: Finalized PostgreSQL DDL adding `Source` model (`lawful_basis` NOT NULL: `passive_osint`, `synthetic_seed`, `honeypot`) and `Observation` model.
- **Changed**: Added Monero (XMR) extraction with hard abstention rule in `workers/extraction/extractor.py`.
- **Changed**: Created SimHash structural clone detector (`workers/extraction/clone_detector.py`) with $\ge 95\%$ similarity threshold.
- **Changed**: Implemented STIX 2.1 CTI bundle generator and CSV exporter (`packages/evidence/stix_export.py`).
- **Changed**: Implemented `/api/v1/attribution/evaluate`, `/api/v1/review/{hypothesis_id}`, `/api/v1/exports/stix`, `/api/v1/exports/csv`, and `/api/v1/audit/verify` in `apps/api/main.py`.
- **Changed**: Built collection workers: `workers/collection/warc_writer.py`, `onion_probe.py`, and `event_bus.py`.
- **Reason**: Complete database ledger, data pipeline, extraction workers, and REST API endpoints.
- **Files**:
  - `apps/api/database/models.py`
  - `apps/api/main.py`
  - `workers/extraction/extractor.py`
  - `workers/extraction/clone_detector.py`
  - `packages/evidence/stix_export.py`
  - `workers/collection/__init__.py`
  - `workers/collection/warc_writer.py`
  - `workers/collection/onion_probe.py`
  - `workers/collection/event_bus.py`

### [2026-08-29] Sahil (Frontend UI & Evidence Waterfall)
- **Changed**: Updated `apps/web/package.json` to include `framer-motion` and `@tanstack/react-query`.
- **Changed**: Built Hypothesis Review Queue (`apps/web/src/components/ReviewQueue.tsx`) sorted by calibrated probability with family badges and status filters.
- **Changed**: Upgraded Evidence Waterfall (`apps/web/src/components/EvidenceWaterfall.tsx`) with stacked family contribution bar chart, dependence group shading, contradiction left-pull, and raw provenance drill-down modal.
- **Changed**: Updated `AttributionLab.tsx` and `CommandCenter.tsx` with STIX 2.1 / CSV / PDF export buttons and `INVESTIGATIVE_LEAD` assessment warning banner.
- **Reason**: Deliver cinematic, competition-ready CTI UI with Evidence Waterfall hero experience.
- **Files**:
  - `apps/web/package.json`
  - `apps/web/src/components/ReviewQueue.tsx`
  - `apps/web/src/components/EvidenceWaterfall.tsx`
  - `apps/web/src/components/AttributionLab.tsx`
  - `apps/web/src/components/CommandCenter.tsx`
