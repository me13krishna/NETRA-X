# MERGE_STRATEGY.md — Practical Git Branching & Merge Strategy

Practical branching and merge guide for the NETRA-X development team.

---

## 🌿 Branch Structure

```text
main                      ← Stays stable (production-ready MVP)
 ├── feature/ml-attribution    ← Krishna only
 ├── feature/backend-ledger    ← Vivek only
 └── feature/frontend-premium  ← Sahil only
```

---

## 🔒 Strict Ownership Rules

| Person | Allowed Directories | Forbidden Directories |
|--------|---------------------|-----------------------|
| **Krishna** | `packages/attribution/`, `packages/stylometry/`, `seed/`, `bench/` | `apps/api/`, `apps/web/`, `workers/` |
| **Vivek** | `apps/api/`, `packages/evidence/`, `workers/`, `packages/schemas/` | `apps/web/` |
| **Sahil** | `apps/web/` | Everything else |

---

## 🔀 Recommended Merge Order

When integrating features back into `main`:

1. **Vivek Merges First (`feature/backend-ledger` $\to$ `main`)**:
   - Establishes updated database schema, SQLAlchemy models, and REST endpoints.
2. **Krishna Merges Second (`feature/ml-attribution` $\to$ `main`)**:
   - Integrates attribution engine, stylometry verifier, and synthetic benchmark generators.
3. **Sahil Merges Last (`feature/frontend-premium` $\to$ `main`)**:
   - Integrates Review Queue, Evidence Waterfall UI, and Cytoscape graph components connected to Vivek & Krishna's API contracts.

```bash
# Standard Merge Workflow
git checkout main
git pull origin main
git merge feature/<your-feature-branch> --no-ff
python -m pytest tests/test_backend.py
python -m pytest tests/test_e2e_hero.py
git push origin main
```

---

## ⚠️ Conflict Prevention Rules

1. **Never edit the same file on two different feature branches.**
2. **Prefer adding new specialized files over editing shared ones.**
3. **Shared Schemas (`packages/schemas/`)**: Vivek updates `packages/schemas/models.py`; Krishna and Sahil submit requests for schema updates.
4. **Update `CONTEXT.md` on Every Commit**: Document what changed, who changed it, and why.
5. **Keep `main` Green**: Never push broken code to `main`. Always run `pytest tests/test_backend.py` before pushing.
