"""Notification-related async tasks."""

import structlog

from app.celery_app import celery

logger = structlog.get_logger()


@celery.task(bind=True, max_retries=3, default_retry_delay=30)
def send_reminder_async(self, user_id: int, task_id: int, message: str = None):
    """Send task reminder notification to user."""
    from app import db
    from app.models import Task, User
    from app.utils.notifications import send_telegram_notification

    try:
        logger.info("send_reminder_started", user_id=user_id, task_id=task_id)

        user = db.session.get(User, user_id)
        task = db.session.get(Task, task_id)

        if not user or not task:
            logger.warning(
                "send_reminder_missing_data",
                user_id=user_id,
                task_id=task_id,
                user_exists=bool(user),
                task_exists=bool(task),
            )
            return {"success": False, "error": "User or task not found"}

        if not user.telegram_id:
            logger.warning("send_reminder_no_telegram", user_id=user_id)
            return {"success": False, "error": "User has no Telegram ID"}

        # Build reminder message
        if not message:
            message = f"Напоминание о задаче: {task.title}"

        success = send_telegram_notification(user.telegram_id, message)

        if success:
            logger.info("send_reminder_completed", user_id=user_id, task_id=task_id)
            return {"success": True}
        else:
            logger.warning("send_reminder_failed", user_id=user_id, task_id=task_id)
            return {"success": False, "error": "Failed to send notification"}

    except Exception as e:
        logger.error(
            "send_reminder_error", user_id=user_id, task_id=task_id, error=str(e)
        )
        raise self.retry(exc=e)


@celery.task(bind=True)
def send_batch_reminders(self, user_ids: list, message: str):
    """Send reminder to multiple users."""
    logger.info("send_batch_reminders_started", user_count=len(user_ids))

    results = {"success": 0, "failed": 0}

    for user_id in user_ids:
        try:
            from app import db
            from app.models import User
            from app.utils.notifications import send_telegram_notification

            user = db.session.get(User, user_id)
            if user and user.telegram_id:
                if send_telegram_notification(user.telegram_id, message):
                    results["success"] += 1
                else:
                    results["failed"] += 1
            else:
                results["failed"] += 1
        except Exception as e:
            logger.error("send_batch_reminder_error", user_id=user_id, error=str(e))
            results["failed"] += 1

    logger.info("send_batch_reminders_completed", results=results)
    return results
