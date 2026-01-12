"""Structured logging configuration for production."""

import logging
import sys

import structlog
from pythonjsonlogger import jsonlogger


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
            fmt="%(timestamp)s %(level)s %(name)s %(message)s",
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
        import time

        from flask import g, request

        if hasattr(g, "request_start_time"):
            duration_ms = (time.time() - g.request_start_time) * 1000

            # Skip health checks from logging
            if request.path != "/health":
                logger = structlog.get_logger()
                logger.info(
                    "request_completed",
                    status_code=response.status_code,
                    duration_ms=round(duration_ms, 2),
                    content_length=response.content_length,
                )

        return response

    return app
