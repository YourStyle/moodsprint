"""Flask application factory."""

import os

from flasgger import Swagger
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from app.config import config

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
swagger = Swagger()


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    # Get static folder from config
    config_obj = config[config_name]
    static_folder = getattr(config_obj, "STATIC_FOLDER", "/app/static")

    app = Flask(__name__, static_folder=static_folder, static_url_path="/static")
    app.config.from_object(config_obj)

    # Initialize core extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Initialize Swagger documentation
    swagger.init_app(app)

    # Initialize caching
    from app.extensions import cache

    cache.init_app(app)

    # Initialize rate limiting
    from app.extensions import limiter

    limiter.init_app(app)

    # Initialize Celery
    from app.celery_app import init_celery

    init_celery(app)

    # Setup structured logging
    from app.logging_config import setup_logging

    setup_logging(app)

    # CORS
    CORS(app, origins=app.config["CORS_ORIGINS"], supports_credentials=True)

    # Register blueprints
    from app.api import api_bp

    app.register_blueprint(api_bp, url_prefix="/api/v1")

    # Health check endpoint with detailed status
    @app.route("/health")
    def health():
        from app.extensions import get_redis_client

        health_status = {"status": "ok", "checks": {}}

        # Check database
        try:
            db.session.execute(db.text("SELECT 1"))
            health_status["checks"]["database"] = "ok"
        except Exception as e:
            health_status["checks"]["database"] = f"error: {str(e)}"
            health_status["status"] = "degraded"

        # Check Redis
        try:
            redis_client = get_redis_client()
            redis_client.ping()
            health_status["checks"]["redis"] = "ok"
        except Exception as e:
            health_status["checks"]["redis"] = f"error: {str(e)}"
            health_status["status"] = "degraded"

        return health_status

    # Readiness endpoint for Kubernetes/orchestration
    @app.route("/ready")
    def ready():
        try:
            db.session.execute(db.text("SELECT 1"))
            return {"status": "ready"}, 200
        except Exception:
            return {"status": "not ready"}, 503

    # Shell context
    @app.shell_context_processor
    def make_shell_context():
        from app.models import Achievement, FocusSession, MoodCheck, Subtask, Task, User

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
