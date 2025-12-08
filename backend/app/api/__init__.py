"""API blueprints."""

from flask import Blueprint

api_bp = Blueprint("api", __name__)

from app.api import (auth, focus, gamification, mood,  # noqa: E402, F401
                     onboarding, tasks)
