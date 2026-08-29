# ROLE_VIVEK.md — Backend, Database & Data Pipelines Ownership

## 👤 Owner: Vivek
- **Branch**: `feature/backend-ledger`
- **Ownership Scope**: `apps/api/`, `packages/evidence/`, `workers/`, `packages/schemas/`
- **Core Goal**: Make the system of record rock-solid, data pipelines reliable, audit log tamper-evident, and REST API complete.

---

## 🎯 Detailed Task Breakdown & Priority Order

### 1. Database DDL & Schema (`apps/api/database/models.py`)
- **Deliverables**:
  - `Source` model (`sources` table): `name`, `source_type`, `lawful_basis` NOT NULL (`passive_osint`, `synthetic_seed`, `honeypot`), `is_active`.
  - `Observation` model (`observations` table): `source_id`, `raw_content`, `content_hash`, `observed_at`, `metadata_json`.
  - `AuditLog` model (`audit_logs` table): UUIDv7 time-ordered PK, `actor_user_id`, `action`, `resource_type`, `resource_id`, `payload_hash`, `prev_hash`.
  - `verify_chain(session)`: Validates cryptographic SHA-256 hash chain integrity.

### 2. REST API Endpoints (`apps/api/main.py`)
- **Deliverables**:
  - `/api/v1/attribution/evaluate`: On-demand dynamic LLR evidence scoring.
  - `/api/v1/review/{hypothesis_id}`: Record analyst decisions (`ACCEPT` / `REJECT` / `INSUFFICIENT`) and append SHA-256 audit log events.
  - `/api/v1/exports/stix`: STIX 2.1 JSON CTI bundle export with `investigative_lead` extension.
  - `/api/v1/exports/csv`: CSV evidence item export.
  - `/api/v1/audit/verify`: SHA-256 audit log chain verification.
  - `/api/v1/actors/{id}/graph` & `/api/v1/actors/{id}/timeline`: Subgraph Cytoscape JSON payload & timeline events.

### 3. Extractors & Pipeline Workers (`workers/`)
- **Deliverables**:
  - `workers/extraction/extractor.py`: PGP fingerprint, BTC, ETH, Monero (XMR hard abstention rule), handle, and email parsers.
  - `workers/extraction/clone_detector.py`: SimHash 64-bit structural clone detector ($\ge 95\% \to \text{phishing\_clone}$ flag & dependence group collapse).
  - `workers/collection/warc_writer.py`: ISO 28500 immutable WARC response record writer with SHA-256 digest.
  - `workers/collection/onion_probe.py`: Favicon mmh3 Shodan matcher, Apache/Nginx status page detector, TLS cert fingerprinting.
  - `workers/collection/event_bus.py`: Redis Streams topic coordinator (`PAGE_COLLECTED` $\to$ extraction $\to$ `RELATIONSHIP_DISCOVERED` $\to$ graph projection).

### 4. Graph Projection (`packages/graph/projection.py`)
- **Deliverables**:
  - PostgreSQL $\to$ Neo4j property graph projection. Must be 100% rebuildable from Postgres.

---

## 📋 Immediate Action Items for Vivek
1. Ensure all new REST endpoints have OpenAPI schema definitions.
2. Verify `verify_audit_chain()` returns `valid = True` after seeding.
3. Keep `tests/test_backend.py` and `tests/test_e2e_hero.py` passing 100%.
4. Update `docs/CONTEXT.md` change log on every commit to `feature/backend-ledger`.
