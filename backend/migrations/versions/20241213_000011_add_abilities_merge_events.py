"""Add card abilities, merge system, and seasonal events.

Revision ID: 000011
Revises: 000010
Create Date: 2024-12-13

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "000011"
down_revision = "000010"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add ability fields to user_cards
    op.add_column(
        "user_cards",
        sa.Column("ability", sa.String(30), nullable=True),
    )
    op.add_column(
        "user_cards",
        sa.Column("ability_cooldown", sa.Integer(), nullable=True, default=0),
    )

    # 2. Create merge_logs table
    op.create_table(
        "merge_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("card1_name", sa.String(100), nullable=False),
        sa.Column("card1_rarity", sa.String(20), nullable=False),
        sa.Column("card2_name", sa.String(100), nullable=False),
        sa.Column("card2_rarity", sa.String(20), nullable=False),
        sa.Column("result_card_id", sa.Integer(), nullable=True),
        sa.Column("result_rarity", sa.String(20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["result_card_id"], ["user_cards.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_merge_logs_user_id", "merge_logs", ["user_id"])

    # 3. Create seasonal_events table
    op.create_table(
        "seasonal_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("event_type", sa.String(20), nullable=False, default="seasonal"),
        sa.Column("start_date", sa.DateTime(), nullable=False),
        sa.Column("end_date", sa.DateTime(), nullable=False),
        sa.Column("banner_url", sa.String(512), nullable=True),
        sa.Column("theme_color", sa.String(7), nullable=True, default="#FF6B00"),
        sa.Column("emoji", sa.String(10), nullable=True, default="🎉"),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("xp_multiplier", sa.Float(), nullable=True, default=1.0),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 4. Create event_monsters table
    op.create_table(
        "event_monsters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("monster_id", sa.Integer(), nullable=False),
        sa.Column("appear_day", sa.Integer(), nullable=True, default=1),
        sa.Column("exclusive_reward_name", sa.String(100), nullable=True),
        sa.Column("guaranteed_rarity", sa.String(20), nullable=True),
        sa.Column("times_defeated", sa.Integer(), nullable=True, default=0),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(
            ["event_id"], ["seasonal_events.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["monster_id"], ["monsters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_monsters_event_id", "event_monsters", ["event_id"])

    # 5. Create user_event_progress table
    op.create_table(
        "user_event_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("monsters_defeated", sa.Integer(), nullable=True, default=0),
        sa.Column("bosses_defeated", sa.Integer(), nullable=True, default=0),
        sa.Column("exclusive_cards_earned", sa.Integer(), nullable=True, default=0),
        sa.Column("milestones", sa.JSON(), nullable=True, default=[]),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["event_id"], ["seasonal_events.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "event_id", name="unique_user_event"),
    )
    op.create_index(
        "ix_user_event_progress_user_id", "user_event_progress", ["user_id"]
    )


def downgrade():
    op.drop_index("ix_user_event_progress_user_id", table_name="user_event_progress")
    op.drop_table("user_event_progress")
    op.drop_index("ix_event_monsters_event_id", table_name="event_monsters")
    op.drop_table("event_monsters")
    op.drop_table("seasonal_events")
    op.drop_index("ix_merge_logs_user_id", table_name="merge_logs")
    op.drop_table("merge_logs")
    op.drop_column("user_cards", "ability_cooldown")
    op.drop_column("user_cards", "ability")
