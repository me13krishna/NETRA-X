# NETRA-X — Architecture

## Problem statement (verbatim, condensed)

**SIH26151 — Dark web threat actor de-anonymization**, National Technical Research Organisation (NTRO). Software track, Blockchain & Cybersecurity theme.

> Build a system for the de-anonymization of dark web threat actors and link them to suspect real-world entities, via three required capabilities:
> 1. Finding misconfigurations in Tor hidden services (exposed status pages, TLS certs tied to clearnet domains, default banners, descriptor inconsistencies) and matching to clearnet infrastructure.
> 2. Mapping threat actors across multiple marketplaces into a single relationship graph of handles, PGP keys, wallets, and trust links.
> 3. Using AI-based stylometric and behavioral analysis to link rebranded or migrated personas to known threat actors.
>
> The system must work in an autonomous mode, provide a queryable analytical front end, and export results as CSV, JSON, and report formats — covering actor profiles, identifiers, infrastructure indicators, persona linkages, attribution confidence, category, last scan date, and source.

## System architecture — four modules + a fusion engine + a delivery layer

### Module 1 — Infra-misconfig matcher
Finds Tor hidden services that leaked clearnet-identifying infrastructure. Built by wrapping **OnionScan** rather than rebuilding it. Checks TLS certificate hashes against Certificate Transparency logs (`crt.sh`) for clearnet reuse, favicon hashes against Shodan's favicon index, and scans for exposed status pages, default banners, and descriptor inconsistencies. Extended with web-template structural hashing for self-hosted storefronts.

### Module 2 — Entity-relationship graph
Extracts identifiers from ingested text (regex + NER: handles, PGP fingerprints, wallet addresses, emails, self-disclosed cross-platform contacts, referral codes, vouch/trust language) and links them into a property graph. Ingestion built on **TorBot**; graph built with NetworkX. Nodes are identifiers; edges are co-occurrence or directed, weighted trust relationships.

### Module 3 — Behavioral/stylometric persona linker
Detects when two differently-named personas are the same author (persona-to-persona), and — where evidence supports it — matches a persona's writing style to a real-world public identity (cross-domain). Built on TF-IDF and function-word/punctuation features, trained on **VeriDark** (github.com/bit-ml/VeriDark — a real, public, dark-web-specific authorship dataset). Widened beyond pure stylometry to include content-reuse fuzzy hashing (catches copy-pasted listings across a rebrand), chronotype/timezone inference, locale signals, and modus-operandi fingerprinting.

The model is allowed to abstain rather than always guess, following the precision/recall tradeoff demonstrated in Narayanan et al., *"On the Feasibility of Internet-Scale Author Identification,"* IEEE S&P 2012 — precision rises from ~20% to >80% when the model only answers its most confident cases.

### Module 4 — Delivery layer
Web dashboard: search by handle, wallet, PGP fingerprint, or date range; graph visualization; confidence breakdown per link showing exactly which signals fired; CSV/JSON/report export; and a scheduler that re-runs ingestion and infra-matching at intervals, satisfying the spec's continuous/autonomous-mode requirement.

## The fusion engine — the system's actual differentiator

Weighted, probabilistic entity resolution following the **Fellegi-Sunter record-linkage model**, not raw graph connectivity. Every candidate pair of personas gets a composite confidence score built from weighted signals, multiplied by a source-reliability factor, then thresholded:

- **> 0.7** — confident link
- **0.4 – 0.7** — flagged for human review
- **< 0.4** — discarded

| Signal | Confidence weight | Why |
|---|---|---|
| PGP key reuse across handles | Very high | Private keys are not casually cloned or shared |
| Wallet address reuse | High | Real leak, though mixers can weaken it |
| TLS cert / favicon / template match | High | Rarely accidental — sloppy reused infrastructure |
| Self-disclosed cross-platform contact | High | The actor posted this themselves |
| Referral code reuse | High | Persistent identifier, same logic as wallet reuse |
| Stylometric similarity | Medium, probabilistic | Real signal, but adversarially defeatable |
| Trust/vouch graph proximity | Low-medium | Indicates relationship, not certainty |
| Shared generic software banner | Low (denylisted) | Thousands of unrelated vendors share templates |

Confidence **diffuses** partially through the trust graph from well-attributed actors to closely-linked, unresolved associates. Where a real, confirmed identity exists (e.g. an already-caught associate), it becomes a **seed** for structural propagation (Narayanan & Shmatikov, *"De-anonymizing Social Networks,"* IEEE S&P 2009) — always flagged explicitly as inference, never presented at the same confidence tier as direct evidence.

## Real-world identity resolution

Beyond linking personas to each other, the system can surface a candidate real-world identity when evidence supports it:
- Cross-domain stylometry against a public background corpus (abstains below threshold)
- PGP keyserver lookup (`keys.openpgp.org`)
- Username-reuse checking across clearnet platforms (Sherlock/Maigret)
- HIBP breach-**membership** checking (which breaches an email appeared in — never leaked passwords, which are never stored)
- Face detection + embedding comparison — **guardrailed**: never auto-merges an identity or auto-feeds the confidence score. Always routes to a human-review gate first.

## Data sourcing

No live scraping of real darknet markets. Ingestion is demoed against VeriDark and a public academic darknet-market research archive. Disclosed explicitly in the pitch: *"ingestion is demoed against a public research corpus; production would plug into NTRO's own authorized collection pipeline and licensed threat-intelligence feeds."*

## Test environment

A self-hosted Tor v3 onion service, run in an isolated VM, with deliberately planted misconfigurations (reused TLS certificate, exposed status page, un-stripped banner, shared favicon) so Module 1 has a real, live target to detect on demand.

## Spec compliance

All 18 requirement line items from NTRO's problem statement — misconfig detection, relationship graph (including trust links), stylometric/behavioral linking, real-identity linking, continuous gathering, autonomous mode, timeline query, actor profiles, identifiers, infra indicators, persona linkages, attribution confidence, category, last-scan-date, source, source reliability, and CSV/JSON/report export — are each covered by a concrete module or engine described above. Nothing rests on an unaddressed assumption.

## Build roadmap

Four MVP stages, each a complete demoable product:

1. **Ingestion, extraction, raw graph** — a searchable, exportable tool proving raw connectivity works (see MVP1.md)
2. **Fusion engine + full product** — real weighted confidence scoring, the complete dashboard, and autonomous scheduling; this is the minimum viable *submission* (see MVP2.md)
3. **Live infra matching + behavioral signals** — the OnionScan-based misconfig matcher running against a real self-hosted test service, plus stylometry (trained on VeriDark) and the cheap identity-enrichment signals (PGP keyserver, username reuse, HIBP breach-membership, content-reuse hashing)
4. **Real-identity resolution + full integration** — cross-domain stylometry against a public background corpus, seed-and-propagate from confirmed anchors, confidence diffusion, the guardrailed face-match module, and final integration into one coherent pitch

MVP 1 and MVP 2 are detailed in full in their own documents. MVP 3 and MVP 4 follow the same module boundaries described above.
