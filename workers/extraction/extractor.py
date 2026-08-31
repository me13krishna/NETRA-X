"""
Multi-Source Entity Extraction & Stylometry Engine
Extracts PGP fingerprints, cryptocurrency wallet addresses (BTC, ETH, XMR with hard abstention),
onion services, handles, emails, computes Burrows' Delta stylometric distances, and hashes site favicons via mmh3.
"""

import base64
import math
import re
from typing import Any, Dict, List, Optional
import mmh3


class ExtractionEngine:
    # Regex patterns
    PGP_FINGERPRINT_REGEX = re.compile(r"\b(?:[A-Fa-f0-9]{4}\s?){10}\b|\b[A-Fa-f0-9]{40}\b")
    BTC_ADDRESS_REGEX = re.compile(r"\b(bc1[a-z0-9]{38,59}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b")
    ETH_ADDRESS_REGEX = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
    XMR_ADDRESS_REGEX = re.compile(r"\b(4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}|8[0-9AB][1-9A-HJ-NP-Za-km-z]{93})\b")
    ONION_SERVICE_REGEX = re.compile(r"\b[a-z2-7]{56}\.onion\b", re.IGNORECASE)
    EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    HANDLE_REGEX = re.compile(r"(?:^|\s)@([A-Za-z0-9_]{3,30})\b")

    @classmethod
    def extract_entities(cls, text_content: str) -> Dict[str, Any]:
        """Extract structured identifiers from raw text content."""
        # The `\s?` between hex groups matches a newline as readily as a space,
        # so the tenth group swallowed the trailing line break and the stored
        # fingerprint carried a newline inside it. That value then never
        # compared equal to the same key extracted from a differently-wrapped
        # page -- an exact-identity match silently lost to whitespace.
        pgp_matches = ["".join(m.split()).upper()
                       for m in cls.PGP_FINGERPRINT_REGEX.findall(text_content)]
        btc_matches = list(set(cls.BTC_ADDRESS_REGEX.findall(text_content)))
        eth_matches = list(set(cls.ETH_ADDRESS_REGEX.findall(text_content)))
        xmr_matches = list(set(cls.XMR_ADDRESS_REGEX.findall(text_content)))
        onion_matches = list(set(cls.ONION_SERVICE_REGEX.findall(text_content)))
        email_matches = list(set(cls.EMAIL_REGEX.findall(text_content)))
        handle_matches = list(set(cls.HANDLE_REGEX.findall(text_content)))

        xmr_abstain = len(xmr_matches) > 0

        return {
            "pgp_fingerprints": list(set(pgp_matches)),
            "btc_addresses": btc_matches,
            "eth_addresses": eth_matches,
            "xmr_addresses": xmr_matches,
            "xmr_abstain": xmr_abstain,
            "onion_services": onion_matches,
            "emails": email_matches,
            "handles": handle_matches
        }

    @staticmethod
    def compute_favicon_mmh3_hash(favicon_bytes: bytes) -> int:
        """
        Compute signed 32-bit MurmurHash3 integer hash of a favicon.
        Encodes bytes in Base64 with strict 76-character line wrapping.
        """
        b64_encoded = base64.encodebytes(favicon_bytes).decode("utf-8")
        return mmh3.hash(b64_encoded)

    @staticmethod
    def compute_burrows_delta(text_a: str, text_b: str, top_words: int = 50) -> float:
        """
        Computes Burrows' Delta distance between two text samples.
        """
        words_a = re.findall(r"\b\w+\b", text_a.lower())
        words_b = re.findall(r"\b\w+\b", text_b.lower())

        if not words_a or not words_b:
            return 2.0  # Max distance fallback

        vocab = set(words_a).union(set(words_b))
        freq_a = {w: words_a.count(w) / len(words_a) for w in vocab}
        freq_b = {w: words_b.count(w) / len(words_b) for w in vocab}

        # Select top most frequent words
        sorted_vocab = sorted(vocab, key=lambda w: (freq_a.get(w, 0) + freq_b.get(w, 0)), reverse=True)[:top_words]

        delta = sum(abs(freq_a.get(w, 0) - freq_b.get(w, 0)) for w in sorted_vocab) / len(sorted_vocab)
        return round(float(delta), 4)

    @classmethod
    def calibrate_stylometry_probability(cls, delta_distance: float) -> float:
        """Transform Burrows' Delta distance into a calibrated same-author probability."""
        beta0 = -2.5
        beta1 = 15.0
        exponent = beta0 + beta1 * delta_distance
        prob = 1.0 / (1.0 + math.exp(exponent))
        return round(float(prob), 4)
