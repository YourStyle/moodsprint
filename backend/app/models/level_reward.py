"""Level reward model for configurable level-up rewards."""

from datetime import datetime

from app import db


class LevelReward(db.Model):
    """Reward granted when a user reaches a specific level.

    Multiple rewards can be configured per level (e.g., level 4 can grant
    a genre_unlock + sparks + energy).
    """

    __tablename__ = "level_rewards"

    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.Integer, nullable=False, index=True)
    reward_type = db.Column(
        db.String(50), nullable=False
    )  # genre_unlock, card, sparks, energy, xp_boost, archetype_tier
    reward_value = db.Column(
        db.JSON, nullable=False
    )  # e.g. {"amount": 50} or {"rarity": "rare"}
    description = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "level": self.level,
            "reward_type": self.reward_type,
            "reward_value": self.reward_value,
            "description": self.description,
            "is_active": self.is_active,
        }

    def __repr__(self) -> str:
        return f"<LevelReward level={self.level} type={self.reward_type}>"
