# ROLE_SAHIL.md — Premium Frontend & Evidence Waterfall Ownership

## 👤 Owner: Sahil
- **Branch**: `feature/frontend-premium`
- **Ownership Scope**: `apps/web/`
- **Core Goal**: Make the UI the standout feature of the demonstration — especially the Evidence Waterfall screen.

---

## 🎯 Detailed Task Breakdown & Priority Order

### 1. Hypothesis Review Queue (`apps/web/src/components/ReviewQueue.tsx`)
- **Deliverables**:
  - Prioritized queue sorted by calibrated posterior probability $P(H_1 \mid E)$.
  - Independent family count badges (e.g. `4 Independent Families`).
  - Red contradiction alert badge (`Contradiction Flagged`).
  - Status filter tabs (`ALL`, `PROPOSED`, `ACCEPTED`, `REJECTED`, `INSUFFICIENT`).
  - Inline analyst decision buttons (`ACCEPT`, `REJECT`, `INSUFFICIENT`).

### 2. Hero Evidence Waterfall Component (`apps/web/src/components/EvidenceWaterfall.tsx`)
- **Deliverables**:
  - Stacked horizontal contribution bar graph showing LLR score per evidence family.
  - Dependence group color tags and visual shading.
  - Red contradiction bars pulling left with penalty callouts (-12.0 LLR, -15.0 LLR).
  - Interactive drill-down modal/drawer on bar click showing raw artifact SHA-256 hash, collection URI, timestamp, extractor version, and dependence group.

### 3. Attribution Intelligence Lab (`apps/web/src/components/AttributionLab.tsx`)
- **Deliverables**:
  - Interactive decision panel with notes textarea.
  - Assessment warning banner (`ASSESSMENT TYPE: INVESTIGATIVE LEAD`).
  - Multi-format export action buttons:
    - **Signed PDF Report**: One-click download via ReportLab endpoint.
    - **STIX 2.1 JSON**: Download STIX 2.1 CTI bundle.
    - **CSV Evidence Ledger**: Download raw CSV table.

### 4. Interactive Graph Explorer (`apps/web/src/components/GraphExplorer.tsx`)
- **Deliverables**:
  - Cytoscape.js interactive property graph visualization.
  - Dynamic edge thickness proportional to LLR contribution score.
  - Filter controls by evidence family, confidence threshold, and valid time window.

### 5. Design Aesthetics & Visual Polish
- **Deliverables**:
  - Deep void black + electric purple $\to$ cyan neon design tokens.
  - Framer Motion transitions and waterfall cascade animations.
  - Loading skeletons and clean empty states.

---

## 📋 Immediate Action Items for Sahil
1. Ensure UI communicates directly with Vivek's REST API (`/api/v1/hypotheses`, `/api/v1/review/{id}`, `/api/v1/exports/...`).
2. Test modal drill-downs for raw SHA-256 provenance hashes.
3. Validate responsive layout for desktop and tablet screens.
4. Update `docs/CONTEXT.md` change log on every commit to `feature/frontend-premium`.
