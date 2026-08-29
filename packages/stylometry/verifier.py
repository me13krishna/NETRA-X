"""
NETRA-X Stylometry Verifier
Verifies same-author hypothesis using Burrows' Delta / Cosine Distance on aggregated feature profiles.
Includes mandatory word count abstention rule (<50 words).
"""

import math
from typing import Dict, List, Optional
from .pipeline import StylometryEpisode, StylometryFeatureExtractor


class StylometryResult:
    def __init__(
        self,
        same_author_prob: float,
        confidence: float,
        distance: float,
        abstain: bool = False,
        abstain_reason: str = ""
    ):
        self.same_author_prob = same_author_prob
        self.confidence = confidence
        self.distance = distance
        self.abstain = abstain
        self.abstain_reason = abstain_reason


class StylometryVerifier:
    """Verifies same-author probability between two text samples or episode collections."""

    def __init__(self, min_word_count: int = 50):
        self.min_word_count = min_word_count
        self.extractor = StylometryFeatureExtractor()

    def verify(self, sample_a: str, sample_b: str) -> StylometryResult:
        """Verify whether two text samples were authored by the same threat actor."""
        words_a = len(sample_a.split())
        words_b = len(sample_b.split())

        # HARD RULE: Abstain if either sample is under threshold (<50 words)
        if words_a < self.min_word_count or words_b < self.min_word_count:
            return StylometryResult(
                same_author_prob=0.50,
                confidence=0.0,
                distance=1.0,
                abstain=True,
                abstain_reason=f"Insufficient text volume ({words_a} and {words_b} words; min required: {self.min_word_count})"
            )

        ep_a = StylometryEpisode("ep_a", "author_a", sample_a)
        ep_b = StylometryEpisode("ep_b", "author_b", sample_b)

        vec_a = self.extractor.extract(ep_a)
        vec_b = self.extractor.extract(ep_b)

        # Compute cosine similarity on common feature keys
        all_keys = set(vec_a.keys()).union(set(vec_b.keys()))
        dot_prod = sum(vec_a.get(k, 0.0) * vec_b.get(k, 0.0) for k in all_keys)
        norm_a = math.sqrt(sum(vec_a.get(k, 0.0) ** 2 for k in all_keys))
        norm_b = math.sqrt(sum(vec_b.get(k, 0.0) ** 2 for k in all_keys))

        if norm_a == 0 or norm_b == 0:
            sim = 0.0
        else:
            sim = dot_prod / (norm_a * norm_b)

        distance = round(1.0 - sim, 4)
        prob = round(max(0.0, min(1.0, sim)), 4)
        confidence = round(min(1.0, (words_a + words_b) / 500.0), 2)

        return StylometryResult(
            same_author_prob=prob,
            confidence=confidence,
            distance=distance,
            abstain=False
        )
