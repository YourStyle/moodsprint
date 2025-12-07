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
            text("SELECT * FROM users WHERE telegram_id = :tid"),
            {"tid": telegram_id}
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
            text("UPDATE users SET notifications_enabled = :enabled WHERE telegram_id = :tid"),
            {"enabled": enabled, "tid": telegram_id}
        )
        await session.commit()


async def get_user_stats(telegram_id: int) -> dict:
    """Get user statistics."""
    async with async_session() as session:
        # Get basic user info
        user_result = await session.execute(
            text("SELECT * FROM users WHERE telegram_id = :tid"),
            {"tid": telegram_id}
        )
        user = user_result.fetchone()
        if not user:
            return {}

        user_id = user._mapping['id']

        # Get task stats
        tasks_result = await session.execute(
            text("""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'completed') as completed_tasks,
                    COUNT(*) as total_tasks
                FROM tasks WHERE user_id = :uid
            """),
            {"uid": user_id}
        )
        tasks = tasks_result.fetchone()

        # Get focus stats
        focus_result = await session.execute(
            text("""
                SELECT
                    COUNT(*) as total_sessions,
                    COALESCE(SUM(actual_duration_minutes), 0) as total_minutes
                FROM focus_sessions
                WHERE user_id = :uid AND status = 'completed'
            """),
            {"uid": user_id}
        )
        focus = focus_result.fetchone()

        return {
            'user': dict(user._mapping),
            'completed_tasks': tasks._mapping['completed_tasks'] or 0,
            'total_tasks': tasks._mapping['total_tasks'] or 0,
            'total_sessions': focus._mapping['total_sessions'] or 0,
            'total_focus_minutes': focus._mapping['total_minutes'] or 0,
        }
