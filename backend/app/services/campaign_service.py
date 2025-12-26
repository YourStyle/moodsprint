"""Campaign/Story mode service."""

import logging
from datetime import datetime
from typing import Any

from app import db
from app.models import User
from app.models.campaign import (
    CampaignChapter,
    CampaignLevel,
    CampaignLevelCompletion,
    CampaignReward,
    UserCampaignProgress,
)
from app.models.card import CardRarity

logger = logging.getLogger(__name__)


class CampaignService:
    """Service for managing campaign/story mode."""

    def get_user_progress(self, user_id: int) -> UserCampaignProgress:
        """Get or create user's campaign progress."""
        progress = UserCampaignProgress.query.filter_by(user_id=user_id).first()
        if not progress:
            progress = UserCampaignProgress(user_id=user_id)
            db.session.add(progress)
            db.session.commit()
        return progress

    def get_campaign_overview(self, user_id: int) -> dict[str, Any]:
        """Get campaign overview for user."""
        progress = self.get_user_progress(user_id)
        chapters = (
            CampaignChapter.query.filter_by(is_active=True)
            .order_by(CampaignChapter.number)
            .all()
        )

        chapters_data = []
        for chapter in chapters:
            chapter_data = chapter.to_dict()

            # Check if unlocked
            is_unlocked = chapter.number <= progress.current_chapter
            is_completed = chapter.id in (progress.chapters_completed or [])

            # Get level progress for this chapter
            level_completions = (
                CampaignLevelCompletion.query.filter_by(progress_id=progress.id)
                .join(CampaignLevel)
                .filter(CampaignLevel.chapter_id == chapter.id)
                .all()
            )

            stars_earned = sum(c.stars_earned for c in level_completions)
            levels_completed = len(level_completions)
            total_levels = chapter.levels.count()

            chapter_data.update(
                {
                    "is_unlocked": is_unlocked,
                    "is_completed": is_completed,
                    "levels_completed": levels_completed,
                    "total_levels": total_levels,
                    "stars_earned": stars_earned,
                    "max_stars": total_levels * 3,
                }
            )
            chapters_data.append(chapter_data)

        return {
            "progress": progress.to_dict(),
            "chapters": chapters_data,
        }

    def get_chapter_details(self, user_id: int, chapter_number: int) -> dict[str, Any]:
        """Get detailed info about a chapter."""
        progress = self.get_user_progress(user_id)
        chapter = CampaignChapter.query.filter_by(number=chapter_number).first()

        if not chapter:
            return {"error": "chapter_not_found"}

        # Check if unlocked
        if chapter_number > progress.current_chapter:
            return {"error": "chapter_locked"}

        levels = chapter.levels.order_by(CampaignLevel.number).all()
        levels_data = []

        for level in levels:
            level_data = level.to_dict()

            # Get completion info
            completion = CampaignLevelCompletion.query.filter_by(
                progress_id=progress.id, level_id=level.id
            ).first()

            is_unlocked = (
                level.number == 1
                or CampaignLevelCompletion.query.filter_by(progress_id=progress.id)
                .join(CampaignLevel)
                .filter(
                    CampaignLevel.chapter_id == chapter.id,
                    CampaignLevel.number == level.number - 1,
                )
                .first()
                is not None
            )

            level_data.update(
                {
                    "is_unlocked": is_unlocked,
                    "is_completed": completion is not None,
                    "stars_earned": completion.stars_earned if completion else 0,
                    "best_rounds": completion.best_rounds if completion else None,
                    "attempts": completion.attempts if completion else 0,
                }
            )
            levels_data.append(level_data)

        # Get chapter rewards
        rewards = CampaignReward.query.filter_by(chapter_id=chapter.id).all()

        return {
            "chapter": chapter.to_dict(),
            "levels": levels_data,
            "rewards": [r.to_dict() for r in rewards],
            "story_intro": chapter.story_intro,
        }

    def start_level(self, user_id: int, level_id: int) -> dict[str, Any]:
        """Start a campaign level (initiates battle)."""
        level = CampaignLevel.query.get(level_id)
        if not level:
            return {"error": "level_not_found"}

        progress = self.get_user_progress(user_id)

        # Check if chapter is unlocked
        if level.chapter.number > progress.current_chapter:
            return {"error": "chapter_locked"}

        # Check if previous level is completed (except first level)
        if level.number > 1:
            prev_completion = (
                CampaignLevelCompletion.query.filter_by(progress_id=progress.id)
                .join(CampaignLevel)
                .filter(
                    CampaignLevel.chapter_id == level.chapter_id,
                    CampaignLevel.number == level.number - 1,
                )
                .first()
            )

            if not prev_completion:
                return {"error": "previous_level_not_completed"}

        # Return level data for battle initiation
        return {
            "success": True,
            "level": level.to_dict(),
            "dialogue_before": level.dialogue_before,
            "monster_id": level.monster_id,
            "difficulty_multiplier": level.difficulty_multiplier,
        }

    def complete_level(
        self,
        user_id: int,
        level_id: int,
        won: bool,
        rounds: int,
        hp_remaining: int,
        cards_lost: int,
    ) -> dict[str, Any]:
        """Complete a campaign level after battle."""
        level = CampaignLevel.query.get(level_id)
        if not level:
            return {"error": "level_not_found"}

        progress = self.get_user_progress(user_id)

        if not won:
            return {
                "success": True,
                "won": False,
                "message": "Попробуй ещё раз!",
            }

        # Calculate stars based on performance
        stars = self._calculate_stars(rounds, hp_remaining, cards_lost)

        # Get or create completion record
        completion = CampaignLevelCompletion.query.filter_by(
            progress_id=progress.id, level_id=level_id
        ).first()

        is_new_completion = completion is None

        if completion:
            # Update if better
            completion.attempts += 1
            if stars > completion.stars_earned:
                completion.stars_earned = stars
            if completion.best_rounds is None or rounds < completion.best_rounds:
                completion.best_rounds = rounds
            if (
                completion.best_hp_remaining is None
                or hp_remaining > completion.best_hp_remaining
            ):
                completion.best_hp_remaining = hp_remaining
            completion.last_completed_at = datetime.utcnow()
        else:
            completion = CampaignLevelCompletion(
                progress_id=progress.id,
                level_id=level_id,
                stars_earned=stars,
                best_rounds=rounds,
                best_hp_remaining=hp_remaining,
            )
            db.session.add(completion)

        # Update progress
        progress.total_stars_earned += stars if is_new_completion else 0

        # Check if this was a boss level
        chapter_completed = False
        rewards = []
        if level.is_boss:
            progress.bosses_defeated += 1

            # Mark chapter as completed
            if level.chapter.id not in (progress.chapters_completed or []):
                if not progress.chapters_completed:
                    progress.chapters_completed = []
                progress.chapters_completed.append(level.chapter.id)
                chapter_completed = True

                # Unlock next chapter
                next_chapter = CampaignChapter.query.filter_by(
                    number=level.chapter.number + 1
                ).first()
                if next_chapter:
                    progress.current_chapter = next_chapter.number
                    progress.current_level = 1

                # Give chapter rewards
                rewards = self._give_chapter_rewards(user_id, level.chapter)

        # Award XP
        user = User.query.get(user_id)
        xp_earned = level.xp_reward * stars
        if user:
            user.add_xp(xp_earned)

        db.session.commit()

        result = {
            "success": True,
            "won": True,
            "stars_earned": stars,
            "xp_earned": xp_earned,
            "is_new_completion": is_new_completion,
            "chapter_completed": chapter_completed,
            "rewards": rewards,
        }

        if level.dialogue_after:
            result["dialogue_after"] = level.dialogue_after

        if chapter_completed and level.chapter.story_outro:
            result["story_outro"] = level.chapter.story_outro

        return result

    def _calculate_stars(self, rounds: int, hp_remaining: int, cards_lost: int) -> int:
        """Calculate stars earned based on performance."""
        # 3 stars: quick victory, no cards lost
        # 2 stars: decent victory
        # 1 star: barely won

        stars = 1  # Minimum for winning

        # Bonus for quick victory
        if rounds <= 5:
            stars += 1
        elif rounds <= 10:
            stars += 0.5

        # Bonus for no cards lost
        if cards_lost == 0:
            stars += 1
        elif cards_lost == 1:
            stars += 0.5

        return min(3, int(stars))

    def _give_chapter_rewards(
        self, user_id: int, chapter: CampaignChapter
    ) -> list[dict]:
        """Give rewards for completing a chapter."""
        from app.services.card_service import CardService

        rewards = CampaignReward.query.filter_by(chapter_id=chapter.id).all()
        given_rewards = []

        card_service = CardService()

        for reward in rewards:
            reward_data = reward.reward_data

            if reward.reward_type == "card":
                rarity_str = reward_data.get("rarity", "rare")
                try:
                    rarity = CardRarity(rarity_str)
                except ValueError:
                    rarity = CardRarity.RARE

                card = card_service.generate_card_for_task(
                    user_id=user_id,
                    task_id=None,
                    task_title=f"Награда: Глава {chapter.number}",
                    forced_rarity=rarity,
                )
                if card:
                    given_rewards.append(
                        {
                            "type": "card",
                            "card": card.to_dict(),
                            "name": reward.name or f"Карта {rarity_str}",
                        }
                    )

            elif reward.reward_type == "xp":
                amount = reward_data.get("amount", 500)
                user = User.query.get(user_id)
                if user:
                    user.add_xp(amount)
                given_rewards.append(
                    {
                        "type": "xp",
                        "amount": amount,
                        "name": reward.name or f"{amount} XP",
                    }
                )

            elif reward.reward_type == "title":
                # Titles can be stored in user profile
                given_rewards.append(
                    {
                        "type": "title",
                        "title": reward_data.get("title"),
                        "name": reward.name,
                    }
                )

        return given_rewards

    def get_level_battle_config(self, level_id: int) -> dict[str, Any]:
        """Get battle configuration for a campaign level."""
        level = CampaignLevel.query.get(level_id)
        if not level:
            return {"error": "level_not_found"}

        monster = level.monster
        if not monster:
            return {"error": "monster_not_configured"}

        # Scale monster stats based on difficulty
        scale = level.difficulty_multiplier

        return {
            "monster_id": monster.id,
            "monster_name": monster.name,
            "is_boss": level.is_boss,
            "scaled_stats": {
                "hp": int(monster.base_hp * scale),
                "attack": int(monster.base_attack * scale),
                "defense": int(monster.base_defense * scale),
                "xp_reward": int(monster.base_xp_reward * scale),
            },
        }


