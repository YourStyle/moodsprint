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
            [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin:broadcast")],
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


def get_freetime_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting available free time."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="15 мин", callback_data="freetime:15"),
                InlineKeyboardButton(text="30 мин", callback_data="freetime:30"),
                InlineKeyboardButton(text="45 мин", callback_data="freetime:45"),
            ],
            [
                InlineKeyboardButton(text="1 час", callback_data="freetime:60"),
                InlineKeyboardButton(text="1.5 часа", callback_data="freetime:90"),
                InlineKeyboardButton(text="2 часа", callback_data="freetime:120"),
            ],
        ]
    )


def get_task_suggestion_keyboard(
    task_id: int, estimated_minutes: int
) -> InlineKeyboardMarkup:
    """Keyboard to start a suggested task."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"▶️ Начать ({estimated_minutes} мин)",
                    web_app=WebAppInfo(url=f"{config.WEBAPP_URL}/tasks/{task_id}"),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Другие варианты",
                    callback_data="freetime:refresh",
                )
            ],
        ]
    )


def get_task_reminder_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Keyboard for task reminder with actions."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="▶️ Начать",
                    web_app=WebAppInfo(url=f"{config.WEBAPP_URL}/tasks/{task_id}"),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏰ Через 30 мин",
                    callback_data=f"reminder:snooze:{task_id}:30",
                ),
                InlineKeyboardButton(
                    text="⏰ Через 1 час",
                    callback_data=f"reminder:snooze:{task_id}:60",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📅 На завтра",
                    callback_data=f"reminder:tomorrow:{task_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Удалить",
                    callback_data=f"reminder:delete:{task_id}",
                ),
            ],
        ]
    )
