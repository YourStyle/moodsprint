"""User handlers."""

from datetime import date, datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from database import (
    create_task_from_voice,
    delete_task,
    get_subtask_suggestions,
    get_task_suggestions,
    get_user_by_telegram_id,
    get_user_language,
    get_user_stats,
    reschedule_task_to_days,
    reschedule_task_to_tomorrow,
    snooze_task_reminder,
    update_task_scheduled_at,
    update_user_notifications,
)
from keyboards import (
    get_cancel_keyboard,
    get_freetime_keyboard,
    get_main_keyboard,
    get_reminder_time_keyboard,
    get_settings_keyboard,
    get_start_inline_button,
    get_task_suggestion_keyboard,
    get_text_task_date_keyboard,
    get_voice_date_keyboard,
    get_webapp_button,
)
from translations import get_text

router = Router()


class PostponeDaysState(StatesGroup):
    """State for postponing task by N days."""

    waiting_for_days = State()


class VoiceTaskState(StatesGroup):
    """State for creating task from voice message."""

    waiting_for_date = State()
    waiting_for_custom_date = State()


class TextTaskState(StatesGroup):
    """State for creating task from text message."""

    waiting_for_text = State()
    waiting_for_date = State()
    waiting_for_custom_date = State()


class ReminderTimeState(StatesGroup):
    """State for entering custom reminder time."""

    waiting_for_time = State()


@router.message(CommandStart(deep_link=True))
async def cmd_start_with_param(message: Message):
    """Handle /start command with deep link parameter (e.g., invite links)."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
    from config import config

    # Extract the deep link parameter
    args = message.text.split(maxsplit=1)
    start_param = args[1] if len(args) > 1 else None

    user = await get_user_by_telegram_id(message.from_user.id)
    lang = await get_user_language(message.from_user.id)

    # Build webapp URL with start param for referral tracking
    webapp_url = config.WEBAPP_URL
    if start_param:
        # Pass start param to webapp via URL fragment
        webapp_url = f"{config.WEBAPP_URL}?startapp={start_param}"

    if user:
        text = get_text("welcome_back", lang) + f" {message.from_user.first_name}!\n\n"
        if lang == "ru":
            text += f"Уровень {user.get('level', 1)} | {user.get('xp', 0)} XP\n"
            text += f"Серия: {user.get('streak_days', 0)} дн.\n\n"
            text += "Нажми кнопку ниже, чтобы открыть MoodSprint!"
        else:
            text += f"Level {user.get('level', 1)} | {user.get('xp', 0)} XP\n"
            text += f"Streak: {user.get('streak_days', 0)} days\n\n"
            text += "Tap the button below to open MoodSprint!"
    else:
        if start_param and start_param.startswith("invite_"):
            if lang == "ru":
                text = (
                    f"Привет, {message.from_user.first_name}!\n\n"
                    "Тебя пригласил друг в MoodSprint! 🎉\n\n"
                    "MoodSprint — твой умный менеджер задач:\n"
                    "• Разбивает задачи с учётом твоей энергии\n"
                    "• Помогает сохранять фокус\n"
                    "• Строит здоровые привычки продуктивности\n\n"
                    "Нажми кнопку ниже, чтобы получить стартовый набор карт!"
                )
            else:
                text = (
                    f"Hi, {message.from_user.first_name}!\n\n"
                    "A friend invited you to MoodSprint! 🎉\n\n"
                    "MoodSprint is your smart task manager:\n"
                    "• Breaks down tasks based on your energy\n"
                    "• Helps maintain focus\n"
                    "• Builds healthy productivity habits\n\n"
                    "Tap the button below to get your starter card pack!"
                )
        else:
            text = get_text("welcome", lang) + f" {message.from_user.first_name}!\n\n"
            if lang == "ru":
                text += (
                    "Добро пожаловать в MoodSprint — твой умный менеджер задач.\n\n"
                    "Я помогу тебе:\n"
                    "• Разбивать задачи с учётом твоей энергии\n"
                    "• Сохранять фокус с помощью таймер-сессий\n"
                    "• Строить здоровые привычки продуктивности\n\n"
                    "Нажми кнопку ниже, чтобы начать!"
                )
            else:
                text += (
                    "Welcome to MoodSprint — your smart task manager.\n\n"
                    "I'll help you:\n"
                    "• Break down tasks based on your energy\n"
                    "• Stay focused with timer sessions\n"
                    "• Build healthy productivity habits\n\n"
                    "Tap the button below to start!"
                )

    # Send main message with reply keyboard
    await message.answer(text, reply_markup=get_main_keyboard(lang))

    # Create inline button with webapp URL (including start param if present)
    btn_text = "🚀 Открыть MoodSprint" if lang == "ru" else "🚀 Open MoodSprint"
    inline_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=btn_text,
                    web_app=WebAppInfo(url=webapp_url),
                )
            ]
        ]
    )
    tap_text = (
        "👇 Нажми, чтобы открыть приложение:"
        if lang == "ru"
        else "👇 Tap to open the app:"
    )
    await message.answer(tap_text, reply_markup=inline_kb)


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command without parameters."""
    user = await get_user_by_telegram_id(message.from_user.id)
    lang = await get_user_language(message.from_user.id)

    if user:
        text = get_text("welcome_back", lang) + f" {message.from_user.first_name}!\n\n"
        if lang == "ru":
            text += f"Уровень {user.get('level', 1)} | {user.get('xp', 0)} XP\n"
            text += f"Серия: {user.get('streak_days', 0)} дн.\n\n"
            text += "Нажми кнопку ниже, чтобы открыть MoodSprint!"
        else:
            text += f"Level {user.get('level', 1)} | {user.get('xp', 0)} XP\n"
            text += f"Streak: {user.get('streak_days', 0)} days\n\n"
            text += "Tap the button below to open MoodSprint!"
    else:
        text = get_text("welcome", lang) + f" {message.from_user.first_name}!\n\n"
        if lang == "ru":
            text += (
                "Добро пожаловать в MoodSprint — твой умный менеджер задач.\n\n"
                "Я помогу тебе:\n"
                "• Разбивать задачи с учётом твоей энергии\n"
                "• Сохранять фокус с помощью таймер-сессий\n"
                "• Строить здоровые привычки продуктивности\n\n"
                "Нажми кнопку ниже, чтобы начать!"
            )
        else:
            text += (
                "Welcome to MoodSprint — your smart task manager.\n\n"
                "I'll help you:\n"
                "• Break down tasks based on your energy\n"
                "• Stay focused with timer sessions\n"
                "• Build healthy productivity habits\n\n"
                "Tap the button below to start!"
            )

    # Send main message with reply keyboard
    await message.answer(text, reply_markup=get_main_keyboard(lang))
    # Also send inline button to open app directly
    tap_text = (
        "👇 Нажми, чтобы открыть приложение:"
        if lang == "ru"
        else "👇 Tap to open the app:"
    )
    await message.answer(tap_text, reply_markup=get_start_inline_button(lang))


