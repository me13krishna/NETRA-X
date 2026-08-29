"""
NETRA-X Stylometry Package
Provides feature extraction, episode aggregation (SYSML-style), and same-author verification with word count abstention.
"""

from .pipeline import StylometryFeatureExtractor, StylometryEpisode
from .verifier import StylometryVerifier, StylometryResult

__all__ = [
    "StylometryFeatureExtractor",
    "StylometryEpisode",
    "StylometryVerifier",
    "StylometryResult"
]
