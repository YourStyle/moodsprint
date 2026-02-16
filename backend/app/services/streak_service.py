"""Streak milestone rewards service."""

import logging

from app import db
from app.models.card import CardRarity
from app.models.user import User
from app.services.card_service import CardService

logger = logging.getLogger(__name__)

# Milestone definitions: {streak_days: {"xp": amount, "card_rarity": CardRarity|None}}
MILESTONES = {
    3: {"xp": 50, "card_rarity": None},
    7: {"xp": 150, "card_rarity": CardRarity.COMMON},
    14: {"xp": 300, "card_rarity": CardRarity.RARE},
    30: {"xp": 500, "card_rarity": CardRarity.EPIC},
}


class StreakService:
    """Service for streak milestone reward checks and grants."""

    def check_and_grant_milestone(self, user: User) -> dict | None:
        """Check if user has reached a new streak milestone and grant rewards.

        Returns milestone data dict or None if no new milestone.
        """
        streak = user.streak_days
        last_claimed = user.last_streak_milestone_claimed or 0

        # Find the highest milestone the user qualifies for
        # that they haven't claimed yet
        eligible_milestone = None
        for days in sorted(MILESTONES.keys()):
            if days <= streak and days > last_claimed:
                eligible_milestone = days

        if eligible_milestone is None:
            return None

        milestone = MILESTONES[eligible_milestone]
        xp_bonus = milestone["xp"]
        card_rarity = milestone["card_rarity"]

        # Grant XP
        user.add_xp(xp_bonus)

        # Grant card if applicable
        card_earned = None
        if card_rarity:
            try:
                card_service = CardService()
                card = card_service.generate_card_for_task(
                    user.id,
                    None,
                    f"Streak {eligible_milestone} days",
                    forced_rarity=card_rarity,
                )
                if card:
                    card_earned = card.to_dict()
            except Exception as e:
                logger.error(f"Failed to generate streak milestone card: {e}")

        # Update last claimed milestone
        user.last_streak_milestone_claimed = eligible_milestone
        db.session.flush()

        result = {
            "milestone_days": eligible_milestone,
            "xp_bonus": xp_bonus,
        }
        if card_earned:
            result["card_earned"] = card_earned

        logger.info(
            f"Streak milestone {eligible_milestone} granted to user {user.id}: "
            f"+{xp_bonus} XP, card={card_rarity}"
        )

        return result
