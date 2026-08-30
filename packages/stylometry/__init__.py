"""
Stylometry package initialization.
"""
from packages.stylometry.features import extract_stylometric_features, extract_word_tokens
from packages.stylometry.episodes import StylometryEpisode, MIN_WORD_COUNT_THRESHOLD
from packages.stylometry.verify import (
    verify_author_stylometry,
    verify_short_text_neural_stylometry,
    compute_burrows_delta,
    compute_cosine_similarity,
)
from packages.stylometry.neural import NeuralStylometryEncoder, extract_neural_style_embedding

__all__ = [
    "extract_stylometric_features",
    "extract_word_tokens",
    "StylometryEpisode",
    "MIN_WORD_COUNT_THRESHOLD",
    "verify_author_stylometry",
    "verify_short_text_neural_stylometry",
    "compute_burrows_delta",
    "compute_cosine_similarity",
    "NeuralStylometryEncoder",
    "extract_neural_style_embedding",
]

