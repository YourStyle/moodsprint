"""Task business logic helpers.

Extracted from app.api.tasks to keep route handlers thin.
"""

import logging
from datetime import date, datetime

from app import db
from app.models import PostponeLog, Task
from app.models.task import TaskPriority, TaskStatus

logger = logging.getLogger(__name__)

# Minimum time (in minutes) after task creation before a card can be earned
MIN_TASK_TIME_FOR_CARD = 10

# Number of first tasks that bypass the time restriction (onboarding experience)
FIRST_TASKS_WITHOUT_TIME_LIMIT = 5


def should_skip_time_check_for_card(user_id: int) -> bool:
    """Check if user should skip the time restriction for cards.

    First N tasks created by user get cards immediately regardless of time.
    This improves onboarding experience.
    """
    completed_tasks_count = Task.query.filter_by(
        user_id=user_id, status=TaskStatus.COMPLETED.value
    ).count()
    return completed_tasks_count < FIRST_TASKS_WITHOUT_TIME_LIMIT


def get_current_time_slot() -> str:
    """Get current time slot based on hour (Moscow time, UTC+3)."""
    # Server is UTC, Moscow is UTC+3
    hour = (datetime.utcnow().hour + 3) % 24
    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "afternoon"
    elif 18 <= hour < 22:
        return "evening"
    else:
        return "night"


def auto_postpone_overdue_tasks(user_id: int) -> int:
    """
    Auto-postpone overdue tasks to today (fallback if bot cron didn't run).

    Returns count of postponed tasks.
    """
    today = date.today()

    # Find overdue incomplete tasks for this user
    overdue_tasks = Task.query.filter(
        Task.user_id == user_id,
        Task.due_date < today,
        Task.status.notin_([TaskStatus.COMPLETED.value, TaskStatus.ARCHIVED.value]),
    ).all()

    if not overdue_tasks:
        return 0

    postponed_count = 0
    priority_changes = []

    for task in overdue_tasks:
        # Save original due_date if not already saved
        if not task.original_due_date:
            task.original_due_date = task.due_date

        task.due_date = today
        task.postponed_count = (task.postponed_count or 0) + 1
        postponed_count += 1

        # Auto-archive after 5 postponements
        if task.postponed_count >= 5:
            task.status = TaskStatus.ARCHIVED.value
            continue

        # Check if priority should be increased (after 2+ postponements)
        if task.postponed_count >= 3 and task.priority != TaskPriority.HIGH.value:
            old_priority = task.priority
            if task.priority == TaskPriority.MEDIUM.value:
                task.priority = TaskPriority.HIGH.value
            elif task.priority == TaskPriority.LOW.value:
                task.priority = TaskPriority.MEDIUM.value

            if old_priority != task.priority:
                priority_changes.append(
                    {
                        "task_id": task.id,
                        "task_title": task.title[:50],
                        "old_priority": old_priority,
                        "new_priority": task.priority,
                        "postponed_count": task.postponed_count,
                    }
                )

    if postponed_count > 0:
        # Create or update postpone log for today
        existing_log = PostponeLog.query.filter_by(user_id=user_id, date=today).first()
        if not existing_log:
            log = PostponeLog(
                user_id=user_id,
                date=today,
                tasks_postponed=postponed_count,
                priority_changes=priority_changes if priority_changes else None,
                notified=False,
            )
            db.session.add(log)

        db.session.commit()
        logger.info(f"Auto-postponed {postponed_count} tasks for user {user_id}")

    return postponed_count


def calculate_task_score(
    task: Task,
    current_time_slot: str,
    user_favorite_types: list[str] | None,
    today: date,
) -> int:
    """Calculate sorting score for a task."""
    score = 0

    # Priority weight (HIGH=100, MEDIUM=50, LOW=0)
    priority_weights = {"high": 100, "medium": 50, "low": 0}
    score += priority_weights.get(task.priority, 50)

    # Time match (+30 if preferred time matches current time slot)
    if task.preferred_time and task.preferred_time == current_time_slot:
        score += 30

    # Type match (+20 if task type is in user's favorites)
    if user_favorite_types and task.task_type in user_favorite_types:
        score += 20

    # Postponed count (+15 per postponement)
    score += (task.postponed_count or 0) * 15

    # Overdue bonus (+50 if task is overdue)
    if (
        task.due_date
        and task.due_date < today
        and task.status != TaskStatus.COMPLETED.value
    ):
        score += 50

    return score
