"""Database connection for bot."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from config import config

engine = create_async_engine(config.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    """Get database session."""
    async with async_session() as session:
        yield session


async def get_user_by_telegram_id(telegram_id: int) -> dict | None:
    """Get user by Telegram ID."""
    async with async_session() as session:
        result = await session.execute(
            text("SELECT * FROM users WHERE telegram_id = :tid"), {"tid": telegram_id}
        )
        row = result.fetchone()
        if row:
            return dict(row._mapping)
        return None


async def get_all_users() -> list[dict]:
    """Get all users for broadcast."""
    async with async_session() as session:
        result = await session.execute(text("SELECT * FROM users"))
        return [dict(row._mapping) for row in result.fetchall()]


async def get_users_with_notifications_enabled() -> list[dict]:
    """Get users who have notifications enabled."""
    async with async_session() as session:
        result = await session.execute(
            text("SELECT * FROM users WHERE notifications_enabled = true")
        )
        return [dict(row._mapping) for row in result.fetchall()]


async def update_user_notifications(telegram_id: int, enabled: bool):
    """Update user notification settings."""
    async with async_session() as session:
        await session.execute(
            text(
                "UPDATE users SET notifications_enabled = :enabled WHERE telegram_id = :tid"
            ),
            {"enabled": enabled, "tid": telegram_id},
        )
        await session.commit()


async def get_user_stats(telegram_id: int) -> dict:
    """Get user statistics."""
    async with async_session() as session:
        # Get basic user info
        user_result = await session.execute(
            text("SELECT * FROM users WHERE telegram_id = :tid"), {"tid": telegram_id}
        )
        user = user_result.fetchone()
        if not user:
            return {}

        user_id = user._mapping["id"]

        # Get task stats
        tasks_result = await session.execute(
            text(
                """
                SELECT
                    COUNT(*) FILTER (WHERE status = 'completed') as completed_tasks,
                    COUNT(*) as total_tasks
                FROM tasks WHERE user_id = :uid
            """
            ),
            {"uid": user_id},
        )
        tasks = tasks_result.fetchone()

        # Get focus stats
        focus_result = await session.execute(
            text(
                """
                SELECT
                    COUNT(*) as total_sessions,
                    COALESCE(SUM(actual_duration_minutes), 0) as total_minutes
                FROM focus_sessions
                WHERE user_id = :uid AND status = 'completed'
            """
            ),
            {"uid": user_id},
        )
        focus = focus_result.fetchone()

        return {
            "user": dict(user._mapping),
            "completed_tasks": tasks._mapping["completed_tasks"] or 0,
            "total_tasks": tasks._mapping["total_tasks"] or 0,
            "total_sessions": focus._mapping["total_sessions"] or 0,
            "total_focus_minutes": focus._mapping["total_minutes"] or 0,
        }


async def get_overdue_tasks_by_user() -> dict[int, list[dict]]:
    """Get all overdue tasks grouped by user_id."""
    async with async_session() as session:
        result = await session.execute(
            text(
                """
                SELECT t.id, t.user_id, t.title, t.description, t.priority,
                       t.postponed_count, t.due_date, u.telegram_id
                FROM tasks t
                JOIN users u ON t.user_id = u.id
                WHERE t.due_date < CURRENT_DATE
                AND t.status != 'completed'
                ORDER BY t.user_id
            """
            )
        )
        rows = result.fetchall()

        # Group by user_id
        users_tasks: dict[int, list[dict]] = {}
        for row in rows:
            data = dict(row._mapping)
            user_id = data["user_id"]
            if user_id not in users_tasks:
                users_tasks[user_id] = []
            users_tasks[user_id].append(data)

        return users_tasks


async def postpone_task(task_id: int) -> int:
    """
    Postpone a task to today and increment postponed_count.

    Returns new postponed_count.
    """
    async with async_session() as session:
        # Update task
        await session.execute(
            text(
                """
                UPDATE tasks
                SET due_date = CURRENT_DATE,
                    postponed_count = COALESCE(postponed_count, 0) + 1,
                    updated_at = NOW()
                WHERE id = :task_id
            """
            ),
            {"task_id": task_id},
        )
        await session.commit()

        # Get new postponed_count
        result = await session.execute(
            text("SELECT postponed_count FROM tasks WHERE id = :task_id"),
            {"task_id": task_id},
        )
        row = result.fetchone()
        return row._mapping["postponed_count"] if row else 0


async def update_task_priority(task_id: int, new_priority: str):
    """Update task priority."""
    async with async_session() as session:
        await session.execute(
            text(
                """
                UPDATE tasks
                SET priority = :priority,
                    updated_at = NOW()
                WHERE id = :task_id
            """
            ),
            {"task_id": task_id, "priority": new_priority},
        )
        await session.commit()


async def create_postpone_log(
    user_id: int,
    tasks_postponed: int,
    priority_changes: list[dict] | None = None,
):
    """Create a postpone log entry for today."""
    async with async_session() as session:
        import json

        priority_changes_json = json.dumps(priority_changes) if priority_changes else None

        await session.execute(
            text(
                """
                INSERT INTO postpone_logs (user_id, date, tasks_postponed, priority_changes, notified, created_at)
                VALUES (:user_id, CURRENT_DATE, :tasks_postponed, :priority_changes::jsonb, false, NOW())
                ON CONFLICT (user_id, date)
                DO UPDATE SET
                    tasks_postponed = :tasks_postponed,
                    priority_changes = :priority_changes::jsonb,
                    notified = false
            """
            ),
            {
                "user_id": user_id,
                "tasks_postponed": tasks_postponed,
                "priority_changes": priority_changes_json,
            },
        )
        await session.commit()


async def get_user_preferred_time(user_id: int) -> str:
    """
    Get user's preferred working time based on their tasks.

    Returns the most common preferred_time from user's tasks,
    or 'morning' as default.
    """
    async with async_session() as session:
        result = await session.execute(
            text(
                """
                SELECT preferred_time, COUNT(*) as cnt
                FROM tasks
                WHERE user_id = :user_id
                AND preferred_time IS NOT NULL
                GROUP BY preferred_time
                ORDER BY cnt DESC
                LIMIT 1
            """
            ),
            {"user_id": user_id},
        )
        row = result.fetchone()
        if row and row._mapping["preferred_time"]:
            return row._mapping["preferred_time"]
        return "morning"  # Default


async def get_unnotified_postpone_logs_for_time(time_slot: str) -> list[dict]:
    """
    Get unnotified postpone logs for users who prefer a specific time slot.

    Returns list of logs with user info for users who:
    - Have unnotified postpone logs for today
    - Have notifications enabled
    - Prefer the given time slot based on their tasks
    """
    async with async_session() as session:
        result = await session.execute(
            text(
                """
                WITH user_preferred_times AS (
                    SELECT
                        user_id,
                        COALESCE(
                            (SELECT preferred_time
                             FROM tasks t2
                             WHERE t2.user_id = users.id
                             AND t2.preferred_time IS NOT NULL
                             GROUP BY preferred_time
                             ORDER BY COUNT(*) DESC
                             LIMIT 1),
                            'morning'
                        ) as preferred_time
                    FROM users
                    WHERE notifications_enabled = true
                )
                SELECT
                    pl.id as log_id,
                    pl.user_id,
                    pl.tasks_postponed,
                    pl.priority_changes,
                    u.telegram_id,
                    u.first_name,
                    upt.preferred_time
                FROM postpone_logs pl
                JOIN users u ON pl.user_id = u.id
                JOIN user_preferred_times upt ON upt.user_id = u.id
                WHERE pl.date = CURRENT_DATE
                AND pl.notified = false
                AND pl.tasks_postponed > 0
                AND upt.preferred_time = :time_slot
            """
            ),
            {"time_slot": time_slot},
        )
        return [dict(row._mapping) for row in result.fetchall()]


async def mark_postpone_log_notified(log_id: int):
    """Mark a postpone log as notified."""
    async with async_session() as session:
        await session.execute(
            text("UPDATE postpone_logs SET notified = true WHERE id = :log_id"),
            {"log_id": log_id},
        )
        await session.commit()
