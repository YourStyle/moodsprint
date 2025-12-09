"""AI-powered priority advisor service."""

import json
from typing import Any

from flask import current_app

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class PriorityAdvisor:
    """Service for AI-powered priority recommendations."""

    def __init__(self):
        self.client = None
        if OPENAI_AVAILABLE:
            api_key = current_app.config.get("OPENAI_API_KEY")
            if api_key:
                self.client = OpenAI(api_key=api_key)

    def should_increase_priority(
        self,
        task_title: str,
        task_description: str | None,
        current_priority: str,
        postponed_count: int,
    ) -> dict[str, Any]:
        """
        Determine if task priority should be increased.

        Returns dict with:
        - should_increase: bool
        - reason: str (explanation in Russian)
        - new_priority: str (if should_increase is True)
        """
        # Already at highest priority
        if current_priority == "high":
            return {
                "should_increase": False,
                "reason": "Задача уже имеет высокий приоритет",
                "new_priority": "high",
            }

        # Try AI advisor first
        if self.client:
            try:
                return self._ai_advise(
                    task_title, task_description, current_priority, postponed_count
                )
            except Exception as e:
                current_app.logger.error(f"AI priority advisor failed: {e}")

        # Fallback to simple rules
        return self._rule_based_advise(current_priority, postponed_count)

    def _ai_advise(
        self,
        task_title: str,
        task_description: str | None,
        current_priority: str,
        postponed_count: int,
    ) -> dict[str, Any]:
        """Use OpenAI to advise on priority."""
        priority_ru = {
            "low": "низкий",
            "medium": "средний",
            "high": "высокий",
        }

        prompt = f"""Определи, нужно ли повысить приоритет этой задачи.

Задача: {task_title}
{f'Описание: {task_description}' if task_description else ''}
Текущий приоритет: {priority_ru.get(current_priority, current_priority)}
Количество переносов: {postponed_count} дней

Критерии для повышения:
- Задача важная и её откладывание может привести к проблемам
- Задача блокирует другие важные дела
- Многократный перенос указывает на избегание важной задачи
- Задача связана с дедлайнами или обязательствами

НЕ повышай приоритет если:
- Это задача низкой важности (хобби, необязательное)
- Откладывание не влечёт негативных последствий
- Задача может подождать без проблем

Верни ТОЛЬКО JSON:
{{"should_increase": true/false, "reason": "краткое объяснение на русском"}}
"""

        current_app.logger.info(f"AI advising priority for task: {task_title}")
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Ты помощник по продуктивности. Отвечай только валидным JSON на русском.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=200,
        )
        current_app.logger.info(
            f"AI priority advice result: {response.choices[0].message.content}"
        )

        content = response.choices[0].message.content.strip()

        # Handle markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        result = json.loads(content)

        should_increase = result.get("should_increase", False)
        reason = result.get("reason", "")

        # Determine new priority
        new_priority = current_priority
        if should_increase:
            if current_priority == "low":
                new_priority = "medium"
            elif current_priority == "medium":
                new_priority = "high"

        return {
            "should_increase": should_increase,
            "reason": reason,
            "new_priority": new_priority,
        }

    def _rule_based_advise(
        self, current_priority: str, postponed_count: int
    ) -> dict[str, Any]:
        """Fallback rule-based priority advice."""
        # Simple rule: increase priority after 3+ postponements
        should_increase = postponed_count >= 3

        if not should_increase:
            return {
                "should_increase": False,
                "reason": f"Задача перенесена {postponed_count} раз(а), пока не требует повышения приоритета",
                "new_priority": current_priority,
            }

        # Determine new priority
        if current_priority == "low":
            new_priority = "medium"
            reason = f"Задача переносилась {postponed_count} раз(а). Повышен приоритет с низкого до среднего."
        elif current_priority == "medium":
            new_priority = "high"
            reason = f"Задача переносилась {postponed_count} раз(а). Повышен приоритет до высокого."
        else:
            new_priority = "high"
            reason = "Задача уже имеет высокий приоритет."
            should_increase = False

        return {
            "should_increase": should_increase,
            "reason": reason,
            "new_priority": new_priority,
        }
