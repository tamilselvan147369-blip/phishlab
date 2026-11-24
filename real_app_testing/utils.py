"""Utility helpers for RealAppTesting.

All functions are pure Python and have no external side‑effects beyond the
SQLAlchemy models defined in ``models.py``.
"""
import secrets
from datetime import datetime, timedelta
from typing import Tuple

from .models import PLATFORMS, RealAppExercise

# ---------------------------------------------------------------------------
# Demo token handling
# ---------------------------------------------------------------------------
TOKEN_TTL_HOURS = 4  # configurable expiry time

def generate_demo_token() -> Tuple[str, datetime]:
    """Return a random token and its expiration datetime.

    The token is URL‑safe, 43 characters long, and stored in the
    ``RealAppExercise.demo_token`` column.  The expiration is ``now`` +
    ``TOKEN_TTL_HOURS``.
    """
    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=TOKEN_TTL_HOURS)
    return token, expires


def verify_demo_token(token: str) -> RealAppExercise | None:
    """Return the exercise if the token exists *and* has not expired.

    ``None`` is returned for an unknown token or an expired token.
    """
    ex = RealAppExercise.query.filter_by(demo_token=token).first()
    if ex and ex.token_expires_at > datetime.utcnow():
        return ex
    return None

# ---------------------------------------------------------------------------
# HTML sanitisation – prevents unsafe markup from campaign content.
# ---------------------------------------------------------------------------
def safe_html(raw_html: str) -> str:
    """Sanitise user‑provided HTML using ``bleach``.

    Only a whitelist of harmless tags is allowed; all others are stripped.
    ``bleach`` is part of the default requirements; if missing the user can
    add it via ``pip install bleach``.
    """
    try:
        import bleach
    except ImportError:
        raise RuntimeError("bleach is required for safe_html sanitisation")
    allowed_tags = ["b", "i", "strong", "em", "ul", "ol", "li", "p", "br"]
    return bleach.clean(raw_html, tags=allowed_tags, strip=True)

# ---------------------------------------------------------------------------
# Platform validation helper
# ---------------------------------------------------------------------------
def validate_platform(value: str) -> bool:
    """Return ``True`` if *value* is a supported platform identifier.
    """
    return value in PLATFORMS
