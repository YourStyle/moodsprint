"""Notification handlers and scheduled tasks."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import psutil
from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from config import config
from database import (
    create_postpone_log,
    get_overdue_tasks_by_user,
    get_scheduled_tasks_for_reminder,
    get_task_suggestions,
    get_unnotified_postpone_logs_for_time,
    get_user_stats,
    get_users_for_daily_suggestion,
    get_users_tasks_for_today,
    get_users_with_notifications_enabled,
    mark_daily_suggestion_sent,
    mark_postpone_log_notified,
    mark_reminder_sent,
    postpone_task,
    update_task_priority,
)
from keyboards import (
    get_morning_reminder_keyboard,
    get_task_reminder_keyboard,
    get_task_suggestion_keyboard,
    get_webapp_button,
)

router = Router()
logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending scheduled notifications."""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_morning_reminder(self):
        """Send personalized morning reminder with today's tasks."""
        from translations import get_text

        # Batch query all today's tasks grouped by user
        users_tasks = await get_users_tasks_for_today()

        # Also get users with no tasks but notifications enabled
        all_users = await get_users_with_notifications_enabled()
        users_with_tasks_ids = set()
        if users_tasks:
            for tasks_list in users_tasks.values():
                if tasks_list:
                    users_with_tasks_ids.add(tasks_list[0]["telegram_id"])

        sent = 0
        failed = 0

        PRIORITY_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🟢"}

        # Send to users WITH tasks
        for user_id, tasks in users_tasks.items():
            if not tasks:
                continue
            telegram_id = tasks[0]["telegram_id"]
            first_name = tasks[0].get("first_name") or ""
            lang = tasks[0].get("language", "ru")
            total = len(tasks)

            task_lines = []
            for t in tasks[:3]:
                emoji = PRIORITY_EMOJI.get(t["priority"], "🟢")
                task_lines.append(f"{emoji} {t['title'][:60]}")

            text = get_text("morning_with_tasks", lang).format(
                name=first_name, count=total
            )
            text += "\n" + "\n".join(task_lines)
            if total > 3:
                text += "\n" + get_text("morning_and_more", lang).format(
                    count=total - 3
                )

            try:
                await self.bot.send_message(
                    telegram_id,
                    text,
                    reply_markup=get_morning_reminder_keyboard(),
                )
                sent += 1
            except (TelegramForbiddenError, TelegramBadRequest):
                failed += 1
            except Exception as e:
                logger.error(f"Failed to send morning reminder to {telegram_id}: {e}")
                failed += 1
            await asyncio.sleep(0.05)

        # Send to users WITHOUT tasks
        for user in all_users:
            if user["telegram_id"] in users_with_tasks_ids:
                continue
            from database import get_user_language

            lang = await get_user_language(user["telegram_id"])
            first_name = user.get("first_name") or ""
            text = get_text("morning_no_tasks", lang).format(name=first_name)

            try:
                await self.bot.send_message(
                    user["telegram_id"],
                    text,
                    reply_markup=get_morning_reminder_keyboard(),
                )
                sent += 1
            except (TelegramForbiddenError, TelegramBadRequest):
                failed += 1
            except Exception as e:
                logger.error(
                    f"Failed to send morning reminder to {user['telegram_id']}: {e}"
                )
                failed += 1
            await asyncio.sleep(0.05)

        logger.info(f"Morning reminders: {sent} sent, {failed} failed")

    async def send_streak_reminder(self):
        """Send reminder to users who might lose their streak."""
        users = await get_users_with_notifications_enabled()
        sent = 0
        failed = 0

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
                # Use Moscow timezone (UTC+3)
                moscow_tz = timezone(timedelta(hours=3))
                today = datetime.now(moscow_tz).date()

                if last_date < today:
                    try:
                        await self.bot.send_message(
                            user["telegram_id"],
                            f"🔥 Не потеряй свою серию в {streak} дней! "
                            "Выполни хотя бы один маленький шаг, чтобы сохранить её.",
                            reply_markup=get_webapp_button(),
                        )
                        sent += 1
                    except (TelegramForbiddenError, TelegramBadRequest):
                        failed += 1
                    except Exception as e:
                        logger.error(
                            f"Failed to send streak reminder to {user['telegram_id']}: {e}"
                        )
                        failed += 1

                    await asyncio.sleep(0.05)

        logger.info(f"Streak reminders: {sent} sent, {failed} failed")

    async def send_weekly_summary(self):
        """Send weekly summary to users."""
        users = await get_users_with_notifications_enabled()
        sent = 0
        failed = 0

        for user in users:
            try:
                stats = await get_user_stats(user["telegram_id"], weekly=True)
                if not stats:
                    continue

                u = stats["user"]
                text = (
                    f"📅 Твой недельный отчёт MoodSprint\n"
                    f"{'─' * 25}\n\n"
                    f"🎯 Уровень: {u.get('level', 1)} | ✨ XP: {u.get('xp', 0)}\n"
                    f"🔥 Текущая серия: {u.get('streak_days', 0)} дн.\n\n"
                    f"✅ Задач выполнено: {stats['completed_tasks']}\n"
                    f"⏱️ Время фокуса: {stats['total_focus_minutes']} мин\n\n"
                    "Так держать! 💪"
                )

                await self.bot.send_message(
                    user["telegram_id"], text, reply_markup=get_webapp_button()
                )
                sent += 1
            except (TelegramForbiddenError, TelegramBadRequest):
                failed += 1
            except Exception as e:
                logger.error(
                    f"Failed to send weekly summary to {user['telegram_id']}: {e}"
                )
                failed += 1

            await asyncio.sleep(0.05)

        logger.info(f"Weekly summaries: {sent} sent, {failed} failed")

    async def send_achievement_notification(
        self, telegram_id: int, achievement_title: str, xp_reward: int
    ):
        """Send achievement unlock notification."""
        try:
            await self.bot.send_message(
                telegram_id,
                f"🏆 Достижение разблокировано!\n\n"
                f"{achievement_title}\n"
                f"+{xp_reward} XP\n\n"
                "Открой MoodSprint, чтобы увидеть свой прогресс!",
                reply_markup=get_webapp_button(),
            )
        except (TelegramForbiddenError, TelegramBadRequest):
            # User blocked bot or chat not found - ignore
            pass
        except Exception as e:
            logger.error(
                f"Failed to send achievement notification to {telegram_id}: {e}"
            )

    async def send_level_up_notification(self, telegram_id: int, new_level: int):
        """Send level up notification."""
        try:
            await self.bot.send_message(
                telegram_id,
                f"🎉 Новый уровень!\n\n"
                f"Ты достиг уровня {new_level}!\n\n"
                "Продолжай в том же духе! 🚀",
                reply_markup=get_webapp_button(),
            )
        except (TelegramForbiddenError, TelegramBadRequest):
            pass
        except Exception as e:
            logger.error(f"Failed to send level up notification to {telegram_id}: {e}")

    async def send_focus_complete_notification(
        self, telegram_id: int, duration_minutes: int, xp_earned: int
    ):
        """Send focus session complete notification."""
        try:
            await self.bot.send_message(
                telegram_id,
                f"✅ Фокус-сессия завершена!\n\n"
                f"⏱️ Длительность: {duration_minutes} мин\n"
                f"✨ Заработано XP: +{xp_earned}\n\n"
                "Отличный фокус! Сделай небольшой перерыв. ☕",
                reply_markup=get_webapp_button(),
            )
        except (TelegramForbiddenError, TelegramBadRequest):
            pass
        except Exception as e:
            logger.error(f"Failed to send focus notification to {telegram_id}: {e}")

    async def postpone_overdue_tasks(self):
        """
        Postpone all overdue tasks to today (without sending notifications).

        Notifications will be sent later based on user's preferred time.
        This runs as a cron job at midnight.
        """
        logger.info("Starting overdue tasks postponement...")

        # Get all overdue tasks grouped by user
        users_tasks = await get_overdue_tasks_by_user()

        if not users_tasks:
            logger.info("No overdue tasks found.")
            return

        total_postponed = 0

        for user_id, tasks in users_tasks.items():
            priority_changes = []

            for task in tasks:
                task_id = task["id"]
                old_priority = task["priority"]

                # Postpone task
                new_postponed_count = await postpone_task(task_id)
                total_postponed += 1

                # Check if priority should be increased (after 2+ postponements)
                if new_postponed_count >= 2 and old_priority != "high":
                    # Simple rule-based priority increase
                    if new_postponed_count >= 3:
                        new_priority = "high" if old_priority == "medium" else "medium"
                        await update_task_priority(task_id, new_priority)

                        priority_changes.append(
                            {
                                "task_id": task_id,
                                "task_title": task["title"][:50],
                                "old_priority": old_priority,
                                "new_priority": new_priority,
                                "postponed_count": new_postponed_count,
                            }
                        )

            # Create postpone log (notification will be sent later)
            await create_postpone_log(
                user_id=user_id,
                tasks_postponed=len(tasks),
                priority_changes=priority_changes if priority_changes else None,
            )

        logger.info(
            f"Postponement complete: {total_postponed} tasks for {len(users_tasks)} users."
        )

    async def send_daily_task_suggestion(self, time_slot: str):
        """
        Send daily task suggestion to users based on their preferred time.

        Sends one task suggestion per day to help users stay productive.
        """
        logger.info(f"Sending daily task suggestions for time slot: {time_slot}")

        import random

        greetings = {
            "morning": [
                "☀️ Доброе утро! ",
                "🌅 Отличное утро для продуктивности! ",
                "✨ Начнём день с пользой? ",
            ],
            "afternoon": [
                "👋 Привет! ",
                "🌤️ Есть минутка? ",
                "💪 Время для небольшого рывка! ",
            ],
            "evening": [
                "🌆 Добрый вечер! ",
                "🌙 Можно успеть ещё одно дело! ",
                "✨ Вечерняя продуктивность? ",
            ],
            "night": [
                "🦉 Привет, полуночник! ",
                "🌙 Ночное вдохновение? ",
                "⭐ Тихий вечер для важных дел! ",
            ],
        }

        # Get users who should receive suggestion now and haven't received one today
        users = await get_users_for_daily_suggestion(time_slot)

        if not users:
            logger.info(f"No users for daily suggestion at {time_slot}")
            return

        suggestions_sent = 0

        for user in users:
            telegram_id = user["telegram_id"]
            first_name = user.get("first_name") or "друг"

            try:
                # Get task suggestions (30 min default)
                suggestions = await get_task_suggestions(telegram_id, 30)

                if not suggestions:
                    # Try with more time
                    suggestions = await get_task_suggestions(telegram_id, 60)

                if not suggestions:
                    continue  # Skip if no tasks

                # Pick the best suggestion
                suggestion = suggestions[0]
                greeting = random.choice(greetings.get(time_slot, greetings["morning"]))

                priority_emoji = (
                    "🔴"
                    if suggestion["priority"] == "high"
                    else "🟡" if suggestion["priority"] == "medium" else "🟢"
                )

                text = f"{greeting}{first_name}!\n\n"
                text += "📋 Предлагаю задачу на сегодня:\n\n"
                text += f"{priority_emoji} <b>{suggestion['task_title']}</b>\n"
                text += f"⏱️ ~{suggestion['estimated_minutes']} мин"

                if suggestion["subtasks_count"]:
                    text += f" • {suggestion['subtasks_count']} шагов"

                text += "\n\nНачнём? 👇"

                await self.bot.send_message(
                    telegram_id,
                    text,
                    reply_markup=get_task_suggestion_keyboard(
                        suggestion["task_id"], suggestion["estimated_minutes"]
                    ),
                    parse_mode="HTML",
                )
                suggestions_sent += 1

            except (TelegramForbiddenError, TelegramBadRequest):
                # User blocked bot - skip silently
                pass
            except Exception as e:
                logger.error(f"Failed to send daily suggestion to {telegram_id}: {e}")

            # Always mark as sent to prevent retry spam
            await mark_daily_suggestion_sent(user["user_id"])
            await asyncio.sleep(0.05)  # Rate limiting

        logger.info(f"Daily suggestions sent: {suggestions_sent} for {time_slot}")

    async def send_postpone_notifications(self, time_slot: str):
        """
        Send friendly postpone notifications to users who prefer this time slot.

        time_slot: 'morning', 'afternoon', 'evening', or 'night'
        """
        logger.info(f"Sending postpone notifications for time slot: {time_slot}")

        # Friendly messages based on time of day
        greetings = {
            "morning": [
                "☀️ Доброе утро! ",
                "🌅 Новый день — новые возможности! ",
                "✨ Привет! Начинаем день? ",
            ],
            "afternoon": [
                "👋 Привет! ",
                "🌤️ Добрый день! ",
                "💪 Отличное время для продуктивности! ",
            ],
            "evening": [
                "🌆 Добрый вечер! ",
                "🌙 Привет! Ещё есть время сделать что-то важное. ",
                "✨ Вечер — отличное время закрыть дела! ",
            ],
            "night": [
                "🌙 Привет, полуночник! ",
                "🦉 Ночная продуктивность? Уважаю! ",
                "⭐ Тихий вечер для важных дел. ",
            ],
        }

        import random

        # Get unnotified logs for this time slot
        logs = await get_unnotified_postpone_logs_for_time(time_slot)

        if not logs:
            logger.info(f"No unnotified postpone logs for {time_slot}.")
            return

        users_notified = 0

        for log in logs:
            telegram_id = log["telegram_id"]
            first_name = log.get("first_name") or "друг"
            tasks_count = log["tasks_postponed"]
            priority_changes = log.get("priority_changes") or []

            try:
                # Build friendly message
                greeting = random.choice(greetings.get(time_slot, greetings["morning"]))

                if tasks_count == 1:
                    count_text = "У тебя есть 1 задача"
                elif tasks_count < 5:
                    count_text = f"У тебя есть {tasks_count} задачи"
                else:
                    count_text = f"У тебя есть {tasks_count} задач"

                message = f"{greeting}{first_name}!\n\n"
                message += f"📋 {count_text} с прошлых дней — я перенёс их на сегодня."

                if priority_changes:
                    message += "\n\n⬆️ Кстати, повысил приоритет для:"
                    for change in priority_changes[:3]:
                        message += f"\n• {change['task_title']}"
                    message += (
                        "\n\nЭти задачи откладывались несколько раз — "
                        "возможно, стоит начать с них?"
                    )

                message += "\n\n💪 Давай сделаем этот день продуктивным!"

                await self.bot.send_message(
                    telegram_id,
                    message,
                    reply_markup=get_webapp_button(),
                )
                users_notified += 1

            except (TelegramForbiddenError, TelegramBadRequest):
                # User blocked bot - skip silently
                pass
            except Exception as e:
                logger.error(
                    f"Failed to send postpone notification to {telegram_id}: {e}"
                )

            # Always mark as notified to prevent retry spam
            await mark_postpone_log_notified(log["log_id"])
            await asyncio.sleep(0.05)  # Rate limiting

        logger.info(
            f"Postpone notifications sent: {users_notified} users for {time_slot}."
        )

    async def send_scheduled_task_reminders(self):
        """
        Send reminders for scheduled tasks.

        Runs every minute to check for tasks that need reminders.
        """
        logger.info("Checking scheduled task reminders...")

        tasks = await get_scheduled_tasks_for_reminder()

        if not tasks:
            logger.info("No scheduled tasks need reminders.")
            return

        reminders_sent = 0
        reminders_failed = 0

        for task in tasks:
            telegram_id = task["telegram_id"]
            first_name = task.get("first_name") or "друг"
            task_id = task["task_id"]
            title = task["title"]
            priority = task["priority"]

            priority_emoji = (
                "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"
            )

            try:
                text = f"⏰ Привет, {first_name}!\n\n"
                text += "Напоминаю о задаче:\n\n"
                text += f"{priority_emoji} <b>{title}</b>\n\n"
                text += "Готов начать?"

                await self.bot.send_message(
                    telegram_id,
                    text,
                    reply_markup=get_task_reminder_keyboard(task_id),
                    parse_mode="HTML",
                )

                reminders_sent += 1

            except TelegramForbiddenError:
                # User blocked the bot or chat doesn't exist
                logger.warning(
                    f"User {telegram_id} blocked the bot or chat not found, "
                    "marking reminder as sent"
                )
                reminders_failed += 1

            except TelegramBadRequest as e:
                # Chat not found or other bad request
                logger.warning(
                    f"Bad request for user {telegram_id}: {e}, "
                    "marking reminder as sent"
                )
                reminders_failed += 1

            except Exception as e:
                # Other errors - still mark as sent to prevent spam
                logger.error(f"Failed to send task reminder to {telegram_id}: {e}")
                reminders_failed += 1

            # Always mark reminder as sent to prevent retry spam
            await mark_reminder_sent(task_id)
            await asyncio.sleep(0.05)  # Rate limiting

        logger.info(f"Task reminders: {reminders_sent} sent, {reminders_failed} failed")

    async def rotate_monsters(self):
        """
        Trigger monster rotation via backend API.
        Called every day at midnight, but only generates on period start days.
        """
        import aiohttp
        from config import config

        if not config.BOT_SECRET:
            logger.warning("BOT_SECRET not configured, skipping monster rotation")
            return

        url = f"{config.API_URL}/arena/monsters/rotate"
        headers = {"X-Bot-Secret": config.BOT_SECRET}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, timeout=60) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("success"):
                            generated = data.get("generated", {})
                            total = sum(generated.values()) if generated else 0
                            if total > 0:
                                logger.info(
                                    f"Monster rotation: generated {total} monsters"
                                )
                            else:
                                logger.info(
                                    f"Monster rotation: {data.get('message', 'no action needed')}"
                                )
                        else:
                            logger.error(f"Monster rotation failed: {data}")
                    else:
                        text = await response.text()
                        logger.error(
                            f"Monster rotation API error: {response.status} - {text}"
                        )
        except Exception as e:
            logger.error(f"Monster rotation error: {e}")

    async def send_new_referral_notifications(self):
        """
        Send notifications to users who have new friends via referral.
        Runs every hour and notifies users with pending referral rewards.
        """
        from database import get_users_with_pending_referrals

        logger.info("Checking for new referral notifications...")

        users = await get_users_with_pending_referrals()

        if not users:
            logger.info("No users with pending referral notifications")
            return

        sent = 0
        failed = 0

        for user in users:
            telegram_id = user["telegram_id"]
            pending_count = user["pending_count"]
            first_name = user.get("first_name") or "друг"

            try:
                if pending_count == 1:
                    text = (
                        f"🎉 {first_name}, у тебя новый друг в MoodSprint!\n\n"
                        "Зайди в раздел Друзья, чтобы увидеть награду 🎁"
                    )
                else:
                    text = (
                        f"🎉 {first_name}, у тебя +{pending_count} новых друзей "
                        f"в MoodSprint!\n\n"
                        "Зайди в раздел Друзья, чтобы увидеть награды 🎁"
                    )

                await self.bot.send_message(
                    telegram_id,
                    text,
                    reply_markup=get_webapp_button(),
                )
                sent += 1

            except (TelegramForbiddenError, TelegramBadRequest):
                failed += 1
            except Exception as e:
                logger.error(
                    f"Failed to send referral notification to {telegram_id}: {e}"
                )
                failed += 1

            await asyncio.sleep(0.05)

        logger.info(f"Referral notifications: {sent} sent, {failed} failed")

    async def check_resource_usage(self):
        """
        Check server resource usage and alert admins if thresholds exceeded.

        Thresholds:
        - CPU: > 80% for 3+ checks
        - Memory: > 85%
        - Disk: > 90%

        Uses Redis for cooldown (30 minutes between alerts).
        """
        import redis.asyncio as redis_async

        # Thresholds
        CPU_THRESHOLD = 80
        MEMORY_THRESHOLD = 85
        DISK_THRESHOLD = 90
        ALERT_COOLDOWN = 1800  # 30 minutes

        if not config.ADMIN_IDS:
            return

        try:
            # Get resource usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            memory_percent = memory.percent
            disk_percent = disk.percent

            alerts = []

            # Check thresholds
            if cpu_percent > CPU_THRESHOLD:
                alerts.append(f"🔥 CPU: {cpu_percent:.1f}% (порог: {CPU_THRESHOLD}%)")

            if memory_percent > MEMORY_THRESHOLD:
                used_gb = memory.used / (1024**3)
                total_gb = memory.total / (1024**3)
                alerts.append(
                    f"💾 RAM: {memory_percent:.1f}% ({used_gb:.1f}/{total_gb:.1f} GB) "
                    f"(порог: {MEMORY_THRESHOLD}%)"
                )

            if disk_percent > DISK_THRESHOLD:
                used_gb = disk.used / (1024**3)
                total_gb = disk.total / (1024**3)
                alerts.append(
                    f"💿 Disk: {disk_percent:.1f}% ({used_gb:.1f}/{total_gb:.1f} GB) "
                    f"(порог: {DISK_THRESHOLD}%)"
                )

            if not alerts:
                logger.debug(
                    f"Resource check: CPU={cpu_percent:.1f}%, "
                    f"RAM={memory_percent:.1f}%, Disk={disk_percent:.1f}%"
                )
                return

            # Check cooldown in Redis
            redis_client = redis_async.from_url(config.REDIS_URL)
            cooldown_key = "bot:resource_alert:cooldown"

            try:
                if await redis_client.get(cooldown_key):
                    logger.info("Resource alert skipped (cooldown active)")
                    await redis_client.aclose()
                    return

                # Set cooldown
                await redis_client.setex(cooldown_key, ALERT_COOLDOWN, "1")
                await redis_client.aclose()
            except Exception as e:
                logger.warning(f"Redis error in resource check: {e}")

            # Build alert message
            message = "🚨 <b>Внимание: высокое использование ресурсов!</b>\n\n"
            message += "\n".join(alerts)
            message += f"\n\n🕐 {datetime.now().strftime('%H:%M:%S')}"

            # Send to all admins
            for admin_id in config.ADMIN_IDS:
                try:
                    await self.bot.send_message(admin_id, message, parse_mode="HTML")
                except Exception as e:
                    logger.error(
                        f"Failed to send resource alert to admin {admin_id}: {e}"
                    )

            logger.warning(f"Resource alert sent: {alerts}")

        except Exception as e:
            logger.error(f"Resource check error: {e}")

    async def send_friend_activity_notifications(self):
        """Send notifications about friend activities (level ups, streak milestones)."""
        from database import (
            get_recent_friend_activities,
            mark_friend_activities_notified,
        )
        from translations import get_text

        logger.info("Checking friend activity notifications...")

        activities = await get_recent_friend_activities()

        if not activities:
            logger.info("No friend activities to notify about.")
            return

        sent = 0
        failed = 0
        notified_ids = []

        # Group by recipient
        recipients: dict[int, list[dict]] = {}
        for act in activities:
            tid = act["recipient_telegram_id"]
            if tid not in recipients:
                recipients[tid] = []
            recipients[tid].append(act)

        for telegram_id, acts in recipients.items():
            lang = acts[0].get("recipient_lang", "ru")
            lines = []
            for act in acts:
                name = act.get("actor_name") or ""
                data = act.get("activity_data") or {}
                if act["activity_type"] == "level_up":
                    lines.append(
                        get_text("friend_level_up", lang).format(
                            name=name, level=data.get("level", "?")
                        )
                    )
                elif act["activity_type"] == "streak_milestone":
                    lines.append(
                        get_text("friend_streak_milestone", lang).format(
                            name=name, days=data.get("streak_days", "?")
                        )
                    )
                notified_ids.append(act["activity_id"])

            if not lines:
                continue

            message = "\n".join(lines)
            try:
                await self.bot.send_message(
                    telegram_id,
                    message,
                    reply_markup=get_webapp_button(),
                )
                sent += 1
            except (TelegramForbiddenError, TelegramBadRequest):
                failed += 1
            except Exception as e:
                logger.error(f"Failed to send friend activity to {telegram_id}: {e}")
                failed += 1
            await asyncio.sleep(0.05)

        # Mark all as notified
        await mark_friend_activities_notified(notified_ids)

        logger.info(f"Friend activity notifications: {sent} sent, {failed} failed")

    async def send_comeback_messages(self):
        """Send comeback messages to users inactive for 2+ days."""
        from database import get_inactive_users, set_comeback_card_pending
        from translations import get_text

        logger.info("Checking for inactive users for comeback messages...")

        users = await get_inactive_users(days=2)

        if not users:
            logger.info("No inactive users for comeback messages.")
            return

        sent = 0
        failed = 0

        for user in users:
            telegram_id = user["telegram_id"]
            first_name = user.get("first_name") or ""
            lang = user.get("language", "ru")

            message = get_text("comeback_message", lang).format(name=first_name)

            try:
                await self.bot.send_message(
                    telegram_id,
                    message,
                    reply_markup=get_webapp_button(),
                )
                await set_comeback_card_pending(user["id"])
                sent += 1
            except (TelegramForbiddenError, TelegramBadRequest):
                # User blocked bot — still mark to avoid retrying
                await set_comeback_card_pending(user["id"])
                failed += 1
            except Exception as e:
                logger.error(f"Failed to send comeback message to {telegram_id}: {e}")
                failed += 1
            await asyncio.sleep(0.05)

        logger.info(f"Comeback messages: {sent} sent, {failed} failed")
