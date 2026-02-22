"""Add guild quest contributions table and preferred_quest_types to guilds.

Revision ID: 20260222_000001
Revises: 20260218_000004
Create Date: 2026-02-22
"""

import sqlalchemy as sa
from alembic import op

revision = "20260222_000001"
down_revision = "20260218_000004"
branch_labels = None
depends_on = None


def upgrade():
    # Guild quest contributions table
    op.create_table(
        "guild_quest_contributions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("quest_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "last_contributed_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["quest_id"],
            ["guild_quests.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("quest_id", "user_id", name="unique_quest_contribution"),
    )
    op.create_index(
        "ix_guild_quest_contributions_quest_id",
        "guild_quest_contributions",
        ["quest_id"],
    )
    op.create_index(
        "ix_guild_quest_contributions_user_id",
        "guild_quest_contributions",
        ["user_id"],
    )

    # Add preferred_quest_types to guilds table
    op.add_column(
        "guilds",
        sa.Column("preferred_quest_types", sa.JSON(), nullable=True),
    )


def downgrade():
    op.drop_column("guilds", "preferred_quest_types")
    op.drop_index("ix_guild_quest_contributions_user_id")
    op.drop_index("ix_guild_quest_contributions_quest_id")
    op.drop_table("guild_quest_contributions")
