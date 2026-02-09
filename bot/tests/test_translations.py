"""Tests for bot translations completeness."""

import os
import sys

# Add bot dir to path so we can import translations
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from translations import TRANSLATIONS as translations  # noqa: E402
from translations import get_text  # noqa: E402


class TestTranslationsCompleteness:
    """Ensure all keys exist in both ru and en."""

    def test_ru_and_en_have_same_keys(self):
        """All keys present in ru must be present in en and vice versa."""
        ru_keys = set(translations["ru"].keys())
        en_keys = set(translations["en"].keys())

        missing_in_en = ru_keys - en_keys
        missing_in_ru = en_keys - ru_keys

        assert not missing_in_en, f"Keys in ru but missing in en: {missing_in_en}"
        assert not missing_in_ru, f"Keys in en but missing in ru: {missing_in_ru}"

    def test_no_empty_values(self):
        """No translation value should be empty."""
        for lang in ["ru", "en"]:
            for key, value in translations[lang].items():
                assert isinstance(value, str), f"{lang}.{key} is not a string"
                assert len(value.strip()) > 0, f"{lang}.{key} is empty"

    def test_new_task_keys_exist(self):
        """New text task creation keys must exist in both languages."""
        required_keys = [
            "btn_add_task",
            "task_enter_text",
            "task_processing",
            "task_command_help",
        ]
        for key in required_keys:
            assert key in translations["ru"], f"Missing ru key: {key}"
            assert key in translations["en"], f"Missing en key: {key}"

    def test_new_reminder_keys_exist(self):
        """New reminder keys must exist in both languages."""
        required_keys = [
            "reminder_ask",
            "reminder_set",
            "reminder_skipped",
            "reminder_enter_time",
        ]
        for key in required_keys:
            assert key in translations["ru"], f"Missing ru key: {key}"
            assert key in translations["en"], f"Missing en key: {key}"

    def test_get_text_returns_value(self):
        """get_text should return the correct translation."""
        assert get_text("btn_add_task", "ru") == "📝 Добавить задачу"
        assert get_text("btn_add_task", "en") == "📝 Add Task"

    def test_get_text_with_format(self):
        """get_text with kwargs should format the string."""
        result = get_text("reminder_set", "ru", time="14:30")
        assert "14:30" in result

        result_en = get_text("reminder_set", "en", time="09:00")
        assert "09:00" in result_en

    def test_get_text_unknown_key_returns_key(self):
        """get_text with unknown key should return the key itself."""
        result = get_text("nonexistent_key_xyz", "ru")
        assert result == "nonexistent_key_xyz"

    def test_get_text_default_language(self):
        """get_text should default to ru when no lang specified."""
        result = get_text("btn_add_task")
        assert "Добавить" in result
