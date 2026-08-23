# NETRA-X

**A confidence-scored entity-resolution system for dark web threat actor de-anonymization.**

Built for **Smart India Hackathon 2026 — Problem Statement SIH26151**, sponsored by the National Technical Research Organisation (NTRO). Software track, Blockchain & Cybersecurity theme.

## What it does

Ingests scattered fragments of information about anonymous dark-web personas — forum posts, marketplace listings, PGP keys, wallet addresses, hidden-service metadata — and determines which fragments belong to the same real actor, even when that actor deliberately hides behind multiple throwaway identities. It does not attack Tor. It correlates things operators already leaked: a reused certificate, a reused wallet, a writing style that doesn't change when the username does.

An investigator can search a handle, wallet address, or PGP fingerprint and get back a graph of every other persona that's provably or probably the same actor — each link labeled with its evidence and a confidence score, never a black-box guess. Where evidence is strong enough, a link can point to an actual real-world identity; where it isn't, the system stays silent rather than force an accusation.

## Documents

| Doc | Contents |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Full system design — modules, fusion engine, workflow, data sourcing, spec compliance |
| [docs/MVP1.md](docs/MVP1.md) | MVP 1 — ingestion, extraction, raw graph. A real, searchable, exportable tool. Pair-wise task breakdown. |
| [docs/MVP2.md](docs/MVP2.md) | MVP 2 — fusion engine + full product (dashboard, autonomy). The minimum viable submission. Pair-wise task breakdown. |
| [schema/actor_profile.schema.json](schema/actor_profile.schema.json) | The canonical data model every module writes into |

**Roadmap:** 4 MVP stages total — MVP 1–2 detailed above; MVP 3 (live infra matching + behavioral signals) and MVP 4 (real-identity resolution + integration) are scoped in ARCHITECTURE.md and will get their own detailed docs closer to build time.

## Team structure

Three pairs, each owning a coherent domain across every build stage:

- **Pair A — Core Backend** (data store, graph engine, fusion/scoring logic): Krishna, Chaitanya
- **Pair B — Signal Intelligence** (text/entity extraction, stylometry, behavioral modeling): Varsharani, Sakshi
- **Pair C — Product & Live Systems** (infra fingerprinting, dashboard, integration, demo): Vivek, Sahil

## Status

MVP 1 and MVP 2 are specified in detail and ready to build. MVP 3 (live infra matching + behavioral signals) and MVP 4 (real-identity resolution + full integration) follow the same architecture, detailed as each stage is reached.
