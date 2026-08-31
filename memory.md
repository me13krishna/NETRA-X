# NETRA-X — Project Memory

This file exists so any future session (human or AI) picking up this project has the full context behind the current docs, not just the current state. `README.md` / `ARCHITECTURE.md` / `MVP1.md` / `MVP2.md` describe *what the project is now*; this file explains *how it got there and why*, so decisions don't get silently re-litigated or reversed by accident.

## What this project is

A confidence-scored entity-resolution system for dark-web threat-actor de-anonymization, built for **Smart India Hackathon 2026, Problem Statement SIH26151**, sponsored by NTRO (National Technical Research Organisation). Software track, Blockchain & Cybersecurity theme.

## How SIH26151 got picked over the alternatives

The team evaluated the real, verified SIH 2026 problem statement list (226 total, pulled directly from the official portal / GitHub mirror — not guessed) and scored candidates on a transparent heuristic (track, theme fit, keyword relevance, sponsor prestige, restricted-data risk). Top contenders compared head-to-head against SIH26151:

- **SIH26153** (AI network attack forecasting / "world models," also NTRO, same top score 19.0) — rejected as primary because it has a hard, numeric, unforgiving pass/fail bar (must beat a logistic-regression baseline with real F1/precision/recall), which is genuinely research-grade difficulty and a real risk without deep ML talent on the team. SIH26151's difficulty is breadth-hard, not depth-hard, and its judging is open-ended rather than a numeric trap.
- **SIH26091** (rural micro-entrepreneur financial advisory, MoSJE) — rejected: no security/blockchain angle, low technical difficulty, doesn't fit team's demonstrated skills (crypto/ledger background from the NETI project).
- **SIH26187** (border CCTV video analytics, MHA/SSB) — rejected: technically the *easiest* of everything compared (mostly wiring together pretrained CV models), but that's exactly why it's the single most saturated hackathon project category nationally — easy to build, hard to win because of competition volume, and it has real unaddressed civil-liberties/FRS framing risk.

**Why 151 won:** best fit to the team's actual strength (the team's other project, NETI, is a cryptographic exam-integrity ledger — Merkle trees, hash chains, k-of-n key splitting, append-only grants), open-ended judging (no numeric benchmark to visibly fail), and by the time this was settled, a large amount of architecture/prior-art research was already sunk into it, which is itself a real advantage over competitors starting cold.

## Key real research this design is grounded in (not invented — cite these if asked)

- **OnionScan** (github.com/s-rah/onionscan, and the actively-maintained fork at github.com/nao1215/onionscan) — open-source Tor hidden-service misconfiguration scanner. Module 1 wraps this rather than rebuilding it.
- **TorBot** (github.com/DedSecInside/TorBot) — dark-web OSINT crawler, 4.7k★, actively maintained. Used for ingestion.
- **VeriDark** (github.com/bit-ml/VeriDark) — real academic authorship-verification/identification datasets sourced from dark-web Reddit communities and illicit-market forums. Used to train the stylometry module. **Access note:** only `MiniDarkReddit` (small, ~200-400 samples/split) is publicly downloadable via Google Drive with no approval. The larger, more useful sets (DarkReddit+, SilkRoad1, Agora) require a Zenodo access-request form (institutional email, stated use, ethics acknowledgment) — likely too slow to clear for hackathon timelines. Their published ethics policy explicitly forbids using the dataset to unmask undercover agents, journalists, dissidents, or whistleblowers — worth citing directly in the pitch as reinforcing (not conflicting with) this project's own guardrails.
- **Narayanan, Paskov et al., "On the Feasibility of Internet-Scale Author Identification," IEEE S&P 2012** — the real paper behind the stylometry module's abstention design. Key number: precision rises from ~20% to >80% when the model is allowed to abstain rather than always guess. This is why the fusion engine's threshold system exists.
- **Narayanan & Shmatikov, "De-anonymizing Social Networks," IEEE S&P 2009** — the real paper behind "seed-and-propagate": if you have a confirmed real identity (e.g. an already-caught associate) as a seed, you can structurally propagate identification outward through a social/trust graph. This is the technique behind the "what if one of his friends was already caught" scenario discussed early in planning.
- **Fellegi-Sunter probabilistic record linkage (1969)** — the formal model behind the fusion engine's weighted, thresholded scoring. Not a naive "if they share anything, merge them" graph.
- **NATO Admiralty System** — the A–F / 1–6 source-reliability grading scale, used for `provenance.sources[].reliability` instead of inventing a custom scheme.
- **Have I Been Pwned (HIBP)** — legitimate breach-*membership* checking API. Used explicitly for membership only; the project deliberately never stores actual leaked passwords/credentials, hashed or otherwise — that would cross from "attribution tool" into unauthorized possession of stolen data.
- **data.gov.in** hosts a real dataset — "Year-wise Number of Cyber Security Incidents (CERT-In), 2020–2024" — useful as a citation for the pitch's stakes ("CERT-In recorded 1.5M incidents in 2023"), not as training data.

## Non-negotiable ethical/legal guardrails (do not weaken these)

