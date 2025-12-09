"""AI-powered task classification service."""

import json
from typing import Any

from flask import current_app

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


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
        self.client = None
        if OPENAI_AVAILABLE:
            api_key = current_app.config.get("OPENAI_API_KEY")
            if api_key:
                self.client = OpenAI(api_key=api_key)

    def classify_task(
        self, task_title: str, task_description: str | None = None
    ) -> dict[str, Any]:
        """
        Classify a task by type and preferred time.

        Returns dict with:
        - task_type: str (one of TASK_TYPES)
        - preferred_time: str (one of TIME_SLOTS)
        """
        # Try AI classification first
        if self.client:
            try:
                return self._ai_classify(task_title, task_description)
            except Exception as e:
                current_app.logger.error(f"AI classification failed: {e}")

        # Fallback to keyword-based classification
        return self._keyword_classify(task_title, task_description)

    def _ai_classify(
        self, task_title: str, task_description: str | None
    ) -> dict[str, Any]:
        """Use OpenAI to classify task."""
        prompt = f"""Определи тип задачи и лучшее время дня для её выполнения.

Задача: {task_title}
{f'Описание: {task_description}' if task_description else ''}

Типы задач (выбери один):
- creative: творческие задачи (дизайн, идеи, креатив)
- analytical: аналитические (отчёты, данные, исследования)
- communication: коммуникация (звонки, встречи, переписка)
- physical: физические (спорт, уборка, прогулки)
- learning: обучение (курсы, чтение, изучение нового)
- planning: планирование (списки, организация, расписание)
- coding: программирование (код, баги, разработка)
- writing: письменные (статьи, документы, тексты)

Время дня (выбери одно):
- morning: утро (6:00-12:00) - для задач требующих концентрации
- afternoon: день (12:00-18:00) - для рутинных и коммуникационных задач
- evening: вечер (18:00-22:00) - для отдыха и учёбы
- night: ночь (22:00-6:00) - для творческих задач в тишине

Верни ТОЛЬКО JSON:
{{"task_type": "тип", "preferred_time": "время"}}
"""

        response = self.client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",
            reasoning_effort="minimal",
            messages=[
                {
                    "role": "system",
                    "content": "Ты классификатор задач. Отвечай только валидным JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=200,
        )

        content = response.choices[0].message.content.strip()

        # Handle markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        result = json.loads(content)

        # Validate and normalize
        task_type = result.get("task_type", "planning")
        if task_type not in self.TASK_TYPES:
            task_type = "planning"

        preferred_time = result.get("preferred_time", "morning")
        if preferred_time not in self.TIME_SLOTS:
            preferred_time = "morning"

        return {
            "task_type": task_type,
            "preferred_time": preferred_time,
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
