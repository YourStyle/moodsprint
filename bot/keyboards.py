"""Keyboard builders for the bot."""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from config import config
from translations import get_text


def get_main_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """Main menu keyboard."""
    placeholder = "Выбери действие..." if lang == "ru" else "Choose action..."
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=get_text("btn_add_task", lang)),
            ],
            [
                KeyboardButton(text=get_text("btn_stats", lang)),
                KeyboardButton(text=get_text("btn_settings", lang)),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder=placeholder,
    )


def get_webapp_button(lang: str = "ru") -> InlineKeyboardMarkup:
    """Inline button to open WebApp in fullscreen."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text("btn_open_app", lang),
                    web_app=WebAppInfo(url=config.WEBAPP_URL),
                )
            ]
        ]
    )


def get_start_inline_button(lang: str = "ru") -> InlineKeyboardMarkup:
    """Inline button for /start command to open WebApp."""
    text = "🚀 Открыть MoodSprint" if lang == "ru" else "🚀 Open MoodSprint"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=text,
                    web_app=WebAppInfo(url=config.WEBAPP_URL),
                )
            ]
        ]
    )


def get_settings_keyboard(
    notifications_enabled: bool, lang: str = "ru"
) -> InlineKeyboardMarkup:
    """Settings keyboard."""
    if notifications_enabled:
        notification_text = "🔕 " + (
            "Выключить уведомления" if lang == "ru" else "Disable notifications"
        )
    else:
        notification_text = "🔔 " + (
            "Включить уведомления" if lang == "ru" else "Enable notifications"
        )
    notification_callback = (
        "notifications:off" if notifications_enabled else "notifications:on"
    )
    back_text = "← Назад" if lang == "ru" else "← Back"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=notification_text, callback_data=notification_callback
                )
            ],
            [InlineKeyboardButton(text=back_text, callback_data="back_to_main")],
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


def get_freetime_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard for selecting available free time."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text("btn_15min", lang), callback_data="freetime:15"
                ),
                InlineKeyboardButton(
                    text=get_text("btn_30min", lang), callback_data="freetime:30"
                ),
                InlineKeyboardButton(
                    text="45 " + ("мин" if lang == "ru" else "min"),
                    callback_data="freetime:45",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=get_text("btn_60min", lang), callback_data="freetime:60"
                ),
                InlineKeyboardButton(
                    text="1.5 " + ("часа" if lang == "ru" else "hours"),
                    callback_data="freetime:90",
                ),
                InlineKeyboardButton(
                    text=get_text("btn_120min", lang), callback_data="freetime:120"
                ),
            ],
        ]
    )


def get_task_suggestion_keyboard(
    task_id: int, estimated_minutes: int, lang: str = "ru"
) -> InlineKeyboardMarkup:
    """Keyboard to start a suggested task."""
    start_text = (
        "▶️ "
        + ("Начать" if lang == "ru" else "Start")
        + f" ({estimated_minutes} "
        + ("мин" if lang == "ru" else "min")
        + ")"
    )
    other_text = "🔄 " + ("Другие варианты" if lang == "ru" else "Other options")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=start_text,
                    web_app=WebAppInfo(url=f"{config.WEBAPP_URL}/tasks/{task_id}"),
                )
            ],
            [
                InlineKeyboardButton(
                    text=other_text,
                    callback_data="freetime:refresh",
                )
            ],
        ]
    )


def get_task_reminder_keyboard(task_id: int, lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard for task reminder with actions."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text("btn_start_task", lang),
                    web_app=WebAppInfo(url=f"{config.WEBAPP_URL}/tasks/{task_id}"),
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_text("btn_snooze_15", lang),
                    callback_data=f"reminder:snooze:{task_id}:15",
                ),
                InlineKeyboardButton(
                    text=get_text("btn_snooze_1h", lang),
                    callback_data=f"reminder:snooze:{task_id}:60",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=get_text("btn_postpone", lang),
                    callback_data=f"reminder:tomorrow:{task_id}",
                ),
                InlineKeyboardButton(
                    text="📆 N " + ("дней" if lang == "ru" else "days"),
                    callback_data=f"reminder:postpone_days:{task_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=get_text("btn_delete_task", lang),
                    callback_data=f"reminder:delete:{task_id}",
                ),
            ],
        ]
    )


def get_cancel_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Cancel action keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text("btn_cancel", lang), callback_data="cancel_state"
                )
            ]
        ]
    )


def get_morning_reminder_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Morning reminder keyboard with open app and disable notifications options."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text("btn_open_app", lang),
                    web_app=WebAppInfo(url=config.WEBAPP_URL),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔕 "
                    + (
                        "Отключить уведомления"
                        if lang == "ru"
                        else "Disable notifications"
                    ),
                    callback_data="notifications:off",
                )
            ],
        ]
    )


def get_voice_date_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard for selecting task date from voice message."""
    from translations import get_text

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text("btn_today", lang),
                    callback_data="voice_date:today",
                ),
                InlineKeyboardButton(
                    text=get_text("btn_tomorrow", lang),
                    callback_data="voice_date:tomorrow",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=get_text("btn_pick_date", lang),
                    callback_data="voice_date:custom",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=get_text("btn_cancel", lang),
                    callback_data="voice_date:cancel",
                ),
            ],
        ]
    )


def get_voice_confirm_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard for confirming task creation from voice."""
    from translations import get_text

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text("btn_confirm", lang),
                    callback_data="voice_confirm:yes",
                ),
                InlineKeyboardButton(
                    text=get_text("btn_cancel", lang),
                    callback_data="voice_confirm:cancel",
                ),
            ],
        ]
    )


def get_text_task_date_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard for selecting task date from text task creation."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text("btn_today", lang),
                    callback_data="text_date:today",
                ),
                InlineKeyboardButton(
                    text=get_text("btn_tomorrow", lang),
                    callback_data="text_date:tomorrow",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=get_text("btn_pick_date", lang),
                    callback_data="text_date:custom",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=get_text("btn_cancel", lang),
                    callback_data="text_date:cancel",
                ),
            ],
        ]
    )


def get_reminder_time_keyboard(task_id: int, lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard for setting a reminder time after task creation."""
    skip_text = "Пропустить" if lang == "ru" else "Skip"
    custom_text = "Другое" if lang == "ru" else "Custom"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="9:00", callback_data=f"set_reminder:{task_id}:09:00"
                ),
                InlineKeyboardButton(
                    text="13:00", callback_data=f"set_reminder:{task_id}:13:00"
                ),
                InlineKeyboardButton(
                    text="18:00", callback_data=f"set_reminder:{task_id}:18:00"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"⌚ {custom_text}",
                    callback_data=f"set_reminder:{task_id}:custom",
                ),
                InlineKeyboardButton(
                    text=f"⏭ {skip_text}", callback_data=f"set_reminder:{task_id}:skip"
                ),
            ],
        ]
    )
