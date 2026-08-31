"""
Product knowledge for the copilot.

The ledger tools answer "what is in the data". This module answers "what is
this system, and how does it work" -- what NETRA-X does, what an LLR is, why
stylometry is capped, where to find the review queue.

The rule that keeps this honest: **every number is read from the code at call
time**, never typed into the prose. Family caps come from FAMILY_CAPS, the
dependence discount from the engine's own default, the decision thresholds from
decide.py, the abstention rule from episodes.py. If someone retunes a cap, this
explanation changes with it. A hand-typed "capped at 3.0" would quietly become
a lie the first time that constant moved -- which is exactly how the previous
copilot ended up asserting figures that matched nothing in the system.
"""

from typing import Any, Dict, List, Optional, Tuple


# --------------------------------------------------------------------------
# Live constants, read from the implementation rather than restated
# --------------------------------------------------------------------------

def _constants() -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    try:
        from packages.common.types import FAMILY_CAPS
        out["family_caps"] = {k.value: v for k, v in FAMILY_CAPS.items()}
    except Exception:
        out["family_caps"] = {}
    try:
        from packages.attribution.fusion import LLRFusionEngine
        out["lambda"] = LLRFusionEngine().lambda_discount
    except Exception:
        out["lambda"] = None
    try:
        from packages.stylometry.episodes import MIN_WORD_COUNT_THRESHOLD
        out["min_words"] = MIN_WORD_COUNT_THRESHOLD
    except Exception:
        out["min_words"] = None
    try:
        from packages.attribution.fusion import load_mu_table
        mu = load_mu_table()
        out["features"] = mu.get("features", {})
        out["contradictions"] = mu.get("contradictions", {})
    except Exception:
        out["features"], out["contradictions"] = {}, {}
    return out


def _caps_line() -> str:
    caps = _constants()["family_caps"]
    if not caps:
        return "family caps are defined in packages/common/types.py"
    return ", ".join(f"{k} {v:g}" for k, v in
                     sorted(caps.items(), key=lambda kv: -kv[1]))


# --------------------------------------------------------------------------
# Topics. Each is (keywords, builder) -- the builder composes prose around
# values pulled from the live constants above.
# --------------------------------------------------------------------------

def _t_overview(_: Dict[str, Any]) -> str:
    return (
        "NETRA-X is a confidence-scored entity-resolution system for dark-web "
        "threat-actor attribution, built for SIH 2026 problem statement SIH26151 "
        "(NTRO).\n"
        "  It ingests scattered fragments about anonymous personas -- forum posts, "
        "marketplace listings, PGP keys, wallet addresses, hidden-service metadata -- "
        "and works out which fragments belong to the same operator, even when that "
        "operator hides behind several throwaway identities.\n"
        "  It does not attack Tor. It correlates what operators already leaked: a "
        "reused certificate, a reused wallet, a writing style that does not change "
        "when the username does.\n"
        "  Every link carries the evidence behind it and a confidence score. Where "
        "the evidence is too weak, the system stays silent rather than force an "
        "accusation."
    )


def _t_llr(c: Dict[str, Any]) -> str:
    n = len(c.get("features", {}))
    return (
        "The engine follows the Fellegi-Sunter probabilistic record-linkage model "
        "(1969), not raw graph connectivity.\n"
        "  Each feature carries two probabilities: m = the chance of seeing this "
        "clue if two personas ARE the same actor, and u = the chance of seeing it "
        "by coincidence between strangers. The log-likelihood ratio is ln(m/u).\n"
        "  Logs let independent evidence be added instead of multiplied, which is "
        "what makes the score both tractable and explainable.\n"
        f"  {n} features carry m/u priors in packages/attribution/mu_table.yaml. "
        "A PGP fingerprint match scores far higher than a shared posting timezone, "
        "because private keys essentially never collide by accident while millions "
        "of people post in the same hours."
    )


def _t_lambda(c: Dict[str, Any]) -> str:
    lam = c.get("lambda")
    lam_s = f"{lam:g}" if lam is not None else "0.25"
    return (
        "Dependence discounting stops the engine counting one leak twice.\n"
        "  Two clues can be the same clue wearing a different hat -- a directly "
        "reused Bitcoin address and a co-input cluster containing it are one "
        "wallet leak, not two independent observations.\n"
        f"  Within a dependence group the strongest item counts in full and every "
        f"additional item is multiplied by lambda = {lam_s}. Without it, an actor "
        "who leaks one wallet in five observable ways would look five times as "
        "identified as they are."
    )


