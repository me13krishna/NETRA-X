"""
Grounded answerer for the investigation copilot.

Every sentence this produces is derived from a row in the ledger. Nothing is a
string literal describing evidence -- the previous implementation was six
hardcoded paragraphs selected by keyword, which answered "tell me about
NightHalo" with a confident paragraph about a different actor entirely.

The design rule is the product's own: when the ledger cannot answer, say so.
A system whose pitch is "never a black-box guess" cannot have an assistant that
invents a confident answer for every input, so `answered=False` is a normal and
correct outcome here, not a failure.
"""

from typing import Any, Dict, List

from sqlalchemy.orm import Session

from packages.copilot import knowledge, tools


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _has(t: str, phrases) -> bool:
    """Word-boundary keyword match.

    Naive substring matching silently mis-routes: "sha" matches
    "ShadowByte", "count" matches "account", "server" matches "observer".
    That sent "Tell me about ShadowByte" to the provenance branch, which
    answered with unrelated evidence rows and never named the actor -- the
    same class of failure this module exists to fix, one layer down.

    Implemented by tokenising rather than with regex word boundaries: the
    escape form is fragile to pass through tooling, and a silently broken
    guard here is worse than a slightly blunter one.
    """
    import re
    words = re.findall('[a-z0-9]+', t.lower())
    padded = ' ' + ' '.join(words) + ' '
    return any((' ' + p + ' ') in padded for p in phrases)


def _intent(q: str) -> str:
    """Classify the question. Intent selects which rows to pull -- it never
    selects a pre-written answer."""
    t = q.lower()
    if _has(t, ("audit", "chain", "integrity", "tamper", "hash chain")):
        return "integrity"
    if _has(t, ("review queue", "awaiting", "pending", "to review", "queue")):
        return "queue"
    if _has(t, ("shared", "reuse", "reused", "same wallet", "same handle", "overlap")):
        return "shared"
    if _has(t, ("infrastructure", "onion", "favicon", "tls", "hosting", "server")):
        return "infrastructure"
    if _has(t, ("how many", "count", "statistics", "stats", "summary", "overview")):
        return "stats"
    if _has(t, ("evidence", "provenance", "artifact", "sha256", "where did")):
        return "provenance"
    if _has(t, ("list actors", "all actors", "roster", "who is in", "which actors",
                "everyone", "actors do you", "actors are in")):
        return "roster"
    if _has(t, ("case", "cases", "investigation", "investigations")):
        return "cases"
    if _has(t, ("timeline", "recent activity", "what happened", "history",
                "latest", "log", "activity")):
        return "timeline"
    if _has(t, ("decision", "decisions", "accepted", "rejected", "verdict",
                "reviewed", "who reviewed")):
        return "decisions"
    if _has(t, ("source", "sources", "lawful basis", "collection", "where does the data")):
        return "sources"
    return "entity"


def _candidate_terms(q: str) -> List[str]:
    """Pull probable entity names out of the question.

    Deliberately crude: capitalised words, quoted strings, and long alphanumeric
    tokens. Resolution against the ledger is what decides whether a candidate is
    real, so over-generating here is cheap and under-generating is not.
    """
    import re

    terms: List[str] = []
    terms += re.findall(r'"([^"]+)"', q)
    terms += re.findall(r"'([^']+)'", q)
    terms += re.findall(r"\b([A-Z][a-zA-Z0-9]{3,})\b", q)
    terms += re.findall(r"\b([a-z0-9_]{4,}\d[a-z0-9_]*)\b", q)   # handles like nightowl99
    terms += re.findall(r"\b(CLUSTER_[A-Z0-9_]+)\b", q)

    stop = {"tell", "what", "which", "about", "know", "show", "list", "there",
            "linked", "does", "have", "with", "from", "this", "that", "actor",
            "give", "find", "many", "much", "does", "into", "them", "they"}
    out, seen = [], set()
    for t in terms:
        k = t.strip().lower()
        if k in stop or k in seen or len(k) < 3:
            continue
        seen.add(k)
        out.append(t.strip())
    return out


