"""Main bot entry point."""

import asyncio
import logging
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from config import config
from handlers import main_router
from handlers.notifications import NotificationService
from services.deposit_service import check_deposits
from services.guild_quest_service import (
    expire_guild_quests,
    generate_guild_weekly_quests,
)

# Moscow timezone for all scheduled jobs
MOSCOW_TZ = ZoneInfo("Europe/Moscow")

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Main bot function."""
    # Initialize bot
    bot = Bot(
        token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Initialize dispatcher
    dp = Dispatcher()
    dp.include_router(main_router)

    # Initialize notification service
    notification_service = NotificationService(bot)

    # Initialize scheduler
    scheduler = AsyncIOScheduler()

    # Morning reminder at 9:00 AM Moscow time
    scheduler.add_job(
        notification_service.send_morning_reminder,
        CronTrigger(hour=9, minute=0, timezone=MOSCOW_TZ),
        id="morning_reminder",
    )

    # Streak reminder at 8:00 PM Moscow time
    scheduler.add_job(
        notification_service.send_streak_reminder,
        CronTrigger(hour=20, minute=0, timezone=MOSCOW_TZ),
        id="streak_reminder",
    )

    # Weekly summary on Sunday at 6:00 PM Moscow time
    scheduler.add_job(
        notification_service.send_weekly_summary,
        CronTrigger(day_of_week="sun", hour=18, minute=0, timezone=MOSCOW_TZ),
        id="weekly_summary",
    )

    # Postpone overdue tasks at 00:05 AM Moscow time daily
    scheduler.add_job(
        notification_service.postpone_overdue_tasks,
        CronTrigger(hour=0, minute=5, timezone=MOSCOW_TZ),
        id="postpone_overdue_tasks",
    )

    # Send postpone notifications based on user's preferred time (Moscow time)
    # Morning users at 9:10 AM
    scheduler.add_job(
        notification_service.send_postpone_notifications,
        CronTrigger(hour=9, minute=10, timezone=MOSCOW_TZ),
        args=["morning"],
        id="postpone_notify_morning",
    )

    # Afternoon users at 13:00
    scheduler.add_job(
        notification_service.send_postpone_notifications,
        CronTrigger(hour=13, minute=0, timezone=MOSCOW_TZ),
        args=["afternoon"],
        id="postpone_notify_afternoon",
    )

    # Evening users at 18:10
    scheduler.add_job(
        notification_service.send_postpone_notifications,
        CronTrigger(hour=18, minute=10, timezone=MOSCOW_TZ),
        args=["evening"],
        id="postpone_notify_evening",
    )

    # Night users at 21:00
    scheduler.add_job(
        notification_service.send_postpone_notifications,
        CronTrigger(hour=21, minute=0, timezone=MOSCOW_TZ),
        args=["night"],
        id="postpone_notify_night",
    )

    # Daily task suggestions based on user's preferred time (Moscow time)
    # Morning users at 9:30 AM
    scheduler.add_job(
        notification_service.send_daily_task_suggestion,
        CronTrigger(hour=9, minute=30, timezone=MOSCOW_TZ),
        args=["morning"],
        id="daily_suggestion_morning",
    )

    # Afternoon users at 13:30
    scheduler.add_job(
        notification_service.send_daily_task_suggestion,
        CronTrigger(hour=13, minute=30, timezone=MOSCOW_TZ),
        args=["afternoon"],
        id="daily_suggestion_afternoon",
    )

    # Evening users at 18:30
    scheduler.add_job(
        notification_service.send_daily_task_suggestion,
        CronTrigger(hour=18, minute=30, timezone=MOSCOW_TZ),
        args=["evening"],
        id="daily_suggestion_evening",
    )

    # Night users at 21:30
    scheduler.add_job(
        notification_service.send_daily_task_suggestion,
        CronTrigger(hour=21, minute=30, timezone=MOSCOW_TZ),
        args=["night"],
        id="daily_suggestion_night",
    )

    # Task reminders - check every minute (timezone doesn't matter for every-minute jobs)
    scheduler.add_job(
        notification_service.send_scheduled_task_reminders,
        CronTrigger(minute="*"),
        id="scheduled_task_reminders",
    )

    # Monster rotation - run daily at 00:10, actual generation happens on period start days
    scheduler.add_job(
        notification_service.rotate_monsters,
        CronTrigger(hour=0, minute=10, timezone=MOSCOW_TZ),
        id="monster_rotation",
    )

    # New referral notifications - check every hour
    scheduler.add_job(
        notification_service.send_new_referral_notifications,
        CronTrigger(minute=15, timezone=MOSCOW_TZ),  # Every hour at :15
        id="referral_notifications",
    )

    # Friend activity notifications - every hour at :45
    scheduler.add_job(
        notification_service.send_friend_activity_notifications,
        CronTrigger(minute=45, timezone=MOSCOW_TZ),
        id="friend_activity_notifications",
    )

    # Comeback messages for inactive users - daily at 14:00
    scheduler.add_job(
        notification_service.send_comeback_messages,
        CronTrigger(hour=14, minute=0, timezone=MOSCOW_TZ),
        id="comeback_messages",
    )

    # TON deposit monitoring - check every 30 seconds
    scheduler.add_job(
        check_deposits,
        "interval",
        seconds=30,
        id="ton_deposit_monitor",
    )

    # Resource usage monitoring - check every 5 minutes
    scheduler.add_job(
        notification_service.check_resource_usage,
        "interval",
        minutes=5,
        id="resource_monitor",
    )

    # Guild weekly quests - generate on Monday at 00:15
    scheduler.add_job(
        generate_guild_weekly_quests,
        CronTrigger(day_of_week="mon", hour=0, minute=15, timezone=MOSCOW_TZ),
        id="guild_weekly_quests",
    )

    # Expire old guild quests - daily at 00:20
    scheduler.add_job(
        expire_guild_quests,
        CronTrigger(hour=0, minute=20, timezone=MOSCOW_TZ),
        id="expire_guild_quests",
    )

    scheduler.start()

    # Run postpone check on startup (catches missed midnight cron after restarts)
    try:
        await notification_service.postpone_overdue_tasks()
        logger.info("Startup postpone check completed.")
    except Exception as e:
        logger.error(f"Startup postpone check failed: {e}")

    # Set bot commands
    from aiogram.types import BotCommand

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Начать"),
            BotCommand(command="app", description="Открыть MoodSprint"),
            BotCommand(command="task", description="Добавить задачу"),
            BotCommand(command="freetime", description="Есть свободное время?"),
            BotCommand(command="admin", description="Админ-панель"),
        ]
    )

    logger.info("Bot started!")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
