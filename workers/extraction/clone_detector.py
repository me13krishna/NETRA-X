"""
NETRA-X SimHash Structural Clone Detector
Computes SimHash 64-bit structural fingerprints for HTML/DOM documents.
If structural match >= 95%, flags site as a phishing clone and collapses dependence group.
"""

import re
import hashlib
from typing import Dict, Any, List


class SimHashCloneDetector:
    """Computes SimHash 64-bit document fingerprints for structural clone detection."""

    def __init__(self, hash_bits: int = 64):
        self.hash_bits = hash_bits

    def _token_hash(self, token: str) -> int:
        """Hash token to 64-bit unsigned integer using MD5."""
        return int(hashlib.md5(token.encode('utf-8')).hexdigest()[:16], 16)

    def compute_simhash(self, text_or_html: str) -> int:
        """Compute 64-bit SimHash fingerprint from text tokens."""
        tokens = re.findall(r'\b\w+\b', text_or_html.lower())
        if not tokens:
            return 0

        v = [0] * self.hash_bits
        for token in tokens:
            h = self._token_hash(token)
            for i in range(self.hash_bits):
                bitmask = 1 << i
                if h & bitmask:
                    v[i] += 1
                else:
                    v[i] -= 1

        fingerprint = 0
        for i in range(self.hash_bits):
            if v[i] > 0:
                fingerprint |= (1 << i)

        return fingerprint

    def similarity(self, hash1: int, hash2: int) -> float:
        """Compute similarity percentage (1.0 - HammingDistance / 64)."""
        x = (hash1 ^ hash2) & ((1 << self.hash_bits) - 1)
        tot_bits = 0
        while x:
            tot_bits += 1
            x &= x - 1
        hamming_dist = tot_bits
        sim = 1.0 - (hamming_dist / float(self.hash_bits))
        return round(sim, 4)

    def evaluate_clone(self, doc_a: str, doc_b: str, threshold: float = 0.95) -> Dict[str, Any]:
        """Check if doc_b is a structural clone of doc_a."""
        sh1 = self.compute_simhash(doc_a)
        sh2 = self.compute_simhash(doc_b)
        sim = self.similarity(sh1, sh2)
        is_clone = sim >= threshold

        return {
            "similarity": sim,
            "phishing_clone": is_clone,
            "collapse_dependence_group": is_clone,
            "simhash_a": hex(sh1),
            "simhash_b": hex(sh2)
        }
