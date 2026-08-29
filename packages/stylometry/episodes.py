"""
episodes.py — SYSML-style episode aggregation and short-text abstention enforcement.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import numpy as np

from packages.stylometry.features import extract_stylometric_features, extract_word_tokens


MIN_WORD_COUNT_THRESHOLD = 50  # Hard rule: abstain if text < 50 words


@dataclass
class StylometryEpisode:
    """
    Container representing aggregated text post observations for a author/profile.
    """
    author_id: str
    episode_id: str
    texts: List[str] = field(default_factory=list)
    word_count: int = 0
    feature_dict: Optional[Dict[str, Any]] = None
    abstain: bool = False

    def add_text(self, text: str):
        """
        Add a text observation to the episode and recalculate features.
        """
        self.texts.append(text)
        combined_text = " ".join(self.texts)
        words = extract_word_tokens(combined_text)
        self.word_count = len(words)

        if self.word_count < MIN_WORD_COUNT_THRESHOLD:
            self.abstain = True
            self.feature_dict = {
                "word_count": self.word_count,
                "function_word_vector": np.zeros(1, dtype=np.float64),
                "char_ngrams": {},
                "punctuation_ratios": {},
                "sentence_stats": {"avg_sentence_len": 0.0, "std_sentence_len": 0.0},
            }
        else:
            self.abstain = False
            self.feature_dict = extract_stylometric_features(combined_text)

    @classmethod
    def from_single_text(cls, author_id: str, episode_id: str, text: str) -> "StylometryEpisode":
        """
        Factory to build an episode from a single text string.
        """
        ep = cls(author_id=author_id, episode_id=episode_id)
        ep.add_text(text)
        return ep
