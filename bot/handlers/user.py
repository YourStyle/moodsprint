"""User handlers."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart

from keyboards import get_main_keyboard, get_webapp_button, get_settings_keyboard
from database import get_user_by_telegram_id, get_user_stats, update_user_notifications

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command."""
    user = await get_user_by_telegram_id(message.from_user.id)

    if user:
        text = (
            f"Welcome back, {message.from_user.first_name}!\n\n"
            f"Level {user.get('level', 1)} | {user.get('xp', 0)} XP\n"
            f"Streak: {user.get('streak_days', 0)} days\n\n"
            "Tap the button below to open MoodSprint!"
        )
    else:
        text = (
            f"Hey {message.from_user.first_name}!\n\n"
            "Welcome to MoodSprint - your mood-aware task manager.\n\n"
            "I'll help you:\n"
            "- Break down tasks based on your energy\n"
            "- Stay focused with timer sessions\n"
            "- Build healthy productivity habits\n\n"
            "Tap below to get started!"
        )

    await message.answer(text, reply_markup=get_main_keyboard())


@router.message(Command("app"))
async def cmd_app(message: Message):
    """Open the webapp."""
    await message.answer(
        "Tap to open MoodSprint in fullscreen:",
        reply_markup=get_webapp_button()
    )


@router.message(F.text == "Open MoodSprint")
async def open_webapp(message: Message):
    """Handle webapp button press."""
    await message.answer(
        "Opening MoodSprint...",
        reply_markup=get_webapp_button()
    )


@router.message(F.text == "My Stats")
async def show_stats(message: Message):
    """Show user statistics."""
    stats = await get_user_stats(message.from_user.id)

    if not stats:
        await message.answer("You haven't started using MoodSprint yet. Tap 'Open MoodSprint' to begin!")
        return

    user = stats['user']
    text = (
        f"Your MoodSprint Stats\n"
        f"{'=' * 20}\n\n"
        f"Level: {user.get('level', 1)}\n"
        f"XP: {user.get('xp', 0)}\n"
        f"Current Streak: {user.get('streak_days', 0)} days\n"
        f"Longest Streak: {user.get('longest_streak', 0)} days\n\n"
        f"Tasks completed: {stats['completed_tasks']}/{stats['total_tasks']}\n"
        f"Focus sessions: {stats['total_sessions']}\n"
        f"Total focus time: {stats['total_focus_minutes']} min\n"
    )

    await message.answer(text)


@router.message(F.text == "Settings")
async def show_settings(message: Message):
    """Show settings."""
    user = await get_user_by_telegram_id(message.from_user.id)
    notifications_enabled = user.get('notifications_enabled', True) if user else True

    await message.answer(
        "Settings:",
        reply_markup=get_settings_keyboard(notifications_enabled)
    )


@router.callback_query(F.data.startswith("notifications:"))
async def toggle_notifications(callback: CallbackQuery):
    """Toggle notifications."""
    action = callback.data.split(":")[1]
    enabled = action == "on"

    await update_user_notifications(callback.from_user.id, enabled)

    status = "enabled" if enabled else "disabled"
    await callback.answer(f"Notifications {status}!")

    await callback.message.edit_reply_markup(
        reply_markup=get_settings_keyboard(enabled)
    )


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Back to main menu."""
    await callback.message.delete()
    await callback.answer()
