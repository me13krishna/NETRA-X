"""
NETRA-X Stylometric Feature Pipeline & Episode Aggregator
Extracts char 3-5grams, function words, punctuation ratios, POS patterns, and sentence length distributions.
"""

import re
from typing import List, Dict, Any

FUNCTION_WORDS = {
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", "not", "on", "with",
    "he", "as", "you", "do", "at", "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
    "or", "an", "will", "my", "one", "all", "would", "there", "their", "what", "so", "up", "out", "if",
    "about", "who", "get", "which", "go", "me", "when", "make", "can", "like", "time", "no", "just",
    "him", "know", "take", "people", "into", "year", "your", "good", "some", "could", "them", "see",
    "other", "than", "then", "now", "look", "only", "come", "its", "over", "think", "also", "back"
}


class StylometryEpisode:
    def __init__(self, episode_id: str, author_id: str, raw_text: str):
        self.episode_id = episode_id
        self.author_id = author_id
        self.raw_text = raw_text
        self.word_count = len(raw_text.split())
        self.features: Dict[str, float] = {}


class StylometryFeatureExtractor:
    """Extracts high-dimensional stylometric feature vectors from text episodes."""

    def extract(self, episode: StylometryEpisode) -> Dict[str, float]:
        text = episode.raw_text
        words = [w.lower() for w in re.findall(r'\b\w+\b', text)]
        n_words = max(len(words), 1)

        features: Dict[str, float] = {}

        # 1. Function Word Frequencies
        for fw in FUNCTION_WORDS:
            count = words.count(fw)
            features[f"fw_{fw}"] = count / n_words

        # 2. Character N-Grams (3-5 grams)
        clean_text = text.lower()
        for n in (3, 4, 5):
            ngrams = [clean_text[i:i+n] for i in range(len(clean_text) - n + 1)]
            n_ngrams = max(len(ngrams), 1)
            # Take top 10 frequent ngrams per n
            for ng in set(ngrams[:50]):
                features[f"char_{n}g_{ng}"] = ngrams.count(ng) / n_ngrams

        # 3. Punctuation Patterns
        punct_chars = [',', '.', '!', '?', ';', ':', '-', '(', ')', '"', "'"]
        for p in punct_chars:
            features[f"punct_{p}"] = text.count(p) / max(len(text), 1)

        # 4. Sentence Length Statistics
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        sentence_lens = [len(s.split()) for s in sentences] if sentences else [n_words]
        features["avg_sentence_len"] = float(sum(sentence_lens) / max(len(sentence_lens), 1))
        features["sentence_count"] = float(len(sentences))
        features["word_count"] = float(n_words)

        episode.features = features
        return features

    def aggregate_episodes(self, episodes: List[StylometryEpisode]) -> Dict[str, float]:
        """Aggregate feature vectors across multiple episodes (SYSML episode aggregation)."""
        if not episodes:
            return {}
        
        aggregated: Dict[str, float] = {}
        all_keys = set()
        for ep in episodes:
            if not ep.features:
                self.extract(ep)
            all_keys.update(ep.features.keys())

        for k in all_keys:
            vals = [ep.features.get(k, 0.0) for ep in episodes]
            aggregated[k] = float(sum(vals) / len(vals))

        return aggregated
