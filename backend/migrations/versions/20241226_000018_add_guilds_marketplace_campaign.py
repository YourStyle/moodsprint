"""Add guilds, marketplace, and campaign tables.

Revision ID: 20241226_000018
Revises: 20241226_000017
Create Date: 2024-12-26

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20241226_000018"
down_revision = "20241226_000017"
branch_labels = None
depends_on = None


def upgrade():
    """Create guilds, marketplace, and campaign tables."""

    # ============ GUILDS ============

    op.create_table(
        "guilds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("emoji", sa.String(10), server_default="⚔️"),
        sa.Column("leader_id", sa.Integer(), nullable=True),
        sa.Column("level", sa.Integer(), server_default="1"),
        sa.Column("xp", sa.Integer(), server_default="0"),
        sa.Column("is_public", sa.Boolean(), server_default="true"),
        sa.Column("max_members", sa.Integer(), server_default="30"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["leader_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "guild_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(20), server_default="member"),
        sa.Column("contribution_xp", sa.Integer(), server_default="0"),
        sa.Column("raids_participated", sa.Integer(), server_default="0"),
        sa.Column("total_damage_dealt", sa.Integer(), server_default="0"),
        sa.Column("joined_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("guild_id", "user_id", name="unique_guild_member"),
    )
    op.create_index("ix_guild_members_guild_id", "guild_members", ["guild_id"])
    op.create_index("ix_guild_members_user_id", "guild_members", ["user_id"])

    op.create_table(
        "guild_raids",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.Integer(), nullable=False),
        sa.Column("monster_id", sa.Integer(), nullable=True),
        sa.Column("boss_name", sa.String(100), nullable=False),
        sa.Column("boss_emoji", sa.String(10), server_default="👹"),
        sa.Column("total_hp", sa.Integer(), nullable=False),
        sa.Column("current_hp", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("xp_reward", sa.Integer(), server_default="500"),
        sa.Column("card_reward_rarity", sa.String(20), server_default="rare"),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("total_damage_dealt", sa.Integer(), server_default="0"),
        sa.Column("participants_count", sa.Integer(), server_default="0"),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["monster_id"], ["monsters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_guild_raids_guild_id", "guild_raids", ["guild_id"])

    op.create_table(
        "guild_raid_contributions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("raid_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("damage_dealt", sa.Integer(), server_default="0"),
        sa.Column("attacks_count", sa.Integer(), server_default="0"),
        sa.Column("last_attack_at", sa.DateTime(), nullable=True),
        sa.Column("attacks_today", sa.Integer(), server_default="0"),
        sa.Column("attacks_reset_date", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["raid_id"], ["guild_raids.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("raid_id", "user_id", name="unique_raid_contribution"),
    )
    op.create_index(
        "ix_guild_raid_contributions_raid_id", "guild_raid_contributions", ["raid_id"]
    )
    op.create_index(
        "ix_guild_raid_contributions_user_id", "guild_raid_contributions", ["user_id"]
    )

    op.create_table(
        "guild_invites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("invited_by_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("responded_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_guild_invites_guild_id", "guild_invites", ["guild_id"])
    op.create_index("ix_guild_invites_user_id", "guild_invites", ["user_id"])

    # ============ MARKETPLACE ============

    op.create_table(
        "market_listings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("price_stars", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("buyer_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("sold_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["card_id"], ["user_cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_market_listings_seller_id", "market_listings", ["seller_id"])
    op.create_index("ix_market_listings_status", "market_listings", ["status"])

    op.create_table(
        "stars_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("reference_type", sa.String(30), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("telegram_payment_id", sa.String(100), nullable=True),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stars_transactions_user_id", "stars_transactions", ["user_id"])

    op.create_table(
        "user_stars_balances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("balance", sa.Integer(), server_default="0"),
        sa.Column("pending_balance", sa.Integer(), server_default="0"),
        sa.Column("total_earned", sa.Integer(), server_default="0"),
        sa.Column("total_spent", sa.Integer(), server_default="0"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ============ CAMPAIGN ============

    op.create_table(
        "campaign_chapters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("genre", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("story_intro", sa.Text(), nullable=True),
        sa.Column("story_outro", sa.Text(), nullable=True),
        sa.Column("emoji", sa.String(10), server_default="📖"),
        sa.Column("background_color", sa.String(20), server_default="#1a1a2e"),
        sa.Column("required_power", sa.Integer(), server_default="0"),
        sa.Column("xp_reward", sa.Integer(), server_default="500"),
        sa.Column("guaranteed_card_rarity", sa.String(20), server_default="rare"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "campaign_levels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("monster_id", sa.Integer(), nullable=True),
        sa.Column("is_boss", sa.Boolean(), server_default="false"),
        sa.Column("title", sa.String(100), nullable=True),
        sa.Column("dialogue_before", sa.JSON(), nullable=True),
        sa.Column("dialogue_after", sa.JSON(), nullable=True),
        sa.Column("difficulty_multiplier", sa.Float(), server_default="1.0"),
        sa.Column("required_power", sa.Integer(), server_default="0"),
        sa.Column("xp_reward", sa.Integer(), server_default="50"),
        sa.Column("stars_max", sa.Integer(), server_default="3"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.ForeignKeyConstraint(
            ["chapter_id"], ["campaign_chapters.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["monster_id"], ["monsters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chapter_id", "number", name="unique_chapter_level"),
    )
    op.create_index("ix_campaign_levels_chapter_id", "campaign_levels", ["chapter_id"])

    op.create_table(
        "campaign_rewards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=False),
        sa.Column("reward_type", sa.String(30), nullable=False),
        sa.Column("reward_data", sa.JSON(), nullable=False),
        sa.Column("name", sa.String(100), nullable=True),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("emoji", sa.String(10), server_default="🎁"),
        sa.ForeignKeyConstraint(
            ["chapter_id"], ["campaign_chapters.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "user_campaign_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("current_chapter", sa.Integer(), server_default="1"),
        sa.Column("current_level", sa.Integer(), server_default="1"),
        sa.Column("chapters_completed", sa.JSON(), nullable=True),
        sa.Column("total_stars_earned", sa.Integer(), server_default="0"),
        sa.Column("bosses_defeated", sa.Integer(), server_default="0"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "campaign_level_completions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("progress_id", sa.Integer(), nullable=False),
        sa.Column("level_id", sa.Integer(), nullable=False),
        sa.Column("stars_earned", sa.Integer(), server_default="1"),
        sa.Column("best_rounds", sa.Integer(), nullable=True),
        sa.Column("best_hp_remaining", sa.Integer(), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="1"),
        sa.Column("first_completed_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("last_completed_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["progress_id"], ["user_campaign_progress.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["level_id"], ["campaign_levels.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("progress_id", "level_id", name="unique_level_completion"),
    )
    op.create_index(
        "ix_campaign_level_completions_progress_id",
        "campaign_level_completions",
        ["progress_id"],
    )


def downgrade():
    """Drop all new tables."""
    # Campaign
    op.drop_table("campaign_level_completions")
    op.drop_table("user_campaign_progress")
    op.drop_table("campaign_rewards")
    op.drop_table("campaign_levels")
    op.drop_table("campaign_chapters")

    # Marketplace
    op.drop_table("user_stars_balances")
    op.drop_table("stars_transactions")
    op.drop_table("market_listings")

    # Guilds
    op.drop_table("guild_invites")
    op.drop_table("guild_raid_contributions")
    op.drop_table("guild_raids")
    op.drop_table("guild_members")
    op.drop_table("guilds")
