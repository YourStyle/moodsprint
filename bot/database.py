"""Database connection for bot."""

from contextlib import asynccontextmanager

from config import config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

engine = create_async_engine(config.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncSession:
    """Get database session as async context manager."""
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


async def get_user_language(telegram_id: int) -> str:
    """Get user's language preference. Returns 'ru' as default."""
    try:
        async with async_session() as session:
            # First try with language column
            try:
                result = await session.execute(
                    text(
                        """
                        SELECT COALESCE(up.language, 'ru') as language
                        FROM users u
                        LEFT JOIN user_profiles up ON up.user_id = u.id
                        WHERE u.telegram_id = :tid
                    """
                    ),
                    {"tid": telegram_id},
                )
                row = result.fetchone()
                if row:
                    return row._mapping["language"]
            except Exception:
                # Column might not exist yet, fall through to default
                pass
            return "ru"
    except Exception:
        return "ru"


async def update_user_language(telegram_id: int, language: str):
    """Update user's language preference."""
    async with async_session() as session:
        # Ensure user profile exists
        await session.execute(
            text(
                """
                INSERT INTO user_profiles (user_id, language)
                SELECT id, :lang FROM users WHERE telegram_id = :tid
                ON CONFLICT (user_id) DO UPDATE SET language = :lang
            """
            ),
            {"tid": telegram_id, "lang": language},
        )
        await session.commit()


async def create_task_from_voice(
    telegram_id: int,
    title: str,
    due_date: str,
    scheduled_at: str | None = None,
) -> dict | None:
    """
    Create a task from voice message.

    Args:
        telegram_id: User's telegram ID
        title: Task title
        due_date: Due date in format 'YYYY-MM-DD'
        scheduled_at: Optional scheduled time in ISO format

    Returns:
        Created task dict or None if failed
    """
    from datetime import date as date_type
    from datetime import datetime

    async with async_session() as session:
        # Get user_id
        user_result = await session.execute(
            text("SELECT id FROM users WHERE telegram_id = :tid"),
            {"tid": telegram_id},
        )
        user_row = user_result.fetchone()
        if not user_row:
            return None

        user_id = user_row._mapping["id"]

        # Convert string date to date object for asyncpg
        if isinstance(due_date, str):
            due_date_obj = date_type.fromisoformat(due_date)
        else:
            due_date_obj = due_date

        # Convert scheduled_at string to datetime if provided
        scheduled_at_obj = None
        if scheduled_at:
            if isinstance(scheduled_at, str):
                scheduled_at_obj = datetime.fromisoformat(
                    scheduled_at.replace("Z", "+00:00")
                )
            else:
                scheduled_at_obj = scheduled_at

        # Create task
        result = await session.execute(
            text(
                """
                INSERT INTO tasks
                    (user_id, title, due_date, scheduled_at,
                     status, priority, created_at, updated_at)
                VALUES
                    (:user_id, :title, :due_date, :scheduled_at,
                     'pending', 'medium', NOW(), NOW())
                RETURNING id, title, due_date, scheduled_at
            """
            ),
            {
                "user_id": user_id,
                "title": title,
                "due_date": due_date_obj,
                "scheduled_at": scheduled_at_obj,
            },
        )
        row = result.fetchone()
        await session.commit()

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
            text(
                """
                SELECT u.*, up.notifications_enabled
                FROM users u
                LEFT JOIN user_profiles up ON up.user_id = u.id
                WHERE COALESCE(up.notifications_enabled, true) = true
            """
            )
        )
        return [dict(row._mapping) for row in result.fetchall()]


