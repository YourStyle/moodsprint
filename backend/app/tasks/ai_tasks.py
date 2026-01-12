"""AI-related async tasks."""

import structlog

from app.celery_app import celery

logger = structlog.get_logger()


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def decompose_task_async(self, task_id: int, user_id: int, mood_level: int = None):
    """Decompose a task into subtasks asynchronously."""
    from app import db
    from app.models import Subtask, Task
    from app.services.ai_decomposer import AIDecomposer

    try:
        logger.info("decompose_task_started", task_id=task_id, user_id=user_id)

        task = db.session.get(Task, task_id)
        if not task:
            logger.warning("task_not_found", task_id=task_id)
            return {"success": False, "error": "Task not found"}

        decomposer = AIDecomposer()
        subtasks_data = decomposer.decompose(
            task_title=task.title,
            mood_level=mood_level,
        )

        # Create subtasks
        for i, subtask_data in enumerate(subtasks_data):
            subtask = Subtask(
                task_id=task_id,
                title=subtask_data.get("title", f"Step {i + 1}"),
                description=subtask_data.get("description"),
                estimated_minutes=subtask_data.get("estimated_minutes", 15),
                order=i + 1,
            )
            db.session.add(subtask)

        db.session.commit()
        logger.info(
            "decompose_task_completed",
            task_id=task_id,
            subtasks_count=len(subtasks_data),
        )

        return {"success": True, "subtasks_count": len(subtasks_data)}

    except Exception as e:
        logger.error("decompose_task_failed", task_id=task_id, error=str(e))
        raise self.retry(exc=e)


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_suggestions_async(self, user_id: int, context: str = None):
    """Generate task suggestions for user asynchronously."""
    from app.services.priority_advisor import PriorityAdvisor

    try:
        logger.info("generate_suggestions_started", user_id=user_id)

        advisor = PriorityAdvisor()
        suggestions = advisor.get_suggestions(user_id=user_id, context=context)

        logger.info(
            "generate_suggestions_completed",
            user_id=user_id,
            suggestions_count=len(suggestions),
        )

        return {"success": True, "suggestions": suggestions}

    except Exception as e:
        logger.error("generate_suggestions_failed", user_id=user_id, error=str(e))
        raise self.retry(exc=e)
