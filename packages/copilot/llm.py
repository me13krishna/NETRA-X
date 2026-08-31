"""
Optional Claude-backed copilot.

The deterministic answerer in `answer.py` is the product: it works offline, for
free, and every sentence it emits comes from a ledger row. This module is an
enhancement on top of it -- when an API key is configured, Claude drives the
same ledger tools and can compose across them, follow up, and handle phrasings
the intent classifier does not cover.

Two rules make the enhancement safe rather than a liability:

  1. Claude gets no facts in its prompt. It gets tools, and every fact in the
     answer has to come back from a tool call against the real database.
  2. The system prompt forbids inventing identifiers and requires abstention.
     A system whose pitch is "never a black-box guess" cannot ship an assistant
     that fabricates confident answers.

`anthropic` is an optional dependency ([copilot] extra). If it is missing, or
no credential is configured, `available()` returns False and the caller uses
the deterministic path -- which is the expected state for the offline demo.
"""

import json
import os
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from packages.copilot import tools

MODEL = "claude-opus-5"

SYSTEM = """You are the NETRA-X investigation copilot, embedded in a dark-web \
threat-actor attribution platform used by analysts.

You have tools that read the authoritative evidence ledger. Follow these rules \
without exception:

1. Every factual claim you make must come from a tool result in this \
conversation. Never state an actor name, handle, wallet address, PGP key, \
hash, probability, or LLR score that a tool did not return.
2. If the tools do not contain the answer, say so plainly and stop. Do not \
substitute a related actor, and do not guess. Abstention is a correct answer \
here -- the attribution engine itself abstains below threshold.
3. Report probabilities and log-likelihood ratios exactly as returned. Do not \
round them into stronger claims or describe a 0.55 link as "confirmed".
4. Attribution decisions belong to the human analyst. Describe what the \
evidence shows; never instruct the analyst to accept or reject a hypothesis.
5. Be concise and concrete. An analyst wants the numbers and the reasoning, \
not preamble.

Start by resolving any entity the analyst names against the ledger."""


TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "name": "resolve_entity",
        "description": "Find actors whose primary alias, any alias, or category matches a search term. Use this first whenever the analyst names something.",
        "input_schema": {
            "type": "object",
            "properties": {"term": {"type": "string", "description": "Name, handle or category to search for"}},
            "required": ["term"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "get_actor_profile",
        "description": "Full ledger record for one actor: aliases, PGP keys, wallets, accounts.",
        "input_schema": {
            "type": "object",
            "properties": {"actor_id": {"type": "string"}},
            "required": ["actor_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "get_actor_links",
        "description": "Scored attribution hypotheses connecting this actor to other personas, with calibrated probability and raw LLR.",
        "input_schema": {
            "type": "object",
            "properties": {"actor_id": {"type": "string"}},
            "required": ["actor_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "get_hypothesis_evidence",
        "description": "Per-family evidence breakdown behind one hypothesis, including contradictions. Use to answer 'why do you believe that'.",
        "input_schema": {
            "type": "object",
            "properties": {"hypothesis_id": {"type": "string"}},
            "required": ["hypothesis_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "find_shared_identifiers",
        "description": "Handles and wallet clusters touched by more than one actor -- the identifier reuse that links differently-named personas.",
        "input_schema": {
            "type": "object",
            "properties": {"actor_id": {"type": "string", "description": "Optional: restrict to identifiers this actor touches"}},
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_evidence_provenance",
        "description": "Recent evidence rows with the SHA-256 artifact digest each was extracted from.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer"},
                "kind": {"type": "string", "description": "Optional extraction-method filter, e.g. 'pgp' or 'btc'"},
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_ledger_stats",
        "description": "Counts across the ledger plus audit-chain verification state.",
        "input_schema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
    },
    {
        "name": "get_infrastructure",
        "description": "Onion services and hosting, including favicon hashes and TLS fingerprints shared by multiple services.",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer"}},
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_review_queue",
        "description": "Hypotheses awaiting an analyst decision, most confident first.",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer"}},
            "required": [],
            "additionalProperties": False,
        },
    },
]


def available() -> bool:
    """True when the SDK is installed and a credential is resolvable."""
    if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def _run_tool(db: Session, name: str, args: Dict[str, Any]) -> Any:
    fn = tools.TOOL_REGISTRY.get(name)
    if fn is None:
        return {"error": f"unknown tool {name}"}
    try:
        return fn(db, **args)
    except TypeError as exc:
        return {"error": f"bad arguments for {name}: {exc}"}


def answer(db: Session, question: str, max_turns: int = 6) -> Dict[str, Any]:
    """Answer via Claude with ledger tools. Caller must check `available()`."""
    import anthropic

    client = anthropic.Anthropic()
    messages: List[Dict[str, Any]] = [{"role": "user", "content": question}]
    used: List[str] = []
    citations: List[Dict[str, Any]] = []

    for _ in range(max_turns):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM,
            thinking={"type": "adaptive"},
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

        if resp.stop_reason == "refusal":
            return {"answer": "The request was declined by safety classification.",
                    "answered": False, "intent": "refused",
                    "citations": [], "tools_used": used, "engine": "claude"}

        messages.append({"role": "assistant", "content": resp.content})

        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        if not tool_uses:
            text = "".join(b.text for b in resp.content if b.type == "text").strip()
            return {"answer": text, "answered": bool(text), "intent": "llm",
                    "citations": citations, "tools_used": used, "engine": "claude"}

        # All results for a parallel batch go back in ONE user message; splitting
        # them teaches the model to stop making parallel calls.
        results = []
        for tu in tool_uses:
            used.append(tu.name)
            out = _run_tool(db, tu.name, dict(tu.input))
            if isinstance(out, list):
                citations.extend(x for x in out if isinstance(x, dict))
            elif isinstance(out, dict):
                citations.append(out)
            results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": json.dumps(out, default=str),
            })
        messages.append({"role": "user", "content": results})

    return {"answer": "Reached the tool-call limit without a final answer.",
            "answered": False, "intent": "llm", "citations": citations,
            "tools_used": used, "engine": "claude"}
