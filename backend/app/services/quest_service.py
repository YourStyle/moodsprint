"""Quest generation and management service."""

import random
from datetime import date, datetime

from flask import current_app

from app import db
from app.models import DailyQuest, User
from app.models.character import GENRE_THEMES
from app.models.quest import QUEST_NAME_PROMPTS, QUEST_TEMPLATES
from app.models.user_profile import UserProfile
from app.services.openai_client import get_openai_client


class QuestService:
    """Service for generating and managing daily quests."""

    def __init__(self):
        self.client = get_openai_client()

    def generate_themed_quest_name(
        self, quest_type: str, genre: str, description: str
    ) -> tuple[str, str]:
        """
        Generate a themed quest name using AI.

        Returns (title, themed_description)
        """
        genre_info = GENRE_THEMES.get(genre, GENRE_THEMES["fantasy"])
        quest_hint = QUEST_NAME_PROMPTS.get(genre, QUEST_NAME_PROMPTS["fantasy"]).get(
            quest_type, "квест"
        )

        if self.client:
            try:
                genre_name = genre_info["name"]
                prompt = f"""Придумай короткое эпическое название для квеста в стиле "{genre_name}".

Тип квеста: {quest_hint}
Что нужно сделать: {description}

Требования:
- Название должно быть коротким (2-5 слов)
- В стиле {genre_info['name']} ({genre_info['description']})
- Можно использовать {', '.join(genre_info['quest_prefix'])} в начале
- Также дай короткое тематическое описание (1 предложение)

Ответь в формате JSON:
{{"title": "Название квеста", "description": "Тематическое описание"}}"""

                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Ты генератор названий для RPG квестов. "
                                "Отвечай только валидным JSON на русском."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_completion_tokens=200,
                )

                import json

                content = response.choices[0].message.content.strip()
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]

                result = json.loads(content)
                return result.get("title", quest_hint), result.get(
                    "description", description
                )

            except Exception as e:
                current_app.logger.error(f"Failed to generate quest name: {e}")

        # Fallback to template-based names
        prefix = random.choice(genre_info["quest_prefix"])
        return f"{prefix}: {quest_hint.title()}", description

    def generate_daily_quests(self, user_id: int) -> list[DailyQuest]:
        """
        Generate daily quests for a user.

        Returns 3 quests per day based on user's genre preference.
        """
        today = date.today()

        # Check if quests already exist for today
        existing = DailyQuest.query.filter_by(user_id=user_id, date=today).all()
        if existing:
            return existing

        # Get user's genre preference
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        genre = profile.favorite_genre if profile else "fantasy"
        if not genre:
            genre = "fantasy"

        # Select 3 random quest types
        quest_types = list(QUEST_TEMPLATES.keys())
        selected_types = random.sample(quest_types, min(3, len(quest_types)))

        quests = []
        for quest_type in selected_types:
            template = QUEST_TEMPLATES[quest_type]

            # Generate themed name
            title, themed_desc = self.generate_themed_quest_name(
                quest_type, genre, template["description"]
            )

            quest = DailyQuest(
                user_id=user_id,
                quest_type=quest_type,
                title=title,
                description=template["description"],
                themed_description=themed_desc,
                target_count=template["target_count"],
                xp_reward=template["xp_reward"],
                stat_points_reward=template["stat_points_reward"],
                date=today,
            )
            db.session.add(quest)
            quests.append(quest)

        db.session.commit()
        return quests

    def get_user_quests(self, user_id: int) -> list[DailyQuest]:
        """Get today's quests for user, generating if needed."""
        today = date.today()
        quests = DailyQuest.query.filter_by(user_id=user_id, date=today).all()

        if not quests:
            quests = self.generate_daily_quests(user_id)

        return quests

    def update_quest_progress(
        self, user_id: int, quest_type: str, increment: int = 1
    ) -> DailyQuest | None:
        """
        Update progress for a specific quest type.

        Called when user completes relevant actions.
        """
        today = date.today()
        quest = DailyQuest.query.filter_by(
            user_id=user_id, quest_type=quest_type, date=today
        ).first()

        if quest and not quest.completed:
            just_completed = quest.increment_progress(increment)
            db.session.commit()

            if just_completed:
                current_app.logger.info(
                    f"Quest {quest_type} completed for user {user_id}"
                )

            return quest

        return None

    def check_task_completion_quests(self, user_id: int, task) -> list[DailyQuest]:
        """
        Check and update quests when a task is completed.

        Returns list of quests that were updated.
        """
        updated_quests = []
        now = datetime.utcnow()
        # Moscow time offset
        moscow_hour = (now.hour + 3) % 24

        # Early bird: task completed before 10:00 Moscow
        if moscow_hour < 10:
            quest = self.update_quest_progress(user_id, "early_bird")
            if quest:
                updated_quests.append(quest)

        # Task before noon
        if moscow_hour < 12:
            quest = self.update_quest_progress(user_id, "task_before_noon")
            if quest:
                updated_quests.append(quest)

        # High priority first (if high priority task)
        if task.priority == "high":
            quest = self.update_quest_progress(user_id, "high_priority_first")
            if quest:
                updated_quests.append(quest)

        return updated_quests

    def check_subtask_completion_quests(self, user_id: int) -> list[DailyQuest]:
        """Check and update quests when a subtask is completed."""
        updated_quests = []

        quest = self.update_quest_progress(user_id, "subtask_warrior")
        if quest:
            updated_quests.append(quest)

        # Check streak_tasks (3 tasks in a row)
        quest = self.update_quest_progress(user_id, "streak_tasks")
        if quest:
            updated_quests.append(quest)

        return updated_quests

    def check_focus_session_quests(self, user_id: int) -> list[DailyQuest]:
        """Check and update quests when a focus session is completed."""
        updated_quests = []

        quest = self.update_quest_progress(user_id, "focus_master")
        if quest:
            updated_quests.append(quest)

        return updated_quests

    def check_mood_quests(self, user_id: int) -> list[DailyQuest]:
        """Check and update quests when mood is logged."""
        updated_quests = []

        quest = self.update_quest_progress(user_id, "mood_tracker")
        if quest:
            updated_quests.append(quest)

        return updated_quests

    def claim_quest_reward(self, user_id: int, quest_id: int) -> dict | None:
        """
        Claim reward for completed quest.

        Returns reward info or None if cannot claim.
        """
        quest = DailyQuest.query.filter_by(id=quest_id, user_id=user_id).first()
        if not quest:
            return None

        reward = quest.claim_reward()
        if not reward:
            return None

        # Apply rewards
        user = User.query.get(user_id)
        if user:
            xp_info = user.add_xp(reward["xp"])
            reward["xp_info"] = xp_info

        # Add stat points to character
        from app.models import CharacterStats

        character = CharacterStats.query.filter_by(user_id=user_id).first()
        if character:
            character.add_stat_points(reward["stat_points"])

        db.session.commit()

        return reward
