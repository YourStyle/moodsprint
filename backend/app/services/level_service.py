"""Level reward service for granting rewards on level-up."""

import logging

from app import db
from app.models.card import CardRarity
from app.models.level_reward import LevelReward
from app.models.user import User
from app.models.user_profile import UserProfile

logger = logging.getLogger(__name__)


class LevelService:
    """Handles level-up reward logic."""

    # Free cosmetic rewards at specific levels
    COSMETIC_REWARDS = {
        5: "card_frame_golden",
        8: "profile_frame_silver",
    }

    RARITY_MAP = {
        "common": CardRarity.COMMON,
        "uncommon": CardRarity.UNCOMMON,
        "rare": CardRarity.RARE,
        "epic": CardRarity.EPIC,
        "legendary": CardRarity.LEGENDARY,
    }

    def get_rewards_for_level(self, level: int) -> list[dict]:
        """Get all active rewards configured for a specific level."""
        rewards = (
            LevelReward.query.filter_by(level=level, is_active=True)
            .order_by(LevelReward.id)
            .all()
        )
        return [r.to_dict() for r in rewards]

    def get_all_level_rewards(self) -> dict:
        """Get all level rewards grouped by level (for frontend preview)."""
        rewards = (
            LevelReward.query.filter_by(is_active=True)
            .order_by(LevelReward.level, LevelReward.id)
            .all()
        )
        grouped = {}
        for r in rewards:
            grouped.setdefault(r.level, []).append(r.to_dict())
        return grouped

    def grant_level_rewards(self, user_id: int, new_level: int) -> dict:
        """Grant all rewards for leveling up. Idempotent via last_rewarded_level.

        Returns a summary of granted rewards for the frontend modal.
        """
        user = User.query.get(user_id)
        if not user:
            return {"granted": False, "rewards": []}

        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            return {"granted": False, "rewards": []}

        last_rewarded = profile.last_rewarded_level or 1

        # Nothing new to grant
        if new_level <= last_rewarded:
            return {"granted": False, "rewards": []}

        # Grant rewards for each level between last_rewarded+1 and new_level
        all_granted = []
        for level in range(last_rewarded + 1, new_level + 1):
            rewards = LevelReward.query.filter_by(level=level, is_active=True).all()
            for reward in rewards:
                granted = self._grant_single_reward(user, profile, reward)
                if granted:
                    all_granted.append(granted)

            # Deck size increase at levels 10 and 15
            if level in (10, 15):
                all_granted.append(
                    {
                        "type": "deck_size",
                        "amount": 1,
                        "description": "Deck size increase",
                    }
                )

            # Auto +1 max energy every 3 levels (3, 6, 9, 12, 15, ...)
            if level % 3 == 0:
                try:
                    from app.services.card_service import CardService

                    CardService().increase_max_energy(user_id, 1)
                except Exception as e:
                    logger.warning(f"Failed to increase max energy: {e}")
                all_granted.append(
                    {
                        "type": "max_energy",
                        "amount": 1,
                        "description": "Energy limit increase",
                    }
                )

            # Free cosmetic rewards at specific levels
            if level in self.COSMETIC_REWARDS:
                cosmetic_id = self.COSMETIC_REWARDS[level]
                owned = profile.owned_cosmetics or []
                if cosmetic_id not in owned:
                    owned.append(cosmetic_id)
                    profile.owned_cosmetics = owned
                all_granted.append(
                    {
                        "type": "cosmetic",
                        "cosmetic_id": cosmetic_id,
                        "description": f"Free cosmetic: {cosmetic_id}",
                    }
                )

        profile.last_rewarded_level = new_level
        db.session.commit()

        return {"granted": bool(all_granted), "rewards": all_granted}

    def _grant_single_reward(
        self, user: User, profile: UserProfile, reward: LevelReward
    ) -> dict | None:
        """Grant a single reward. Returns summary dict or None."""
        rtype = reward.reward_type
        rval = reward.reward_value

        if rtype == "sparks":
            amount = rval.get("amount", 0)
            user.add_sparks(amount)
            return {
                "type": "sparks",
                "amount": amount,
                "description": reward.description,
            }

        elif rtype == "energy":
            amount = rval.get("amount", 0)
            try:
                from app.services.card_service import CardService

                CardService().add_energy(user.id, amount)
            except Exception as e:
                logger.warning(f"Failed to add energy reward: {e}")
            return {
                "type": "energy",
                "amount": amount,
                "description": reward.description,
            }

        elif rtype == "max_energy":
            amount = rval.get("amount", 0)
            try:
                from app.services.card_service import CardService

                CardService().increase_max_energy(user.id, amount)
            except Exception as e:
                logger.warning(f"Failed to increase max energy: {e}")
            return {
                "type": "max_energy",
                "amount": amount,
                "description": reward.description,
            }

        elif rtype == "card":
            rarity_str = rval.get("rarity", "common")
            forced_rarity = self.RARITY_MAP.get(rarity_str)
            card = None
            try:
                from app.services.card_service import CardService

                card = CardService().generate_card_for_task(
                    user.id, None, "Level reward", forced_rarity=forced_rarity
                )
            except Exception as e:
                logger.warning(f"Failed to generate card reward: {e}")
            return {
                "type": "card",
                "rarity": rarity_str,
                "card": card.to_dict() if card else None,
                "description": reward.description,
            }

        elif rtype == "genre_unlock":
            # Flag only — frontend presents the choice
            slot = rval.get("slot", 2)
            return {
                "type": "genre_unlock",
                "slot": slot,
                "description": reward.description,
            }

        elif rtype == "archetype_tier":
            # Info only — tiers are level-gated in card_service
            tier = rval.get("tier", "basic")
            return {
                "type": "archetype_tier",
                "tier": tier,
                "description": reward.description,
            }

        elif rtype == "xp_boost":
            # XP boost — could be a multiplier or flat bonus
            return {
                "type": "xp_boost",
                "value": rval,
                "description": reward.description,
            }

        return None

    # ============ Admin CRUD ============

    def get_all_level_configs(self) -> list[dict]:
        """Get all level rewards for admin panel."""
        rewards = LevelReward.query.order_by(LevelReward.level, LevelReward.id).all()
        return [r.to_dict() for r in rewards]

    def create_reward(
        self,
        level: int,
        reward_type: str,
        reward_value: dict,
        description: str | None = None,
    ) -> LevelReward:
        """Create a new level reward."""
        reward = LevelReward(
            level=level,
            reward_type=reward_type,
            reward_value=reward_value,
            description=description,
        )
        db.session.add(reward)
        db.session.commit()
        return reward

    def update_reward(self, reward_id: int, **kwargs) -> LevelReward | None:
        """Update an existing level reward."""
        reward = LevelReward.query.get(reward_id)
        if not reward:
            return None
        for key, value in kwargs.items():
            if hasattr(reward, key):
                setattr(reward, key, value)
        db.session.commit()
        return reward

    def delete_reward(self, reward_id: int) -> bool:
        """Delete a level reward."""
        reward = LevelReward.query.get(reward_id)
        if not reward:
            return False
        db.session.delete(reward)
        db.session.commit()
        return True
