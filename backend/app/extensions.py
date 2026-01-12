"""Flask extensions initialization."""

import os

import redis
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Redis client
redis_client = None


def get_redis_client():
    """Get or create Redis client."""
    global redis_client
    if redis_client is None:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.from_url(redis_url, decode_responses=True)
    return redis_client


# Cache configuration
cache = Cache()

# Rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.environ.get("REDIS_URL", "memory://"),
)


def init_sentry(app):
    """Initialize Sentry error tracking."""
    sentry_dsn = os.environ.get("SENTRY_DSN")
    if sentry_dsn:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.flask import FlaskIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[
                FlaskIntegration(),
                SqlalchemyIntegration(),
                CeleryIntegration(),
                RedisIntegration(),
            ],
            traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
            profiles_sample_rate=0.1,
            environment=os.environ.get("FLASK_ENV", "production"),
            send_default_pii=False,  # Don't send personal data
        )
        app.logger.info("Sentry initialized successfully")
    else:
        app.logger.warning("SENTRY_DSN not set, error tracking disabled")
