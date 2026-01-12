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
