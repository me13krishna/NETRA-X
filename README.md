# NETRA-X: Dark Web Threat Actor Intelligence & Attribution Platform

> **SEE BEYOND. UNMASK THE REAL.**  
> *Authorized Research / Law-Enforcement Oriented / Defensive Use Only*

NETRA-X is an evidence-driven Cyber Threat Intelligence (CTI) & Attribution Operating System. It transforms fragmented dark-web observations (onion services, forum handles, PGP key fingerprints, cryptocurrency wallets, server misconfigurations, and stylometric patterns) into a connected knowledge graph and evidence-backed attribution hypotheses with calibrated posterior confidence, complete provenance, and mandatory analyst review.

---

## 🏛️ Core Methodological Philosophy

- **COLLECT EVERYTHING PASSIVELY & LEGALLY**
- **TRUST NOTHING BLINDLY**
- **PRESERVE EVERYTHING IMMUTABLY (SHA-256)**
- **CORRELATE INDEPENDENTLY ACROSS FAMILIES**
- **MODEL UNCERTAINTY VIA ISOTONIC CALIBRATION**
- **EXPOSE CONTRADICTIONS FIRST-CLASS**
- **AI ASSISTS — MANDATORY ANALYST DECIDES**

---

## 🚀 Key Features

1. **Immutable Evidence Ledger & Provenance**: Every assertion carries source URI, collection timestamp, collector version, raw artifact SHA-256 hash, and extraction method.
2. **Log-Likelihood Ratio (LLR) Attribution Engine**: Multi-evidence fusion using $LLR_i = \ln(m_i / u_i)$, dependence discounting ($\lambda=0.15$), and evidence family contribution caps (`Exact Identity`: 10.0, `Financial`: 7.5, `Infrastructure`: 5.0, `Content/NLP`: 5.0, `Stylometry`: 3.0, `Temporal`: 2.0, `Semantic`: 2.0).
3. **First-Class Contradiction Subsystem**: Mutually exclusive signals (e.g. Temporal Impossibility, PGP Key Conflicts) subtract penalties $W_c$ without capping or dampening.
4. **Isotonic Calibration & Decision Policy**: Maps raw LLR scores into calibrated probabilities $P(H_1 \mid E) \in [0, 1]$ categorizing confidence into High ($\ge 0.85$), Medium ($0.60-0.84$), Low ($0.35-0.59$), and Insufficient ($<0.35$).
5. **Interactive Cytoscape.js Knowledge Graph**: Property graph projection (rebuildable 100% from PostgreSQL) mapping `Actor`, `Alias`, `Account`, `PGPKey`, `Wallet`, `OnionService`, and `Server` nodes.
6. **Evidence Waterfall UI**: Visually unique stacked contribution breakdown displaying every supporting and contradictory evidence item with reliability weights and raw artifact references.
7. **Cryptographic SHA-256 Audit Log**: Append-only hash-chained audit trail (`payload_hash`, `prev_hash`) ensuring tamper-evident accountability.
8. **Signed ReportLab PDF Export**: One-click generation of evidence-backed CTI case reports.
9. **Constrained AI Copilot**: LLM assistant enforcing strict evidence citations.

---

## 🏗️ Repository Architecture

```
netra-x/
├── apps/
│   ├── web/                   # Next.js 14+ / TypeScript / Tailwind CSS / Cytoscape.js
│   └── api/                   # FastAPI modular monolith (Python 3.11+, SQLAlchemy Async, Pydantic)
├── workers/
│   ├── extraction/            # spaCy NER + Regex + PGP/Wallet parsers + faststylometry + mmh3
│   ├── graph/                 # Async Neo4j graph projection consumer
│   └── attribution/           # LLR scoring & contradiction calculation
├── packages/
│   ├── schemas/               # Shared Pydantic models & JSON schemas
│   ├── graph/                 # Neo4j Cypher queries & projection logic
│   └── evidence/              # Evidence Model, LLR formulas, family caps, calibration
├── seed/                      # Deterministic synthetic seed pipeline (python -m seed.generator)
├── tests/                     # Unit, integration, and E2E hero acceptance tests
├── docker-compose.yml         # Service orchestration (Postgres 16, Neo4j 5, Redis 7, MinIO, API, Web)
└── Makefile                   # System operational shortcuts (`make setup`, `make seed`, `make test`)
```

