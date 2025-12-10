"""User handlers."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart

from keyboards import (
    get_main_keyboard,
    get_webapp_button,
    get_settings_keyboard,
    get_start_inline_button,
    get_freetime_keyboard,
    get_task_suggestion_keyboard,
)
from database import (
    get_user_by_telegram_id,
    get_user_stats,
    update_user_notifications,
    get_task_suggestions,
    get_subtask_suggestions,
    snooze_task_reminder,
    reschedule_task_to_tomorrow,
    delete_task,
)

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command."""
    user = await get_user_by_telegram_id(message.from_user.id)

    if user:
        text = (
            f"С возвращением, {message.from_user.first_name}!\n\n"
            f"Уровень {user.get('level', 1)} | {user.get('xp', 0)} XP\n"
            f"Серия: {user.get('streak_days', 0)} дн.\n\n"
            "Нажми кнопку ниже, чтобы открыть MoodSprint!"
        )
    else:
        text = (
            f"Привет, {message.from_user.first_name}!\n\n"
            "Добро пожаловать в MoodSprint — твой умный менеджер задач.\n\n"
            "Я помогу тебе:\n"
            "• Разбивать задачи с учётом твоей энергии\n"
            "• Сохранять фокус с помощью таймер-сессий\n"
            "• Строить здоровые привычки продуктивности\n\n"
            "Нажми кнопку ниже, чтобы начать!"
        )

    # Send main message with reply keyboard
    await message.answer(text, reply_markup=get_main_keyboard())
    # Also send inline button to open app directly
    await message.answer(
        "👇 Нажми, чтобы открыть приложение:", reply_markup=get_start_inline_button()
    )


@router.message(Command("app"))
async def cmd_app(message: Message):
    """Open the webapp."""
    await message.answer(
        "Нажми, чтобы открыть MoodSprint:", reply_markup=get_webapp_button()
    )


@router.message(F.text.in_(["Open MoodSprint", "Открыть MoodSprint"]))
async def open_webapp(message: Message):
    """Handle webapp button press."""
    await message.answer("Открываю MoodSprint...", reply_markup=get_webapp_button())


@router.message(F.text.in_(["My Stats", "Статистика"]))
async def show_stats(message: Message):
    """Show user statistics."""
    stats = await get_user_stats(message.from_user.id)

    if not stats:
        await message.answer(
            "Ты ещё не начал использовать MoodSprint. "
            "Нажми 'Открыть MoodSprint', чтобы начать!"
        )
        return

    user = stats["user"]
    text = (
        f"📊 Твоя статистика MoodSprint\n"
        f"{'─' * 20}\n\n"
        f"🎯 Уровень: {user.get('level', 1)}\n"
        f"✨ XP: {user.get('xp', 0)}\n"
        f"🔥 Текущая серия: {user.get('streak_days', 0)} дн.\n"
        f"🏆 Лучшая серия: {user.get('longest_streak', 0)} дн.\n\n"
        f"✅ Задач выполнено: {stats['completed_tasks']}/{stats['total_tasks']}\n"
        f"⏱️ Фокус-сессий: {stats['total_sessions']}\n"
        f"⏳ Всего фокус-времени: {stats['total_focus_minutes']} мин\n"
    )

    await message.answer(text)


@router.message(F.text.in_(["Settings", "Настройки"]))
async def show_settings(message: Message):
    """Show settings."""
    user = await get_user_by_telegram_id(message.from_user.id)
    notifications_enabled = user.get("notifications_enabled", True) if user else True

    await message.answer(
        "⚙️ Настройки:", reply_markup=get_settings_keyboard(notifications_enabled)
    )


