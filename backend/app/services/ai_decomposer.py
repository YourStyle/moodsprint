"""AI-powered task decomposition service."""

import hashlib
import json
import re as _re
import time
from typing import Any

from flask import current_app

from app.services.openai_client import get_openai_client

# Cache key prefix
AI_CACHE_PREFIX = "ai_cache:decompose:"
AI_CACHE_STATS_KEY = "ai_cache:stats"
AI_CACHE_DEFAULT_TTL = 86400  # 24 hours


def _normalize_title(title: str) -> str:
    """Normalize task title for cache key generation."""
    t = title.lower().strip()
    t = _re.sub(r"\s+", " ", t)
    return t


def _make_cache_key(
    title: str, strategy: str, mood: int | None, energy: int | None
) -> str:
    """Create a deterministic cache key from decomposition inputs."""
    normalized = _normalize_title(title)
    raw = f"{normalized}|{strategy}|{mood or 0}|{energy or 0}"
    h = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"{AI_CACHE_PREFIX}{h}"


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
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Decompose a task into subtasks based on strategy, task type, and user state.

        Returns dict with:
        - subtasks: list of subtask dicts (title, estimated_minutes, order)
        - no_new_steps: bool - True if task doesn't need more decomposition
        """
        strategy_config = self.STRATEGIES.get(strategy, self.STRATEGIES["standard"])
        type_context = self.TASK_TYPE_CONTEXT.get(task_type) if task_type else None

        # ── Check Template Library first ──
        if not task_description and existing_subtasks_count == 0:
            template_result = self._match_template(task_title, strategy, mood, energy)
            if template_result is not None:
                current_app.logger.info(f"Template match for: {task_title}")
                return template_result

        # Check Redis cache (skip for tasks with descriptions)
        use_cache = not task_description and existing_subtasks_count == 0
        cache_key = None

        if use_cache:
            cache_key = _make_cache_key(task_title, strategy, mood, energy)
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                current_app.logger.info(f"AI cache HIT for: {task_title}")
                return cached

        # Try AI decomposition first
        if self.client:
            try:
                result = self._ai_decompose(
                    task_title,
                    task_description,
                    strategy_config,
                    type_context,
                    strategy,
                    mood,
                    energy,
                    existing_subtasks_count,
                    user_id=user_id,
                )
                # Store in cache
                if use_cache and cache_key:
                    self._store_in_cache(
                        cache_key, result, task_title, strategy, mood, energy
                    )
                return result
            except Exception as e:
                current_app.logger.error(f"AI decomposition failed: {e}")

        # Fallback to simple decomposition
        subtasks = self._simple_decompose(
            task_title, task_description, strategy_config, task_type
        )
        return {"subtasks": subtasks, "no_new_steps": False}

    def _get_from_cache(self, key: str) -> dict | None:
        """Try to get a cached decomposition result from Redis."""
        try:
            from app.extensions import get_redis_client

            r = get_redis_client()
            data = r.get(key)
            if data:
                entry = json.loads(data)
                # Update hit stats
                r.hincrby(AI_CACHE_STATS_KEY, "hits", 1)
                entry["hits"] = entry.get("hits", 0) + 1
                entry["last_hit_at"] = time.time()
                r.set(key, json.dumps(entry), keepttl=True)
                return entry["result"]
        except Exception as e:
            current_app.logger.warning(f"AI cache read error: {e}")
        return None

    def _store_in_cache(
        self,
        key: str,
        result: dict,
        title: str,
        strategy: str,
        mood: int | None,
        energy: int | None,
    ) -> None:
        """Store a decomposition result in Redis cache."""
        try:
            from app.extensions import get_redis_client

            r = get_redis_client()
            entry = {
                "result": result,
                "title": title,
                "strategy": strategy,
                "mood": mood,
                "energy": energy,
                "created_at": time.time(),
                "hits": 0,
                "last_hit_at": None,
            }
            # Read TTL from Redis config (set via admin), fallback to app config
            config_ttl = r.get("ai_cache:config:ttl")
            ttl = (
                int(config_ttl)
                if config_ttl
                else int(current_app.config.get("AI_CACHE_TTL", AI_CACHE_DEFAULT_TTL))
            )
            r.set(key, json.dumps(entry), ex=ttl)
            r.hincrby(AI_CACHE_STATS_KEY, "misses", 1)
            r.hincrby(AI_CACHE_STATS_KEY, "stored", 1)
        except Exception as e:
            current_app.logger.warning(f"AI cache write error: {e}")

    def _match_template(
        self,
        task_title: str,
        strategy: str,
        mood: int | None,
        energy: int | None,
    ) -> dict | None:
        """Try to match a decomposition template from the database."""
        try:
            from sqlalchemy import text

            from app import db

            normalized = _normalize_title(task_title)

            # Find matching templates: title pattern match + strategy + mood/energy range
            rows = db.session.execute(
                text(
                    """
                SELECT id, subtasks, no_new_steps
                FROM decomposition_templates
                WHERE is_active = true
                  AND strategy = :strategy
                  AND LOWER(:title) LIKE LOWER(title_pattern)
                  AND (mood_min IS NULL OR :mood >= mood_min)
                  AND (mood_max IS NULL OR :mood <= mood_max)
                  AND (energy_min IS NULL OR :energy >= energy_min)
                  AND (energy_max IS NULL OR :energy <= energy_max)
                ORDER BY LENGTH(title_pattern) DESC
                LIMIT 1
            """
                ),
                {
                    "title": normalized,
                    "strategy": strategy,
                    "mood": mood or 3,
                    "energy": energy or 3,
                },
            ).fetchone()

            if rows:
                template_id, subtasks_data, no_new_steps = rows
                # Increment usage count
                db.session.execute(
                    text(
                        "UPDATE decomposition_templates "
                        "SET usage_count = usage_count + 1 WHERE id = :id"
                    ),
                    {"id": template_id},
                )
                db.session.commit()

                if no_new_steps:
                    return {"subtasks": [], "no_new_steps": True}

                return {"subtasks": subtasks_data, "no_new_steps": False}
        except Exception as e:
            current_app.logger.warning(f"Template match error: {e}")
        return None

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
        user_id: int | None = None,
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

        # Check if description contains explicit steps/list
        description_has_steps = False
        if task_description:
            # Check for numbered lists or bullet points
            import re

            has_numbers = bool(
                re.search(r"^\s*\d+[\.\)]\s", task_description, re.MULTILINE)
            )
            has_bullets = bool(
                re.search(r"^\s*[-•*]\s", task_description, re.MULTILINE)
            )
            has_newlines = (
                "\n" in task_description and len(task_description.split("\n")) >= 2
            )
            description_has_steps = has_numbers or has_bullets or has_newlines

        description_instruction = ""
        if description_has_steps:
            description_instruction = """
