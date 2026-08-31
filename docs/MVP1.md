# MVP 1 — Ingestion, extraction, raw graph

**Goal:** a real, presentable tool — not just proof the pipeline works. Feed in records, search a handle, see who it's really connected to, see *why*, export the result. The full weighted confidence engine is still MVP 2's job, but MVP1 should stand on its own if the clock runs out here.

**Checkpoint / demo bar:** search `zx_reaper`, the tool surfaces `nightowl99` as the same actor, shows the shared PGP fingerprint and wallet as the reason, and lets you export that finding.

## What MVP1 delivers as a product

Not a script that dumps a graph to a terminal — an actual small tool:
- **Search bar:** type a handle, wallet, or PGP fingerprint, get back everything connected to it
- **Visual graph:** an interactive network view (not a static image) — click a node, see its connections highlight
- **Evidence per connection:** every edge says *why* two nodes are linked ("shared PGP fingerprint," "shared wallet," "shared Telegram handle") — not just a bare line
- **A simple connection-strength indicator:** not the full weighted fusion score (that's MVP2), but a first-pass count — "linked via 2 shared identifiers" reads very differently from "linked via 1 shared identifier," and costs almost nothing to add now
- **Export:** CSV/JSON of any search result — hand someone a file, not just a screenshot

## Pair A — Core Backend

- Shared data store / schema — the `ActorProfile` contract every other pair writes into (build this first or fastest; it's the one dependency everyone else needs)
- Pluggable source connectors: VeriDark loader, synthetic-record loader, TorBot wrapper, manual-upload path
- Retry-with-backoff on failed fetches
- Circuit rotation via `stem` for repeated scans
- Deduplication logic (a record scraped twice shouldn't double-count)
- Record versioning (track when a listing changes over time)
- NetworkX graph builder — consumes Pair B and Pair C's extracted output into nodes/edges
- The unweighted "shared-identifier candidate" preview pass — this *is* the MVP1 demo
- **Search backend:** query the graph by handle/wallet/PGP fingerprint and return the connected subgraph, not just "is there a link" — this is what Pair C's search UI calls
- **Simple connection-strength count:** number and type of shared identifiers per link — deliberately not weighted (no "PGP > banner" prioritization yet), just an honest count, clearly labeled as provisional so nobody mistakes it for MVP2's real confidence score

## Pair B — Signal Intelligence

- Text identifier extraction: PGP fingerprints, PGP client/version signature, wallet addresses (BTC/ETH/XMR), handles, emails, self-disclosed cross-platform contacts (Telegram/Session/Signal/Jabber), referral codes
- Vouch/trust-language extraction ("vouched for by," "confirmed trade with")
- NER complement (spaCy) for anything regex misses
- Entity normalization (handle case-folding, wallet-address checksum validation)
- Marketplace-metadata extraction (shipping hints, vendor tier, join date, feedback text)
- Early groundwork for MVP5: download VeriDark's MiniDarkReddit, do an initial pass at the data

## Pair C — Product & Live Systems

- Visual & file forensics: perceptual image hashing (pHash), EXIF metadata extraction, document property extraction, face-detection flag (detection only — matching is MVP 6, and even then it's human-review-gated, never automatic)
- Source-reliability schema (the A–F Admiralty-System grading structure — populated with real logic in MVP2, defined now)
- **Interactive graph view** (pyvis is the fast option — Python-native, produces a real clickable network visualization with no separate frontend framework needed)
- **Search UI** — a real search bar wired to Pair A's search backend, not a static dump
- **Evidence display** — surface each edge's "why" (the signal type already stored on the graph edge) directly in the UI, next to the connection
- **Export button** — CSV/JSON of a search result

## Dependency order

Pair A's data store should be moving first or fastest — Pairs B and C are both writing into it. Once its shape is settled (even a first draft), B and C run fully in parallel. Pair A's graph-builder task naturally lands last, since it integrates B and C's output into the actual demo.

## Out of scope for MVP 1 (deliberately deferred)

- **Real weighted confidence scoring** — MVP1's "connection-strength count" is an honest, unweighted count of shared identifiers, clearly labeled as provisional in the UI. It does not distinguish a PGP-key match (near-certain) from a shared generic banner (near-meaningless) — that discrimination is MVP2's fusion engine, and MVP2 replaces this count with the real score, not adds to it
- Live Tor/onion-service scanning (MVP 4)
- Stylometric modeling (MVP 5)
- Real-world identity resolution (MVP 6)

## Why this scope increase, not more

Search, visualization, evidence display, and export make MVP1 a real tool instead of a script — cheap additions since they mostly expose data the graph already has. What we deliberately did **not** pull forward: the weighted scoring model itself. Faking a "confidence score" without the real Fellegi-Sunter weighting behind it would be worse than an honest raw count — it would look like MVP2's work already existed when it doesn't, which is exactly the kind of overclaim this whole project has been careful to avoid everywhere else.
