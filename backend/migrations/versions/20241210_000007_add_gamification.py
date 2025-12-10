"""Add gamification: character stats, monsters, battles, quests, genre preference

Revision ID: 008_add_gamification
Revises: 007_add_scheduled_at
Create Date: 2024-12-10 20:00:07

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "008_add_gamification"
down_revision = "007_add_scheduled_at"
branch_labels = None
depends_on = None


def upgrade():
    # Add favorite_genre to user_profiles
    op.add_column(
        "user_profiles",
        sa.Column("favorite_genre", sa.String(50), nullable=True),
    )

    # Create character_stats table
    op.create_table(
        "character_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("agility", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("intelligence", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("max_hp", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("current_hp", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("battles_won", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("battles_lost", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "available_stat_points", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # Create monsters table
    op.create_table(
        "monsters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("genre", sa.String(50), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("hp", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("attack", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("defense", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("speed", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("xp_reward", sa.Integer(), nullable=False, server_default="20"),
        sa.Column(
            "stat_points_reward", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column("sprite_url", sa.String(512), nullable=True),
        sa.Column("emoji", sa.String(10), nullable=True, server_default="'👾'"),
        sa.Column("is_boss", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_monsters_genre", "monsters", ["genre"], unique=False)

    # Create battle_logs table
    op.create_table(
        "battle_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("monster_id", sa.Integer(), nullable=True),
        sa.Column("won", sa.Boolean(), nullable=False),
        sa.Column("rounds", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("damage_dealt", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("damage_taken", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("xp_earned", sa.Integer(), nullable=True, server_default="0"),
        sa.Column(
            "stat_points_earned", sa.Integer(), nullable=True, server_default="0"
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["monster_id"], ["monsters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_battle_logs_user_id", "battle_logs", ["user_id"], unique=False)

    # Create daily_quests table
    op.create_table(
        "daily_quests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("quest_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("themed_description", sa.String(500), nullable=True),
        sa.Column("target_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("current_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("xp_reward", sa.Integer(), nullable=False, server_default="50"),
        sa.Column(
            "stat_points_reward", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("claimed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "quest_type", "date", name="unique_user_quest_date"
        ),
    )
    op.create_index(
        "ix_daily_quests_user_id", "daily_quests", ["user_id"], unique=False
    )
    op.create_index("ix_daily_quests_date", "daily_quests", ["date"], unique=False)


def downgrade():
    op.drop_index("ix_daily_quests_date", table_name="daily_quests")
    op.drop_index("ix_daily_quests_user_id", table_name="daily_quests")
    op.drop_table("daily_quests")

    op.drop_index("ix_battle_logs_user_id", table_name="battle_logs")
    op.drop_table("battle_logs")

    op.drop_index("ix_monsters_genre", table_name="monsters")
    op.drop_table("monsters")

    op.drop_table("character_stats")

    op.drop_column("user_profiles", "favorite_genre")
