"""Add English translation fields to cards, monsters, and campaign.

Revision ID: add_english_translations
Revises:
Create Date: 2025-01-19
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250119_000001"
down_revision = "20250115_000001"
branch_labels = None
depends_on = None


def upgrade():
    # CardTemplate - add name_en, description_en
    op.add_column(
        "card_templates",
        sa.Column("name_en", sa.String(100), nullable=True),
    )
    op.add_column(
        "card_templates",
        sa.Column("description_en", sa.Text(), nullable=True),
    )

    # Monster - add name_en, description_en
    op.add_column(
        "monsters",
        sa.Column("name_en", sa.String(100), nullable=True),
    )
    op.add_column(
        "monsters",
        sa.Column("description_en", sa.Text(), nullable=True),
    )

    # MonsterCard - add name_en, description_en
    op.add_column(
        "monster_cards",
        sa.Column("name_en", sa.String(100), nullable=True),
    )
    op.add_column(
        "monster_cards",
        sa.Column("description_en", sa.Text(), nullable=True),
    )

    # CampaignChapter - add name_en, description_en, story_intro_en, story_outro_en
    op.add_column(
        "campaign_chapters",
        sa.Column("name_en", sa.String(100), nullable=True),
    )
    op.add_column(
        "campaign_chapters",
        sa.Column("description_en", sa.Text(), nullable=True),
    )
    op.add_column(
        "campaign_chapters",
        sa.Column("story_intro_en", sa.Text(), nullable=True),
    )
    op.add_column(
        "campaign_chapters",
        sa.Column("story_outro_en", sa.Text(), nullable=True),
    )

    # CampaignLevel - add title_en, dialogue_before_en, dialogue_after_en
    op.add_column(
        "campaign_levels",
        sa.Column("title_en", sa.String(100), nullable=True),
    )
    op.add_column(
        "campaign_levels",
        sa.Column("dialogue_before_en", sa.JSON(), nullable=True),
    )
    op.add_column(
        "campaign_levels",
        sa.Column("dialogue_after_en", sa.JSON(), nullable=True),
    )

    # CampaignReward - add name_en, description_en
    op.add_column(
        "campaign_rewards",
        sa.Column("name_en", sa.String(100), nullable=True),
    )
    op.add_column(
        "campaign_rewards",
        sa.Column("description_en", sa.String(200), nullable=True),
    )


def downgrade():
    # Remove all _en columns
    op.drop_column("campaign_rewards", "description_en")
    op.drop_column("campaign_rewards", "name_en")
    op.drop_column("campaign_levels", "dialogue_after_en")
    op.drop_column("campaign_levels", "dialogue_before_en")
    op.drop_column("campaign_levels", "title_en")
    op.drop_column("campaign_chapters", "story_outro_en")
    op.drop_column("campaign_chapters", "story_intro_en")
    op.drop_column("campaign_chapters", "description_en")
    op.drop_column("campaign_chapters", "name_en")
    op.drop_column("monster_cards", "description_en")
    op.drop_column("monster_cards", "name_en")
    op.drop_column("monsters", "description_en")
    op.drop_column("monsters", "name_en")
    op.drop_column("card_templates", "description_en")
    op.drop_column("card_templates", "name_en")