@router.message(Command("app"))
async def cmd_app(message: Message):
    """Open the webapp."""
    lang = await get_user_language(message.from_user.id)
    text = (
        "Нажми, чтобы открыть MoodSprint:"
        if lang == "ru"
        else "Tap to open MoodSprint:"
    )
    await message.answer(text, reply_markup=get_webapp_button(lang))


@router.message(
    F.text.in_(["My Stats", "Статистика", "📊 Statistics", "📊 Статистика"])
)
async def show_stats(message: Message):
    """Show user statistics."""
    lang = await get_user_language(message.from_user.id)
    stats = await get_user_stats(message.from_user.id)

    if not stats:
        text = get_text("stats_no_data", lang)
        await message.answer(text)
        return

    user = stats["user"]
    text = get_text("stats_title", lang) + "\n"
    text += f"{'─' * 20}\n\n"

    if lang == "ru":
        text += f"🎯 Уровень: {user.get('level', 1)}\n"
        text += f"✨ XP: {user.get('xp', 0)}\n"
        text += f"🔥 Текущая серия: {user.get('streak_days', 0)} дн.\n"
        text += f"🏆 Лучшая серия: {user.get('longest_streak', 0)} дн.\n\n"
        text += (
            f"✅ Задач выполнено: {stats['completed_tasks']}/{stats['total_tasks']}\n"
        )
        text += f"⏱️ Фокус-сессий: {stats['total_sessions']}\n"
        text += f"⏳ Всего фокус-времени: {stats['total_focus_minutes']} мин\n"
    else:
        text += f"🎯 Level: {user.get('level', 1)}\n"
        text += f"✨ XP: {user.get('xp', 0)}\n"
        text += f"🔥 Current streak: {user.get('streak_days', 0)} days\n"
        text += f"🏆 Best streak: {user.get('longest_streak', 0)} days\n\n"
        text += (
            f"✅ Tasks completed: {stats['completed_tasks']}/{stats['total_tasks']}\n"
        )
        text += f"⏱️ Focus sessions: {stats['total_sessions']}\n"
        text += f"⏳ Total focus time: {stats['total_focus_minutes']} min\n"

    await message.answer(text)


