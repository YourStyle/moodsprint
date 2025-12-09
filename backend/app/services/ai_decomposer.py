"""AI-powered task decomposition service."""

import json
from typing import Any

from flask import current_app

from app.services.openai_client import get_openai_client


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
        self.client = get_openai_client()

    # Task type context for better decomposition
    TASK_TYPE_CONTEXT = {
        "creative": {
            "focus": "творческий процесс и вдохновение",
            "steps_style": "этапы должны чередовать генерацию идей и их реализацию",
            "examples": "набросок идей, создание черновика, доработка деталей",
        },
        "analytical": {
            "focus": "анализ данных и систематизация",
            "steps_style": "этапы должны идти от сбора данных к выводам",
            "examples": "сбор информации, анализ, формирование выводов, оформление",
        },
        "communication": {
            "focus": "подготовка и проведение коммуникации",
            "steps_style": "этапы должны включать подготовку, основную часть и follow-up",
            "examples": "подготовка тезисов, проведение встречи/звонка, фиксация договорённостей",
        },
        "physical": {
            "focus": "физическая активность с разминкой и заминкой",
            "steps_style": (
                "этапы должны включать подготовку тела и увеличение нагрузки"
            ),
            "examples": "разминка, основная часть, заминка, отдых",
        },
        "learning": {
            "focus": "усвоение нового материала",
            "steps_style": "этапы должны чередовать изучение и практику",
            "examples": "чтение/просмотр, конспектирование, практика, повторение",
        },
        "planning": {
            "focus": "организация и структурирование",
            "steps_style": "этапы должны идти от анализа к конкретному плану",
            "examples": "сбор информации, приоритизация, составление плана, назначение сроков",
        },
        "coding": {
            "focus": "разработка и тестирование кода",
            "steps_style": "этапы должны следовать циклу разработки",
            "examples": "анализ требований, написание кода, тестирование, рефакторинг",
        },
        "writing": {
            "focus": "создание текстового контента",
            "steps_style": "этапы должны идти от структуры к финальной версии",
            "examples": "составление плана, написание черновика, редактирование, финализация",
        },
    }

    def decompose_task(
        self,
        task_title: str,
        task_description: str | None,
        strategy: str,
        task_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Decompose a task into subtasks based on strategy and task type.

        Returns list of subtask dicts with:
        - title: str
        - estimated_minutes: int
        - order: int
        """
        strategy_config = self.STRATEGIES.get(strategy, self.STRATEGIES["standard"])
        type_context = self.TASK_TYPE_CONTEXT.get(task_type) if task_type else None

        # Try AI decomposition first
        if self.client:
            try:
                return self._ai_decompose(
                    task_title, task_description, strategy_config, type_context
                )
            except Exception as e:
                current_app.logger.error(f"AI decomposition failed: {e}")

        # Fallback to simple decomposition
        return self._simple_decompose(
            task_title, task_description, strategy_config, task_type
        )

    def _ai_decompose(
        self,
        task_title: str,
        task_description: str | None,
        strategy_config: dict,
        type_context: dict | None = None,
    ) -> list[dict[str, Any]]:
        """Use OpenAI to decompose task."""
        min_minutes, max_minutes = strategy_config["step_range"]
        max_steps = strategy_config["max_steps"]

        # Build context-aware prompt
        type_instructions = ""
        if type_context:
            type_instructions = f"""
Контекст типа задачи:
- Фокус: {type_context['focus']}
- Стиль шагов: {type_context['steps_style']}
- Примеры шагов: {type_context['examples']}

"""

        prompt = f"""Разбей эту задачу на конкретные, полезные шаги.

Задача: {task_title}
{f'Описание: {task_description}' if task_description else ''}
{type_instructions}
ВАЖНО - Будь креативным помощником:
- Если задача про путешествие/прогулку — предложи конкретные места, достопримечательности, маршруты
- Если задача про обучение — предложи конкретные ресурсы, темы, упражнения
- Если задача про покупки — предложи конкретный список или магазины
- Если задача про готовку — предложи рецепт или ингредиенты
- Используй свои знания чтобы ОБОГАТИТЬ задачу полезной информацией

Требования к шагам:
- Создай от {max_steps - 2} до {max_steps} шагов
- Каждый шаг {min_minutes}-{max_minutes} минут
- Шаги должны быть КОНКРЕТНЫМИ и ПОЛЕЗНЫМИ (не "подготовиться", а что именно сделать)
- НЕ добавляй разминку/заминку если это не спортивная тренировка
- Начинай каждый шаг с глагола
- Добавляй реальные названия мест, ресурсов, инструментов где это уместно

Верни ТОЛЬКО JSON массив:
[
  {{"title": "описание шага", "estimated_minutes": число}}
]
"""

        current_app.logger.info(f"AI decomposing task: {task_title}")
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты умный помощник-планировщик. Разбиваешь задачи на шаги, "
                        "обогащая их своими знаниями: предлагаешь конкретные места, "
                        "ресурсы, идеи. Отвечай только валидным JSON на русском."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=1000,
        )
        current_app.logger.info(
            f"AI decomposition result: {response.choices[0].message.content}"
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

    # Type-specific fallback steps
    FALLBACK_STEPS = {
        "creative": [
            "Собрать референсы и вдохновение",
            "Сделать наброски идей",
            "Выбрать лучшую идею и развить",
            "Создать черновую версию",
            "Доработать детали и финализировать",
        ],
        "analytical": [
            "Собрать исходные данные",
            "Систематизировать информацию",
            "Провести анализ",
            "Сформулировать выводы",
            "Оформить результаты",
        ],
        "communication": [
            "Подготовить тезисы и материалы",
            "Провести встречу/звонок",
            "Зафиксировать договорённости",
            "Отправить follow-up",
        ],
        "physical": [
            "Подготовиться и размяться",
            "Выполнить основную часть",
            "Сделать заминку",
            "Отдохнуть и восстановиться",
        ],
        "learning": [
            "Изучить теоретический материал",
            "Сделать конспект ключевых моментов",
            "Попрактиковаться на примерах",
            "Повторить и закрепить",
        ],
        "planning": [
            "Собрать всю информацию",
            "Определить приоритеты",
            "Составить план действий",
            "Назначить сроки и ответственных",
        ],
        "coding": [
            "Изучить требования и контекст",
            "Написать код",
            "Протестировать решение",
            "Сделать код-ревью и рефакторинг",
        ],
        "writing": [
            "Составить план текста",
            "Написать черновик",
            "Отредактировать и улучшить",
            "Финальная проверка",
        ],
    }

    def _simple_decompose(
        self,
        task_title: str,
        task_description: str | None,
        strategy_config: dict,
        task_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Simple rule-based decomposition as fallback."""
        min_minutes, max_minutes = strategy_config["step_range"]
        avg_minutes = (min_minutes + max_minutes) // 2
        max_steps = strategy_config["max_steps"]

        # Use type-specific steps if available
        if task_type and task_type in self.FALLBACK_STEPS:
            steps = self.FALLBACK_STEPS[task_type][:max_steps]
        else:
            # Generic steps as last resort
            steps = [
                f"Изучить и понять: {task_title}",
                "Собрать необходимые ресурсы",
                "Выполнить основную работу",
                "Проверить результат",
                "Завершить и закрыть задачу",
            ][:max_steps]

        return [
            {"title": step, "estimated_minutes": avg_minutes, "order": i + 1}
            for i, step in enumerate(steps)
        ]

    def get_strategy_message(self, strategy: str) -> str:
        """Get user-friendly message about the decomposition strategy."""
        messages = {
            "micro": (
                "Задача разбита на очень маленькие шаги для твоего текущего "
                "уровня энергии. Делай перерывы чаще!"
            ),
            "gentle": "Задача разбита на выполнимые шаги с мягким темпом.",
            "careful": "Задача разбита на средние шаги. Не забывай перерывы!",
            "standard": "Задача разбита на стандартные шаги продуктивности.",
        }
        return messages.get(strategy, messages["standard"])
