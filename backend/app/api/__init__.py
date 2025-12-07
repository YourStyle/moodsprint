"""API blueprints."""
from flask import Blueprint

api_bp = Blueprint('api', __name__)

from app.api import auth, tasks, mood, focus, gamification, onboarding  # noqa: E402, F401
