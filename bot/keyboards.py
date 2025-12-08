"""Keyboard builders for the bot."""

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from config import config


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Main menu keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="Open MoodSprint", web_app=WebAppInfo(url=config.WEBAPP_URL)
                )
            ],
            [KeyboardButton(text="My Stats"), KeyboardButton(text="Settings")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def get_webapp_button() -> InlineKeyboardMarkup:
    """Inline button to open WebApp in fullscreen."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Open MoodSprint", web_app=WebAppInfo(url=config.WEBAPP_URL)
                )
            ]
        ]
    )


def get_settings_keyboard(notifications_enabled: bool) -> InlineKeyboardMarkup:
    """Settings keyboard."""
    notification_text = (
        "Disable Notifications" if notifications_enabled else "Enable Notifications"
    )
    notification_callback = (
        "notifications:off" if notifications_enabled else "notifications:on"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=notification_text, callback_data=notification_callback
                )
            ],
            [InlineKeyboardButton(text="Back", callback_data="back_to_main")],
        ]
    )


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Admin panel keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="User Stats", callback_data="admin:stats")],
            [
                InlineKeyboardButton(
                    text="Broadcast Message", callback_data="admin:broadcast"
                )
            ],
            [
                InlineKeyboardButton(
                    text="View Active Users", callback_data="admin:active_users"
                )
            ],
        ]
    )


def get_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """Broadcast confirmation keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Confirm Send", callback_data="broadcast:confirm"
                ),
                InlineKeyboardButton(text="Cancel", callback_data="broadcast:cancel"),
            ]
        ]
    )
