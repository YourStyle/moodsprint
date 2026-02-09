"""Bot translations for multi-language support."""

from typing import Callable

TRANSLATIONS = {
    "ru": {
        # General
        "welcome": "Добро пожаловать в MoodSprint! 🚀",
        "welcome_back": "С возвращением! 👋",
        "error": "Произошла ошибка. Попробуйте позже.",
        "unknown_command": "Неизвестная команда. Используйте /help для списка команд.",
        # Main menu buttons
        "btn_open_app": "📱 Открыть приложение",
        "btn_stats": "📊 Статистика",
        "btn_settings": "⚙️ Настройки",
        "btn_help": "❓ Помощь",
        # Stats
        "stats_title": "📊 Ваша статистика",
        "stats_level": "Уровень",
        "stats_xp": "Опыт",
        "stats_streak": "Серия дней",
        "stats_tasks_completed": "Задач выполнено",
        "stats_focus_time": "Время фокуса",
        "stats_minutes": "мин",
        "stats_no_data": "Пока нет данных. Начните выполнять задачи!",
        # Settings
        "settings_title": "⚙️ Настройки",
        "settings_notifications": "🔔 Уведомления",
        "settings_notifications_on": "Включены",
        "settings_notifications_off": "Выключены",
        "settings_language": "🌐 Язык",
        "settings_changed": "Настройки сохранены ✓",
        # Notifications
        "notif_morning": "Доброе утро! ☀️\nКакие задачи запланированы на сегодня?",
        "notif_evening": "Добрый вечер! 🌙\nНе забудьте проверить свой прогресс за день.",
        "notif_streak_warning": (
            "⚠️ Ваша серия в {days} дней под угрозой!"
            "\nВыполните хотя бы одну задачу сегодня."
        ),
        "notif_streak_lost": "😔 Серия прервана. Но ничего, начнём заново!",
        # Task reminders
        "reminder_title": "⏰ Напоминание о задаче",
        "reminder_task": "Задача: {title}",
        "reminder_scheduled": "Запланировано на: {time}",
        "btn_start_task": "▶️ Начать",
        "btn_done_task": "✅ Готово",
        "btn_snooze_15": "⏰ +15 мин",
        "btn_snooze_1h": "⏰ +1 час",
        "btn_postpone": "📅 Перенести",
        "btn_delete_task": "🗑 Удалить",
        # Task postpone
        "postpone_ask_days": "На сколько дней перенести задачу?",
        "postpone_success": "✓ Задача перенесена на {date}",
        "postpone_cancelled": "Перенос отменён",
        "btn_postpone_1": "На завтра",
        "btn_postpone_2": "Через 2 дня",
        "btn_postpone_7": "Через неделю",
        "btn_postpone_custom": "Другое...",
        "btn_cancel": "❌ Отмена",
        # Free time
        "freetime_ask": "Сколько у вас свободного времени?",
        "freetime_suggestions": "📋 Вот что можно сделать за {minutes} минут:",
        "freetime_no_tasks": "Нет подходящих задач. Отдохните! 😊",
        "btn_15min": "15 мин",
        "btn_30min": "30 мин",
        "btn_60min": "1 час",
        "btn_120min": "2 часа",
        # Voice messages
        "voice_processing": "🎤 Обрабатываю голосовое сообщение...",
        "voice_recognized": "📝 Распознанный текст:\n\n{text}",
        "voice_task_created": "✅ Задача создана!\n\n📌 {title}\n📅 {date}",
        "voice_ask_date": "На какую дату поставить задачу?",
        "voice_error": "❌ Не удалось распознать голосовое сообщение. Попробуйте ещё раз.",
        "voice_no_task": (
            "🤔 Не удалось понять задачу из сообщения."
            " Попробуйте сформулировать иначе."
        ),
        "voice_enter_date": (
            "📅 Введите дату в одном из форматов:"
            "\n• 25.01.2026\n• 25/01/2026\n• 25 января"
        ),
        "voice_invalid_date": (
            "❌ Не удалось распознать дату."
            " Попробуйте в формате: 25.01.2026 или 25 января"
        ),
        "btn_today": "Сегодня",
        "btn_tomorrow": "Завтра",
        "btn_pick_date": "📅 Другая дата",
        # Dates
        "date_today": "сегодня",
        "date_tomorrow": "завтра",
        # Weekly summary
        "weekly_title": "📊 Итоги недели",
        "weekly_tasks": "Выполнено задач: {count}",
        "weekly_focus": "Время в фокусе: {minutes} мин",
        "weekly_streak": "Текущая серия: {days} дней",
        "weekly_xp": "Заработано XP: {xp}",
        "weekly_great": "Отличная неделя! 🎉",
        "weekly_good": "Хорошая работа! 👍",
        "weekly_keep_going": "Продолжайте в том же духе! 💪",
        # Help
        "help_title": "❓ Помощь",
        "help_text": """
MoodSprint — умный планировщик с геймификацией.

🎤 <b>Голосовые сообщения</b>
Просто отправьте голосовое сообщение с задачей, и бот создаст её автоматически!

📱 <b>Приложение</b>
/app — открыть веб-приложение

📊 <b>Статистика</b>
/stats — ваша статистика

⏰ <b>Свободное время</b>
/freetime — получить предложения задач

⚙️ <b>Настройки</b>
/settings — управление уведомлениями
""",
        # Admin
        "admin_broadcast_start": "Введите сообщение для рассылки (текст, фото или видео):",
        "admin_broadcast_confirm": "Отправить это сообщение {count} пользователям?",
        "admin_broadcast_sent": "✅ Рассылка завершена: {success}/{total}",
        "admin_broadcast_cancelled": "Рассылка отменена",
        "btn_confirm": "✅ Подтвердить",
        # Text task creation
        "btn_add_task": "📝 Добавить задачу",
        "task_enter_text": "📝 Введите описание задачи:\n\nНапример: <i>Купить молоко завтра</i>",
        "task_processing": "⏳ Обрабатываю задачу...",
        "task_command_help": (
            "📝 Чтобы создать задачу, напишите:"
            "\n/task Купить молоко завтра"
            "\n\nИли нажмите кнопку «📝 Добавить задачу»"
        ),
        # Reminders after task creation
        "reminder_ask": "⏰ Хотите поставить напоминание?",
        "reminder_set": "✅ Напоминание установлено на {time}",
        "reminder_skipped": "Хорошо, без напоминания",
        "reminder_enter_time": "⌚ Введите время в формате ЧЧ:ММ (например, 14:30):",
        # Errors
        "error_not_registered": "Вы не зарегистрированы. Откройте приложение через /app",
        "error_task_not_found": "Задача не найдена",
    },
    "en": {
        # General
        "welcome": "Welcome to MoodSprint! 🚀",
        "welcome_back": "Welcome back! 👋",
        "error": "An error occurred. Please try again later.",
        "unknown_command": "Unknown command. Use /help to see available commands.",
        # Main menu buttons
        "btn_open_app": "📱 Open App",
        "btn_stats": "📊 Statistics",
        "btn_settings": "⚙️ Settings",
        "btn_help": "❓ Help",
        # Stats
        "stats_title": "📊 Your Statistics",
        "stats_level": "Level",
        "stats_xp": "Experience",
        "stats_streak": "Day Streak",
        "stats_tasks_completed": "Tasks Completed",
        "stats_focus_time": "Focus Time",
        "stats_minutes": "min",
        "stats_no_data": "No data yet. Start completing tasks!",
        # Settings
        "settings_title": "⚙️ Settings",
        "settings_notifications": "🔔 Notifications",
        "settings_notifications_on": "Enabled",
        "settings_notifications_off": "Disabled",
        "settings_language": "🌐 Language",
        "settings_changed": "Settings saved ✓",
        # Notifications
        "notif_morning": "Good morning! ☀️\nWhat tasks are planned for today?",
        "notif_evening": "Good evening! 🌙\nDon't forget to check your progress today.",
        "notif_streak_warning": (
            "⚠️ Your {days}-day streak is at risk!" "\nComplete at least one task today."
        ),
        "notif_streak_lost": "😔 Streak lost. But let's start again!",
        # Task reminders
        "reminder_title": "⏰ Task Reminder",
        "reminder_task": "Task: {title}",
        "reminder_scheduled": "Scheduled for: {time}",
        "btn_start_task": "▶️ Start",
        "btn_done_task": "✅ Done",
        "btn_snooze_15": "⏰ +15 min",
        "btn_snooze_1h": "⏰ +1 hour",
        "btn_postpone": "📅 Postpone",
        "btn_delete_task": "🗑 Delete",
        # Task postpone
        "postpone_ask_days": "How many days to postpone the task?",
        "postpone_success": "✓ Task postponed to {date}",
        "postpone_cancelled": "Postpone cancelled",
        "btn_postpone_1": "Tomorrow",
        "btn_postpone_2": "In 2 days",
        "btn_postpone_7": "In a week",
        "btn_postpone_custom": "Other...",
        "btn_cancel": "❌ Cancel",
        # Free time
        "freetime_ask": "How much free time do you have?",
        "freetime_suggestions": "📋 Here's what you can do in {minutes} minutes:",
        "freetime_no_tasks": "No suitable tasks. Take a rest! 😊",
        "btn_15min": "15 min",
        "btn_30min": "30 min",
        "btn_60min": "1 hour",
        "btn_120min": "2 hours",
        # Voice messages
        "voice_processing": "🎤 Processing voice message...",
        "voice_recognized": "📝 Recognized text:\n\n{text}",
        "voice_task_created": "✅ Task created!\n\n📌 {title}\n📅 {date}",
        "voice_ask_date": "What date should the task be set for?",
        "voice_error": "❌ Could not recognize voice message. Please try again.",
        "voice_no_task": "🤔 Could not understand the task from the message. Please try rephrasing.",
        "voice_enter_date": (
            "📅 Enter the date in one of these formats:"
            "\n• 25.01.2026\n• 25/01/2026\n• 25 January"
        ),
        "voice_invalid_date": "❌ Could not parse the date. Try format: 25.01.2026 or 25 January",
        "btn_today": "Today",
        "btn_tomorrow": "Tomorrow",
        "btn_pick_date": "📅 Other date",
        # Dates
        "date_today": "today",
        "date_tomorrow": "tomorrow",
        # Weekly summary
        "weekly_title": "📊 Weekly Summary",
        "weekly_tasks": "Tasks completed: {count}",
        "weekly_focus": "Focus time: {minutes} min",
        "weekly_streak": "Current streak: {days} days",
        "weekly_xp": "XP earned: {xp}",
        "weekly_great": "Great week! 🎉",
        "weekly_good": "Good job! 👍",
        "weekly_keep_going": "Keep it up! 💪",
        # Help
        "help_title": "❓ Help",
        "help_text": """
MoodSprint — smart task planner with gamification.

🎤 <b>Voice Messages</b>
Just send a voice message with your task, and the bot will create it automatically!

📱 <b>App</b>
/app — open web application

📊 <b>Statistics</b>
/stats — your statistics

⏰ <b>Free Time</b>
/freetime — get task suggestions

⚙️ <b>Settings</b>
/settings — manage notifications
""",
        # Admin
        "admin_broadcast_start": "Enter the message to broadcast (text, photo, or video):",
        "admin_broadcast_confirm": "Send this message to {count} users?",
        "admin_broadcast_sent": "✅ Broadcast complete: {success}/{total}",
        "admin_broadcast_cancelled": "Broadcast cancelled",
        "btn_confirm": "✅ Confirm",
        # Text task creation
        "btn_add_task": "📝 Add Task",
        "task_enter_text": (
            "📝 Enter your task description:"
            "\n\nExample: <i>Buy groceries tomorrow</i>"
        ),
        "task_processing": "⏳ Processing task...",
        "task_command_help": (
            "📝 To create a task, type:"
            "\n/task Buy groceries tomorrow"
            "\n\nOr tap the «📝 Add Task» button"
        ),
        # Reminders after task creation
        "reminder_ask": "⏰ Want to set a reminder?",
        "reminder_set": "✅ Reminder set for {time}",
        "reminder_skipped": "OK, no reminder",
        "reminder_enter_time": "⌚ Enter time in HH:MM format (e.g., 14:30):",
        # Errors
        "error_not_registered": "You are not registered. Open the app via /app",
        "error_task_not_found": "Task not found",
    },
}


def get_translator(lang: str = "ru") -> Callable[[str], str]:
    """
    Get a translation function for the specified language.

    Args:
        lang: Language code ('ru' or 'en')

    Returns:
        Function that translates keys to localized strings
    """
    translations = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])

    def t(key: str, **kwargs) -> str:
        """Translate a key with optional formatting."""
        text = translations.get(key, TRANSLATIONS["ru"].get(key, key))
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError:
                return text
        return text

    return t


def get_text(key: str, lang: str = "ru", **kwargs) -> str:
    """
    Get translated text for a key.

    Args:
        key: Translation key
        lang: Language code ('ru' or 'en')
        **kwargs: Format arguments

    Returns:
        Translated string
    """
    t = get_translator(lang)
    return t(key, **kwargs)
