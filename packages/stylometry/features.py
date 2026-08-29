"""
features.py — Stylometric feature extraction pipeline.

Extracts:
1. Character n-grams (3-grams, 4-grams, 5-grams)
2. English function word frequency vector (top 50 standard function words)
3. Punctuation ratios
4. Sentence & word length distributions (mean, standard deviation)
"""

import re
import math
from typing import Dict, List, Any
import numpy as np


ENGLISH_FUNCTION_WORDS = [
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so",
    "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
    "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll",
    "they're", "they've", "this", "those", "through", "to", "too", "under", "until",
    "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves"
]


def extract_word_tokens(text: str) -> List[str]:
    """
    Lowercase word tokenization.
    """
    return re.findall(r"\b\w+\b", text.lower())


def extract_char_ngrams(text: str, n_range=(3, 5)) -> Dict[str, float]:
    """
    Extract normalized character n-gram frequencies.
    """
    cleaned = re.sub(r"\s+", " ", text.lower())
    counts: Dict[str, int] = {}
    total = 0

    for n in range(n_range[0], n_range[1] + 1):
        for i in range(len(cleaned) - n + 1):
            gram = cleaned[i : i + n]
            counts[gram] = counts.get(gram, 0) + 1
            total += 1

    if total == 0:
        return {}
    return {gram: count / total for gram, count in counts.items()}


def extract_function_word_frequencies(words: List[str]) -> np.ndarray:
    """
    Calculate frequency distribution vector over standard function words.
    """
    total_words = len(words)
    if total_words == 0:
        return np.zeros(len(ENGLISH_FUNCTION_WORDS), dtype=np.float64)

    counts = {w: 0 for w in ENGLISH_FUNCTION_WORDS}
    for w in words:
        if w in counts:
            counts[w] += 1

    vec = [counts[w] / total_words for w in ENGLISH_FUNCTION_WORDS]
    return np.array(vec, dtype=np.float64)


def extract_punctuation_ratios(text: str) -> Dict[str, float]:
    """
    Extract relative frequencies of punctuation marks per 100 characters.
    """
    length = max(len(text), 1)
    puncts = [".", ",", "!", "?", ";", ":", "-", '"', "'", "(", ")"]
    ratios = {}
    for p in puncts:
        ratios[f"punct_{p}"] = text.count(p) / length * 100.0
    return ratios


def extract_sentence_distributions(text: str) -> Dict[str, float]:
    """
    Calculate mean and standard deviation of sentence lengths.
    """
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    if not sentences:
        return {"avg_sentence_len": 0.0, "std_sentence_len": 0.0}

    word_counts = [len(extract_word_tokens(s)) for s in sentences]
    mean_len = float(np.mean(word_counts))
    std_len = float(np.std(word_counts))
    return {"avg_sentence_len": mean_len, "std_sentence_len": std_len}


def extract_stylometric_features(text: str) -> Dict[str, Any]:
    """
    Full feature extraction pipeline returning a feature dictionary.
    """
    words = extract_word_tokens(text)
    word_count = len(words)
    func_vec = extract_function_word_frequencies(words)
    char_ngrams = extract_char_ngrams(text)
    punct_ratios = extract_punctuation_ratios(text)
    sentence_stats = extract_sentence_distributions(text)

    return {
        "word_count": word_count,
        "function_word_vector": func_vec,
        "char_ngrams": char_ngrams,
        "punctuation_ratios": punct_ratios,
        "sentence_stats": sentence_stats,
    }
