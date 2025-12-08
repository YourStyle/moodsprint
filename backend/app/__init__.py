"""Flask application factory."""

import os

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from app.config import config

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # CORS
    CORS(app, origins=app.config["CORS_ORIGINS"], supports_credentials=True)

    # Register blueprints
    from app.api import api_bp

    app.register_blueprint(api_bp, url_prefix="/api/v1")

    # Health check endpoint
    @app.route("/health")
    def health():
        return {"status": "ok"}

    # Shell context
    @app.shell_context_processor
    def make_shell_context():
        from app.models import (Achievement, FocusSession, MoodCheck, Subtask,
                                Task, User)

        return {
            "db": db,
            "User": User,
            "Task": Task,
            "Subtask": Subtask,
            "MoodCheck": MoodCheck,
            "FocusSession": FocusSession,
            "Achievement": Achievement,
        }

    return app
