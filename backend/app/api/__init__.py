"""API blueprints."""

from flask import Blueprint

api_bp = Blueprint("api", __name__)

# Import modules to register routes - noqa: F401, E402
from app.api import auth  # noqa: F401, E402
from app.api import focus  # noqa: F401, E402
from app.api import gamification  # noqa: F401, E402
from app.api import mood  # noqa: F401, E402
from app.api import onboarding  # noqa: F401, E402
from app.api import tasks  # noqa: F401, E402