async def update_user_notifications(telegram_id: int, enabled: bool):
    """Update user notification settings."""
    async with async_session() as session:
        await session.execute(
            text(
                """
                UPDATE user_profiles SET notifications_enabled = :enabled
                WHERE user_id = (SELECT id FROM users WHERE telegram_id = :tid)
            """
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
                WHERE t.due_date < (CURRENT_TIMESTAMP AT TIME ZONE 'Europe/Moscow')::date
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
    Postpone a task to today (Moscow time) and increment postponed_count.

    Returns new postponed_count.
    """
    async with async_session() as session:
        # Update task - use Moscow timezone for date
        await session.execute(
            text(
                """
                UPDATE tasks
                SET due_date = (CURRENT_TIMESTAMP AT TIME ZONE 'Europe/Moscow')::date,
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

        priority_changes_json = (
            json.dumps(priority_changes) if priority_changes else None
        )

        await session.execute(
            text(
                """
                INSERT INTO postpone_logs
                    (user_id, date, tasks_postponed, priority_changes, notified, created_at)
                VALUES
                    (:user_id, CURRENT_DATE, :tasks_postponed,
                     :priority_changes::jsonb, false, NOW())
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
                        u.id as user_id,
                        COALESCE(
                            (SELECT preferred_time
                             FROM tasks t2
                             WHERE t2.user_id = u.id
                             AND t2.preferred_time IS NOT NULL
                             GROUP BY preferred_time
                             ORDER BY COUNT(*) DESC
                             LIMIT 1),
                            'morning'
                        ) as preferred_time
                    FROM users u
                    LEFT JOIN user_profiles up ON up.user_id = u.id
                    WHERE COALESCE(up.notifications_enabled, true) = true
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


async def get_task_suggestions(telegram_id: int, available_minutes: int) -> list[dict]:
    """
    Get task suggestions for a user based on available time.

    Returns tasks/subtasks that fit within the available time,
    sorted by priority and best fit.
    """
    async with async_session() as session:
        # First get user_id
        user_result = await session.execute(
            text("SELECT id FROM users WHERE telegram_id = :tid"),
            {"tid": telegram_id},
        )
        user_row = user_result.fetchone()
        if not user_row:
            return []

        user_id = user_row._mapping["id"]

        # Get incomplete tasks with their subtasks info
        result = await session.execute(
            text(
                """
                SELECT
                    t.id as task_id,
                    t.title as task_title,
                    t.priority,
                    t.task_type,
                    t.preferred_time,
                    t.postponed_count,
                    t.due_date,
                    COALESCE(
                        (SELECT SUM(s.estimated_minutes)
                         FROM subtasks s
                         WHERE s.task_id = t.id AND s.status != 'completed'),
                        30
                    ) as estimated_minutes,
                    (SELECT COUNT(*)
                     FROM subtasks s
                     WHERE s.task_id = t.id AND s.status != 'completed') as subtasks_count
                FROM tasks t
                WHERE t.user_id = :user_id
                AND t.status != 'completed'
                AND t.preferred_time IS NOT NULL
                ORDER BY
                    CASE t.priority
                        WHEN 'high' THEN 3
                        WHEN 'medium' THEN 2
                        ELSE 1
                    END DESC,
                    COALESCE(t.postponed_count, 0) DESC,
                    t.due_date ASC NULLS LAST
                LIMIT 10
            """
            ),
            {"user_id": user_id},
        )
        tasks = [dict(row._mapping) for row in result.fetchall()]

        suggestions = []
        for task in tasks:
            estimated = task["estimated_minutes"] or 30

            if estimated <= available_minutes:
                # Task fits
                fit_quality = (
                    "perfect" if estimated >= available_minutes * 0.7 else "good"
                )
                suggestions.append(
                    {
                        "task_id": task["task_id"],
                        "task_title": task["task_title"],
                        "priority": task["priority"],
                        "estimated_minutes": estimated,
                        "subtasks_count": task["subtasks_count"] or 0,
                        "fit_quality": fit_quality,
                    }
                )

        return suggestions[:5]  # Return top 5


async def get_subtask_suggestions(
    telegram_id: int, available_minutes: int
) -> list[dict]:
    """
    Get individual subtask suggestions that fit the available time.
    """
    async with async_session() as session:
        # First get user_id
        user_result = await session.execute(
            text("SELECT id FROM users WHERE telegram_id = :tid"),
            {"tid": telegram_id},
        )
        user_row = user_result.fetchone()
        if not user_row:
            return []

        user_id = user_row._mapping["id"]

        # Get incomplete subtasks that fit
        result = await session.execute(
            text(
                """
                SELECT
                    s.id as subtask_id,
                    s.title as subtask_title,
                    s.estimated_minutes,
                    t.id as task_id,
                    t.title as task_title,
                    t.priority
                FROM subtasks s
                JOIN tasks t ON s.task_id = t.id
                WHERE t.user_id = :user_id
                AND t.status != 'completed'
                AND s.status != 'completed'
                AND s.estimated_minutes <= :available_minutes
                ORDER BY
                    CASE t.priority
                        WHEN 'high' THEN 3
                        WHEN 'medium' THEN 2
                        ELSE 1
                    END DESC,
                    s.estimated_minutes DESC,
                    s."order" ASC
                LIMIT 5
            """
            ),
            {"user_id": user_id, "available_minutes": available_minutes},
        )
        return [dict(row._mapping) for row in result.fetchall()]


async def get_users_for_daily_suggestion(time_slot: str) -> list[dict]:
    """
    Get users who should receive daily task suggestion at this time slot.

    Returns users who:
    - Have notifications enabled
    - Prefer the given time slot based on their tasks
    - Haven't received a daily suggestion today
    """
    async with async_session() as session:
        result = await session.execute(
            text(
                """
                WITH user_preferred_times AS (
                    SELECT
                        u.id as user_id,
                        u.telegram_id,
                        u.first_name,
                        COALESCE(
                            (SELECT preferred_time
                             FROM tasks t2
                             WHERE t2.user_id = u.id
                             AND t2.preferred_time IS NOT NULL
                             GROUP BY preferred_time
                             ORDER BY COUNT(*) DESC
                             LIMIT 1),
                            'morning'
                        ) as preferred_time
                    FROM users u
                    LEFT JOIN user_profiles up ON up.user_id = u.id
                    WHERE COALESCE(up.notifications_enabled, true) = true
                )
                SELECT
                    upt.user_id,
                    upt.telegram_id,
                    upt.first_name,
                    upt.preferred_time
                FROM user_preferred_times upt
                WHERE upt.preferred_time = :time_slot
                AND NOT EXISTS (
                    SELECT 1 FROM daily_suggestion_logs dsl
                    WHERE dsl.user_id = upt.user_id
                    AND dsl.date = CURRENT_DATE
                )
            """
            ),
            {"time_slot": time_slot},
        )
        return [dict(row._mapping) for row in result.fetchall()]


async def mark_daily_suggestion_sent(user_id: int):
    """Mark that daily suggestion was sent to user today."""
    async with async_session() as session:
        await session.execute(
            text(
                """
                INSERT INTO daily_suggestion_logs (user_id, date, created_at)
                VALUES (:user_id, CURRENT_DATE, NOW())
                ON CONFLICT (user_id, date) DO NOTHING
            """
            ),
            {"user_id": user_id},
        )
        await session.commit()


async def get_scheduled_tasks_for_reminder() -> list[dict]:
    """
    Get tasks that are scheduled and need reminder notification.

    Returns tasks where:
    - scheduled_at <= NOW() (in UTC)
    - reminder_sent = false
    - status != completed

    Note: scheduled_at is stored in UTC, so we compare with UTC time.
    """
    async with async_session() as session:
        result = await session.execute(
            text(
                """
                SELECT
                    t.id as task_id,
                    t.title,
                    t.priority,
                    t.scheduled_at,
                    u.telegram_id,
                    u.first_name
                FROM tasks t
                JOIN users u ON t.user_id = u.id
                WHERE t.scheduled_at <= (NOW() AT TIME ZONE 'UTC')
                AND t.reminder_sent = false
                AND t.status != 'completed'
                ORDER BY t.scheduled_at ASC
                LIMIT 100
            """
            )
        )
        return [dict(row._mapping) for row in result.fetchall()]


async def mark_reminder_sent(task_id: int):
    """Mark task reminder as sent."""
    async with async_session() as session:
        await session.execute(
            text("UPDATE tasks SET reminder_sent = true WHERE id = :task_id"),
            {"task_id": task_id},
        )
        await session.commit()


async def snooze_task_reminder(task_id: int, minutes: int):
    """Snooze task reminder by specified minutes."""
    async with async_session() as session:
        await session.execute(
            text(
                """
                UPDATE tasks
                SET scheduled_at = NOW() + INTERVAL ':minutes minutes',
                    reminder_sent = false
                WHERE id = :task_id
            """.replace(
                    ":minutes", str(minutes)
                )
            ),
            {"task_id": task_id},
        )
        await session.commit()


async def reschedule_task_to_tomorrow(task_id: int):
    """Reschedule task to tomorrow at 9:00 Moscow time (6:00 UTC)."""
    async with async_session() as session:
        await session.execute(
            text(
                """
                UPDATE tasks
                SET scheduled_at = (CURRENT_DATE + INTERVAL '1 day' + INTERVAL '6 hours'),
                    reminder_sent = false,
                    due_date = CURRENT_DATE + INTERVAL '1 day'
                WHERE id = :task_id
            """
            ),
            {"task_id": task_id},
        )
        await session.commit()


async def reschedule_task_to_days(task_id: int, days: int):
    """Reschedule task to N days from now at 9:00 Moscow time (6:00 UTC)."""
    async with async_session() as session:
        await session.execute(
            text(
                f"""
                UPDATE tasks
                SET scheduled_at = (CURRENT_DATE + INTERVAL '{days} days' + INTERVAL '6 hours'),
                    reminder_sent = false,
                    due_date = CURRENT_DATE + INTERVAL '{days} days'
                WHERE id = :task_id
            """
            ),
            {"task_id": task_id},
        )
        await session.commit()


async def update_task_scheduled_at(task_id: int, scheduled_at: str):
    """Update task scheduled_at time for reminder."""
    async with async_session() as session:
        await session.execute(
            text(
                """
                UPDATE tasks
                SET scheduled_at = :scheduled_at,
                    reminder_sent = false
                WHERE id = :task_id
            """
            ),
            {"task_id": task_id, "scheduled_at": scheduled_at},
        )
        await session.commit()


async def delete_task(task_id: int):
    """Delete a task."""
    async with async_session() as session:
        await session.execute(
            text("DELETE FROM tasks WHERE id = :task_id"),
            {"task_id": task_id},
        )
        await session.commit()


async def get_users_with_pending_referrals() -> list[dict]:
    """
    Get users who have pending referral rewards that haven't been notified.
    Returns users with pending_count > 0 who need notification.
    """
    async with async_session() as session:
        result = await session.execute(
            text(
                """
                SELECT
                    u.telegram_id,
                    u.first_name,
                    COUNT(pr.id) as pending_count
                FROM users u
                JOIN pending_referral_rewards pr ON pr.user_id = u.id
                LEFT JOIN user_profiles up ON up.user_id = u.id
                WHERE pr.is_claimed = false
                  AND pr.notified_at IS NULL
                  AND COALESCE(up.notifications_enabled, true) = true
                GROUP BY u.id, u.telegram_id, u.first_name
                HAVING COUNT(pr.id) > 0
            """
            )
        )
        users = [dict(row._mapping) for row in result.fetchall()]

        # Mark as notified
        if users:
            user_ids = [u["telegram_id"] for u in users]
            await session.execute(
                text(
                    """
                    UPDATE pending_referral_rewards
                    SET notified_at = NOW()
                    WHERE user_id IN (SELECT id FROM users WHERE telegram_id = ANY(:tids))
                      AND is_claimed = false
                      AND notified_at IS NULL
                """
                ),
                {"tids": user_ids},
            )
            await session.commit()

        return users


# ============ Marketplace/Payment Functions ============


async def check_listing_available(listing_id: int) -> bool:
    """Check if a marketplace listing is still active."""
    async with async_session() as session:
        result = await session.execute(
            text(
                """
                SELECT id FROM market_listings
                WHERE id = :listing_id AND status = 'active'
            """
            ),
            {"listing_id": listing_id},
        )
        return result.fetchone() is not None


async def check_card_on_cooldown(card_id: int, user_id: int) -> bool:
    """Check if a card is on cooldown and belongs to user."""
    async with async_session() as session:
        result = await session.execute(
            text(
                """
                SELECT id FROM user_cards
                WHERE id = :card_id
                  AND user_id = :user_id
                  AND cooldown_until > NOW()
            """
            ),
            {"card_id": card_id, "user_id": user_id},
        )
        return result.fetchone() is not None


async def get_listing_for_purchase(listing_id: int) -> dict | None:
    """Get listing with card info for purchase."""
    async with async_session() as session:
        result = await session.execute(
            text(
                """
                SELECT
                    ml.id,
                    ml.seller_id,
                    ml.price_stars,
                    uc.id as card_id,
                    uc.name as card_name,
                    uc.rarity as card_rarity
                FROM market_listings ml
                JOIN user_cards uc ON ml.card_id = uc.id
                WHERE ml.id = :listing_id AND ml.status = 'active'
            """
            ),
            {"listing_id": listing_id},
        )
        row = result.fetchone()
        if not row:
            return None

        data = dict(row._mapping)
        return {
            "id": data["id"],
            "seller_id": data["seller_id"],
            "price_stars": data["price_stars"],
            "card": {
                "id": data["card_id"],
                "name": data["card_name"],
                "rarity": data["card_rarity"],
            },
        }


async def get_card_cooldown_info(card_id: int, user_id: int) -> dict | None:
    """Get card cooldown info for skip purchase."""
    async with async_session() as session:
        result = await session.execute(
            text(
                """
                SELECT
                    id, name, cooldown_until,
                    EXTRACT(EPOCH FROM (cooldown_until - NOW())) / 3600 as remaining_hours
                FROM user_cards
                WHERE id = :card_id AND user_id = :user_id
            """
            ),
            {"card_id": card_id, "user_id": user_id},
        )
        row = result.fetchone()
        if not row:
            return None

        data = dict(row._mapping)
        is_on_cooldown = (
            data["cooldown_until"] is not None and data["remaining_hours"] > 0
        )

        return {
            "id": data["id"],
            "name": data["name"],
            "is_on_cooldown": is_on_cooldown,
            "remaining_hours": (
                max(1, int(data["remaining_hours"] or 0) + 1) if is_on_cooldown else 0
            ),
        }


async def complete_marketplace_purchase(
    listing_id: int, buyer_id: int, telegram_payment_id: str
) -> dict:
    """Complete a marketplace purchase after successful payment."""
    async with async_session() as session:
        # Get listing
        listing_result = await session.execute(
            text(
                """
                SELECT ml.*, uc.name as card_name
                FROM market_listings ml
                JOIN user_cards uc ON ml.card_id = uc.id
                WHERE ml.id = :listing_id AND ml.status = 'active'
                FOR UPDATE
            """
            ),
            {"listing_id": listing_id},
        )
        listing_row = listing_result.fetchone()

        if not listing_row:
            return {"error": "listing_not_found"}

        listing = dict(listing_row._mapping)

        if listing["seller_id"] == buyer_id:
            return {"error": "cannot_buy_own"}

        seller_id = listing["seller_id"]
        card_id = listing["card_id"]
        price = listing["price_stars"]
        card_name = listing["card_name"]

        # Commission 10%
        commission = int(price * 0.10)
        seller_revenue = price - commission

        # Transfer card
        await session.execute(
            text(
                """
                UPDATE user_cards SET user_id = :buyer_id, is_in_deck = false
                WHERE id = :card_id
            """
            ),
            {"buyer_id": buyer_id, "card_id": card_id},
        )

        # Update listing
        await session.execute(
            text(
                """
                UPDATE market_listings
                SET status = 'sold', buyer_id = :buyer_id, sold_at = NOW()
                WHERE id = :listing_id
            """
            ),
            {"buyer_id": buyer_id, "listing_id": listing_id},
        )

        # Record buyer transaction
        await session.execute(
            text(
                """
                INSERT INTO stars_transactions
                    (user_id, amount, type, reference_type, reference_id,
                     telegram_payment_id, description, created_at)
                VALUES
                    (:user_id, :amount, 'card_purchase', 'listing', :listing_id,
                     :payment_id, :description, NOW())
            """
            ),
            {
                "user_id": buyer_id,
                "amount": -price,
                "listing_id": listing_id,
                "payment_id": telegram_payment_id,
                "description": f"Покупка карты: {card_name}",
            },
        )

        # Record seller transaction
        await session.execute(
            text(
                """
                INSERT INTO stars_transactions
                    (user_id, amount, type, reference_type, reference_id,
                     description, created_at)
                VALUES
                    (:user_id, :amount, 'card_sale', 'listing', :listing_id,
                     :description, NOW())
            """
            ),
            {
                "user_id": seller_id,
                "amount": seller_revenue,
                "listing_id": listing_id,
                "description": f"Продажа карты: {card_name}",
            },
        )

        # Update seller balance
        await session.execute(
            text(
                """
                INSERT INTO user_stars_balances (user_id, pending_balance, total_earned)
                VALUES (:user_id, :amount, :amount)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    pending_balance = user_stars_balances.pending_balance + :amount,
                    total_earned = user_stars_balances.total_earned + :amount,
                    updated_at = NOW()
            """
            ),
            {"user_id": seller_id, "amount": seller_revenue},
        )

        # Update buyer stats
        await session.execute(
            text(
                """
                INSERT INTO user_stars_balances (user_id, total_spent)
                VALUES (:user_id, :amount)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    total_spent = user_stars_balances.total_spent + :amount,
                    updated_at = NOW()
            """
            ),
            {"user_id": buyer_id, "amount": price},
        )

        await session.commit()

        return {
            "success": True,
            "card": {"id": card_id, "name": card_name},
            "price_paid": price,
            "seller_revenue": seller_revenue,
        }


async def complete_cooldown_skip(
    card_id: int, user_id: int, telegram_payment_id: str, price: int
) -> dict:
    """Complete cooldown skip after successful payment."""
    async with async_session() as session:
        # Get card
        card_result = await session.execute(
            text(
                """
                SELECT id, name, hp FROM user_cards
                WHERE id = :card_id AND user_id = :user_id
            """
            ),
            {"card_id": card_id, "user_id": user_id},
        )
        card_row = card_result.fetchone()

        if not card_row:
            return {"error": "card_not_found"}

        card = dict(card_row._mapping)

        # Clear cooldown and restore HP
        await session.execute(
            text(
                """
                UPDATE user_cards
                SET cooldown_until = NULL, current_hp = hp
                WHERE id = :card_id
            """
            ),
            {"card_id": card_id},
        )

        # Record transaction
        await session.execute(
            text(
                """
                INSERT INTO stars_transactions
                    (user_id, amount, type, reference_type, reference_id,
                     telegram_payment_id, description, created_at)
                VALUES
                    (:user_id, :amount, 'skip_cooldown', 'card', :card_id,
                     :payment_id, :description, NOW())
            """
            ),
            {
                "user_id": user_id,
                "amount": -price,
                "card_id": card_id,
                "payment_id": telegram_payment_id,
                "description": f"Пропуск перезарядки: {card['name']}",
            },
        )

        # Update balance stats
        await session.execute(
            text(
                """
                INSERT INTO user_stars_balances (user_id, total_spent)
                VALUES (:user_id, :amount)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    total_spent = user_stars_balances.total_spent + :amount,
                    updated_at = NOW()
            """
            ),
            {"user_id": user_id, "amount": price},
        )

        await session.commit()

        return {
            "success": True,
            "card": {"id": card_id, "name": card["name"]},
        }


# Sparks packs (mirrored from backend)
SPARKS_PACKS = {
    "starter": {"sparks": 100, "price_stars": 10},
    "basic": {"sparks": 500, "price_stars": 45},
    "standard": {"sparks": 1000, "price_stars": 80},
    "premium": {"sparks": 2500, "price_stars": 175},
    "elite": {"sparks": 5000, "price_stars": 300},
    "ultimate": {"sparks": 10000, "price_stars": 500},
}


async def complete_sparks_purchase(
    pack_id: str,
    user_id: int,
    telegram_payment_id: str,
) -> dict:
    """Complete sparks pack purchase after successful Stars payment."""
    pack = SPARKS_PACKS.get(pack_id)
    if not pack:
        return {"success": False, "error": "Invalid pack"}

    sparks_amount = pack["sparks"]

    async with get_session() as session:
        # Credit sparks to user
        await session.execute(
            text(
                """
                UPDATE users
                SET sparks = sparks + :amount
                WHERE id = :user_id
            """
            ),
            {"user_id": user_id, "amount": sparks_amount},
        )

        # Record sparks transaction
        await session.execute(
            text(
                """
                INSERT INTO sparks_transactions
                    (user_id, amount, type, description, created_at)
                VALUES
                    (:user_id, :amount, 'stars_purchase', :description, NOW())
            """
            ),
            {
                "user_id": user_id,
                "amount": sparks_amount,
                "description": f"Покупка пакета {pack_id} за Stars",
            },
        )

        # Record stars transaction
        await session.execute(
            text(
                """
                INSERT INTO stars_transactions
                    (user_id, amount, type, reference_type,
                     telegram_payment_id, description, created_at)
                VALUES
                    (:user_id, :amount, 'sparks_purchase', 'sparks',
                     :payment_id, :description, NOW())
            """
            ),
            {
                "user_id": user_id,
                "amount": -pack["price_stars"],
                "payment_id": telegram_payment_id,
                "description": f"Покупка {sparks_amount} Sparks",
            },
        )

        await session.commit()

        return {
            "success": True,
            "sparks": sparks_amount,
        }