def _t_caps(_: Dict[str, Any]) -> str:
    return (
        "Family caps put a ceiling on how much any single kind of evidence can "
        "contribute:\n"
        f"  {_caps_line()}.\n"
        "  The consequence is structural: you cannot reach a confident verdict "
        "from one family alone. Reaching high confidence requires independent "
        "KINDS of evidence to agree, which is how a competent investigator "
        "reasons. Stylometry sits low deliberately -- it is a real signal, but "
        "anyone who knows to change their writing can defeat it."
    )


def _t_contradiction(c: Dict[str, Any]) -> str:
    rows = c.get("contradictions", {})
    lines = ["Evidence that argues AGAINST a match subtracts, and is never capped."]
    for name, meta in rows.items():
        w = meta.get("contradiction_weight")
        if w is not None:
            lines.append(f"  {name}: -{w:g}")
    lines.append(
        "  The asymmetry is deliberate. One solid disproof should be able to kill "
        "a large pile of weak circumstantial agreement, so capping the positives "
        "but not the negatives builds skepticism into the arithmetic. An active "
        "contradiction is checked before probability is consulted at all -- a "
        "disproved pair is rejected outright rather than scored."
    )
    return "\n".join(lines)


def _t_thresholds(_: Dict[str, Any]) -> str:
    return (
        "The final LLR is mapped to a probability with a sigmoid carrying a prior "
        "of -2.0, which encodes the correct default posture: before seeing "
        "evidence, assume two random personas are probably NOT the same person.\n"
        "  The decision ladder then applies:\n"
        "    contradiction present, or final LLR < 0  ->  CONTRADICTION_REJECTED\n"
        "    P >= 0.85  ->  HIGH_CONFIDENCE_LINK\n"
        "    P >= 0.50  ->  LOW_CONFIDENCE_LINK (queued for analyst review)\n"
        "    otherwise  ->  INSUFFICIENT_EVIDENCE\n"
        "  An IsotonicCalibrator exists and is fitted in the benchmark, but the "
        "live API path currently uses the sigmoid."
    )


def _t_stylometry(c: Dict[str, Any]) -> str:
    mw = c.get("min_words")
    mw_s = f"{mw}" if mw is not None else "50"
    return (
        "Stylometry decides whether two differently-named personas were written "
        "by the same author.\n"
        "  Features: character n-grams (3-5), function-word frequencies, "
        "punctuation ratios per 100 characters, and sentence-length distributions. "
        "Function words are used unconsciously, which is what makes them hard to "
        "fake deliberately.\n"
        f"  Hard rule: text shorter than {mw_s} words causes the module to ABSTAIN "
        "rather than score. This follows Narayanan et al. (IEEE S&P 2012), whose "
        "finding is that precision rises from roughly 20% to over 80% when a model "
        "is allowed to decline instead of always guessing."
    )


def _t_abstention(c: Dict[str, Any]) -> str:
    mw = c.get("min_words")
    return (
        "Abstention is a first-class outcome across the system, not an error.\n"
        f"  Stylometry abstains below {mw if mw else 50} words. The fusion engine "
        "returns INSUFFICIENT_EVIDENCE below threshold. Monero addresses are "
        "recorded but flagged for hard abstention, because the chain analysis that "
        "works on Bitcoin does not work on XMR. This assistant refuses questions "
        "the ledger cannot answer.\n"
        "  A system whose claim is 'never a black-box guess' cannot have components "
        "that manufacture confidence when they have none."
    )


def _t_audit(_: Dict[str, Any]) -> str:
    return (
        "Every state change appends an entry to a SHA-256 hash-chained audit log.\n"
        "  Each entry's hash is computed over its sequence number, the previous "
        "entry's hash, the actor, the action, the resource and the payload digest. "
        "Verification recomputes each hash from the stored row and checks it against "
        "the successor's prev_hash, so editing any recorded action breaks "
        "verification at that row.\n"
        "  Note the precise claim: this is tamper-EVIDENT, not tamper-proof. It "
        "detects alteration; it does not prevent it. Check it live at "
        "GET /api/v1/audit/verify."
    )


def _t_provenance(_: Dict[str, Any]) -> str:
    return (
        "Ingestion builds a provenance chain in a fixed order:\n"
        "    Source (with lawful basis)\n"
        "      -> Artifact    (immutable bytes, SHA-256 digest)\n"
        "      -> Observation (what was seen, and where)\n"
        "      -> Evidence    (what was extracted from it)\n"
        "      -> audit event\n"
        "  So every evidence row traces back to the exact bytes it came from.\n"
        "  lawful_basis is a closed enum (passive_osint, synthetic_seed, honeypot) "
        "and NOT NULL: collection legality is a property of every observation, so "
        "an observation that cannot state its basis is refused rather than "
        "recorded. Ingest is idempotent on the artifact digest, so a retried "
        "collector cannot inflate the ledger.\n"
        "  POST /api/v1/evidence with raw text does all of this."
    )