def answer(db: Session, question: str) -> Dict[str, Any]:
    """Answer `question` from the ledger.

    Returns a dict with `answer`, `answered`, `intent`, `citations` (the rows
    the answer rests on) and `tools_used`, so a caller can show the working.
    """
    q = (question or "").strip()
    if not q:
        return {"answer": "No question supplied.", "answered": False,
                "intent": "none", "citations": [], "tools_used": []}

    intent = _intent(q)
    used: List[str] = []
    cites: List[Dict[str, Any]] = []

    # A question naming a real actor is about that actor, whatever topic words
    # it also contains. Resolution against the ledger decides, not the keyword.
    if intent != "entity":
        for term in _candidate_terms(q):
            if tools.resolve_entity(db, term):
                intent = "entity"
                break

    # ---------------------------------------------------------------- stats
    if intent == "stats":
        s = tools.get_ledger_stats(db); used.append("get_ledger_stats")
        text = (
            f"Ledger holds {s['actors']} actors, {s['aliases']} aliases, "
            f"{s['pgp_keys']} PGP keys and {s['wallets']} wallets across "
            f"{s['onion_services']} onion services. Evidence: {s['evidence']} rows "
            f"drawn from {s['artifacts']} artifacts and {s['observations']} observations "
            f"across {s['sources']} sources. "
            f"{s['hypotheses']} attribution hypotheses exist, "
            f"{s['hypotheses_awaiting_review']} awaiting analyst review. "
            f"Audit chain: {s['audit_records']} records, "
            f"{'verified intact' if s['audit_chain_valid'] else 'VERIFICATION FAILED'}."
        )
        return {"answer": text, "answered": True, "intent": intent,
                "citations": [s], "tools_used": used}

    # ------------------------------------------------------------ integrity
    if intent == "integrity":
        s = tools.get_ledger_stats(db); used.append("get_ledger_stats")
        if s["audit_chain_valid"]:
            text = (
                f"The SHA-256 hash chain verifies intact across all {s['audit_records']} "
                f"audit records. Each entry's hash is recomputed from its stored payload and "
                f"checked against the successor's prev_hash, so an edit to any recorded action "
                f"would break verification at that row."
            )
        else:
            text = (f"Audit chain verification FAILED across {s['audit_records']} records: "
                    f"{s['audit_chain_error']}")
        return {"answer": text, "answered": True, "intent": intent,
                "citations": [s], "tools_used": used}

    # ---------------------------------------------------------------- queue
    if intent == "queue":
        rows = tools.get_review_queue(db, limit=8); used.append("get_review_queue")
        if not rows:
            return {"answer": "No hypotheses are currently awaiting analyst review.",
                    "answered": True, "intent": intent, "citations": [], "tools_used": used}
        lines = [f"{len(rows)} hypotheses await analyst review, most confident first:"]
        for r in rows:
            lines.append(f"  {r['subject']} <-> {r['object']}: "
                         f"P={_fmt_pct(r['calibrated_prob'])}, LLR={r['raw_log_lr']:+.2f}")
        return {"answer": "\n".join(lines), "answered": True, "intent": intent,
                "citations": rows, "tools_used": used}

    # --------------------------------------------------------------- shared
    if intent == "shared":
        sh = tools.find_shared_identifiers(db); used.append("find_shared_identifiers")
        handles, wallets = sh["shared_handles"], sh["shared_wallet_clusters"]
        if not handles and not wallets:
            return {"answer": "No identifier in the ledger is currently used by more than one actor.",
                    "answered": True, "intent": intent, "citations": [], "tools_used": used}
        lines = ["Identifiers touched by more than one actor -- the reuse that links personas:"]
        for h in handles:
            lines.append(f"  handle '{h['handle']}' used by {h['actor_count']}: "
                         f"{', '.join(h['actors'])}")
        for w in wallets:
            lines.append(f"  wallet cluster {w['cluster_id']} ({w['addresses']} addresses, "
                         f"{'/'.join(w['chains'])}) controlled by {w['actor_count']}: "
                         f"{', '.join(w['actors'])}")
        return {"answer": "\n".join(lines), "answered": True, "intent": intent,
                "citations": handles + wallets, "tools_used": used}

    # ------------------------------------------------------- infrastructure
    if intent == "infrastructure":
        inf = tools.get_infrastructure(db); used.append("get_infrastructure")
        lines = [f"{len(inf['services'])} onion services on record."]
        if inf["shared_favicon_hashes"]:
            for f in inf["shared_favicon_hashes"]:
                lines.append(f"  favicon mmh3 {f['favicon_mmh3']} appears on "
                             f"{f['service_count']} services -- a clearnet pivot candidate "
                             f"(Shodan: http.favicon.hash:{f['favicon_mmh3']}).")
        if inf["shared_tls_fingerprints"]:
            for t in inf["shared_tls_fingerprints"]:
                lines.append(f"  TLS fingerprint {str(t['fingerprint'])[:24]}... shared by "
                             f"{t['service_count']} services.")
        if not inf["shared_favicon_hashes"] and not inf["shared_tls_fingerprints"]:
            lines.append("  No favicon hash or TLS fingerprint is shared between services.")
        return {"answer": "\n".join(lines), "answered": True, "intent": intent,
                "citations": inf["services"], "tools_used": used}

    # ----------------------------------------------------------- provenance
    if intent == "provenance":
        rows = tools.get_evidence_provenance(db, limit=6); used.append("get_evidence_provenance")
        if not rows:
            return {"answer": "The evidence ledger is empty.", "answered": True,
                    "intent": intent, "citations": [], "tools_used": used}
        lines = ["Most recent evidence, each traceable to the artifact it came from:"]
        for r in rows:
            digest = (r["artifact_sha256"] or "")[:16]
            lines.append(f"  {r['extraction_method']}: {r['value'][:48]} "
                         f"(group {r['dependence_group']}, artifact {digest}...)")
        return {"answer": "\n".join(lines), "answered": True, "intent": intent,
                "citations": rows, "tools_used": used}

    # ---------------------------------------------- roster / cases / history
    def _wrap(text: str, rows: List[Dict[str, Any]], tool: str) -> Dict[str, Any]:
        return {"answer": text, "answered": True, "intent": intent,
                "citations": rows, "tools_used": used + [tool]}

    if intent == "roster":
        rows = tools.list_actors(db)
        lines = [f"{len(rows)} actors on record, most confident first:"]
        lines += [f"  {r['primary_alias']} -- {r['category']}, "
                  f"{_fmt_pct(r['confidence'])}, {r['alias_count']} aliases" for r in rows]
        return _wrap("\n".join(lines), rows, "list_actors")

    if intent == "cases":
        rows = tools.get_cases(db)
        if not rows:
            return _wrap("No investigation cases exist in the ledger.", [], "get_cases")
        lines = [f"{len(rows)} case(s) on record:"]
        lines += [f"  {r['title']} [{r['status']}]" for r in rows]
        return _wrap("\n".join(lines), rows, "get_cases")

    if intent == "timeline":
        rows = tools.get_timeline(db)
        if not rows:
            return _wrap("The audit log holds no recorded activity yet.", [], "get_timeline")
        lines = ["Most recent recorded activity, newest first "
                 "(read from the hash-chained audit log):"]
        lines += [f"  #{r['seq']} {r['action']} on {r['resource_type']} "
                  f"at {r['at']} [{r['entry_hash']}...]" for r in rows]
        return _wrap("\n".join(lines), rows, "get_timeline")

    if intent == "decisions":
        rows = tools.get_decisions(db)
        if not rows:
            return _wrap("No analyst has recorded a decision yet; every hypothesis "
                         "is still awaiting review.", [], "get_decisions")
        lines = [f"{len(rows)} analyst decision(s) recorded:"]
        for r in rows:
            p = _fmt_pct(r["calibrated_prob"]) if r["calibrated_prob"] is not None else "n/a"
            lines.append(f"  {r['decision']} on {r['pair']} (P={p})"
                         + (f" -- {r['notes']}" if r["notes"] else ""))
        return _wrap("\n".join(lines), rows, "get_decisions")

    if intent == "sources":
        rows = tools.get_sources(db)
        if not rows:
            return _wrap("No collection sources are registered.", [], "get_sources")
        lines = ["Collection sources, each with the lawful basis recorded against it:"]
        lines += [f"  {r['name']} [{r['source_type']}] -- lawful basis: "
                  f"{r['lawful_basis']}" for r in rows]
        return _wrap("\n".join(lines), rows, "get_sources")

    # --------------------------------------------------------------- entity
    for term in _candidate_terms(q):
        matches = tools.resolve_entity(db, term)
        used.append("resolve_entity")
        if not matches:
            continue

        m = matches[0]
        profile = tools.get_actor_profile(db, m["actor_id"]); used.append("get_actor_profile")
        links = tools.get_actor_links(db, m["actor_id"]); used.append("get_actor_links")
        evidence_ids: List[str] = []
        shared = tools.find_shared_identifiers(db, actor_id=m["actor_id"])
        used.append("find_shared_identifiers")

        lines = [
            f"{profile['primary_alias']} -- {profile['category']}, "
            f"actor confidence {_fmt_pct(profile['confidence'])}."
        ]
        if profile["aliases"]:
            lines.append(f"  Aliases ({len(profile['aliases'])}): "
                         + ", ".join(a["value"] for a in profile["aliases"][:8]))
        if profile["pgp_keys"]:
            lines.append("  PGP: " + ", ".join(k["key_id"] for k in profile["pgp_keys"]))
        if profile["wallets"]:
            lines.append(f"  Wallets ({len(profile['wallets'])}): "
                         + ", ".join(f"{w['address'][:14]}... [{w['chain']}]"
                                     for w in profile["wallets"][:4]))

        if links:
            lines.append(f"  Attribution links ({len(links)}):")
            for l in links[:6]:
                lines.append(f"    {l['counterpart']}: P={_fmt_pct(l['calibrated_prob'])}, "
                             f"LLR={l['raw_log_lr']:+.2f}, {l['status']}")
            top = links[0]
            ev = tools.get_hypothesis_evidence(db, top["hypothesis_id"])
            used.append("get_hypothesis_evidence")
            evidence_ids = ev.get("evidence_ids", []) if ev else []
            if ev and ev.get("family_totals"):
                fam = ", ".join(f"{k} {v:+.2f}" for k, v in ev["family_totals"].items())
                lines.append(f"  Strongest link ({top['counterpart']}) rests on "
                             f"{ev['independent_families']} independent families: {fam}.")
                if ev["contradictions"]:
                    lines.append(f"  {len(ev['contradictions'])} contradiction(s) recorded "
                                 f"against that link.")
        else:
            lines.append("  No attribution hypothesis links this actor to another persona.")

        if shared["shared_handles"] or shared["shared_wallet_clusters"]:
            for h in shared["shared_handles"]:
                others = [n for n in h["actors"] if n != profile["primary_alias"]]
                lines.append(f"  Shares handle '{h['handle']}' with {', '.join(others)}.")
            for w in shared["shared_wallet_clusters"]:
                others = [n for n in w["actors"] if n != profile["primary_alias"]]
                lines.append(f"  Shares wallet cluster {w['cluster_id']} with {', '.join(others)}.")

        return {"answer": "\n".join(lines), "answered": True, "intent": "entity",
                "citations": [profile] + links, "tools_used": used,
                "resolved_actor": profile["primary_alias"]}

    # --------------------------------------------------- product knowledge
    # Reached only when no ledger entity matched: an analyst asking "what is
    # an LLR" or "where is the review queue" is asking about the system, not
    # about a row. Previously every such question was refused.
    kb = knowledge.lookup(q)
    if kb is not None:
        kb["tools_used"] = used + kb["tools_used"]
        return kb

    # ----------------------------------------------------- universal search
    # An analyst mid-investigation holds a wallet address, a fingerprint or an
    # onion host, not a persona name. resolve_entity knows only actors and
    # aliases, so those all fell through to a refusal.
    for term in _candidate_terms(q) or [w for w in q.split() if len(w) >= 8]:
        hits = tools.universal_search(db, term)
        used.append("universal_search")
        if not hits:
            continue
        lines = [f"'{term}' matches {len(hits)} record(s) in the ledger:"]
        for h in hits[:10]:
            who = f" -- {h['actor']}" if h.get("actor") else ""
            lines.append(f"  [{h['kind']}] {h['value']}{who}"
                         + (f" ({h['detail']})" if h.get("detail") else ""))
        owners = sorted({h["actor"] for h in hits if h.get("actor")})
        if len(owners) > 1:
            lines.append(f"  Used by {len(owners)} distinct actors: {', '.join(owners)} "
                         f"-- identifier reuse across personas.")
        return {"answer": "\n".join(lines), "answered": True, "intent": "search",
                "citations": hits, "tools_used": used}

    # ------------------------------------------------------------ no answer
    terms = _candidate_terms(q)
    hint = f" No ledger entity matches {', '.join(repr(t) for t in terms)}." if terms else ""
    return {
        "answer": (
            "I cannot answer that from the evidence ledger." + hint +
            " I can answer questions about the data (an actor or handle, the "
            "review queue, shared identifiers, infrastructure, provenance, "
            "audit-chain integrity) and about the system itself (how attribution "
            "scoring works, family caps, contradictions, stylometry, exports, "
            "the analyst workflow, guardrails, or where to find something)."
        ),
        "answered": False,
        "intent": intent,
        "citations": [],
        "tools_used": used or ["resolve_entity"],
    }
