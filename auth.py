"""Authentication and authorization utilities for PhishLab.

Provides access control decorators decoupled from the Flask application
instance to prevent circular imports during blueprint registration.
"""

import time
from collections import defaultdict
from functools import wraps
from flask import session, abort

# Rate limiting storage: IP -> list of failed attempt timestamps
_failed_attempts = defaultdict(list)
_MAX_FAILED_ATTEMPTS = 5
_WINDOW_SECONDS = 900  # 15 minutes


def is_login_rate_limited(ip_address: str) -> bool:
    """Check if IP has exceeded failed login threshold in the sliding window."""
    now = time.time()
    attempts = [t for t in _failed_attempts[ip_address] if now - t < _WINDOW_SECONDS]
    _failed_attempts[ip_address] = attempts
    return len(attempts) >= _MAX_FAILED_ATTEMPTS


def record_failed_login(ip_address: str):
    """Record a failed login attempt timestamp for an IP address."""
    _failed_attempts[ip_address].append(time.time())


def clear_failed_logins(ip_address: str):
    """Clear failed login history upon successful authentication."""
    _failed_attempts.pop(ip_address, None)


def admin_required(view_func):
    """Decorator to protect admin routes requiring is_admin session flag and valid session epoch."""
    @wraps(view_func)
    def _wrapped_view(*args, **kwargs):
        from flask import current_app
        if session.get('is_admin'):
            expected_epoch = str(current_app.config.get('SESSION_EPOCH', '1'))
            token_epoch = session.get('_session_epoch')
            if token_epoch is not None and str(token_epoch) != expected_epoch:
                session.clear()
                abort(403)
            return view_func(*args, **kwargs)
        abort(403)
    return _wrapped_view