ВАЖНО: В описании задачи УЖЕ ЕСТЬ готовый список пунктов!
АНАЛИЗИРУЙ ТИП СПИСКА:

1. Если это СПИСОК ПОКУПОК (продукты, товары):
   - Сгруппируй по категориям или магазинам (если можешь определить)
   - Шаги типа: "Купить овощи: морковь, лук, картофель" или "Купить молочные продукты"
   - НЕ создавай отдельный шаг для каждого товара!

2. Если это СПИСОК ЗАДАЧ/ДЕЙСТВИЙ:
   - Каждый пункт = отдельный шаг
   - Сохраняй формулировки пользователя

3. Если это ПЛАН/ИНСТРУКЦИЯ:
   - Преврати пункты в последовательные шаги
   - Добавь оценку времени

ВСЕГДА используй формулировки пользователя как основу!
"""

        prompt = f"""Разбей эту задачу на конкретные, выполнимые шаги.

Задача: {task_title}
{f'Описание: {task_description}' if task_description else '(без описания)'}
{description_instruction}{type_instructions}{user_state_instructions}{existing_steps_context}
КРИТИЧЕСКИ ВАЖНО - НЕ РАЗБИВАЙ простые задачи:
- Если НЕТ описания И задача простая → ВСЕГДА возвращай no_new_steps!
- Примеры задач БЕЗ разбивки: погулять с собакой, выпить воды, позвонить маме,
  сходить в магазин, помыть посуду, постирать вещи, полить цветы, вынести мусор
- Эти задачи понятны сами по себе и НЕ требуют пошаговой инструкции!

Когда НУЖНО разбивать:
- Есть описание со СПИСКОМ товаров/пунктов → разбить на шаги по каждому пункту
- Сложная задача (проект, презентация, мероприятие) → 3-8 шагов
- Задача с несколькими этапами в названии → разбить по этапам

Если задача ПРОСТАЯ (особенно без описания) — верни:
{{"no_new_steps": true, "reason": "Задача понятна и не требует разбивки"}}

ВАЖНО: Если в описании есть СПИСОК (товары, пункты через запятую) —
тогда разбивай на шаги по каждому пункту!

КОНТЕКСТНОЕ ПОНИМАНИЕ:
- Если в описании СПИСОК ТОВАРОВ → создай ОТДЕЛЬНЫЙ шаг для КАЖДОГО товара!
- Если в описании перечислены конкретные пункты → создай шаг для КАЖДОГО пункта
- Если задача про обучение с конкретной темой → предложи ресурсы
- БЕЗ описания = НЕ выдумывай шаги, верни no_new_steps!

ПРИМЕРЫ:
✅ РАЗБИВАТЬ:
- "Купить лекарства" + "аспирин, бинт, зелёнка" → 3 шага по товару
- "Подготовить презентацию" (сложная) → 4-5 шагов

❌ НЕ РАЗБИВАТЬ (вернуть no_new_steps):
- "Погулять с собакой" (без описания) → no_new_steps
- "Помыть посуду" (без описания) → no_new_steps
- "Позвонить маме" (без описания) → no_new_steps
- "Сходить в магазин" (без списка) → no_new_steps

Требования:
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
        from app.utils.ai_tracker import tracked_openai_call

        response = tracked_openai_call(
            self.client,
            user_id=user_id,
            endpoint="decompose_task",
            model="gpt-5-mini",
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
            max_completion_tokens=1000,
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

        # It's a list of steps (AI sometimes wraps in {"steps": [...]})
        if isinstance(parsed, list):
            steps = parsed
        elif isinstance(parsed, dict) and "steps" in parsed:
            steps = parsed["steps"]
        else:
            steps = []

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
