"""AI-powered task decomposition service."""

import json
from typing import Any

from flask import current_app

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class AIDecomposer:
    """Service for AI-powered task decomposition based on mood/energy."""

    # Decomposition strategies
    STRATEGIES = {
        "micro": {
            "description": "Very small steps for low energy state",
            "step_range": (5, 10),
            "max_steps": 8,
            "break_frequency": 2,
        },
        "gentle": {
            "description": "Medium steps with gentle pacing",
            "step_range": (10, 15),
            "max_steps": 6,
            "break_frequency": 3,
        },
        "careful": {
            "description": "Medium steps with frequent breaks",
            "step_range": (10, 15),
            "max_steps": 6,
            "break_frequency": 2,
        },
        "standard": {
            "description": "Normal productivity steps",
            "step_range": (15, 25),
            "max_steps": 5,
            "break_frequency": 4,
        },
    }

    def __init__(self):
        self.client = None
        if OPENAI_AVAILABLE:
            api_key = current_app.config.get("OPENAI_API_KEY")
            if api_key:
                self.client = OpenAI(api_key=api_key)

    def decompose_task(
        self, task_title: str, task_description: str | None, strategy: str
    ) -> list[dict[str, Any]]:
        """
        Decompose a task into subtasks based on strategy.

        Returns list of subtask dicts with:
        - title: str
        - estimated_minutes: int
        - order: int
        """
        strategy_config = self.STRATEGIES.get(strategy, self.STRATEGIES["standard"])

        # Try AI decomposition first
        if self.client:
            try:
                return self._ai_decompose(task_title, task_description, strategy_config)
            except Exception as e:
                current_app.logger.error(f"AI decomposition failed: {e}")

        # Fallback to simple decomposition
        return self._simple_decompose(task_title, task_description, strategy_config)

    def _ai_decompose(
        self, task_title: str, task_description: str | None, strategy_config: dict
    ) -> list[dict[str, Any]]:
        """Use OpenAI to decompose task."""
        min_minutes, max_minutes = strategy_config["step_range"]
        max_steps = strategy_config["max_steps"]

        prompt = f"""Разбей эту задачу на небольшие, конкретные шаги.

Задача: {task_title}
{f'Описание: {task_description}' if task_description else ''}

Требования:
- Создай от {max_steps-2} до {max_steps} конкретных шагов
- Каждый шаг должен занимать {min_minutes}-{max_minutes} минут
- Шаги должны быть конкретными и выполнимыми (начинай с глагола)
- Шаги должны быть выполнимы за один подход
- Расположи шаги в логическом порядке

Верни ТОЛЬКО JSON массив с объектами:
- "title": описание шага на русском (строка, макс 100 символов)
- "estimated_minutes": оценка времени (целое число от {min_minutes} до {max_minutes})

Пример формата:
[
  {{"title": "Открыть проект и изучить требования", "estimated_minutes": 10}},
  {{"title": "Создать базовую структуру файлов", "estimated_minutes": 15}}
]
"""

        response = self.client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",
            reasoning_effort="minimal",
            messages=[
                {
                    "role": "system",
                    "content": "Ты помощник по продуктивности, который разбивает задачи на выполнимые шаги. Всегда отвечай только валидным JSON на русском языке.",
                },
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=1000,
        )

        content = response.choices[0].message.content.strip()

        # Parse JSON response
        # Handle potential markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        steps = json.loads(content)

        # Validate and format
        result = []
        for i, step in enumerate(steps[:max_steps]):
            result.append(
                {
                    "title": str(step.get("title", f"Step {i+1}"))[:500],
                    "estimated_minutes": max(
                        min_minutes,
                        min(
                            max_minutes, int(step.get("estimated_minutes", min_minutes))
                        ),
                    ),
                    "order": i + 1,
                }
            )

        return result

    def _simple_decompose(
        self, task_title: str, task_description: str | None, strategy_config: dict
    ) -> list[dict[str, Any]]:
        """Simple rule-based decomposition as fallback."""
        min_minutes, max_minutes = strategy_config["step_range"]
        avg_minutes = (min_minutes + max_minutes) // 2

        # Generic steps based on common task patterns
        generic_steps = [
            f"Изучить и понять: {task_title}",
            "Собрать необходимые ресурсы и информацию",
            "Начать работу над основной частью",
            "Продолжить работу над оставшимся",
            "Проверить и завершить",
        ]

        max_steps = strategy_config["max_steps"]
        steps = generic_steps[:max_steps]

        return [
            {"title": step, "estimated_minutes": avg_minutes, "order": i + 1}
            for i, step in enumerate(steps)
        ]

    def get_strategy_message(self, strategy: str) -> str:
        """Get user-friendly message about the decomposition strategy."""
        messages = {
            "micro": "Задача разбита на очень маленькие шаги для твоего текущего уровня энергии. Делай перерывы чаще!",
            "gentle": "Задача разбита на выполнимые шаги с мягким темпом.",
            "careful": "Задача разбита на средние шаги. Не забывай делать перерывы!",
            "standard": "Задача разбита на стандартные шаги продуктивности.",
        }
        return messages.get(strategy, messages["standard"])
