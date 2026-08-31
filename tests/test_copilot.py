"""Tests for the investigation copilot.

The copilot previously returned one of six hardcoded paragraphs chosen by
keyword. Asking about any actor produced identical text about ShadowByte and
Vortex99 -- including for gibberish -- with every number a string literal.

These tests pin the two properties that failure violated: answers are grounded
in ledger rows, and an unanswerable question is refused rather than answered
about someone else.
"""

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.database.session import SyncSessionLocal
from apps.api.database.models import Actor
from packages.copilot import ask
from packages.copilot import tools


@pytest.fixture
def db():
    s = SyncSessionLocal()
    yield s
    s.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth(client):
    r = client.post("/api/v1/auth/login", json={
        "email": "analyst@netra-x.local", "password": "AnalystPass2026!"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _some_actor(db):
    a = db.query(Actor).first()
    assert a is not None, "ledger has no actors; run the seed"
    return a


# ---------------------------------------------------------------- grounding

def test_answer_names_the_actor_that_was_asked_about(db):
    """The original bug: asking about X returned a paragraph about Y."""
    actor = _some_actor(db)
    out = ask(db, f"Tell me about {actor.primary_alias}", prefer_llm=False)
    assert out["answered"] is True
    assert actor.primary_alias in out["answer"]
    assert out.get("resolved_actor") == actor.primary_alias


def test_different_actors_get_different_answers(db):
    names = [a.primary_alias for a in db.query(Actor).limit(3).all()]
    if len(names) < 2:
        pytest.skip("needs at least two actors")
    answers = [ask(db, f"Tell me about {n}", prefer_llm=False)["answer"] for n in names]
    assert len(set(answers)) == len(answers), "answers are not actor-specific"


def test_reported_probability_matches_the_stored_row(db):
    """No figure may be a literal: the percentage shown must equal the row."""
    actor = next(
        (a for a in db.query(Actor).all() if tools.get_actor_links(db, a.id)), None)
    if actor is None:
        pytest.skip("no actor has attribution links")

    links = tools.get_actor_links(db, actor.id)
    top = links[0]
    out = ask(db, f"Who is {actor.primary_alias} linked to?", prefer_llm=False)

    assert top["counterpart"] in out["answer"]
    assert f"{top['calibrated_prob'] * 100:.1f}%" in out["answer"]


# --------------------------------------------------------------- abstention

def test_unknown_entity_is_refused_not_substituted(db):
    out = ask(db, "Tell me about Zzzqqq_NotARealActor", prefer_llm=False)
    assert out["answered"] is False
    assert "cannot answer" in out["answer"].lower()
    # The failure mode being guarded: answering about a real actor instead.
    for a in db.query(Actor).all():
        assert a.primary_alias not in out["answer"]


def test_gibberish_is_refused(db):
    out = ask(db, "zzzz qqqq wwww", prefer_llm=False)
    assert out["answered"] is False


def test_empty_question_is_refused(db):
    assert ask(db, "", prefer_llm=False)["answered"] is False


# ------------------------------------------------------------- capabilities

def test_ledger_statistics_match_direct_counts(db):
    stats = tools.get_ledger_stats(db)
    out = ask(db, "How many actors and hypotheses are in the ledger?", prefer_llm=False)
    assert out["answered"] is True
    assert str(stats["actors"]) in out["answer"]
    assert str(stats["hypotheses"]) in out["answer"]


def test_audit_integrity_question_reports_real_chain_state(db):
    out = ask(db, "Is the audit chain intact?", prefer_llm=False)
    assert out["answered"] is True
    stats = tools.get_ledger_stats(db)
    assert str(stats["audit_records"]) in out["answer"]


def test_shared_identifier_question_reports_real_reuse(db):
    shared = tools.find_shared_identifiers(db)
    out = ask(db, "Which identifiers are shared between actors?", prefer_llm=False)
    assert out["answered"] is True
    if shared["shared_wallet_clusters"]:
        assert shared["shared_wallet_clusters"][0]["cluster_id"] in out["answer"]


def test_review_queue_question_reports_real_queue(db):
    out = ask(db, "What is in the review queue?", prefer_llm=False)
    assert out["answered"] is True


# ---------------------------------------------------------------- endpoint

def test_endpoint_returns_grounded_answer(client, auth, db):
    actor = _some_actor(db)
    r = client.post(f"/api/v1/copilot/query?query_text=Tell+me+about+{actor.primary_alias}",
                    headers=auth)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["answered"] is True
    assert actor.primary_alias in body["response"]
    assert body["engine"] in ("deterministic", "claude")
    assert body["tools_used"], "no ledger tool was consulted"
    assert body["citation_count"] > 0


def test_endpoint_refuses_unknown_entity(client, auth):
    r = client.post("/api/v1/copilot/query?query_text=Tell+me+about+Zzzqqq_NotReal",
                    headers=auth)
    assert r.status_code == 200
    assert r.json()["answered"] is False


def test_endpoint_requires_authentication(client):
    assert client.post("/api/v1/copilot/query?query_text=hi").status_code in (401, 403)


# ------------------------------------------------------- product knowledge
#
# The copilot previously refused everything that was not a ledger lookup, so an
# analyst asking "what is an LLR" or "is this legal" got a refusal. These cover
# the second half of its job: explaining the system itself.

def test_answers_what_the_product_is(db):
    out = ask(db, "What is NETRA-X?", prefer_llm=False)
    assert out["answered"] is True
    assert out["intent"] == "knowledge"
    assert "attribution" in out["answer"].lower()


def test_explains_the_scoring_model(db):
    out = ask(db, "How does the attribution scoring work?", prefer_llm=False)
    assert out["answered"] is True
    assert "fellegi" in out["answer"].lower()


def test_family_caps_are_read_from_code_not_typed(db):
    """The explanation must track the implementation, not a copied constant."""
    from packages.common.types import FAMILY_CAPS
    out = ask(db, "What are family caps?", prefer_llm=False)
    assert out["answered"] is True
    for fam, cap in FAMILY_CAPS.items():
        assert f"{fam.value} {cap:g}" in out["answer"], f"{fam.value} cap not reported live"


def test_lambda_is_read_from_the_engine(db):
    from packages.attribution.fusion import LLRFusionEngine
    lam = LLRFusionEngine().lambda_discount
    out = ask(db, "What is dependence discounting?", prefer_llm=False)
    assert out["answered"] is True
    assert f"{lam:g}" in out["answer"]


def test_abstention_threshold_is_read_from_the_module(db):
    from packages.stylometry.episodes import MIN_WORD_COUNT_THRESHOLD
    out = ask(db, "How does stylometry work?", prefer_llm=False)
    assert out["answered"] is True
    assert str(MIN_WORD_COUNT_THRESHOLD) in out["answer"]


def test_answers_guardrail_and_stack_and_capability_questions(db):
    for q, expect in [
        ("Is this legal?", "guardrails"),
        ("What technologies is this built with?", "stack"),
        ("What can you do?", "copilot"),
        ("How do I export a report?", "exports"),
        ("Explain the analyst workflow", "workflow"),
    ]:
        out = ask(db, q, prefer_llm=False)
        assert out["answered"] is True, f"refused: {q}"
        assert out["topic"] == expect, f"{q} -> {out.get('topic')}"


def test_ledger_facts_still_outrank_product_knowledge(db):
    """A named actor must not be hijacked by a topic keyword in the question."""
    actor = _some_actor(db)
    out = ask(db, f"What is the attribution score for {actor.primary_alias}?",
              prefer_llm=False)
    assert out["intent"] == "entity"
    assert actor.primary_alias in out["answer"]
