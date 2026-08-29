"""
test_stylometry.py — Unit tests for Stylometry feature extraction and short-text abstention rule.
"""

import pytest
from packages.stylometry.features import extract_stylometric_features, extract_word_tokens
from packages.stylometry.episodes import StylometryEpisode, MIN_WORD_COUNT_THRESHOLD
from packages.stylometry.verify import verify_author_stylometry, compute_cosine_similarity
from packages.common.types import EvidenceFamily


SAMPLE_LONG_TEXT_1 = """
Defensive CTI operational teams must continuously monitor onion service infrastructure for configuration anomalies. 
Passive OSINT collection provides transparent evidence acquisition without triggering active IDS alerts. 
Ensure that all extractors preserve raw payload digests using SHA-256 hash chains to guarantee cryptographic verification. 
The Bayesian attribution engine combines Log-Likelihood Ratios with dependence discounting parameter lambda equal to zero point twenty five.
"""

SAMPLE_LONG_TEXT_2 = """
Operating defensive threat intelligence systems requires strict adherence to lawful allow-list controls. 
All crawled artifacts are stored immutably inside PostgreSQL system of record before Neo4j graph projections are generated. 
When verifying PGP signatures, ensure that the full 160-bit key fingerprint matches administrative declarations. 
In addition, stylometric analysis must abstain when processing short forum comments containing under fifty total words.
"""

SAMPLE_SHORT_TEXT = "This is a very short comment on darknet."  # <50 words


def test_stylometric_feature_extraction():
    """
    Test feature extraction dictionary components.
    """
    feats = extract_stylometric_features(SAMPLE_LONG_TEXT_1)
    assert feats["word_count"] > 50
    assert len(feats["function_word_vector"]) > 0
    assert "avg_sentence_len" in feats["sentence_stats"]


def test_short_text_abstention_hard_rule():
    """
    MANDATORY HARD RULE TEST: Text < 50 words MUST set abstain = True and return LLR = 0.0.
    """
    ep_short = StylometryEpisode.from_single_text("auth1", "ep_short", SAMPLE_SHORT_TEXT)
    assert ep_short.word_count < MIN_WORD_COUNT_THRESHOLD
    assert ep_short.abstain is True

    ep_long = StylometryEpisode.from_single_text("auth1", "ep_long", SAMPLE_LONG_TEXT_1)
    assert ep_long.abstain is False

    # Verification between long text and short text
    ev_item = verify_author_stylometry(ep_long, ep_short, item_id="test_short_ev")
    assert ev_item.family == EvidenceFamily.STYLOMETRY
    assert ev_item.abstain is True
    assert ev_item.get_effective_llr() == 0.0


def test_long_text_same_author_verification():
    """
    Test verification of two long text samples from same author style.
    """
    ep1 = StylometryEpisode.from_single_text("auth1", "ep1", SAMPLE_LONG_TEXT_1)
    ep2 = StylometryEpisode.from_single_text("auth1", "ep2", SAMPLE_LONG_TEXT_2)

    ev_item = verify_author_stylometry(ep1, ep2, item_id="test_long_ev")
    assert ev_item.family == EvidenceFamily.STYLOMETRY
    assert ev_item.abstain is False
    assert ev_item.get_effective_llr() > 0.0
