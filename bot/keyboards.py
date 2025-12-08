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
                    text="Открыть MoodSprint",
                    web_app=WebAppInfo(url=config.WEBAPP_URL),
                )
            ],
            [KeyboardButton(text="Статистика"), KeyboardButton(text="Настройки")],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Выбери действие...",
    )


def get_webapp_button() -> InlineKeyboardMarkup:
    """Inline button to open WebApp in fullscreen."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Открыть приложение",
                    web_app=WebAppInfo(url=config.WEBAPP_URL),
                )
            ]
        ]
    )


def get_start_inline_button() -> InlineKeyboardMarkup:
    """Inline button for /start command to open WebApp."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Открыть MoodSprint",
                    web_app=WebAppInfo(url=config.WEBAPP_URL),
                )
            ]
        ]
    )


def get_settings_keyboard(notifications_enabled: bool) -> InlineKeyboardMarkup:
    """Settings keyboard."""
    notification_text = (
        "🔕 Выключить уведомления"
        if notifications_enabled
        else "🔔 Включить уведомления"
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
            [InlineKeyboardButton(text="← Назад", callback_data="back_to_main")],
        ]
    )


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Admin panel keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Статистика пользователей", callback_data="admin:stats"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📢 Рассылка", callback_data="admin:broadcast"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👥 Активные пользователи", callback_data="admin:active_users"
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
                    text="✅ Отправить", callback_data="broadcast:confirm"
                ),
                InlineKeyboardButton(
                    text="❌ Отмена", callback_data="broadcast:cancel"
                ),
            ]
        ]
    )
