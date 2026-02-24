"""AI-powered task classification service."""

import json
from typing import Any

from flask import current_app

from app.services.openai_client import get_openai_client


class TaskClassifier:
    """Service for AI-powered task classification."""

    # Valid task types (matching onboarding options)
    TASK_TYPES = [
        "creative",  # Творческие
        "analytical",  # Аналитические
        "communication",  # Общение
        "physical",  # Физические
        "learning",  # Обучение
        "planning",  # Планирование
        "coding",  # Программирование
        "writing",  # Письмо
    ]

    # Valid time slots
    TIME_SLOTS = ["morning", "afternoon", "evening", "night"]

    VALID_DIFFICULTIES = ["easy", "medium", "hard", "very_hard"]

    # Urgency keywords — force hard difficulty
    URGENCY_KEYWORDS = [
        "срочно",
        "срочное",
        "срочная",
        "срочный",
        "asap",
        "urgent",
        "немедленно",
        "сейчас",
        "важно",
        "важная",
        "важное",
        "критично",
        "дедлайн",
        "deadline",
        "горит",
    ]

    # Keywords for fallback classification
    KEYWORDS = {
        "creative": [
            "дизайн",
            "рисовать",
            "создать",
            "креатив",
            "идея",
            "design",
            "create",
        ],
        "analytical": [
            "анализ",
            "отчёт",
            "данные",
            "исследование",
            "analyze",
            "report",
            "data",
        ],
        "communication": [
            "позвонить",
            "встреча",
            "написать",
            "связаться",
            "call",
            "meeting",
            "email",
        ],
        "physical": [
            "спорт",
            "тренировка",
            "уборка",
            "прогулка",
            "exercise",
            "workout",
            "clean",
        ],
        "learning": [
            "учить",
            "курс",
            "читать",
            "изучить",
            "learn",
            "study",
            "read",
            "course",
        ],
        "planning": [
            "план",
            "организовать",
            "расписание",
            "список",
            "plan",
            "organize",
            "schedule",
        ],
        "coding": [
            "код",
            "программа",
            "баг",
            "фикс",
            "разработка",
            "code",
            "bug",
            "fix",
            "develop",
        ],
        "writing": [
            "статья",
            "документ",
            "текст",
            "написать",
            "article",
            "document",
            "write",
        ],
    }

    # Default time preferences for task types
    TYPE_TIME_MAPPING = {
        "creative": "morning",  # Творческие лучше утром
        "analytical": "morning",  # Аналитика требует свежей головы
        "communication": "afternoon",  # Коммуникации в рабочее время
        "physical": "evening",  # Физические после работы
        "learning": "evening",  # Учёба вечером
        "planning": "morning",  # Планирование с утра
        "coding": "afternoon",  # Кодинг в середине дня
        "writing": "morning",  # Писательство утром
    }

    def __init__(self):
        self.client = get_openai_client()

    def classify_and_rate_task(
        self,
        task_title: str,
        task_description: str | None = None,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Combined AI call: classify task type, preferred time, AND difficulty
        in a single gpt-5-nano request.

        Returns dict with:
        - difficulty: str (easy|medium|hard|very_hard)
        - task_type: str (one of TASK_TYPES)
        - preferred_time: str (one of TIME_SLOTS)
        """
        text_lower = f"{task_title} {task_description or ''}".lower()

        # Fast pre-check: urgency keywords force hard difficulty
        forced_difficulty = None
        for keyword in self.URGENCY_KEYWORDS:
            if keyword in text_lower:
                forced_difficulty = "hard"
                break

        # Try AI classification
        if self.client:
            try:
                result = self._ai_classify_and_rate(
                    task_title, task_description, user_id=user_id
                )
                # Override difficulty if urgency keyword detected
                if forced_difficulty:
                    result["difficulty"] = forced_difficulty
                return result
            except Exception as e:
                current_app.logger.error(f"AI classify_and_rate failed: {e}")

        # Fallback to keyword/heuristic classification
        fallback = self._keyword_classify(task_title, task_description)
        fallback["difficulty"] = forced_difficulty or self._heuristic_difficulty(
            text_lower
        )
        return fallback

    def _ai_classify_and_rate(
        self,
        task_title: str,
        task_description: str | None,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """Single AI call for difficulty + type + time using gpt-5-nano.

        Note: gpt-5-nano does NOT support reasoning_effort in Chat Completions API.
        """
        prompt = f"""Задача: {task_title}
{f'Описание: {task_description}' if task_description else ''}

Определи:
1) difficulty (easy|medium|hard|very_hard):
 - easy: 5-15 мин, рутина
 - medium: 30-60 мин, концентрация
 - hard: 1-3 часа, глубокая работа / срочно
 - very_hard: 3+ часов, комплекс
2) task_type (creative|analytical|communication|physical|learning|planning|coding|writing)
3) preferred_time (morning|afternoon|evening|night)

JSON: {{"difficulty":"...","task_type":"...","preferred_time":"..."}}"""

        from app.utils.ai_tracker import tracked_openai_call

        response = tracked_openai_call(
            self.client,
            user_id=user_id,
            endpoint="classify_and_rate",
            model="gpt-5-nano",
            messages=[
                {
                    "role": "system",
                    "content": "Классификатор задач. Только JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=60,
        )

        raw = response.choices[0].message.content
        if not raw:
            raise ValueError("Empty response from AI classifier")

        content = raw.strip()

        # Handle markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        result = json.loads(content)

        # Validate
        difficulty = result.get("difficulty", "medium")
        if difficulty not in self.VALID_DIFFICULTIES:
            difficulty = "medium"

        task_type = result.get("task_type", "planning")
        if task_type not in self.TASK_TYPES:
            task_type = "planning"

        preferred_time = result.get("preferred_time", "morning")
        if preferred_time not in self.TIME_SLOTS:
            preferred_time = "morning"

        return {
            "difficulty": difficulty,
            "task_type": task_type,
            "preferred_time": preferred_time,
        }

    @staticmethod
    def _heuristic_difficulty(text_lower: str) -> str:
        """Fallback difficulty based on text length."""
        if len(text_lower) < 20:
            return "easy"
        elif len(text_lower) < 50:
            return "medium"
        return "hard"

    def classify_task(
        self,
        task_title: str,
        task_description: str | None = None,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Classify a task by type and preferred time.
        Kept for backward compatibility.
        """
        result = self.classify_and_rate_task(task_title, task_description, user_id)
        return {
            "task_type": result["task_type"],
            "preferred_time": result["preferred_time"],
        }

    def _keyword_classify(
        self, task_title: str, task_description: str | None
    ) -> dict[str, Any]:
        """Fallback keyword-based classification."""
        text = f"{task_title} {task_description or ''}".lower()

        # Find matching task type
        task_type = "planning"  # default
        max_matches = 0

        for t_type, keywords in self.KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in text)
            if matches > max_matches:
                max_matches = matches
                task_type = t_type

        # Get preferred time from mapping
        preferred_time = self.TYPE_TIME_MAPPING.get(task_type, "morning")

        return {
            "task_type": task_type,
            "preferred_time": preferred_time,
        }
