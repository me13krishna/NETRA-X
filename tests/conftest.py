"""Shared test configuration.

Set before any application module is imported: packages/evidence/auth.py now
refuses to sign JWTs with a hardcoded default key and raises at import time if
no SECRET_KEY is present. Tests opt into a random per-process key, so they
never depend on a committed secret and tokens cannot outlive the run.
"""
import os

os.environ.setdefault("NETRAX_ALLOW_EPHEMERAL_SECRET", "1")