- **No live scraping of real darknet marketplaces**, ever, in the demo or build. Ingestion is demoed against VeriDark + a public academic research corpus. The disclosure line to say explicitly in any pitch: *"ingestion is demoed against a public research corpus; production would plug into NTRO's own authorized collection pipeline."*
- **Face matching never auto-confirms an identity.** Detection + embedding comparison is allowed to run automatically; a match only ever reaches `flagged_for_human_review` — a human must explicitly confirm before it can affect any actor's confidence score. This is enforced at the schema level (`visual_fingerprint.face_match_status` enum has no automatic "confirmed" state).
- **Breach data: membership only, never credentials.** `linked_emails[].breach_membership` stores which breaches an email appeared in — never a leaked password, hashed or plaintext.
- **Seed-and-propagate results are always flagged as inference**, never presented at the same confidence tier as direct evidence (PGP/wallet/cert match). Proximity to a caught associate is a lead, not proof.
- **The system matches against real-identity records it's given by an investigator; it does not go out and build profiles on private individuals on its own.** This is the line between "attribution tool" and "unauthorized surveillance system."
- The team's own test Tor onion service (for testing Module 1) should only ever be run against **their own self-hosted, isolated instance** — never a real, live onion service.

## Architecture summary (full detail in ARCHITECTURE.md)

Four modules + a fusion engine + a delivery layer:
1. **Infra-misconfig matcher** — OnionScan + `crt.sh` (Certificate Transparency) + Shodan favicon index + web-template hashing
2. **Entity-relationship graph** — TorBot ingestion + regex/NER extraction + NetworkX graph
3. **Behavioral/stylometric persona linker** — VeriDark-trained model, widened to include content-reuse fuzzy hashing, chronotype, locale signals, modus operandi
4. **Delivery layer** — dashboard, scheduler (autonomous mode), export

**Fusion engine** (the actual differentiator): Fellegi-Sunter-style weighted composite scoring, thresholded (>0.7 confident / 0.4-0.7 review / <0.4 discard), multiplied by source-reliability grade, with confidence diffusion through the trust graph.

Full data model: `schema/actor_profile.schema.json` — every module writes into one section of this canonical record.

## How the MVP plan evolved (so nobody re-derives this from scratch)

1. Started from the PS's literal 3 capabilities.
2. Audited against the actual spec text and found real gaps (no "category" field, no source-reliability weighting, trust-links assumed but not designed, autonomous mode left as stretch-only) — all closed with concrete designs.
3. Expanded into a 12-stage, then 14-stage workflow once the full schema (visual forensics, marketplace metadata, wallet clustering, human-review gate) was accounted for.
4. Restructured for a 6-person team into 6 sequential MVP checkpoints, each independently demoable.
5. Regrouped the 6 solo roles into **3 pairs** (natural dependency pairs: backend+graph, extraction+ML, security+frontend) so nobody works alone and pairs have built-in review partners.
6. **Consolidated 6 MVPs down to the current 4** (user's explicit request): MVP1 unchanged; MVP2 = old fusion engine + dashboard/autonomy merged; MVP3 = old infra-matcher + stylometry/cheap-signals merged; MVP4 = old real-identity-resolution + integration, unchanged.
7. MVP1's scope was later deliberately increased (search, interactive graph view, evidence-per-connection, export) so it stands as a real, presentable tool even if the build stops there — but the *real weighted confidence score* was deliberately kept out of MVP1 and left in MVP2, to avoid overclaiming work that isn't done yet. MVP1's "connection-strength count" is explicitly labeled provisional, unweighted, and cannot yet distinguish a meaningful match (PGP key) from a coincidental one (shared generic template).

**Honest assessment on record:** MVP1 alone is useful as infrastructure/de-risking, not as a standalone investigative tool — it can surface connections but can't yet judge them, which is the entire point of MVP2. Don't let a future session or teammate oversell MVP1 as more than that.

## Team

Three pairs, real names on record:
- **Pair A — Core Backend** (data store, graph engine, fusion/scoring): **Krishna, Chaitanya**
- **Pair B — Signal Intelligence** (extraction, stylometry, behavioral modeling): **Varsharani, Sakshi**
- **Pair C — Product & Live Systems** (infra fingerprinting, dashboard, integration, demo): **Vivek, Sahil**

## Repository

`github.com/kevivek-cyber/NETRA-X`, `main` branch. **House rule: no Claude/AI attribution in any commit message or file, ever** — the user explicitly required this; keep every future commit clean of it.

## Current build status (as of this writing)

- **No code has been written or run yet.** Everything pushed so far is planning/spec documents (`README.md`, `ARCHITECTURE.md`, `MVP1.md`, `MVP2.md`, `schema/actor_profile.schema.json`).
- An earlier, now-superseded draft (simpler, pre-schema-expansion version) exists locally at `C:\Users\Vivek\Desktop\sih2026-151-threat-attribution\` — `extract.py`, `graph_builder.py`, a synthetic-data generator, and a generated `Architecture_Document.pdf`. This was written before the MVP1 scope was expanded (search/viz/export/evidence-display) and before the 6→4 MVP consolidation — treat it as reference/scrap, not something to build directly on top of, since it predates several design changes.
- **MVP3 and MVP4 do not have their own detailed pair-wise docs yet** — only scoped at a summary level in `ARCHITECTURE.md`'s roadmap section. Write these the same way MVP1.md/MVP2.md were written when the team gets closer to needing them.
- Next real step whenever the team is ready: actually build MVP1 — the data store, extractors, graph, search, and visualization — against the schema and task list already locked in.
