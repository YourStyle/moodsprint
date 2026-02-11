"""Card system improvements: leveling, companion, showcase, genre unlock, energy, hard mode.

Revision ID: 20250211_000001
Revises: 20250121_000001
Create Date: 2025-02-11

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250211_000001"
down_revision = "20250121_000001"
branch_labels = None
depends_on = None


def upgrade():
    # --- UserCard: card leveling, companion, showcase ---
    op.add_column(
        "user_cards",
        sa.Column("card_level", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "user_cards",
        sa.Column("card_xp", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "user_cards",
        sa.Column("is_companion", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "user_cards",
        sa.Column("is_showcase", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column("user_cards", sa.Column("showcase_slot", sa.Integer(), nullable=True))

    # --- CardTemplate: archetype tier ---
    op.add_column(
        "card_templates",
        sa.Column("unlock_level", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "card_templates", sa.Column("archetype_tier", sa.String(20), nullable=True)
    )

    # --- UserProfile: genre unlocking + campaign energy ---
    op.add_column(
        "user_profiles", sa.Column("unlocked_genres", sa.JSON(), nullable=True)
    )
    op.add_column(
        "user_profiles",
        sa.Column("campaign_energy", sa.Integer(), nullable=False, server_default="3"),
    )
    op.add_column(
        "user_profiles",
        sa.Column(
            "max_campaign_energy", sa.Integer(), nullable=False, server_default="5"
        ),
    )
    op.add_column(
        "user_profiles", sa.Column("last_energy_update", sa.DateTime(), nullable=True)
    )

    # --- CampaignLevelCompletion: hard mode ---
    op.add_column(
        "campaign_level_completions",
        sa.Column("is_hard_mode", sa.Boolean(), nullable=False, server_default="false"),
    )

    # --- Data migration: set unlocked_genres to [favorite_genre] for existing users ---
    # Use raw SQL to update existing profiles
    op.execute(
        """
        UPDATE user_profiles
        SET unlocked_genres = json_build_array(favorite_genre)
        WHERE favorite_genre IS NOT NULL AND unlocked_genres IS NULL
    """
    )


def downgrade():
    op.drop_column("campaign_level_completions", "is_hard_mode")
    op.drop_column("user_profiles", "last_energy_update")
    op.drop_column("user_profiles", "max_campaign_energy")
    op.drop_column("user_profiles", "campaign_energy")
    op.drop_column("user_profiles", "unlocked_genres")
    op.drop_column("card_templates", "archetype_tier")
    op.drop_column("card_templates", "unlock_level")
    op.drop_column("user_cards", "showcase_slot")
    op.drop_column("user_cards", "is_showcase")
    op.drop_column("user_cards", "is_companion")
    op.drop_column("user_cards", "card_xp")
    op.drop_column("user_cards", "card_level")
