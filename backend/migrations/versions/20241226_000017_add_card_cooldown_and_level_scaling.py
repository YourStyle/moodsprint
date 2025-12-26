"""Add card cooldown and recalculate card stats by user level.

Revision ID: 20241226_000017
Revises: 20241222_000016
Create Date: 2024-12-26

"""

import math

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20241226_000017"
down_revision = "20241222_000016"
branch_labels = None
depends_on = None

# Rarity multipliers for reverse calculation
RARITY_MULTIPLIERS = {
    "common": {"hp": 1.0, "attack": 1.0},
    "uncommon": {"hp": 1.3, "attack": 1.2},
    "rare": {"hp": 1.6, "attack": 1.5},
    "epic": {"hp": 2.0, "attack": 1.8},
    "legendary": {"hp": 2.5, "attack": 2.2},
}

# Level scaling multiplier per level
LEVEL_STAT_MULTIPLIER = 0.05


def get_user_level(xp):
    """Calculate user level from XP."""
    if xp < 100:
        return 1
    return int(math.floor(math.sqrt(xp / 100))) + 1


def upgrade():
    """Add cooldown_until column and recalculate card stats by user level."""
    # 1. Add cooldown_until column
    op.add_column(
        "user_cards",
        sa.Column("cooldown_until", sa.DateTime(), nullable=True),
    )

    # 2. Recalculate card stats based on user level
    conn = op.get_bind()

    # Get all users with their XP
    users = conn.execute(text("SELECT id, xp FROM users")).fetchall()

    for user_row in users:
        user_id = user_row[0]
        user_xp = user_row[1] or 0
        user_level = get_user_level(user_xp)
        level_mult = 1 + (user_level * LEVEL_STAT_MULTIPLIER)

        # Get user's cards that are not destroyed
        cards = conn.execute(
            text(
                "SELECT id, hp, attack, current_hp, rarity "
                "FROM user_cards WHERE user_id = :user_id AND is_destroyed = false"
            ),
            {"user_id": user_id},
        ).fetchall()

        for card_row in cards:
            card_id = card_row[0]
            old_hp = card_row[1]
            old_attack = card_row[2]
            old_current_hp = card_row[3]
            rarity = card_row[4]

            rarity_mult = RARITY_MULTIPLIERS.get(rarity, RARITY_MULTIPLIERS["common"])

            # Reverse calculate base stats (removing rarity multiplier)
            base_hp = old_hp / rarity_mult["hp"]
            base_attack = old_attack / rarity_mult["attack"]

            # Apply new stats with level multiplier
            new_hp = int(base_hp * rarity_mult["hp"] * level_mult)
            new_attack = int(base_attack * rarity_mult["attack"] * level_mult)

            # Scale current_hp proportionally
            if old_hp > 0:
                hp_ratio = old_current_hp / old_hp
                new_current_hp = int(new_hp * hp_ratio)
            else:
                new_current_hp = new_hp

            # Update card
            conn.execute(
                text(
                    "UPDATE user_cards SET hp = :hp, attack = :attack, "
                    "current_hp = :current_hp WHERE id = :id"
                ),
                {
                    "id": card_id,
                    "hp": new_hp,
                    "attack": new_attack,
                    "current_hp": new_current_hp,
                },
            )


def downgrade():
    """Remove cooldown_until column."""
    op.drop_column("user_cards", "cooldown_until")
    # Note: Card stats changes are not reverted as it would require
    # storing original values which is impractical