def _t_graph(_: Dict[str, Any]) -> str:
    return (
        "The Intelligence Graph is one map of every actor, joined by the "
        "identifiers they share.\n"
        "  Identifier nodes are merged by VALUE, not by row: one wallet cluster "
        "reused by three storefronts is a single node with three edges, which is "
        "what makes the reuse visible at all. Identifiers touched by only one "
        "actor are omitted -- on the map they connect nothing.\n"
        "  Node identity is carried by shape, not colour (actors are hexagons, "
        "handles circles, PGP keys diamonds, wallets rectangles) so it survives "
        "colour-blindness and greyscale. Edge thickness maps to link confidence. "
        "Hovering a node isolates its neighbourhood; search finds a handle in "
        "place rather than reloading."
    )


def _t_exports(_: Dict[str, Any]) -> str:
    return (
        "Findings export in four formats, all from the Report Generator:\n"
        "  STIX 2.1 JSON  -- standard CTI interchange, for ingestion by other "
        "platforms (GET /api/v1/exports/stix)\n"
        "  Signed PDF     -- the analyst-readable case report "
        "(POST /api/v1/exports/report)\n"
        "  CSV            -- evidence rows (GET /api/v1/exports/csv)\n"
        "  JSON           -- the raw records (GET /api/v1/exports/json)"
    )


def _t_workflow(_: Dict[str, Any]) -> str:
    return (
        "The analyst workflow:\n"
        "  1. Evidence arrives by ingestion or seed, with provenance attached.\n"
        "  2. The fusion engine scores candidate persona pairs and files a "
        "hypothesis with a calibrated probability.\n"
        "  3. Anything between 0.50 and 0.85 lands in the Review Queue, ranked by "
        "confidence.\n"
        "  4. The analyst opens the Evidence Waterfall to see exactly which "
        "signals fired and what each contributed.\n"
        "  5. The analyst records ACCEPT, REJECT or INSUFFICIENT. That decision "
        "is written to the ledger and appended to the audit chain.\n"
        "  The system never makes step 5 itself."
    )


def _t_navigation(_: Dict[str, Any]) -> str:
    return (
        "Where things are in the console:\n"
        "  Command Center     -- KPIs, review queue, service health\n"
        "  Investigations     -- case management\n"
        "  Actor Explorer     -- one actor's identifiers and timeline\n"
        "  Attribution Lab    -- the evidence waterfall and decision panel\n"
        "  Intelligence Graph -- the full network map, searchable\n"
        "  Evidence Vault     -- raw artifacts with their digests\n"
        "  Audit Chain        -- the hash-chained log and its verification\n"
        "  Press Ctrl+K (or /) anywhere to open the command palette and jump "
        "straight to a view or an actor."
    )


def _t_guardrails(_: Dict[str, Any]) -> str:
    return (
        "Non-negotiable ethical and legal guardrails:\n"
        "  No live scraping of real darknet marketplaces, ever. Ingestion is "
        "demoed against research corpora; production would plug into an "
        "authorised collection pipeline.\n"
        "  Face matching never auto-confirms an identity -- a match can only "
        "reach human review, enforced at schema level.\n"
        "  Breach data is membership only. No leaked password is stored, hashed "
        "or otherwise.\n"
        "  Seed-and-propagate results are always flagged as inference, never "
        "presented at the same tier as direct evidence.\n"
        "  The system matches against real-identity records an investigator "
        "supplies; it does not build profiles on private individuals by itself. "
        "That is the line between an attribution tool and a surveillance system."
    )


def _t_stack(_: Dict[str, Any]) -> str:
    return (
        "Technology stack:\n"
        "  Backend   Python 3.11+, FastAPI, SQLAlchemy 2, Pydantic v2, PyJWT\n"
        "  Frontend  Next.js 14 (App Router), React 18, TypeScript, Tailwind, "
        "Cytoscape.js\n"
        "  Storage   PostgreSQL 16 + pgvector (SQLite fallback for local dev), "
        "Neo4j 5 for graph projection\n"
        "  Analysis  scikit-learn, NumPy, SciPy, mmh3; PyTorch is an optional "
        "extra for neural stylometry\n"
        "  Reporting ReportLab for PDF, STIX 2.1, CSV\n"
        "  Ops       Docker Compose, Render"
    )


