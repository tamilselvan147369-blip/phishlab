"""Package initialisation for the Multi-Platform Social Media Simulation Engine.

Exposes ``social_sim_bp`` for registration into the main Flask application.
"""

from flask import Blueprint

social_sim_bp = Blueprint(
    'social_sim',
    __name__,
    template_folder='templates',
    static_folder='static'
)

from . import routes  # Ensure routes are registered with blueprint

__all__ = ['social_sim_bp']
