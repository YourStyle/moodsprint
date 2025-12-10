"""Main bot entry point."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import config
from handlers import main_router
from handlers.notifications import NotificationService

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

    # Morning reminder at 9:00 AM
    scheduler.add_job(
        notification_service.send_morning_reminder,
        CronTrigger(hour=9, minute=0),
        id="morning_reminder",
    )

    # Streak reminder at 8:00 PM
    scheduler.add_job(
        notification_service.send_streak_reminder,
        CronTrigger(hour=20, minute=0),
        id="streak_reminder",
    )

    # Weekly summary on Sunday at 6:00 PM
    scheduler.add_job(
        notification_service.send_weekly_summary,
        CronTrigger(day_of_week="sun", hour=18, minute=0),
        id="weekly_summary",
    )

    # Postpone overdue tasks at 00:05 AM daily (just postpones, no notifications)
    scheduler.add_job(
        notification_service.postpone_overdue_tasks,
        CronTrigger(hour=0, minute=5),
        id="postpone_overdue_tasks",
    )

    # Send postpone notifications based on user's preferred time
    # Morning users at 9:10 AM
    scheduler.add_job(
        notification_service.send_postpone_notifications,
        CronTrigger(hour=9, minute=10),
        args=["morning"],
        id="postpone_notify_morning",
    )

    # Afternoon users at 13:00
    scheduler.add_job(
        notification_service.send_postpone_notifications,
        CronTrigger(hour=13, minute=0),
        args=["afternoon"],
        id="postpone_notify_afternoon",
    )

    # Evening users at 18:10
    scheduler.add_job(
        notification_service.send_postpone_notifications,
        CronTrigger(hour=18, minute=10),
        args=["evening"],
        id="postpone_notify_evening",
    )

    # Night users at 21:00
    scheduler.add_job(
        notification_service.send_postpone_notifications,
        CronTrigger(hour=21, minute=0),
        args=["night"],
        id="postpone_notify_night",
    )

    # Daily task suggestions based on user's preferred time
    # Morning users at 9:30 AM
    scheduler.add_job(
        notification_service.send_daily_task_suggestion,
        CronTrigger(hour=9, minute=30),
        args=["morning"],
        id="daily_suggestion_morning",
    )

    # Afternoon users at 13:30
    scheduler.add_job(
        notification_service.send_daily_task_suggestion,
        CronTrigger(hour=13, minute=30),
        args=["afternoon"],
        id="daily_suggestion_afternoon",
    )

    # Evening users at 18:30
    scheduler.add_job(
        notification_service.send_daily_task_suggestion,
        CronTrigger(hour=18, minute=30),
        args=["evening"],
        id="daily_suggestion_evening",
    )

    # Night users at 21:30
    scheduler.add_job(
        notification_service.send_daily_task_suggestion,
        CronTrigger(hour=21, minute=30),
        args=["night"],
        id="daily_suggestion_night",
    )

    scheduler.start()

    # Set bot commands
    from aiogram.types import BotCommand

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Начать"),
            BotCommand(command="app", description="Открыть MoodSprint"),
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
