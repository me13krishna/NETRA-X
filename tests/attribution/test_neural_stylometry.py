"""
test_neural_stylometry.py — Unit tests for PyTorch Neural Short-Text Stylometry module.
"""

import math
import numpy as np
import pytest

from packages.stylometry.neural import (
    NeuralStylometryEncoder,
    extract_neural_style_embedding,
)
from packages.stylometry.episodes import StylometryEpisode
from packages.stylometry.verify import verify_short_text_neural_stylometry
from packages.common.types import EvidenceFamily


SHORT_SAMPLE_A = "Checking onion probe status on darknet node."
SHORT_SAMPLE_B = "Checking onion probe status on darknet node."  # Exact match
SHORT_SAMPLE_C = "Selling credit card dumps on dark market."      # Different topic/style


def test_neural_encoder_embedding_shape_and_norm():
    """
    Test that extract_neural_style_embedding returns 128d float32 L2-normalized vector.
    """
    emb = extract_neural_style_embedding(SHORT_SAMPLE_A)
    assert isinstance(emb, np.ndarray)
    assert emb.shape == (128,)
    assert emb.dtype == np.float32
    norm = float(np.linalg.norm(emb))
    assert math.isclose(norm, 1.0, rel_tol=1e-3)


def test_neural_encoder_reproducibility():
    """
    Test that deterministic weights produce identical embeddings for identical text.
    """
    emb1 = extract_neural_style_embedding(SHORT_SAMPLE_A)
    emb2 = extract_neural_style_embedding(SHORT_SAMPLE_B)
    assert np.allclose(emb1, emb2, atol=1e-5)


def test_verify_short_text_neural_stylometry():
    """
    Test verify_short_text_neural_stylometry generating EvidenceItem for short text episodes.
    """
    ep1 = StylometryEpisode.from_single_text("actor1", "ep1", SHORT_SAMPLE_A)
    ep2 = StylometryEpisode.from_single_text("actor1", "ep2", SHORT_SAMPLE_B)

    # Ep1 and Ep2 are both short (<50 words)
    assert ep1.abstain is True
    assert ep2.abstain is True

    # Neural verification provides non-abstained EvidenceItem for short texts
    item = verify_short_text_neural_stylometry(ep1, ep2, item_id="test_neural_1")

    assert item.family == EvidenceFamily.STYLOMETRY
    assert item.feature_name == "stylometry_neural_embedding"
    assert item.abstain is False
    assert "neural_cosine_similarity" in item.metadata
    assert item.metadata["neural_cosine_similarity"] > 0.80
    assert item.get_effective_llr() > 0.0


def test_verify_short_text_empty_fallback():
    """
    Test short text neural verification fallback on empty episode text.
    """
    ep_empty = StylometryEpisode(author_id="a1", episode_id="e1")
    ep_valid = StylometryEpisode.from_single_text("a1", "e2", SHORT_SAMPLE_A)

    item = verify_short_text_neural_stylometry(ep_empty, ep_valid, item_id="test_empty")
    assert item.abstain is True
    assert item.get_effective_llr() == 0.0
