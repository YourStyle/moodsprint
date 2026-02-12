"""Add level_rewards table and last_rewarded_level to user_profiles.

Revision ID: 20260212_000001
Revises: 20250211_000001
Create Date: 2026-02-12

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260212_000001"
down_revision = "20250211_000001"
branch_labels = None
depends_on = None


def upgrade():
    # Create level_rewards table
    level_rewards = op.create_table(
        "level_rewards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("level", sa.Integer(), nullable=False, index=True),
        sa.Column("reward_type", sa.String(50), nullable=False),
        sa.Column("reward_value", sa.JSON(), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Add last_rewarded_level to user_profiles for idempotency
    op.add_column(
        "user_profiles",
        sa.Column(
            "last_rewarded_level",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )

    # Seed default level rewards
    op.bulk_insert(
        level_rewards,
        [
            # Level 2
            {
                "level": 2,
                "reward_type": "sparks",
                "reward_value": {"amount": 50},
                "description": "50 sparks",
            },
            {
                "level": 2,
                "reward_type": "energy",
                "reward_value": {"amount": 1},
                "description": "1 campaign energy",
            },
            # Level 3
            {
                "level": 3,
                "reward_type": "card",
                "reward_value": {"rarity": "uncommon"},
                "description": "Uncommon card",
            },
            {
                "level": 3,
                "reward_type": "sparks",
                "reward_value": {"amount": 100},
                "description": "100 sparks",
            },
            # Level 4
            {
                "level": 4,
                "reward_type": "genre_unlock",
                "reward_value": {"slot": 2},
                "description": "2nd genre slot",
            },
            {
                "level": 4,
                "reward_type": "energy",
                "reward_value": {"amount": 2},
                "description": "2 campaign energy",
            },
            {
                "level": 4,
                "reward_type": "sparks",
                "reward_value": {"amount": 150},
                "description": "150 sparks",
            },
            # Level 5
            {
                "level": 5,
                "reward_type": "card",
                "reward_value": {"rarity": "rare"},
                "description": "Rare card",
            },
            {
                "level": 5,
                "reward_type": "sparks",
                "reward_value": {"amount": 200},
                "description": "200 sparks",
            },
            {
                "level": 5,
                "reward_type": "archetype_tier",
                "reward_value": {"tier": "advanced"},
                "description": "Advanced archetypes unlocked",
            },
            # Level 6
            {
                "level": 6,
                "reward_type": "sparks",
                "reward_value": {"amount": 100},
                "description": "100 sparks",
            },
            {
                "level": 6,
                "reward_type": "energy",
                "reward_value": {"amount": 1},
                "description": "1 campaign energy",
            },
            # Level 7
            {
                "level": 7,
                "reward_type": "genre_unlock",
                "reward_value": {"slot": 3},
                "description": "3rd genre slot",
            },
            {
                "level": 7,
                "reward_type": "card",
                "reward_value": {"rarity": "rare"},
                "description": "Rare card",
            },
            # Level 8
            {
                "level": 8,
                "reward_type": "sparks",
                "reward_value": {"amount": 150},
                "description": "150 sparks",
            },
            {
                "level": 8,
                "reward_type": "energy",
                "reward_value": {"amount": 2},
                "description": "2 campaign energy",
            },
            # Level 9
            {
                "level": 9,
                "reward_type": "sparks",
                "reward_value": {"amount": 200},
                "description": "200 sparks",
            },
            {
                "level": 9,
                "reward_type": "card",
                "reward_value": {"rarity": "uncommon"},
                "description": "Uncommon card",
            },
            # Level 10
            {
                "level": 10,
                "reward_type": "genre_unlock",
                "reward_value": {"slot": 4},
                "description": "4th genre slot",
            },
            {
                "level": 10,
                "reward_type": "card",
                "reward_value": {"rarity": "epic"},
                "description": "Epic card",
            },
            {
                "level": 10,
                "reward_type": "archetype_tier",
                "reward_value": {"tier": "elite"},
                "description": "Elite archetypes unlocked",
            },
            # Level 11
            {
                "level": 11,
                "reward_type": "sparks",
                "reward_value": {"amount": 200},
                "description": "200 sparks",
            },
            {
                "level": 11,
                "reward_type": "energy",
                "reward_value": {"amount": 2},
                "description": "2 campaign energy",
            },
            # Level 12
            {
                "level": 12,
                "reward_type": "card",
                "reward_value": {"rarity": "rare"},
                "description": "Rare card",
            },
            {
                "level": 12,
                "reward_type": "sparks",
                "reward_value": {"amount": 250},
                "description": "250 sparks",
            },
            # Level 13
            {
                "level": 13,
                "reward_type": "sparks",
                "reward_value": {"amount": 300},
                "description": "300 sparks",
            },
            {
                "level": 13,
                "reward_type": "energy",
                "reward_value": {"amount": 3},
                "description": "3 campaign energy",
            },
            # Level 14
            {
                "level": 14,
                "reward_type": "card",
                "reward_value": {"rarity": "epic"},
                "description": "Epic card",
            },
            {
                "level": 14,
                "reward_type": "sparks",
                "reward_value": {"amount": 350},
                "description": "350 sparks",
            },
            # Level 15
            {
                "level": 15,
                "reward_type": "genre_unlock",
                "reward_value": {"slot": 5},
                "description": "5th genre slot",
            },
            {
                "level": 15,
                "reward_type": "card",
                "reward_value": {"rarity": "legendary"},
                "description": "Legendary card",
            },
            {
                "level": 15,
                "reward_type": "archetype_tier",
                "reward_value": {"tier": "legendary"},
                "description": "Legendary archetypes unlocked",
            },
        ],
    )


def downgrade():
    op.drop_column("user_profiles", "last_rewarded_level")
    op.drop_table("level_rewards")
