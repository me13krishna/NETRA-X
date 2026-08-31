"""
corpus_stats.py — Pre-trained Darknet Stylometric Background Corpus Reference Statistics.
Provides mean frequency and standard deviation vectors for Burrows' Delta z-score normalization.
"""

import json
import os
import numpy as np
from typing import List, Dict, Any, Optional

from packages.stylometry.features import ENGLISH_FUNCTION_WORDS, extract_word_tokens, extract_function_word_frequencies

_DEFAULT_CORPUS_STATS: Optional["BackgroundCorpusStats"] = None


class BackgroundCorpusStats:
    """
    Manages background corpus reference statistics for function-word z-scores.
    """

    def __init__(self, means: np.ndarray, std_devs: np.ndarray, num_documents: int = 500):
        self.means = np.array(means, dtype=np.float64)
        self.std_devs = np.array(std_devs, dtype=np.float64)
        self.std_devs[self.std_devs == 0] = 1e-5
        self.num_documents = num_documents

    @classmethod
    def load_default(cls) -> "BackgroundCorpusStats":
        """
        Loads pre-trained reference statistics from corpus_stats.json.
        """
        global _DEFAULT_CORPUS_STATS
        if _DEFAULT_CORPUS_STATS is not None:
            return _DEFAULT_CORPUS_STATS

        json_path = os.path.join(os.path.dirname(__file__), "corpus_stats.json")
        vocab_len = len(ENGLISH_FUNCTION_WORDS)

        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            means = np.array(data.get("means", []), dtype=np.float64)
            std_devs = np.array(data.get("std_devs", []), dtype=np.float64)
            num_docs = data.get("num_documents", 500)

            # Ensure exact length match with ENGLISH_FUNCTION_WORDS (174)
            if len(means) != vocab_len:
                means = np.pad(means, (0, max(0, vocab_len - len(means))))[:vocab_len]
                means[means == 0] = 0.002
            if len(std_devs) != vocab_len:
                std_devs = np.pad(std_devs, (0, max(0, vocab_len - len(std_devs))))[:vocab_len]
                std_devs[std_devs == 0] = 0.005

            _DEFAULT_CORPUS_STATS = cls(means=means, std_devs=std_devs, num_documents=num_docs)
            return _DEFAULT_CORPUS_STATS

        default_std = np.full(vocab_len, 0.005, dtype=np.float64)
        default_mean = np.full(vocab_len, 0.002, dtype=np.float64)
        _DEFAULT_CORPUS_STATS = cls(means=default_mean, std_devs=default_std, num_documents=100)
        return _DEFAULT_CORPUS_STATS


    @classmethod
    def compute_from_texts(cls, texts: List[str]) -> "BackgroundCorpusStats":
        """
        Computes empirical mean and standard deviation vectors across raw text samples.
        """
        if not texts:
            return cls.load_default()

        vecs = []
        for text in texts:
            words = extract_word_tokens(text)
            fvec = extract_function_word_frequencies(words)
            vecs.append(fvec)

        matrix = np.array(vecs, dtype=np.float64)
        means = np.mean(matrix, axis=0)
        std_devs = np.std(matrix, axis=0)
        return cls(means=means, std_devs=std_devs, num_documents=len(texts))

    def get_std_devs(self) -> np.ndarray:
        """
        Returns standard deviation vector for Burrows' Delta z-score scaling.
        """
        return self.std_devs

    def save(self, file_path: str):
        """
        Exports corpus statistics to JSON file.
        """
        payload = {
            "description": "NETRA-X Stylometric Background Corpus Reference Statistics",
            "num_documents": self.num_documents,
            "vocab_size": len(self.means),
            "means": [round(float(m), 6) for m in self.means],
            "std_devs": [round(float(s), 6) for s in self.std_devs],
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
