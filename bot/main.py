"""Main bot entry point."""
import asyncio
import logging
from datetime import datetime

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
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main bot function."""
    # Initialize bot
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
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
        id='morning_reminder'
    )

    # Streak reminder at 8:00 PM
    scheduler.add_job(
        notification_service.send_streak_reminder,
        CronTrigger(hour=20, minute=0),
        id='streak_reminder'
    )

    # Weekly summary on Sunday at 6:00 PM
    scheduler.add_job(
        notification_service.send_weekly_summary,
        CronTrigger(day_of_week='sun', hour=18, minute=0),
        id='weekly_summary'
    )

    scheduler.start()

    # Set bot commands
    from aiogram.types import BotCommand
    await bot.set_my_commands([
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="app", description="Open MoodSprint"),
        BotCommand(command="admin", description="Admin panel (admins only)"),
    ])

    logger.info("Bot started!")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(main())
