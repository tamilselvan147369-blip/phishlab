"""Utility functions for token handling in RealAppTesting.

We generate a random URL‑safe token, store only its SHA‑256 hash in the DB,
and keep the raw token in memory long enough to embed it in the demo URL.
"""
import secrets
import hashlib
from typing import Tuple

TOKEN_TTL_HOURS = 4  # default expiry, can be overridden via app config

def generate_token() -> Tuple[str, str]:
    """Generate a random token and its SHA‑256 hash.

    Returns a tuple ``(raw_token, token_hash)`` where ``raw_token`` is safe to
    embed in a URL and ``token_hash`` is the value stored in the database.
    """
    raw = secrets.token_urlsafe(32)
    h = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    return raw, h

def verify_token(raw_token: str, stored_hash: str) -> bool:
    """Constant‑time comparison of a raw token against a stored hash.
    Returns ``True`` if they match.
    """
    raw_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
    # use secrets.compare_digest for constant‑time safety
    return secrets.compare_digest(raw_hash, stored_hash)