@router.message(F.text.in_(["Settings", "Настройки", "⚙️ Settings", "⚙️ Настройки"]))
async def show_settings(message: Message):
    """Show settings."""
    lang = await get_user_language(message.from_user.id)
    user = await get_user_by_telegram_id(message.from_user.id)
    notifications_enabled = user.get("notifications_enabled", True) if user else True

    await message.answer(
        get_text("settings_title", lang),
        reply_markup=get_settings_keyboard(notifications_enabled, lang),
    )


@router.callback_query(F.data.startswith("notifications:"))
async def toggle_notifications(callback: CallbackQuery):
    """Toggle notifications."""
    lang = await get_user_language(callback.from_user.id)
    action = callback.data.split(":")[1]
    enabled = action == "on"

    await update_user_notifications(callback.from_user.id, enabled)

    status = (
        get_text("settings_notifications_on", lang)
        if enabled
        else get_text("settings_notifications_off", lang)
    )
    await callback.answer(f"{status}!")

    await callback.message.edit_reply_markup(
        reply_markup=get_settings_keyboard(enabled, lang)
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
    lang = await get_user_language(message.from_user.id)
    await message.answer(
        get_text("freetime_ask", lang),
        reply_markup=get_freetime_keyboard(lang),
    )


@router.message(F.text.in_(["Есть время", "Свободное время", "Free time"]))
async def freetime_button(message: Message):
    """Handle free time button press."""
    await cmd_freetime(message)


@router.callback_query(F.data.startswith("freetime:"))
async def handle_freetime_callback(callback: CallbackQuery):
    """Handle free time selection."""
    lang = await get_user_language(callback.from_user.id)
    action = callback.data.split(":")[1]

    if action == "refresh":
        # Use last selected time
        minutes = _user_last_time.get(callback.from_user.id, 30)
    else:
        minutes = int(action)
        _user_last_time[callback.from_user.id] = minutes

    searching_text = "Подбираю задачи..." if lang == "ru" else "Finding tasks..."
    await callback.answer(searching_text)

    # Get suggestions
    suggestions = await get_task_suggestions(callback.from_user.id, minutes)

    min_word = "минут" if lang == "ru" else "minutes"
    from_task = "из задачи" if lang == "ru" else "from task"
    open_app = (
        "Открой приложение, чтобы начать!" if lang == "ru" else "Open the app to start!"
    )
    steps_word = "шагов" if lang == "ru" else "steps"

    if not suggestions:
        # Try subtasks
        subtask_suggestions = await get_subtask_suggestions(
            callback.from_user.id, minutes
        )
        if subtask_suggestions:
            # Format subtask suggestions
            text = get_text("freetime_suggestions", lang, minutes=minutes) + "\n\n"
            for i, s in enumerate(subtask_suggestions, 1):
                priority_emoji = (
                    "🔴"
                    if s["priority"] == "high"
                    else "🟡" if s["priority"] == "medium" else "🟢"
                )
                text += f"{i}. {priority_emoji} {s['subtask_title']}\n"
                text += f"   📋 {from_task}: {s['task_title'][:30]}...\n"
                text += f"   ⏱️ ~{s['estimated_minutes']} {min_word}\n\n"

            text += f"{open_app} 👇"
            await callback.message.edit_text(text, reply_markup=get_webapp_button(lang))
        else:
            await callback.message.edit_text(
                get_text("freetime_no_tasks", lang),
                reply_markup=get_freetime_keyboard(lang),
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
        if lang == "ru":
            fit_text = (
                "идеально подходит"
                if s["fit_quality"] == "perfect"
                else "хорошо впишется"
            )
            text = f"⚡ Предлагаю задачу, которая {fit_text}:\n\n"
            text += f"{priority_emoji} <b>{s['task_title']}</b>\n"
            text += f"⏱️ ~{s['estimated_minutes']} мин"
            if s["subtasks_count"]:
                text += f" • {s['subtasks_count']} шагов"
            text += "\n\nНачнём?"
        else:
            fit_text = "perfect fit" if s["fit_quality"] == "perfect" else "good fit"
            text = f"⚡ Here's a task that's a {fit_text}:\n\n"
            text += f"{priority_emoji} <b>{s['task_title']}</b>\n"
            text += f"⏱️ ~{s['estimated_minutes']} min"
            if s["subtasks_count"]:
                text += f" • {s['subtasks_count']} steps"
            text += "\n\nLet's start?"

        await callback.message.edit_text(
            text,
            reply_markup=get_task_suggestion_keyboard(
                s["task_id"], s["estimated_minutes"], lang
            ),
            parse_mode="HTML",
        )
    else:
        # Multiple suggestions
        text = get_text("freetime_suggestions", lang, minutes=minutes) + "\n\n"

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
            text += f"\n   ⏱️ ~{s['estimated_minutes']} {min_word} {fit_badge}"
            if s["subtasks_count"]:
                text += f" • {s['subtasks_count']} {steps_word}"
            text += "\n\n"

        text += f"{open_app} 👇"

        await callback.message.edit_text(text, reply_markup=get_webapp_button(lang))


@router.callback_query(F.data.startswith("reminder:"))
async def handle_reminder_callback(callback: CallbackQuery, state: FSMContext):
    """Handle task reminder actions."""
    lang = await get_user_language(callback.from_user.id)
    parts = callback.data.split(":")
    action = parts[1]

    if action == "snooze":
        task_id = int(parts[2])
        minutes = int(parts[3])
        await snooze_task_reminder(task_id, minutes)
        min_word = "мин" if lang == "ru" else "min"
        await callback.answer(
            f"{'Напомню через' if lang == 'ru' else 'Will remind in'} {minutes} {min_word}"
        )
        if lang == "ru":
            await callback.message.edit_text(
                f"⏰ Хорошо! Напомню через {minutes} минут."
            )
        else:
            await callback.message.edit_text(
                f"⏰ OK! Will remind in {minutes} minutes."
            )

    elif action == "tomorrow":
        task_id = int(parts[2])
        await reschedule_task_to_tomorrow(task_id)
        await callback.answer(get_text("btn_postpone_1", lang))
        if lang == "ru":
            await callback.message.edit_text("📅 Задача перенесена на завтра в 9:00.")
        else:
            await callback.message.edit_text(
                "📅 Task rescheduled to tomorrow at 9:00 AM."
            )

    elif action == "postpone_days":
        task_id = int(parts[2])
        await state.set_state(PostponeDaysState.waiting_for_days)
        await state.update_data(task_id=task_id, lang=lang)
        await callback.answer()
        if lang == "ru":
            await callback.message.edit_text(
                "📆 На сколько дней отложить задачу?\n\nНапиши число от 1 до 30:",
                reply_markup=get_cancel_keyboard(lang),
            )
        else:
            await callback.message.edit_text(
                "📆 How many days to postpone the task?\n\nEnter a number from 1 to 30:",
                reply_markup=get_cancel_keyboard(lang),
            )

    elif action == "delete":
        task_id = int(parts[2])
        await delete_task(task_id)
        deleted_text = "Задача удалена" if lang == "ru" else "Task deleted"
        await callback.answer(deleted_text)
        await callback.message.edit_text(f"❌ {deleted_text}.")


@router.callback_query(F.data == "cancel_state")
async def cancel_state(callback: CallbackQuery, state: FSMContext):
    """Cancel current state."""
    lang = await get_user_language(callback.from_user.id)
    await state.clear()
    cancelled_text = "Отменено" if lang == "ru" else "Cancelled"
    await callback.answer(cancelled_text)
    await callback.message.edit_text(f"❌ {cancelled_text}.")


@router.message(PostponeDaysState.waiting_for_days)
async def process_postpone_days(message: Message, state: FSMContext):
    """Process postpone days input."""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    text = message.text.strip()

    # Try to parse number
    try:
        days = int(text)
    except ValueError:
        error_text = (
            "⚠️ Пожалуйста, введи число от 1 до 30."
            if lang == "ru"
            else "⚠️ Please enter a number from 1 to 30."
        )
        await message.answer(error_text, reply_markup=get_cancel_keyboard(lang))
        return

    # Validate range
    if days < 1 or days > 30:
        error_text = (
            "⚠️ Число должно быть от 1 до 30."
            if lang == "ru"
            else "⚠️ Number must be from 1 to 30."
        )
        await message.answer(error_text, reply_markup=get_cancel_keyboard(lang))
        return

    # Get task_id from state
    task_id = data.get("task_id")

    if not task_id:
        await state.clear()
        error_text = (
            "⚠️ Произошла ошибка. Попробуй ещё раз."
            if lang == "ru"
            else "⚠️ An error occurred. Please try again."
        )
        await message.answer(error_text)
        return

    # Reschedule task
    await reschedule_task_to_days(task_id, days)
    await state.clear()

    # Format response
    if lang == "ru":
        if days == 1:
            days_text = "1 день"
        elif days < 5:
            days_text = f"{days} дня"
        else:
            days_text = f"{days} дней"
        await message.answer(f"📆 Задача перенесена на {days_text} (в 9:00).")
    else:
        days_text = f"{days} day" if days == 1 else f"{days} days"
        await message.answer(f"📆 Task rescheduled to {days_text} (at 9:00 AM).")


# ============ Text Task Handlers ============


@router.message(Command("task"))
async def cmd_task(message: Message, state: FSMContext):
    """Handle /task command - create task from text."""
    lang = await get_user_language(message.from_user.id)

    # Check if text was provided with the command
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        task_text = parts[1].strip()
        if task_text:
            await _process_text_task(message, state, task_text, lang)
            return

    # No text provided - show help or enter FSM
    await state.set_state(TextTaskState.waiting_for_text)
    await state.update_data(lang=lang)
    await message.answer(
        get_text("task_enter_text", lang),
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(lang),
    )


@router.message(F.text.in_(["📝 Добавить задачу", "📝 Add Task"]))
async def add_task_button(message: Message, state: FSMContext):
    """Handle 'Add Task' button press."""
    lang = await get_user_language(message.from_user.id)
    await state.set_state(TextTaskState.waiting_for_text)
    await state.update_data(lang=lang)
    await message.answer(
        get_text("task_enter_text", lang),
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(lang),
    )


@router.message(TextTaskState.waiting_for_text)
async def process_text_task_input(message: Message, state: FSMContext):
    """Process text task input from FSM state."""
    data = await state.get_data()
    lang = data.get("lang", "ru")

    if not message.text or message.text.startswith("/"):
        await state.clear()
        return

    await _process_text_task(message, state, message.text, lang)


async def _process_text_task(
    message: Message, state: FSMContext, task_text: str, lang: str
):
    """Process text and create a task from it."""
    from services.voice_service import extract_task_from_text

    processing_msg = await message.answer(get_text("task_processing", lang))

    try:
        task_info = await extract_task_from_text(task_text, lang)

        if not task_info:
            await processing_msg.edit_text(get_text("voice_no_task", lang))
            await state.clear()
            return

        # If date was explicitly mentioned, create task immediately
        if task_info.has_explicit_date:
            task_date = task_info.due_date
            date_obj = date.fromisoformat(task_date)
            today = date.today()

            if date_obj == today:
                date_display = get_text("date_today", lang)
            elif date_obj == today + timedelta(days=1):
                date_display = get_text("date_tomorrow", lang)
            else:
                date_display = task_date

            created_task = await create_task_from_voice(
                telegram_id=message.from_user.id,
                title=task_info.title,
                due_date=task_info.due_date,
                scheduled_at=task_info.scheduled_at,
            )

            await state.clear()

            if created_task:
                await processing_msg.edit_text(
                    get_text(
                        "voice_task_created",
                        lang,
                        title=task_info.title,
                        date=date_display,
                    )
                )
                # Offer reminder
                task_id = created_task.get("id")
                if task_id:
                    await message.answer(
                        get_text("reminder_ask", lang),
                        reply_markup=get_reminder_time_keyboard(task_id, lang),
                    )
            else:
                await processing_msg.edit_text(get_text("error_not_registered", lang))
        else:
            # No date mentioned - ask user to choose
            await processing_msg.delete()
            await state.set_state(TextTaskState.waiting_for_date)
            await state.update_data(
                task_title=task_info.title,
                lang=lang,
            )
            await message.answer(
                get_text("voice_ask_date", lang),
                reply_markup=get_text_task_date_keyboard(lang),
            )

    except Exception as e:
        print(f"Error processing text task: {e}")
        await processing_msg.edit_text(get_text("error", lang))
        await state.clear()


@router.callback_query(F.data.startswith("text_date:"))
async def handle_text_date_callback(callback: CallbackQuery, state: FSMContext):
    """Handle date selection for text task."""
    action = callback.data.split(":")[1]

    data = await state.get_data()
    task_title = data.get("task_title")
    lang = data.get("lang", "ru")

    if action == "cancel":
        await state.clear()
        await callback.answer(get_text("postpone_cancelled", lang))
        await callback.message.edit_text(get_text("postpone_cancelled", lang))
        return

    if not task_title:
        await state.clear()
        await callback.answer(get_text("error", lang))
        await callback.message.edit_text(get_text("error", lang))
        return

    if action == "custom":
        await state.set_state(TextTaskState.waiting_for_custom_date)
        await callback.answer()
        await callback.message.edit_text(
            get_text("voice_enter_date", lang),
            reply_markup=get_cancel_keyboard(lang),
        )
        return

    # Determine date
    today = date.today()
    if action == "today":
        task_date = today
        date_display = get_text("date_today", lang)
    elif action == "tomorrow":
        task_date = today + timedelta(days=1)
        date_display = get_text("date_tomorrow", lang)
    else:
        await callback.answer()
        return

    created_task = await create_task_from_voice(
        telegram_id=callback.from_user.id,
        title=task_title,
        due_date=task_date.strftime("%Y-%m-%d"),
    )

    await state.clear()

    if created_task:
        await callback.answer("✅")
        await callback.message.edit_text(
            get_text("voice_task_created", lang, title=task_title, date=date_display)
        )
        # Offer reminder
        task_id = created_task.get("id")
        if task_id:
            await callback.message.answer(
                get_text("reminder_ask", lang),
                reply_markup=get_reminder_time_keyboard(task_id, lang),
            )
    else:
        await callback.answer(get_text("error", lang))
        await callback.message.edit_text(get_text("error_not_registered", lang))


@router.message(TextTaskState.waiting_for_custom_date)
async def handle_text_task_custom_date(message: Message, state: FSMContext):
    """Handle custom date text input for text task."""
    data = await state.get_data()
    task_title = data.get("task_title")
    lang = data.get("lang", "ru")

    if not task_title:
        await state.clear()
        await message.answer(get_text("error", lang))
        return

    task_date = parse_custom_date(message.text, lang)

    if not task_date:
        await message.answer(
            get_text("voice_invalid_date", lang),
            reply_markup=get_cancel_keyboard(lang),
        )
        return

    if lang == "ru":
        months_ru = [
            "",
            "января",
            "февраля",
            "марта",
            "апреля",
            "мая",
            "июня",
            "июля",
            "августа",
            "сентября",
            "октября",
            "ноября",
            "декабря",
        ]
        date_display = f"{task_date.day} {months_ru[task_date.month]} {task_date.year}"
    else:
        date_display = task_date.strftime("%B %d, %Y")

    created_task = await create_task_from_voice(
        telegram_id=message.from_user.id,
        title=task_title,
        due_date=task_date.strftime("%Y-%m-%d"),
    )

    await state.clear()

    if created_task:
        await message.answer(
            get_text("voice_task_created", lang, title=task_title, date=date_display)
        )
        # Offer reminder
        task_id = created_task.get("id")
        if task_id:
            await message.answer(
                get_text("reminder_ask", lang),
                reply_markup=get_reminder_time_keyboard(task_id, lang),
            )
    else:
        await message.answer(get_text("error_not_registered", lang))


# ============ Reminder Handlers ============


@router.callback_query(F.data.startswith("set_reminder:"))
async def handle_set_reminder(callback: CallbackQuery, state: FSMContext):
    """Handle reminder time selection after task creation."""
    lang = await get_user_language(callback.from_user.id)
    parts = callback.data.split(":")
    task_id = int(parts[1])
    time_value = parts[2]

    if len(parts) > 3:
        # Time format like 09:00 split into parts[2]:parts[3]
        time_value = f"{parts[2]}:{parts[3]}"

    if time_value == "skip":
        await callback.answer(get_text("reminder_skipped", lang))
        await callback.message.edit_text(get_text("reminder_skipped", lang))
        return

    if time_value == "custom":
        await state.set_state(ReminderTimeState.waiting_for_time)
        await state.update_data(task_id=task_id, lang=lang)
        await callback.answer()
        await callback.message.edit_text(
            get_text("reminder_enter_time", lang),
            reply_markup=get_cancel_keyboard(lang),
        )
        return

    # Parse the time (HH:MM format)
    try:
        hour, minute = map(int, time_value.split(":"))
        # Set reminder for today or tomorrow if time already passed
        now = datetime.utcnow()
        moscow_hour = (now.hour + 3) % 24
        reminder_date = date.today()
        if hour < moscow_hour or (hour == moscow_hour and minute <= now.minute):
            reminder_date = date.today() + timedelta(days=1)

        # Convert Moscow time to UTC (Moscow = UTC+3)
        utc_hour = (hour - 3) % 24
        scheduled_at = datetime(
            reminder_date.year, reminder_date.month, reminder_date.day, utc_hour, minute
        ).isoformat()

        await update_task_scheduled_at(task_id, scheduled_at)

        await callback.answer("✅")
        await callback.message.edit_text(
            get_text("reminder_set", lang, time=time_value)
        )
    except (ValueError, IndexError):
        await callback.answer(get_text("error", lang))


@router.message(ReminderTimeState.waiting_for_time)
async def process_custom_reminder_time(message: Message, state: FSMContext):
    """Process custom reminder time input."""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    task_id = data.get("task_id")

    if not task_id:
        await state.clear()
        await message.answer(get_text("error", lang))
        return

    import re

    time_match = re.match(r"^(\d{1,2})[:\.](\d{2})$", message.text.strip())
    if not time_match:
        await message.answer(
            get_text("reminder_enter_time", lang),
            reply_markup=get_cancel_keyboard(lang),
        )
        return

    hour = int(time_match.group(1))
    minute = int(time_match.group(2))

    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        await message.answer(
            get_text("reminder_enter_time", lang),
            reply_markup=get_cancel_keyboard(lang),
        )
        return

    # Set reminder
    now = datetime.utcnow()
    moscow_hour = (now.hour + 3) % 24
    reminder_date = date.today()
    if hour < moscow_hour or (hour == moscow_hour and minute <= now.minute):
        reminder_date = date.today() + timedelta(days=1)

    utc_hour = (hour - 3) % 24
    scheduled_at = datetime(
        reminder_date.year, reminder_date.month, reminder_date.day, utc_hour, minute
    ).isoformat()

    await update_task_scheduled_at(task_id, scheduled_at)
    await state.clear()

    time_str = f"{hour:02d}:{minute:02d}"
    await message.answer(get_text("reminder_set", lang, time=time_str))


# ============ Voice Message Handlers ============


@router.message(F.voice)
async def handle_voice_message(message: Message, state: FSMContext):
    """Handle voice message and create task from it."""
    from services.voice_service import process_voice_message

    # Get user language with fallback
    try:
        lang = await get_user_language(message.from_user.id)
    except Exception:
        lang = "ru"

    # Send processing message
    processing_msg = await message.answer(get_text("voice_processing", lang))

    try:
        # Process voice message
        transcribed_text, task_info = await process_voice_message(
            message.bot, message.voice.file_id, lang
        )

        if not transcribed_text:
            await processing_msg.edit_text(get_text("voice_error", lang))
            return

        if not task_info:
            await processing_msg.edit_text(get_text("voice_no_task", lang))
            return

        # Show recognized text
        await processing_msg.edit_text(
            get_text("voice_recognized", lang, text=transcribed_text)
        )

        # If date was explicitly mentioned, create task immediately
        if task_info.has_explicit_date:
            # Format date for display
            task_date = task_info.due_date
            date_obj = date.fromisoformat(task_date)
            today = date.today()

            if date_obj == today:
                date_display = get_text("date_today", lang)
            elif date_obj == today + timedelta(days=1):
                date_display = get_text("date_tomorrow", lang)
            else:
                date_display = task_date

            # Create task
            created_task = await create_task_from_voice(
                telegram_id=message.from_user.id,
                title=task_info.title,
                due_date=task_info.due_date,
                scheduled_at=task_info.scheduled_at,
            )

            if created_task:
                await message.answer(
                    get_text(
                        "voice_task_created",
                        lang,
                        title=task_info.title,
                        date=date_display,
                    )
                )
                # Offer reminder for voice-created tasks too
                task_id = created_task.get("id")
                if task_id:
                    await message.answer(
                        get_text("reminder_ask", lang),
                        reply_markup=get_reminder_time_keyboard(task_id, lang),
                    )
            else:
                await message.answer(get_text("error_not_registered", lang))
        else:
            # No date mentioned - ask user to choose
            await state.set_state(VoiceTaskState.waiting_for_date)
            await state.update_data(
                task_title=task_info.title,
                lang=lang,
            )

            await message.answer(
                get_text("voice_ask_date", lang),
                reply_markup=get_voice_date_keyboard(lang),
            )

    except Exception as e:
        print(f"Error processing voice message: {e}")
        await processing_msg.edit_text(get_text("error", lang))


@router.callback_query(F.data.startswith("voice_date:"))
async def handle_voice_date_callback(callback: CallbackQuery, state: FSMContext):
    """Handle date selection for voice task."""
    action = callback.data.split(":")[1]

    # Get state data
    data = await state.get_data()
    task_title = data.get("task_title")
    lang = data.get("lang", "ru")

    if action == "cancel":
        await state.clear()
        await callback.answer(get_text("postpone_cancelled", lang))
        await callback.message.edit_text(get_text("postpone_cancelled", lang))
        return

    if not task_title:
        await state.clear()
        await callback.answer(get_text("error", lang))
        await callback.message.edit_text(get_text("error", lang))
        return

    # Handle custom date input
    if action == "custom":
        await state.set_state(VoiceTaskState.waiting_for_custom_date)
        await callback.answer()
        await callback.message.edit_text(
            get_text("voice_enter_date", lang),
            reply_markup=get_cancel_keyboard(lang),
        )
        return

    # Determine date
    today = date.today()
    if action == "today":
        task_date = today
        date_display = get_text("date_today", lang)
    elif action == "tomorrow":
        task_date = today + timedelta(days=1)
        date_display = get_text("date_tomorrow", lang)
    else:
        # Unknown action
        await callback.answer()
        return

    # Create task
    created_task = await create_task_from_voice(
        telegram_id=callback.from_user.id,
        title=task_title,
        due_date=task_date.strftime("%Y-%m-%d"),
    )

    await state.clear()

    if created_task:
        await callback.answer("✅")
        await callback.message.edit_text(
            get_text("voice_task_created", lang, title=task_title, date=date_display)
        )
        # Offer reminder
        task_id = created_task.get("id")
        if task_id:
            await callback.message.answer(
                get_text("reminder_ask", lang),
                reply_markup=get_reminder_time_keyboard(task_id, lang),
            )
    else:
        await callback.answer(get_text("error", lang))
        await callback.message.edit_text(get_text("error_not_registered", lang))


def parse_custom_date(text: str, lang: str = "ru") -> date | None:
    """
    Parse custom date from user input.

    Supports formats:
    - dd.mm.yyyy / dd/mm/yyyy
    - dd.mm / dd/mm (assumes current year)
    - day + month name (e.g., "25 января", "25 January")
    """
    import re

    text = text.strip().lower()
    today = date.today()

    # Russian month names
    months_ru = {
        "января": 1,
        "янв": 1,
        "февраля": 2,
        "фев": 2,
        "марта": 3,
        "мар": 3,
        "апреля": 4,
        "апр": 4,
        "мая": 5,
        "июня": 6,
        "июн": 6,
        "июля": 7,
        "июл": 7,
        "августа": 8,
        "авг": 8,
        "сентября": 9,
        "сен": 9,
        "октября": 10,
        "окт": 10,
        "ноября": 11,
        "ноя": 11,
        "декабря": 12,
        "дек": 12,
    }

    # English month names
    months_en = {
        "january": 1,
        "jan": 1,
        "february": 2,
        "feb": 2,
        "march": 3,
        "mar": 3,
        "april": 4,
        "apr": 4,
        "may": 5,
        "june": 6,
        "jun": 6,
        "july": 7,
        "jul": 7,
        "august": 8,
        "aug": 8,
        "september": 9,
        "sep": 9,
        "sept": 9,
        "october": 10,
        "oct": 10,
        "november": 11,
        "nov": 11,
        "december": 12,
        "dec": 12,
    }

    months = {**months_ru, **months_en}

    try:
        # Try dd.mm.yyyy or dd/mm/yyyy
        match = re.match(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", text)
        if match:
            day, month, year = (
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            )
            return date(year, month, day)

        # Try dd.mm or dd/mm (current year)
        match = re.match(r"(\d{1,2})[./](\d{1,2})$", text)
        if match:
            day, month = int(match.group(1)), int(match.group(2))
            result = date(today.year, month, day)
            # If date is in the past, use next year
            if result < today:
                result = date(today.year + 1, month, day)
            return result

        # Try "day month" format (e.g., "25 января", "25 January")
        match = re.match(r"(\d{1,2})\s+(\w+)", text)
        if match:
            day = int(match.group(1))
            month_name = match.group(2).lower()
            if month_name in months:
                month = months[month_name]
                result = date(today.year, month, day)
                # If date is in the past, use next year
                if result < today:
                    result = date(today.year + 1, month, day)
                return result

        return None

    except (ValueError, KeyError):
        return None


@router.message(VoiceTaskState.waiting_for_custom_date)
async def handle_custom_date_input(message: Message, state: FSMContext):
    """Handle custom date text input for voice task."""
    data = await state.get_data()
    task_title = data.get("task_title")
    lang = data.get("lang", "ru")

    if not task_title:
        await state.clear()
        await message.answer(get_text("error", lang))
        return

    # Parse the date
    task_date = parse_custom_date(message.text, lang)

    if not task_date:
        await message.answer(
            get_text("voice_invalid_date", lang),
            reply_markup=get_cancel_keyboard(lang),
        )
        return

    # Format date for display
    if lang == "ru":
        months_ru = [
            "",
            "января",
            "февраля",
            "марта",
            "апреля",
            "мая",
            "июня",
            "июля",
            "августа",
            "сентября",
            "октября",
            "ноября",
            "декабря",
        ]
        date_display = f"{task_date.day} {months_ru[task_date.month]} {task_date.year}"
    else:
        date_display = task_date.strftime("%B %d, %Y")

    # Create task
    created_task = await create_task_from_voice(
        telegram_id=message.from_user.id,
        title=task_title,
        due_date=task_date.strftime("%Y-%m-%d"),
    )

    await state.clear()

    if created_task:
        await message.answer(
            get_text("voice_task_created", lang, title=task_title, date=date_display)
        )
        # Offer reminder
        task_id = created_task.get("id")
        if task_id:
            await message.answer(
                get_text("reminder_ask", lang),
                reply_markup=get_reminder_time_keyboard(task_id, lang),
            )
    else:
        await message.answer(get_text("error_not_registered", lang))
