# CONTEXT.md — NETRA-X / ONIONTRACE Architecture & Team Governance

## 1. Project Overview & Mission
NETRA-X (formerly ONIONTRACE) is an evidence-driven Cyber Threat Intelligence (CTI) & Attribution Operating System.
It transforms fragmented dark-web observations (onion services, forum handles, PGP key fingerprints, cryptocurrency wallets, server misconfigurations, and stylometric patterns) into a connected knowledge graph and evidence-backed attribution hypotheses with calibrated posterior confidence, complete provenance, and mandatory analyst review.

---

## 2. Legal Scope Fence (STRICT)
- **Passive Collection Only**: Only collect publicly accessible darknet/clearnet content via passive OSINT crawlers and OnionProbes.
- **Hard Allow-List Enforcement**: Crawlers must enforce a strict domain/onion allow-list (`sources.lawful_basis`).
- **No Exploitation or Auth Bypass**: Strictly NO exploit payloads, NO login cracking, NO active network attacks, NO automated messaging of threat actors.
- **Synthetic & Honeypot Focus**: Demo environments rely on synthetic datasets and self-owned honeypots (`lawful_basis = 'synthetic_seed'` or `'honeypot'`).

---

## 3. Current MVP Status Summary
- **Backend**: FastAPI modular monolith with PostgreSQL 16 (authoritative ledger), Neo4j 5 (property graph projection), and Redis Streams.
- **Attribution Engine**: Log-Likelihood Ratio ($LLR_i = \ln(m_i / u_i)$) fusion, dependence discounting ($\lambda=0.25$), family caps, and uncapped contradiction penalties.
- **Calibration & Stylometry**: Isotonic probability calibration and stylometric feature pipeline with word count abstention rule ($<50$ words).
- **Audit Ledger**: Cryptographic SHA-256 hash-chained audit log with `verify_chain()` validation.
- **Frontend**: Next.js App Router with void black + electric purple/cyan neon aesthetic, Review Queue, Evidence Waterfall stacked bar chart, and Cytoscape graph explorer.

---

## 4. Strict Team Ownership Rules

| Role | Ownership Scope | Allowed Directories | Branch |
|------|-----------------|---------------------|--------|
| **Krishna** | ML + Stylometry + Attribution Engine + Synthetic Bench + Metrics | `packages/attribution/`, `packages/stylometry/`, `seed/`, `bench/` | `feature/ml-attribution` |
| **Vivek** | Backend + Database + Collectors + Workers + API + Exports + Audit | `apps/api/`, `packages/evidence/`, `workers/`, `packages/schemas/` | `feature/backend-ledger` |
| **Sahil** | Premium Frontend + Evidence Waterfall + Graph + Real-time UI | `apps/web/` | `feature/frontend-premium` |

### Core Rules:
1. **Postgres is Single Source of Truth**: Neo4j graph projections and vector embeddings are derived and must be 100% rebuildable from Postgres.
2. **Every Code Change Must Update CONTEXT.md**: Any commit must append a log entry with Date, Author, Rationale, and Files Touched.
3. **Prefer Adding New Files**: Avoid mutating shared core files directly unless coordinated.

---

## 5. Change Log

### [2026-08-29] System Setup & Documentation Initialization
- **Author**: Team (Krishna, Vivek, Sahil)
- **Description**: Initialized structured team governance documentation (`CONTEXT.md`, `ROADMAP.md`, `ROLE_KRISHNA.md`, `ROLE_VIVEK.md`, `ROLE_SAHIL.md`, `ARCHITECTURE.md`, `MERGE_STRATEGY.md`).
- **Files**: `CONTEXT.md`, `ROADMAP.md`, `ROLE_KRISHNA.md`, `ROLE_VIVEK.md`, `ROLE_SAHIL.md`, `ARCHITECTURE.md`, `MERGE_STRATEGY.md`