def seed_campaign_data():
    """Seed initial campaign chapters and levels."""
    # Check if already seeded
    if CampaignChapter.query.first():
        logger.info("Campaign data already seeded")
        return

    chapters_data = [
        {
            "number": 1,
            "name": "Пробуждение",
            "genre": "fantasy",
            "description": "Начало твоего путешествия в мир карточных сражений",
            "story_intro": (
                "Добро пожаловать, герой! Впереди тебя ждут великие испытания. "
                "Собери свою колоду и докажи, что ты достоин называться настоящим бойцом!"
            ),
            "story_outro": (
                "Ты одолел первого босса! Твоя сила растёт. "
                "Впереди новые приключения и более могущественные враги."
            ),
            "emoji": "⚔️",
            "background_color": "#2d3a4a",
            "required_power": 0,
            "xp_reward": 500,
            "guaranteed_card_rarity": "rare",
        },
        {
            "number": 2,
            "name": "Тёмные чары",
            "genre": "magic",
            "description": "Противостой силам магии и разрушь древнее проклятие",
            "story_intro": (
                "Тёмные маги пробудили древнее зло. "
                "Только ты можешь остановить надвигающуюся тьму!"
            ),
            "story_outro": "Проклятие снято! Но это лишь начало большой битвы...",
            "emoji": "✨",
            "background_color": "#3d2a5a",
            "required_power": 100,
            "xp_reward": 750,
            "guaranteed_card_rarity": "rare",
        },
        {
            "number": 3,
            "name": "Киберпанк",
            "genre": "cyberpunk",
            "description": "Взломай систему и победи корпорации",
            "story_intro": (
                "Добро пожаловать в Нео-Сити. Здесь правит сила и технологии. "
                "Корпорации контролируют всё. Пора это изменить."
            ),
            "story_outro": (
                "Система взломана! Но главный босс ещё ждёт своего часа..."
            ),
            "emoji": "🌆",
            "background_color": "#1a2a3a",
            "required_power": 200,
            "xp_reward": 1000,
            "guaranteed_card_rarity": "epic",
        },
        {
            "number": 4,
            "name": "Космические войны",
            "genre": "scifi",
            "description": "Сражайся за галактику против инопланетных захватчиков",
            "story_intro": (
                "Галактика в опасности! Флот инопланетян приближается к Земле. "
                "Ты — последняя надежда человечества."
            ),
            "story_outro": ("Инопланетный флот повержен! Но их командир скрылся..."),
            "emoji": "🚀",
            "background_color": "#0a1a2a",
            "required_power": 350,
            "xp_reward": 1250,
            "guaranteed_card_rarity": "epic",
        },
        {
            "number": 5,
            "name": "Финальная битва",
            "genre": "anime",
            "description": "Сразись с Тёмным Лордом и спаси все миры",
            "story_intro": (
                "Все миры объединились против общего врага — Тёмного Лорда. "
                "Это финальная битва. Победа или вечная тьма."
            ),
            "story_outro": (
                "Ты сделал это! Тёмный Лорд повержен, миры спасены. "
                "Ты — истинный Герой!"
            ),
            "emoji": "👑",
            "background_color": "#2a1a2a",
            "required_power": 500,
            "xp_reward": 2000,
            "guaranteed_card_rarity": "legendary",
        },
    ]

    for ch_data in chapters_data:
        chapter = CampaignChapter(**ch_data)
        db.session.add(chapter)
        db.session.flush()

        # Create 5 normal levels + 1 boss per chapter
        for i in range(6):
            is_boss = i == 5
            level = CampaignLevel(
                chapter_id=chapter.id,
                number=i + 1,
                is_boss=is_boss,
                title=f"Уровень {i + 1}" if not is_boss else "БОСС",
                difficulty_multiplier=1.0 + (i * 0.15) + (chapter.number * 0.2),
                required_power=chapter.required_power + (i * 20),
                xp_reward=50 + (i * 10) + (chapter.number * 20),
            )
            db.session.add(level)

        # Create chapter reward
        reward = CampaignReward(
            chapter_id=chapter.id,
            reward_type="card",
            reward_data={"rarity": chapter.guaranteed_card_rarity},
            name=f"Карта главы {chapter.number}",
            description=f"Награда за прохождение: {chapter.name}",
            emoji="🎁",
        )
        db.session.add(reward)

    db.session.commit()
    logger.info("Campaign data seeded successfully")