@router.callback_query(F.data.startswith("notifications:"))
async def toggle_notifications(callback: CallbackQuery):
    """Toggle notifications."""
    action = callback.data.split(":")[1]
    enabled = action == "on"

    await update_user_notifications(callback.from_user.id, enabled)

    status = "включены" if enabled else "выключены"
    await callback.answer(f"Уведомления {status}!")

    await callback.message.edit_reply_markup(
        reply_markup=get_settings_keyboard(enabled)
    )


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Back to main menu."""
    await callback.message.delete()
    await callback.answer()


# Store last selected time for refresh
_user_last_time: dict[int, int] = {}


@router.message(Command("freetime"))
async def cmd_freetime(message: Message):
    """Handle /freetime command - suggest tasks for free time."""
    await message.answer(
        "⏰ Сколько у тебя свободного времени?\n\n"
        "Выбери, и я подберу подходящие задачи:",
        reply_markup=get_freetime_keyboard(),
    )


@router.message(F.text.in_(["Есть время", "Свободное время", "Free time"]))
async def freetime_button(message: Message):
    """Handle free time button press."""
    await cmd_freetime(message)


@router.callback_query(F.data.startswith("freetime:"))
async def handle_freetime_callback(callback: CallbackQuery):
    """Handle free time selection."""
    action = callback.data.split(":")[1]

    if action == "refresh":
        # Use last selected time
        minutes = _user_last_time.get(callback.from_user.id, 30)
    else:
        minutes = int(action)
        _user_last_time[callback.from_user.id] = minutes

    await callback.answer("Подбираю задачи...")

    # Get suggestions
    suggestions = await get_task_suggestions(callback.from_user.id, minutes)

    if not suggestions:
        # Try subtasks
        subtask_suggestions = await get_subtask_suggestions(
            callback.from_user.id, minutes
        )
        if subtask_suggestions:
            # Format subtask suggestions
            text = f"⏰ У тебя {minutes} минут. Вот подходящие шаги:\n\n"
            for i, s in enumerate(subtask_suggestions, 1):
                priority_emoji = (
                    "🔴"
                    if s["priority"] == "high"
                    else "🟡" if s["priority"] == "medium" else "🟢"
                )
                text += f"{i}. {priority_emoji} {s['subtask_title']}\n"
                text += f"   📋 из задачи: {s['task_title'][:30]}...\n"
                text += f"   ⏱️ ~{s['estimated_minutes']} мин\n\n"

            text += "Открой приложение, чтобы начать! 👇"
            await callback.message.edit_text(text, reply_markup=get_webapp_button())
        else:
            await callback.message.edit_text(
                f"🤔 Не нашёл задач, которые вписались бы в {minutes} минут.\n\n"
                "Попробуй выбрать больше времени или создай новую задачу!",
                reply_markup=get_freetime_keyboard(),
            )
        return

    # Format suggestions
    if len(suggestions) == 1:
        # Single best suggestion - show prominently
        s = suggestions[0]
        priority_emoji = (
            "🔴"
            if s["priority"] == "high"
            else "🟡" if s["priority"] == "medium" else "🟢"
        )
        fit_text = (
            "идеально подходит" if s["fit_quality"] == "perfect" else "хорошо впишется"
        )

        text = f"⚡ Предлагаю задачу, которая {fit_text}:\n\n"
        text += f"{priority_emoji} <b>{s['task_title']}</b>\n"
        text += f"⏱️ ~{s['estimated_minutes']} мин"
        if s["subtasks_count"]:
            text += f" • {s['subtasks_count']} шагов"
        text += "\n\nНачнём?"

        await callback.message.edit_text(
            text,
            reply_markup=get_task_suggestion_keyboard(
                s["task_id"], s["estimated_minutes"]
            ),
            parse_mode="HTML",
        )
    else:
        # Multiple suggestions
        text = f"⏰ У тебя {minutes} минут. Вот что подойдёт:\n\n"

        for i, s in enumerate(suggestions, 1):
            priority_emoji = (
                "🔴"
                if s["priority"] == "high"
                else "🟡" if s["priority"] == "medium" else "🟢"
            )
            fit_badge = "✨" if s["fit_quality"] == "perfect" else ""

            text += f"{i}. {priority_emoji} {s['task_title'][:40]}"
            if len(s["task_title"]) > 40:
                text += "..."
            text += f"\n   ⏱️ ~{s['estimated_minutes']} мин {fit_badge}"
            if s["subtasks_count"]:
                text += f" • {s['subtasks_count']} шагов"
            text += "\n\n"

        text += "Выбери задачу в приложении! 👇"

        await callback.message.edit_text(text, reply_markup=get_webapp_button())


@router.callback_query(F.data.startswith("reminder:"))
async def handle_reminder_callback(callback: CallbackQuery):
    """Handle task reminder actions."""
    parts = callback.data.split(":")
    action = parts[1]

    if action == "snooze":
        task_id = int(parts[2])
        minutes = int(parts[3])
        await snooze_task_reminder(task_id, minutes)
        await callback.answer(f"Напомню через {minutes} мин")
        await callback.message.edit_text(
            f"⏰ Хорошо! Напомню через {minutes} минут.",
        )

    elif action == "tomorrow":
        task_id = int(parts[2])
        await reschedule_task_to_tomorrow(task_id)
        await callback.answer("Перенесено на завтра")
        await callback.message.edit_text(
            "📅 Задача перенесена на завтра в 9:00.",
        )

    elif action == "delete":
        task_id = int(parts[2])
        await delete_task(task_id)
        await callback.answer("Задача удалена")
        await callback.message.edit_text(
            "❌ Задача удалена.",
        )
