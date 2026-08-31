# MVP 2 — Fusion engine + full product (dashboard, autonomy)

**Goal:** turn raw graph connectivity into an actual attribution system, and turn MVP1's tool into the real, fully-usable product — this is your minimum viable *submission*. (Merges what were previously separate "fusion engine" and "dashboard/autonomy" stages — they belong together: the scoring engine only matters once there's a real product surfacing it.)

**Checkpoint / demo bar:** the rebrand pair from MVP1 now carries a real, explainable confidence score above the "confident link" threshold, with a visible evidence breakdown — and it's all sitting inside a real app: searchable, browsable, exportable, and running on a schedule without anyone manually re-triggering it.

## Pair A — Core Backend

- Source-reliability multiplier — wires the A–F grades from MVP1 into the scoring formula
- The scoring core:
  - Weight table for every signal type (see ARCHITECTURE.md for the full table)
  - Composite scoring formula (Fellegi-Sunter-style weighted probability, not raw connectivity)
  - Threshold logic: > 0.7 confident, 0.4–0.7 flagged for review, < 0.4 discarded
  - Pairwise-comparison module — explicitly its own function, called by the scorer, not buried inline
  - Evidence-log generator — human-readable "why," not a bare number
- The autonomous scheduler — re-runs ingestion + scoring at intervals, satisfies the spec's continuous/autonomous-mode requirement
- Graph-serialization + confidence/evidence API endpoints for the frontend to consume

## Pair B — Signal Intelligence

- Trust-edge weighting (vouch frequency + reciprocity feed into edge weight)
- Rule-based category tagger (drugs / arms / stolen data / money laundering / terror financing / other), built behind a swappable interface so it can become a trained classifier later without touching downstream code
- A small labeled validation set — a handful of known-true and known-false synthetic pairs — to sanity-check the scoring formula before anyone trusts its output
- Groundwork for MVP3: behavioral-fingerprint feature pipeline, VeriDark preprocessing finished and ready

## Pair C — Product & Live Systems

- Wallet clustering (common-input-ownership heuristic) — expands a known wallet into a full cluster of addresses belonging to the same owner
- Review-queue data contract *and* its UI — the state machine for flagged (0.4–0.7) links: pending → confirmed/rejected, with a human confirmation feeding back into `attribution_confidence`
- Configurable weight-table interface — so Pair A's hand-tuned weights are tunable without a redeploy
- **The full dashboard** — search/filter by handle, wallet, PGP fingerprint, or date range; interactive graph visualization; confidence + evidence display per link; CSV/JSON/report export. This is the heaviest single piece of work in this stage — everything else in the project ultimately gets looked at through this screen.

## Dependency order

Pair A's scoring core is the center of this stage — B's weighting refinements and C's wallet clustering both feed into it, and C's dashboard consumes its output via the API. This is the most interdependent stage of the whole build; sync early and often, not just at the end.

## Out of scope for MVP 2 (deliberately deferred)

- Live infra signals (MVP3) — the weight table has a slot for them, but nothing populates it yet
- Stylometric and behavioral signals (MVP3) — same: slot exists, not populated
- Real-world identity resolution, seed-and-propagate, confidence diffusion, face-matching (MVP4)
