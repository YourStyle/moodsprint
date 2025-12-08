"""User handlers."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart

from keyboards import (
    get_main_keyboard,
    get_webapp_button,
    get_settings_keyboard,
    get_start_inline_button,
)
from database import get_user_by_telegram_id, get_user_stats, update_user_notifications

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
