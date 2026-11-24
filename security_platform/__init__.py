"""Package initialization for the Real-Time Phishing Security Testing Platform.

Exposes ``security_platform_bp`` for registration into the Flask application factory.
"""

from flask import Blueprint

security_platform_bp = Blueprint(
    'security_platform',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/security/static'
)

# Initialize participant and administrator route handlers
from .routes_participant import init_participant_routes
from .routes_admin import init_admin_routes

init_participant_routes(security_platform_bp)
init_admin_routes(security_platform_bp)

__all__ = ['security_platform_bp']
