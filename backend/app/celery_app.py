"""Celery application configuration."""

import os

from celery import Celery

# Create Celery app
celery = Celery(
    "moodsprint",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
    include=[
        "app.tasks.ai_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.card_tasks",
    ],
)

# Celery configuration
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit
    worker_prefetch_multiplier=1,  # Disable prefetching for long tasks
    task_acks_late=True,  # Acknowledge after task completion
    task_reject_on_worker_lost=True,
    result_expires=3600,  # Results expire after 1 hour
    broker_connection_retry_on_startup=True,
)


def init_celery(app):
    """Initialize Celery with Flask app context."""
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        """Task that runs within Flask app context."""

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery
