# real_app_testing package

"""Package initialisation for the RealAppTesting subsystem.

It defines a Flask Blueprint that will be registered by the main app
(`app.py`). The Blueprint is exposed as ``realapp_bp`` for import by the
parent application.
"""

from flask import Blueprint

# Blueprint for all RealAppTesting routes – URL prefix will be added when
# the blueprint is registered in ``app.py``.
realapp_bp = Blueprint('realapp', __name__, template_folder='templates')

from . import routes  # Ensure routes are registered

__all__ = ["realapp_bp"]
