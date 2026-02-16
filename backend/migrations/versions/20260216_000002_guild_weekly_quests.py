"""Add guild weekly quests table.

Revision ID: a4b5c6d7e8f9
Revises: 20260216_000001
Create Date: 2026-02-16
"""

import sqlalchemy as sa
from alembic import op

revision = "a4b5c6d7e8f9"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "guild_quests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "guild_id",
            sa.Integer(),
            sa.ForeignKey("guilds.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("quest_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("emoji", sa.String(10), server_default="📋"),
        sa.Column("target", sa.Integer(), nullable=False),
        sa.Column("progress", sa.Integer(), server_default="0"),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("week_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("xp_reward", sa.Integer(), server_default="200"),
        sa.Column("sparks_reward", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table("guild_quests")
