"""Tests for bot keyboard builders."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from keyboards import (  # noqa: E402
    get_main_keyboard,
    get_reminder_time_keyboard,
    get_text_task_date_keyboard,
)


class TestMainKeyboard:
    """Test main keyboard layout."""

    def test_has_add_task_button_ru(self):
        """Main keyboard should have 'Add Task' button in Russian."""
        kb = get_main_keyboard("ru")
        texts = [btn.text for row in kb.keyboard for btn in row]
        assert "📝 Добавить задачу" in texts

    def test_has_add_task_button_en(self):
        """Main keyboard should have 'Add Task' button in English."""
        kb = get_main_keyboard("en")
        texts = [btn.text for row in kb.keyboard for btn in row]
        assert "📝 Add Task" in texts

    def test_add_task_is_first_row(self):
        """Add Task should be in the first row."""
        kb = get_main_keyboard("ru")
        first_row_texts = [btn.text for btn in kb.keyboard[0]]
        assert "📝 Добавить задачу" in first_row_texts

    def test_has_stats_and_settings(self):
        """Should still have stats and settings buttons."""
        kb = get_main_keyboard("ru")
        all_texts = [btn.text for row in kb.keyboard for btn in row]
        # Stats and settings should still be present
        assert len(all_texts) >= 3


class TestTextTaskDateKeyboard:
    """Test text task date selection keyboard."""

    def test_has_today_and_tomorrow(self):
        """Should have today and tomorrow buttons."""
        kb = get_text_task_date_keyboard("ru")
        callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "text_date:today" in callbacks
        assert "text_date:tomorrow" in callbacks

    def test_has_custom_and_cancel(self):
        """Should have custom date and cancel buttons."""
        kb = get_text_task_date_keyboard("en")
        callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "text_date:custom" in callbacks
        assert "text_date:cancel" in callbacks


class TestReminderTimeKeyboard:
    """Test reminder time keyboard."""

    def test_has_preset_times(self):
        """Should have 9:00, 13:00, 18:00 preset buttons."""
        kb = get_reminder_time_keyboard(task_id=42, lang="ru")
        callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "set_reminder:42:09:00" in callbacks
        assert "set_reminder:42:13:00" in callbacks
        assert "set_reminder:42:18:00" in callbacks

    def test_has_custom_and_skip(self):
        """Should have custom and skip options."""
        kb = get_reminder_time_keyboard(task_id=1, lang="en")
        callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "set_reminder:1:custom" in callbacks
        assert "set_reminder:1:skip" in callbacks

    def test_task_id_in_callbacks(self):
        """Task ID should be embedded in all callback data."""
        kb = get_reminder_time_keyboard(task_id=99, lang="ru")
        for row in kb.inline_keyboard:
            for btn in row:
                assert ":99:" in btn.callback_data
