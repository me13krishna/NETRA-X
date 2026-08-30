"""Smoke tests for the extraction workers.

These modules were unreachable for their whole existence: `extractor.py`
annotated a return type as `Dict[str, Any]` without importing `Any`, which
raises NameError at class-definition time, and `workers/extraction/__init__.py`
imports it -- so importing *any* module in the package failed too.

Nothing outside `workers/` imported either module, so the entire test suite
passed while both were dead code. The first test here exists to make that
specific failure impossible to reintroduce quietly.
"""

import pytest

from workers.extraction import ExtractionEngine, SimHashCloneDetector


def test_package_imports():
    """Guards the NameError regression: importing the package must not raise."""
    assert ExtractionEngine is not None
    assert SimHashCloneDetector is not None


def test_extracts_identifiers_from_a_forum_post():
    text = (
        "Vendor contact @shadow_byte on Telegram. PGP fingerprint "
        "4A8F912C7E3B1D5069A2F4C8B0D3E7F1A6C90B2D. Payment to "
        "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh or "
        "0x742d35Cc6634C0532925a3b844Bc454e4438f44e. "
        "Mirror at abcdefghijklmnopqrstuvwxyz234567abcdefghijklmnopqrstuvwx.onion. "
        "Reach me at vendor@protonmail.com."
    )
    out = ExtractionEngine.extract_entities(text)

    assert "4A8F912C7E3B1D5069A2F4C8B0D3E7F1A6C90B2D" in out["pgp_fingerprints"]
    assert "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh" in out["btc_addresses"]
    assert "0x742d35Cc6634C0532925a3b844Bc454e4438f44e" in out["eth_addresses"]
    assert "vendor@protonmail.com" in out["emails"]
    assert "shadow_byte" in out["handles"]
    assert len(out["onion_services"]) == 1


def test_monero_triggers_hard_abstention():
    """XMR is untraceable by these methods; the engine must flag, not guess."""
    xmr = "4" + "A" * 94
    out = ExtractionEngine.extract_entities(f"Only XMR accepted: {xmr}")
    assert out["xmr_abstain"] is True

    clean = ExtractionEngine.extract_entities("BTC only, no monero here.")
    assert clean["xmr_abstain"] is False


def test_favicon_hash_is_stable_and_distinguishing():
    a = ExtractionEngine.compute_favicon_mmh3_hash(b"\x89PNG\r\n\x1a\n" + b"icon-a" * 8)
    b = ExtractionEngine.compute_favicon_mmh3_hash(b"\x89PNG\r\n\x1a\n" + b"icon-b" * 8)
    assert isinstance(a, int)
    assert a == ExtractionEngine.compute_favicon_mmh3_hash(b"\x89PNG\r\n\x1a\n" + b"icon-a" * 8)
    assert a != b


def test_simhash_detects_a_near_duplicate_but_not_unrelated_text():
    det = SimHashCloneDetector()
    original = "Premium vendor account. Fast shipping, vacuum sealed, stealth guaranteed. " * 4
    edited = "Premium vendor account. Fast shipping, vacuum sealed, stealth guaranteed today. " * 4
    unrelated = "Completely different marketplace listing about unrelated hardware parts. " * 4

    assert det.similarity(det.compute_simhash(original), det.compute_simhash(edited)) > 0.85
    assert det.similarity(det.compute_simhash(original), det.compute_simhash(unrelated)) < 0.85
