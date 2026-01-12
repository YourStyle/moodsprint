"""Structured logging configuration for production."""

import logging
import sys
import time

import requests
import structlog
from pythonjsonlogger import jsonlogger

# Redis keys for error tracking
ERROR_COUNT_KEY = "backend:errors:5xx:count"
ERROR_ALERT_SENT_KEY = "backend:errors:5xx:alert_sent"


def send_admin_alert(app, error_count: int, sample_errors: list):
    """Send alert to admin Telegram IDs about high error rate."""
    bot_token = app.config.get("TELEGRAM_BOT_TOKEN", "")
    admin_ids = app.config.get("ADMIN_TELEGRAM_IDS", [])

    if not bot_token or not admin_ids:
        return

    message = (
        f"🚨 <b>Backend Alert</b>\n\n"
        f"Обнаружено {error_count} ошибок 5xx за последние 5 минут!\n\n"
    )
    if sample_errors:
        message += "<b>Примеры:</b>\n"
        for err in sample_errors[:3]:
            message += f"• {err}\n"

    for admin_id in admin_ids:
        try:
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": admin_id,
                    "text": message,
                    "parse_mode": "HTML",
                },
                timeout=5,
            )
        except Exception:
            pass  # Don't fail on alert errors


def track_5xx_error(app, path: str, status_code: int):
    """Track 5xx errors in Redis and alert if threshold exceeded."""
    from app.extensions import get_redis_client

    try:
        redis = get_redis_client()
        window = app.config.get("ERROR_ALERT_WINDOW", 300)
        threshold = app.config.get("ERROR_ALERT_THRESHOLD", 10)
        cooldown = app.config.get("ERROR_ALERT_COOLDOWN", 600)

        # Add error to list with timestamp
        error_key = f"{ERROR_COUNT_KEY}:{int(time.time() // window)}"
        error_info = f"{status_code} {path}"

        pipe = redis.pipeline()
        pipe.rpush(error_key, error_info)
        pipe.expire(error_key, window * 2)
        pipe.llen(error_key)
        results = pipe.execute()

        error_count = results[2]

        # Check if we should alert
        if error_count >= threshold:
            # Check cooldown
            if not redis.get(ERROR_ALERT_SENT_KEY):
                # Get sample errors
                sample_errors = redis.lrange(error_key, 0, 4)
                sample_errors = [
                    e.decode() if isinstance(e, bytes) else e for e in sample_errors
                ]

                # Send alert
                send_admin_alert(app, error_count, sample_errors)

                # Set cooldown
                redis.setex(ERROR_ALERT_SENT_KEY, cooldown, "1")

    except Exception:
        pass  # Don't fail on tracking errors


def setup_logging(app):
    """Configure structured JSON logging for production."""
    log_level = logging.DEBUG if app.debug else logging.INFO

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            (
                structlog.processors.JSONRenderer()
                if not app.debug
                else structlog.dev.ConsoleRenderer()
            ),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    if not app.debug:
        # JSON formatter for production
        json_formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"levelname": "level", "asctime": "timestamp"},
        )

        # Remove default handlers
        app.logger.handlers = []

        # Add JSON handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(json_formatter)
        handler.setLevel(log_level)

        app.logger.addHandler(handler)
        app.logger.setLevel(log_level)

        # Configure werkzeug and sqlalchemy loggers
        for logger_name in ["werkzeug", "sqlalchemy.engine"]:
            logger = logging.getLogger(logger_name)
            logger.handlers = []
            logger.addHandler(handler)
            logger.setLevel(logging.WARNING)

    # Request logging middleware
    @app.before_request
    def log_request_info():
        import time
        import uuid

        from flask import g, request

        g.request_id = str(uuid.uuid4())[:8]
        g.request_start_time = time.time()

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=g.request_id,
            method=request.method,
            path=request.path,
            remote_addr=request.remote_addr,
        )

    @app.after_request
    def log_response_info(response):
        from flask import g, request

        if hasattr(g, "request_start_time"):
            duration_ms = (time.time() - g.request_start_time) * 1000

            # Skip health checks from logging
            if request.path not in ("/health", "/ready"):
                logger = structlog.get_logger()
                logger.info(
                    "request_completed",
                    status_code=response.status_code,
                    duration_ms=round(duration_ms, 2),
                    content_length=response.content_length,
                )

            # Track 5xx errors for alerting
            if response.status_code >= 500:
                track_5xx_error(app, request.path, response.status_code)

        return response

    return app
