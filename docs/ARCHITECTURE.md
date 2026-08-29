# ARCHITECTURE.md — NETRA-X Technical & Methodological Architecture

> **SEE BEYOND. UNMASK THE REAL.**  
> *Authorized Research / Law-Enforcement Oriented / Defensive Use Only*

---

## 🏛️ Methodological Philosophy & Core Principles

1. **COLLECT EVERYTHING PASSIVELY & LEGALLY**: Passive OSINT, synthetic seeds, and self-owned honeypots (`sources.lawful_basis`).
2. **TRUST NOTHING BLINDLY**: Raw artifacts are preserved immutably with SHA-256 digests before extraction.
3. **PRESERVE EVERYTHING IMMUTABLY**: Append-only cryptographic hash-chained audit log (`AuditLog`).
4. **CORRELATE INDEPENDENTLY ACROSS FAMILIES**: Log-Likelihood Ratio ($LLR_i = \ln(m_i / u_i)$) fusion with dependence discounting ($\lambda=0.25$) and family caps.
5. **MODEL UNCERTAINTY VIA ISOTONIC CALIBRATION**: Isotonic regression mapping raw LLR scores to empirical posterior probabilities $P(H_1 \mid E) \in [0, 1]$.
6. **EXPOSE CONTRADICTIONS FIRST-CLASS**: Mutually exclusive signals subtract uncapped penalties ($W_c$) without damping or capping.
7. **AI ASSISTS — MANDATORY ANALYST DECIDES**: AI models emit candidate hypotheses only; human analysts issue final linkage decisions (`ACCEPT` / `REJECT` / `INSUFFICIENT`).

---

## 🏗️ Layered System Architecture

```
+-----------------------------------------------------------------------------------+
|                            NETRA-X WEB UI (Next.js 14)                             |
|    Review Queue | Evidence Waterfall | Graph Explorer | Profile | Multi-Export    |
+-----------------------------------------------------------------------------------+
                                         │  (REST API / JSON)
                                         ▼
+-----------------------------------------------------------------------------------+
|                         FASTAPI MODULAR MONOLITH BACKEND                          |
|  /auth | /actors | /hypotheses | /review | /attribution/evaluate | /audit/verify  |
+-----------------------------------------------------------------------------------+
           │                                 │                                 │
           ▼                                 ▼                                 ▼
+-----------------------+   +-------------------------------+   +-------------------+
|  ATTRIBUTION ENGINE   |   |   POSTGRESQL 16 (AUTHORITATIVE)   |   | NEO4J 5 GRAPH     |
| LLR Fusion, λ=0.25,   |   | Artifacts, Evidence,          |   | Rebuildable Node/ |
| Family Caps, Isotonic |   | Hypotheses, Audit Hash-Chain  |   | Edge Subgraph     |
+-----------------------+   +-------------------------------+   +-------------------+
           ▲                                 ▲
           │                                 │
+-----------------------------------------------------------------------------------+
|                          EXTRACTION & PIPELINE WORKERS                            |
| PGP, BTC, Monero (Abstain), Favicon mmh3, SimHash Clone Detector (>=95%), Stylometry |
+-----------------------------------------------------------------------------------+
                                         ▲
                                         │  (Redis Streams Event Bus)
+-----------------------------------------------------------------------------------+
|                         PASSIVE COLLECTION & ONIONPROBE                           |
|  WARC Writer (ISO 28500), OnionProbe (Favicon, Status, Certs, Banners)            |
+-----------------------------------------------------------------------------------+
```

---

## ⚙️ Key Technical Design Decisions

### 1. PostgreSQL as Single Source of Truth
PostgreSQL 16 is the sole authoritative system of record. All artifacts, extracted evidence items, hypotheses, analyst reviews, and audit logs reside in Postgres. Neo4j graph projections and OpenSearch/pgvector indices are derived and must be 100% rebuildable from Postgres.

### 2. Bayesian Log-Likelihood Ratio (LLR) Evidence Fusion
Evidence items are scored using item LLR:
$$LLR_i = \ln \left( \frac{P(E_i \mid H_1)}{P(E_i \mid H_0)} \right) = \ln \left( \frac{m_i}{u_i} \right)$$
Items belonging to the same `dependence_group` undergo dependence discounting ($\lambda=0.25$):
$$S_{\text{group}} = \text{max}(LLR) + \lambda \sum_{k=2}^{N} LLR_k$$
Group scores are aggregated per evidence family and capped according to `FAMILY_CAPS` (`EXACT_IDENTITY`: 10.0, `FINANCIAL`: 7.5, `INFRASTRUCTURE`: 5.0, `CONTENT_NLP`: 5.0, `STYLOMETRY`: 3.0, `TEMPORAL`: 2.0, `SEMANTIC_HANDLE`: 2.0).

### 3. First-Class Contradiction Penalties
Contradictions (e.g. Temporal Impossibility, PGP Key Conflicts) subtract uncapped penalties $W_c$ directly from total LLR:
$$LLR_{\text{raw}} = \sum S_{\text{family}} - \sum W_c$$

### 4. Cryptographic SHA-256 Audit Hash Chain
Audit entries are appended immutably to `audit_logs`:
$$\text{payload\_hash}_i = \text{SHA256}(\text{payload}_i)$$
$$\text{prev\_hash}_i = \text{SHA256}(\text{record}_{i-1})$$
Any modification to historical records invalidates `verify_chain()`.

---

## 🛡️ Legal Scope & Safety Constraints

- **Passive Collection Only**: All network probes connect exclusively to publicly reachable endpoints over Tor/HTTP.
- **Allow-List Enforcement**: Crawlers enforce `sources.lawful_basis` (`passive_osint`, `synthetic_seed`, `honeypot`).
- **Monero (XMR) Hard Abstention**: Monero address extractions emit $0.0$ score weight (`abstain=True`) due to protocol-level stealth addressing.
- **Investigative Lead Banner**: All exported reports carry the mandatory `ASSESSMENT TYPE: INVESTIGATIVE LEAD` header.
