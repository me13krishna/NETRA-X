"""
Authentication and JWT Token Security Utilities for NETRA-X Backend
Supports PBKDF2-HMAC-SHA256 and bcrypt password hashing, and PyJWT issuance/verification.
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import jwt

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

# Set NETRAX_ALLOW_EPHEMERAL_SECRET=1 for tests and local demos.
_ALLOW_EPHEMERAL = os.getenv("NETRAX_ALLOW_EPHEMERAL_SECRET", "").lower() in {"1", "true", "yes"}


def _resolve_secret_key() -> str:
    """Resolve the JWT signing key, refusing to fall back to a published one.

    This previously defaulted to a literal string committed to a public
    repository. `.env` is gitignored, so on any fresh clone that literal *was*
    the signing key -- meaning anyone who read the repo could mint a valid
    admin token. A hardcoded default for a signing key is not a convenience,
    it is a credential disclosure.

    Behaviour now:
      * SECRET_KEY set              -> use it
      * NETRAX_ALLOW_EPHEMERAL_SECRET -> generate a random key for this process.
                                       Tokens do not survive a restart, which
                                       is correct for a test or a demo.
      * neither                     -> raise, loudly, at import time.
    """
    key = os.getenv("SECRET_KEY")
    if key:
        return key

    if _ALLOW_EPHEMERAL:
        # Random per process: usable, and impossible to accidentally ship.
        return secrets.token_urlsafe(64)

    raise RuntimeError(
        "SECRET_KEY is not set. NETRA-X refuses to sign JWTs with a default key "
        "because a committed default is publicly readable and lets anyone forge "
        "an admin token.\n"
        "  Production/dev: set SECRET_KEY in .env (see .env.example)\n"
        "  Tests/demo:     set NETRAX_ALLOW_EPHEMERAL_SECRET=1 for a random "
        "per-process key"
    )


SECRET_KEY = _resolve_secret_key()


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with random salt."""
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"pbkdf2:sha256:100000${salt.hex()}${pwd_hash.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed representation."""
    if not hashed_password:
        return False

    if hashed_password.startswith("pbkdf2:sha256:"):
        try:
            parts = hashed_password.split("$")
            iterations = int(parts[0].split(":")[-1])
            salt = bytes.fromhex(parts[1])
            expected_hash = bytes.fromhex(parts[2])
            pwd_hash = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, iterations)
            return pwd_hash == expected_hash
        except Exception:
            return False
    else:
        try:
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Issue PyJWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate PyJWT access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception:
        return None