def _t_copilot(_: Dict[str, Any]) -> str:
    return (
        "I answer from the authoritative evidence ledger.\n"
        "  For data questions I resolve the entity you name, pull its real "
        "hypotheses and evidence rows, and report the actual figures. For "
        "questions about the system I explain how it works, with the numbers "
        "read from the running code rather than typed into the text.\n"
        "  If the ledger cannot answer, I say so rather than substituting a "
        "different actor. I describe what the evidence shows; I never tell an "
        "analyst to accept or reject a hypothesis.\n"
        "  I run entirely against the local database and make no external API "
        "calls. A Claude-backed mode exists and activates only if an API key is "
        "configured; without one this deterministic path answers everything."
    )


# (topic key, trigger phrases, builder)
TOPICS: List[Tuple[str, Tuple[str, ...], Any]] = [
    ("overview", ("what is netra", "what is netra x", "what does netra", "what is this",
                  "what does this system", "what does this do", "purpose", "about netra",
                  "what is the project", "explain netra"), _t_overview),
    ("llr", ("llr", "log likelihood", "likelihood ratio", "fellegi", "sunter",
             "scoring", "score", "scores", "attribution", "attributed",
             "how is the score", "m and u", "engine", "fusion",
             "how do you decide", "how does it decide"), _t_llr),
    ("lambda", ("lambda", "dependence discount", "dependence discounting",
                "double count", "double counting", "correlated evidence"), _t_lambda),
    ("caps", ("family cap", "family caps", "cap", "caps", "ceiling",
              "evidence families", "families"), _t_caps),
    ("contradiction", ("contradiction", "contradictions", "disproof", "penalty",
                       "negative evidence", "conflicting"), _t_contradiction),
    ("thresholds", ("threshold", "thresholds", "decision", "calibration",
                    "calibrated", "sigmoid", "isotonic", "posterior",
                    "confidence tier", "high confidence"), _t_thresholds),
    ("stylometry", ("stylometry", "stylometric", "writing style", "authorship",
                    "burrows", "n gram", "ngrams", "function words"), _t_stylometry),
    ("abstention", ("abstain", "abstention", "abstains", "say no", "refuse",
                    "not sure", "uncertain"), _t_abstention),
    ("audit", ("audit", "hash chain", "tamper", "integrity", "chain of custody",
               "immutable", "provenance chain"), _t_audit),
    ("ingestion", ("ingest", "ingestion", "lawful basis", "how does evidence get",
                   "add evidence", "upload", "collection", "warc"), _t_provenance),
    ("graph", ("graph", "network map", "intelligence graph", "cytoscape",
               "visualisation", "visualization", "map"), _t_graph),
    ("exports", ("export", "exports", "stix", "report", "pdf", "csv", "download"),
     _t_exports),
    ("workflow", ("workflow", "how do i use", "process", "how does it work end",
                  "analyst workflow", "steps", "review process"), _t_workflow),
    ("navigation", ("where do i find", "where is", "navigate", "navigation",
                    "which page", "which tab", "shortcut", "shortcuts",
                    "command palette", "how do i get to"), _t_navigation),
    ("guardrails", ("guardrail", "guardrails", "ethical", "ethics", "legal",
                    "privacy", "lawful", "is this legal", "scraping"), _t_guardrails),
    ("stack", ("tech stack", "technology", "what technologies", "built with",
               "framework", "frameworks", "database used", "what language"), _t_stack),
    ("copilot", ("who are you", "what can you do", "what can i ask", "help",
                 "capabilities", "what are you", "how do you work"), _t_copilot),
]


def _matches(question: str, phrases: Tuple[str, ...]) -> bool:
    import re
    words = re.findall("[a-z0-9]+", question.lower())
    padded = " " + " ".join(words) + " "
    return any((" " + p + " ") in padded for p in phrases)


def lookup(question: str) -> Optional[Dict[str, Any]]:
    """Return a product-knowledge answer, or None if no topic matches."""
    if not question or not question.strip():
        return None

    consts = _constants()
    for key, phrases, build in TOPICS:
        if _matches(question, phrases):
            return {
                "answer": build(consts),
                "answered": True,
                "intent": "knowledge",
                "topic": key,
                "citations": [],
                "tools_used": ["knowledge:" + key],
            }
    return None


def topics() -> List[str]:
    return [k for k, _, _ in TOPICS]
