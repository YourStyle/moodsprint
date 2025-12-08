"""Notification handlers and scheduled tasks."""

from aiogram import Router, Bot
from datetime import datetime
import asyncio
import logging

from database import get_users_with_notifications_enabled, get_user_stats
from keyboards import get_webapp_button

router = Router()
logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending scheduled notifications."""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_morning_reminder(self):
        """Send morning motivation reminder."""
        users = await get_users_with_notifications_enabled()

        messages = [
            "Good morning! Ready to tackle today? Open MoodSprint and log how you're feeling.",
            "Rise and shine! Start your day with a quick mood check.",
            "New day, new opportunities! What's on your mind today?",
        ]

        import random

        message = random.choice(messages)

        for user in users:
            try:
                await self.bot.send_message(
                    user["telegram_id"], f"{message}", reply_markup=get_webapp_button()
                )
            except Exception as e:
                logger.error(
                    f"Failed to send morning reminder to {user['telegram_id']}: {e}"
                )

            await asyncio.sleep(0.05)  # Rate limiting

    async def send_streak_reminder(self):
        """Send reminder to users who might lose their streak."""
        users = await get_users_with_notifications_enabled()

        for user in users:
            streak = user.get("streak_days", 0)
            last_activity = user.get("last_activity_date")

            if streak > 0 and last_activity:
                # Check if they haven't been active today
                last_date = (
                    datetime.fromisoformat(str(last_activity)).date()
                    if isinstance(last_activity, str)
                    else last_activity
                )
                today = datetime.now().date()

                if last_date < today:
                    try:
                        await self.bot.send_message(
                            user["telegram_id"],
                            f"Don't lose your {streak}-day streak! Complete just one small step to keep it going.",
                            reply_markup=get_webapp_button(),
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to send streak reminder to {user['telegram_id']}: {e}"
                        )

                    await asyncio.sleep(0.05)

    async def send_weekly_summary(self):
        """Send weekly summary to users."""
        users = await get_users_with_notifications_enabled()

        for user in users:
            try:
                stats = await get_user_stats(user["telegram_id"])
                if not stats:
                    continue

                u = stats["user"]
                text = (
                    f"Your weekly MoodSprint summary\n"
                    f"{'=' * 25}\n\n"
                    f"Level: {u.get('level', 1)} | XP: {u.get('xp', 0)}\n"
                    f"Current streak: {u.get('streak_days', 0)} days\n\n"
                    f"Tasks completed: {stats['completed_tasks']}\n"
                    f"Focus time: {stats['total_focus_minutes']} min\n\n"
                    "Keep up the great work!"
                )

                await self.bot.send_message(
                    user["telegram_id"], text, reply_markup=get_webapp_button()
                )
            except Exception as e:
                logger.error(
                    f"Failed to send weekly summary to {user['telegram_id']}: {e}"
                )

            await asyncio.sleep(0.05)

    async def send_achievement_notification(
        self, telegram_id: int, achievement_title: str, xp_reward: int
    ):
        """Send achievement unlock notification."""
        try:
            await self.bot.send_message(
                telegram_id,
                f"Achievement Unlocked!\n\n"
                f"{achievement_title}\n"
                f"+{xp_reward} XP\n\n"
                "Open MoodSprint to see your progress!",
                reply_markup=get_webapp_button(),
            )
        except Exception as e:
            logger.error(
                f"Failed to send achievement notification to {telegram_id}: {e}"
            )

    async def send_level_up_notification(self, telegram_id: int, new_level: int):
        """Send level up notification."""
        try:
            await self.bot.send_message(
                telegram_id,
                f"Level Up!\n\n" f"You've reached Level {new_level}!\n\n" "Keep going!",
                reply_markup=get_webapp_button(),
            )
        except Exception as e:
            logger.error(f"Failed to send level up notification to {telegram_id}: {e}")

    async def send_focus_complete_notification(
        self, telegram_id: int, duration_minutes: int, xp_earned: int
    ):
        """Send focus session complete notification."""
        try:
            await self.bot.send_message(
                telegram_id,
                f"Focus session complete!\n\n"
                f"Duration: {duration_minutes} minutes\n"
                f"XP earned: +{xp_earned}\n\n"
                "Great focus! Take a short break.",
                reply_markup=get_webapp_button(),
            )
        except Exception as e:
            logger.error(f"Failed to send focus notification to {telegram_id}: {e}")
