"""
NETRA-X investigation copilot.

`ask()` is the single entry point. It prefers the Claude-backed path when a
credential and the optional SDK are present, and otherwise answers
deterministically from the same ledger tools. Both paths read the same rows
through packages.copilot.tools, so the offline answer is never less grounded
than the online one -- only less fluent.
"""

from typing import Any, Dict

from sqlalchemy.orm import Session

from packages.copilot import answer as _deterministic
from packages.copilot import tools


def ask(db: Session, question: str, prefer_llm: bool = True) -> Dict[str, Any]:
    """Answer an analyst question from the evidence ledger."""
    if prefer_llm:
        try:
            from packages.copilot import llm
            if llm.available():
                try:
                    return llm.answer(db, question)
                except Exception as exc:  # pragma: no cover - network/API failure
                    # Never let an API problem take the assistant down: fall back
                    # to the grounded path and say which engine actually answered.
                    out = _deterministic.answer(db, question)
                    out["engine"] = "deterministic"
                    out["llm_error"] = str(exc)[:200]
                    return out
        except ImportError:
            pass

    out = _deterministic.answer(db, question)
    out["engine"] = "deterministic"
    return out


__all__ = ["ask", "tools"]
