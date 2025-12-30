"""GPT-based user profile analyzer for onboarding."""

import json
from typing import Any

from flask import current_app

from app.services.openai_client import get_openai_client


class ProfileAnalyzer:
    """Service for analyzing user responses and creating productivity profile."""

    def __init__(self):
        self.client = get_openai_client()

    def analyze_onboarding(self, responses: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze user's onboarding responses and create a productivity profile.

        Expected responses:
        - productive_time: str (morning/afternoon/evening/night)
        - favorite_tasks: list[str]
        - challenges: list[str]
        - work_description: str (free text about their work habits)
        - goals: str (what they want to achieve)
        """
        if self.client:
            try:
                return self._gpt_analyze(responses)
            except Exception as e:
                current_app.logger.error(f"GPT analysis failed: {e}")

        # Fallback to rule-based analysis
        return self._rule_based_analyze(responses)

    def _gpt_analyze(self, responses: dict[str, Any]) -> dict[str, Any]:
        """Use GPT to analyze responses."""
        prompt = f"""Analyze this user's productivity profile based on their onboarding responses.

User responses:
- Most productive time: {responses.get('productive_time', 'not specified')}
- Favorite types of tasks: {', '.join(responses.get('favorite_tasks', []))}
- Main challenges: {', '.join(responses.get('challenges', []))}
- Work description: {responses.get('work_description', 'not provided')}
- Productivity goals: {responses.get('goals', 'not specified')}

Based on this information, provide a JSON response with:
{{
    "productivity_type": "morning_bird" | "afternoon_peak" | "night_owl" | "steady_pace",
    "preferred_time": "morning" | "afternoon" | "evening" | "night",
    "work_style": "deep_focus" | "sprinter" | "pomodoro" | "flexible",
    "favorite_task_types": ["creative", "analytical", "communication", "planning", "execution"],
    "main_challenges": ["procrastination", "focus", "overwhelm", "motivation", "planning"],
    "recommended_session_duration": 15 | 25 | 45,
    "personalized_tips": ["tip1", "tip2", "tip3"],
    "motivation_style": "gentle" | "encouraging" | "challenging"
}}

Return ONLY valid JSON, no other text.
"""

        current_app.logger.info("AI analyzing user profile from onboarding")
        response = self.client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a productivity coach analyzing user profiles. "
                        "Always respond with valid JSON only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=500,
        )
        current_app.logger.info(
            f"AI profile analysis result: {response.choices[0].message.content}"
        )

        content = response.choices[0].message.content.strip()

        # Parse JSON
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        result = json.loads(content)

        # Add raw GPT response
        result["gpt_raw"] = content

        return result

    def _rule_based_analyze(self, responses: dict[str, Any]) -> dict[str, Any]:
        """Rule-based fallback analysis."""
        productive_time = responses.get("productive_time", "morning")
        challenges = responses.get("challenges", [])

        # Determine productivity type
        time_to_type = {
            "morning": "morning_bird",
            "afternoon": "afternoon_peak",
            "evening": "night_owl",
            "night": "night_owl",
        }
        productivity_type = time_to_type.get(productive_time, "steady_pace")

        # Determine work style based on challenges
        if "focus" in challenges:
            work_style = "pomodoro"
            session_duration = 25
        elif "overwhelm" in challenges:
            work_style = "sprinter"
            session_duration = 15
        else:
            work_style = "flexible"
            session_duration = 25

        return {
            "productivity_type": productivity_type,
            "preferred_time": productive_time,
            "work_style": work_style,
            "favorite_task_types": responses.get("favorite_tasks", []),
            "main_challenges": challenges,
            "recommended_session_duration": session_duration,
            "personalized_tips": [
                "Начни с самой простой задачи, чтобы набрать темп",
                "Делай перерывы каждые 25-30 минут",
                "Отмечай маленькие победы по ходу дела",
            ],
            "motivation_style": "gentle",
        }

    def get_personalized_message(self, profile: dict[str, Any]) -> str:
        """Generate a personalized welcome message based on profile."""
        productivity_type = profile.get("productivity_type", "steady_pace")
        # work_style can be used for more personalized messages in the future
        _ = profile.get("work_style", "flexible")

        messages = {
            "morning_bird": "Кто рано встаёт, тому бог даёт! Используй утро по максимуму.",
            "afternoon_peak": "Впереди самые продуктивные часы! Планируй на пике энергии.",
            "night_owl": "Режим совы активирован! Тихие часы — твоя сила.",
            "steady_pace": "Стабильность — залог успеха! Строим устойчивые привычки.",
        }

        return messages.get(productivity_type, "Сделаем этот день продуктивным!")
