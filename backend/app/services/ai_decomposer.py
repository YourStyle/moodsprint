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

        prompt = f"""Break down this task into small, actionable steps.

Task: {task_title}
{f'Description: {task_description}' if task_description else ''}

Requirements:
- Create {max_steps-2} to {max_steps} concrete steps
- Each step should take {min_minutes}-{max_minutes} minutes
- Steps should be specific and actionable (start with a verb)
- Steps should be achievable in one sitting
- Order steps logically

Return ONLY a JSON array with objects containing:
- "title": step description (string, max 100 chars)
- "estimated_minutes": time estimate (integer between {min_minutes} and {max_minutes})

Example format:
[
  {{"title": "Open project and review requirements", "estimated_minutes": 10}},
  {{"title": "Create basic file structure", "estimated_minutes": 15}}
]
"""

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a productivity assistant that breaks down tasks into manageable steps. Always respond with valid JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=500,
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
            f"Review and understand: {task_title}",
            "Gather necessary resources and information",
            "Start working on the main part",
            "Continue with remaining work",
            "Review and finalize",
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
            "micro": "Task broken into very small steps for your current energy level. Take breaks often!",
            "gentle": "Task broken into manageable steps with gentle pacing.",
            "careful": "Task broken into medium steps. Remember to take breaks!",
            "standard": "Task broken into standard productivity steps.",
        }
        return messages.get(strategy, messages["standard"])
