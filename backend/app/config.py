"""Application configuration."""

import os
from datetime import timedelta


class Config:
    """Base configuration."""

    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    # Static files
    STATIC_FOLDER = os.environ.get("STATIC_FOLDER", "/app/static")

    # Database with production-ready connection pooling
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql://moodsprint:moodsprint@localhost:5432/moodsprint"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,  # Verify connections before using
        "pool_recycle": 300,  # Recycle connections after 5 minutes
        "pool_size": 10,  # Base number of connections
        "max_overflow": 20,  # Allow up to 30 total connections
        "pool_timeout": 30,  # Wait up to 30s for a connection
        "echo": False,  # Don't log all SQL statements
    }

    # JWT
    JWT_SECRET_KEY = os.environ.get(
        "JWT_SECRET_KEY", "jwt-secret-key-change-in-production"
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=30)

    # Redis
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # Cache configuration
    CACHE_TYPE = "RedisCache"
    CACHE_REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes default

    # Celery
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND = os.environ.get(
        "CELERY_RESULT_BACKEND", "redis://localhost:6379/1"
    )

    # Rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get("REDIS_URL", "memory://")
    RATELIMIT_STRATEGY = "fixed-window"
    RATELIMIT_DEFAULT = "10000 per day;2000 per hour"
    RATELIMIT_HEADERS_ENABLED = True

    # Telegram
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    ADMIN_TELEGRAM_IDS = [
        int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()
    ]

    # Error alerting
    ERROR_ALERT_THRESHOLD = 10  # Alert after 10 5xx errors
    ERROR_ALERT_WINDOW = 300  # Within 5 minutes
    ERROR_ALERT_COOLDOWN = 600  # Don't alert more than once per 10 minutes

    # Bot secret for cron job authentication
    BOT_SECRET = os.environ.get("BOT_SECRET", "")

    # OpenAI
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    OPENAI_PROXY = os.environ.get(
        "OPENAI_PROXY", ""
    )  # e.g., http://user:pass@host:port

    # CORS
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")

    # Swagger
    SWAGGER = {
        "title": "MoodSprint API",
        "uiversion": 3,
        "version": "1.0.0",
        "description": "API for MoodSprint - Mood-aware task management with gamification",
        "termsOfService": "",
        "specs_route": "/docs/",
    }


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    CACHE_TYPE = "SimpleCache"  # In-memory cache for development
    RATELIMIT_STORAGE_URL = "memory://"


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    # High rate limits for production app usage
    RATELIMIT_DEFAULT = "10000 per day;2000 per hour"


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    DEBUG = True  # Enable dev endpoints for testing
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}  # SQLite doesn't need pool settings
    STATIC_FOLDER = "/tmp/moodsprint_test_static"
    CACHE_TYPE = "NullCache"  # Disable cache for testing
    RATELIMIT_ENABLED = False  # Disable rate limiting for tests


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
