"""
test_corpus_stats.py — Unit tests for pre-trained background corpus statistics & z-score normalization.
"""

import os
import numpy as np
import pytest
from packages.stylometry.corpus_stats import BackgroundCorpusStats
from packages.stylometry.episodes import StylometryEpisode
from packages.stylometry.verify import verify_author_stylometry


from packages.stylometry.features import ENGLISH_FUNCTION_WORDS


def test_default_corpus_stats_loading():
    stats = BackgroundCorpusStats.load_default()
    assert stats is not None
    assert len(stats.means) == len(ENGLISH_FUNCTION_WORDS)
    assert len(stats.std_devs) == len(ENGLISH_FUNCTION_WORDS)
    assert stats.num_documents >= 100
    assert np.all(stats.std_devs > 0)


def test_empirical_corpus_stats_computation():
    sample_texts = [
        "This is a test sample text for computing function word frequency statistics in python.",
        "Another long sample document with various function words like and or but not so.",
        "A third darknet forum posting containing technical discussions on hidden services.",
    ]
    stats = BackgroundCorpusStats.compute_from_texts(sample_texts)
    assert stats.num_documents == 3
    assert len(stats.means) == len(ENGLISH_FUNCTION_WORDS)
    assert len(stats.std_devs) == len(ENGLISH_FUNCTION_WORDS)
    assert np.all(stats.std_devs > 0)



def test_verify_author_stylometry_auto_uses_corpus_stats():
    text_long_a = "The quick brown fox jumps over the lazy dog. " * 15
    text_long_b = "The quick brown fox jumps over the lazy dog. " * 15

    ep1 = StylometryEpisode.from_single_text("author_x", "ep1", text_long_a)
    ep2 = StylometryEpisode.from_single_text("author_y", "ep2", text_long_b)

    # Calling without background_std_devs should auto-load corpus stats and compute z-score delta
    item = verify_author_stylometry(ep1, ep2)

    assert item.family.value == "STYLOMETRY"
    assert item.abstain is False
    assert "burrows_delta" in item.metadata
    assert item.metadata["burrows_delta"] >= 0.0
