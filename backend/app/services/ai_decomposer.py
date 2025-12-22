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
        mood: int | None = None,
        energy: int | None = None,
        existing_subtasks_count: int = 0,
    ) -> dict[str, Any]:
        """
        Decompose a task into subtasks based on strategy, task type, and user state.

        Returns dict with:
        - subtasks: list of subtask dicts (title, estimated_minutes, order)
        - no_new_steps: bool - True if task doesn't need more decomposition
        """
        strategy_config = self.STRATEGIES.get(strategy, self.STRATEGIES["standard"])
        type_context = self.TASK_TYPE_CONTEXT.get(task_type) if task_type else None

        # Try AI decomposition first
        if self.client:
            try:
                return self._ai_decompose(
                    task_title,
                    task_description,
                    strategy_config,
                    type_context,
                    strategy,
                    mood,
                    energy,
                    existing_subtasks_count,
                )
            except Exception as e:
                current_app.logger.error(f"AI decomposition failed: {e}")

        # Fallback to simple decomposition
        subtasks = self._simple_decompose(
            task_title, task_description, strategy_config, task_type
        )
        return {"subtasks": subtasks, "no_new_steps": False}

    # Mood/energy labels for AI context
    MOOD_LABELS_RU = {
        1: "очень плохое",
        2: "плохое",
        3: "нормальное",
        4: "хорошее",
        5: "отличное",
    }
    ENERGY_LABELS_RU = {
        1: "очень низкая (истощён)",
        2: "низкая (устал)",
        3: "нормальная",
        4: "высокая (бодрый)",
        5: "максимальная (на пике)",
    }

    def _ai_decompose(
        self,
        task_title: str,
        task_description: str | None,
        strategy_config: dict,
        type_context: dict | None = None,
        strategy: str | None = None,
        mood: int | None = None,
        energy: int | None = None,
        existing_subtasks_count: int = 0,
    ) -> dict[str, Any]:
        """Use OpenAI to decompose task."""
        min_minutes, max_minutes = strategy_config["step_range"]

        # Build context-aware prompt
        type_instructions = ""
        if type_context:
            type_instructions = f"""
Контекст типа задачи:
- Фокус: {type_context['focus']}
- Стиль шагов: {type_context['steps_style']}
- Примеры шагов: {type_context['examples']}
"""

        # Build user state context
        user_state_instructions = ""
        if mood is not None or energy is not None:
            mood_text = (
                self.MOOD_LABELS_RU.get(mood, "не указано") if mood else "не указано"
            )
            energy_text = (
                self.ENERGY_LABELS_RU.get(energy, "не указана")
                if energy
                else "не указана"
            )
            user_state_instructions = f"""
Состояние пользователя:
- Настроение: {mood_text}
- Энергия: {energy_text}
"""
            if strategy == "micro":
                user_state_instructions += """
ВАЖНО: У пользователя сейчас низкая энергия/плохое настроение!
- Делай шаги ОЧЕНЬ маленькими и простыми (5-15 мин каждый)
- Больше шагов, но каждый легко выполнимый
- Добавь мотивирующие формулировки
- Предложи 6-8 микрошагов
"""
            elif strategy == "gentle":
                user_state_instructions += """
Пользователь не в лучшей форме:
- Шаги должны быть комфортными (10-20 мин)
- Предложи 4-6 шагов умеренной сложности
"""
            elif strategy == "careful":
                user_state_instructions += """
У пользователя мало энергии:
- Шаги средние по размеру (10-20 мин)
- Предложи 4-6 шагов с учётом усталости
"""

        # Add existing subtasks context
        existing_steps_context = ""
        if existing_subtasks_count > 0:
            no_new = '{"no_new_steps": true}'
            existing_steps_context = f"""
ВАЖНО: У задачи уже есть {existing_subtasks_count} шагов!
- Если задача уже достаточно разбита (простая с 2+ шагами, средняя с 4+) — верни {no_new}
- Если можно добавить полезные шаги — предложи их
"""

        prompt = f"""Разбей эту задачу на конкретные, выполнимые шаги.

Задача: {task_title}
{f'Описание: {task_description}' if task_description else ''}
{type_instructions}{user_state_instructions}{existing_steps_context}
КРИТИЧЕСКИ ВАЖНО - Подстрой количество шагов под сложность задачи:
- Очень простая задача (сесть, выпить воды) → 1 шаг ИЛИ no_new_steps если уже разбита
- Простая бытовая задача (постирать вещи, помыть посуду) → 1-2 шага максимум!
- Средняя задача (написать отчёт, убрать квартиру, приготовить ужин) → 3-5 шагов
- Сложная задача (организовать мероприятие, изучить новую тему, большой проект) → 5-8 шагов

Если задача СЛИШКОМ ПРОСТАЯ для разбиения или уже разбита достаточно — верни:
{{"no_new_steps": true, "reason": "Задача слишком простая/уже достаточно разбита"}}

Креативность:
- Если задача про путешествие/прогулку — предложи конкретные места
- Если задача про обучение — предложи ресурсы, темы
- Если задача про покупки — предложи список
- Используй свои знания чтобы ОБОГАТИТЬ задачу, НО НЕ РАЗДУВАЙ простые задачи!

Требования к шагам:
- НЕ РАЗДУВАЙ простые задачи! «Постирать вещи» = максимум «Загрузить и запустить стирку»
- Оценивай время РЕАЛИСТИЧНО: быстрые действия 2-5 мин, средние 10-20 мин, сложные 30-60+ мин
- НЕ делай все шаги одинаковыми по времени — разные шаги занимают разное время!
- Шаги должны быть КОНКРЕТНЫМИ и ПОЛЕЗНЫМИ
- НЕ добавляй разминку/заминку если это не спортивная тренировка
- Начинай каждый шаг с глагола

Верни ТОЛЬКО JSON:
Либо массив шагов: [{{"title": "описание", "estimated_minutes": число}}]
Либо отказ: {{"no_new_steps": true, "reason": "причина"}}
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
        current_app.logger.info(f"AI raw response: {content[:500]}")

        # Parse JSON response
        # Handle potential markdown code blocks
        if "```" in content:
            # Extract content between ``` markers
            parts = content.split("```")
            for part in parts:
                part = part.strip()
                # Skip empty parts
                if not part:
                    continue
                # Remove "json" language identifier if present
                if part.startswith("json"):
                    part = part[4:].strip()
                # Try to find JSON in this part
                if part.startswith("[") or part.startswith("{"):
                    content = part
                    break

        # Clean up any remaining whitespace
        content = content.strip()
        current_app.logger.info(f"AI cleaned content: {content[:500]}")

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            current_app.logger.error(f"JSON parse error: {e}, content: {content[:200]}")
            raise

        # Check if AI returned no_new_steps
        if isinstance(parsed, dict) and parsed.get("no_new_steps"):
            return {
                "subtasks": [],
                "no_new_steps": True,
                "reason": parsed.get("reason", "Задача уже достаточно разбита"),
            }

        # It's a list of steps
        steps = parsed if isinstance(parsed, list) else []

        # Validate and format (allow up to 10 steps for complex tasks)
        result = []
        for i, step in enumerate(steps[:10]):
            if not isinstance(step, dict):
                continue
            title = step.get("title")
            if not title:
                continue
            # Allow realistic time estimates from AI (2-180 min range)
            estimated = int(step.get("estimated_minutes", 15))
            estimated = max(2, min(180, estimated))  # Clamp to reasonable bounds
            result.append(
                {
                    "title": str(title)[:500],
                    "estimated_minutes": estimated,
                    "order": i + 1,
                }
            )

        # If AI returned empty list, fall back to simple decomposition
        if not result:
            current_app.logger.warning(
                "AI returned empty subtasks, falling back to simple decomposition"
            )
            raise ValueError("AI returned empty subtasks list")

        return {"subtasks": result, "no_new_steps": False}

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
