"""
Stylometry package initialization.
"""
from packages.stylometry.features import extract_stylometric_features, extract_word_tokens
from packages.stylometry.episodes import StylometryEpisode, MIN_WORD_COUNT_THRESHOLD
from packages.stylometry.verify import verify_author_stylometry, compute_burrows_delta, compute_cosine_similarity

__all__ = [
    "extract_stylometric_features",
    "extract_word_tokens",
    "StylometryEpisode",
    "MIN_WORD_COUNT_THRESHOLD",
    "verify_author_stylometry",
    "compute_burrows_delta",
    "compute_cosine_similarity",
]