---

## 🛠️ How to Run the Hero Demonstration

### Prerequisites
- Python 3.11+
- Node.js 18+ / npm
- Docker & Docker Compose (Optional for full stack)

### Quick Start (Standalone / Offline Local Mode)

1. **Clone Repository & Install Dependencies**:
   ```bash
   git clone <repo_url> netra-x
   cd netra-x
   cp .env.example .env
   python -m pip install -e .[dev]
   ```

2. **Initialize Database & Seed Hero Dataset**:
   ```bash
   python -m seed.generator
   ```
   *Output*:
   ```
   [+] Initializing database tables...
   [+] Creating default system users...
   [+] Creating Synthetic Threat Actor A (ShadowByte)...
   [+] Creating Candidate Target Entity B (Unlinked Alias Vortex99)...
   [+] Creating Raw Immutable Artifacts & Evidence Ledger Items...
   [+] Evaluating LLR Attribution Engine for Hero Hypothesis...
   [+] Generating Hash-Chained Audit Log Entries...
   [+] PostgreSQL Seeding Succeeded.
   ```

3. **Run Unit & E2E Acceptance Tests**:
   ```bash
   python -m pytest tests/test_backend.py
   python -m pytest tests/test_e2e_hero.py
   ```
   *Result*: `100% OF SECTION 36 DEFINITION OF DONE PASSED SUCCESSFUL!`

4. **Launch Backend API & Web Frontend**:
   - **Start API Backend**:
     ```bash
     python -m uvicorn apps.api.main:app --port 8000 --reload
     ```
   - **Start Next.js Frontend**:
     ```bash
     cd apps/web
     npm install
     npm run dev
     ```

5. **Open Browser & Walk Through Hero Story**:
   - Navigate to `http://localhost:3000`
   - **Login**: `analyst@netra-x.local` / `AnalystPass2026!`
   - **Command Center**: View active metrics, live activity feed, and Attribution Review Queue.
   - **Actor Explorer**: Click `ShadowByte` to inspect aliases (`DarkSpectre`, `CipherVoid`), PGP keys (`4A8F 912C B301 772E...`), BTC wallets (`bc1qxy2k...`), and Onion misconfiguration (`shadowmarket7x4k2.onion` $\to$ Favicon mmh3 `-1598234912` $\to$ Clearnet IP `185.220.101.5`).
   - **Attribution Lab**: Inspect candidate pair `ShadowByte` $\leftrightarrow$ `Vortex99`. Observe Evidence Waterfall breakdown and planted Temporal Impossibility contradiction flag.
   - **Analyst Decision**: Click `ACCEPT LINKAGE` $\to$ confirm status update to `ACCEPTED` and SHA-256 audit log append.
   - **PDF Report Export**: Click `Export Signed PDF Report` to download the ReportLab PDF case file.
   - **Audit Log Viewer**: Inspect tamper-evident hash chain verification (`SHA-256 Hash Chain Intact & Verified`).

---

## ⚡ Docker Compose Deployment

To deploy all microservices (PostgreSQL 16 + pgvector, Neo4j 5, Redis 7, MinIO, OpenSearch, API, Web):

```bash
docker compose up --build -d
```
- **Web UI**: `http://localhost:3000`
- **FastAPI OpenAPI Docs**: `http://localhost:8000/docs`
- **Neo4j Browser**: `http://localhost:7474`
- **MinIO Console**: `http://localhost:9001`
