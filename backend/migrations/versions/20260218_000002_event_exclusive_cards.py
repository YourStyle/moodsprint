"""Add event exclusive card support and event leaderboard.

- Add is_event_exclusive and event_id to user_cards
- Add event_points to user_event_progress for leaderboard

Revision ID: 20260218_000002
Revises: 20260218_000001
Create Date: 2026-02-18
"""

import sqlalchemy as sa
from alembic import op

revision = "20260218_000002"
down_revision = "20260218_000001"
branch_labels = None
depends_on = None


def upgrade():
    # Add event exclusive flags to user_cards
    op.add_column(
        "user_cards",
        sa.Column(
            "is_event_exclusive", sa.Boolean(), server_default="false", nullable=False
        ),
    )
    op.add_column(
        "user_cards",
        sa.Column(
            "event_id",
            sa.Integer(),
            sa.ForeignKey("seasonal_events.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Add event_points for leaderboard ranking
    op.add_column(
        "user_event_progress",
        sa.Column("event_points", sa.Integer(), server_default="0", nullable=False),
    )

    # Index for fast leaderboard queries
    op.create_index(
        "ix_user_event_progress_leaderboard",
        "user_event_progress",
        ["event_id", "event_points"],
    )

    # Index for event exclusive card queries
    op.create_index(
        "ix_user_cards_event_exclusive",
        "user_cards",
        ["event_id"],
        postgresql_where=sa.text("is_event_exclusive = true"),
    )


def downgrade():
    op.drop_index("ix_user_cards_event_exclusive", table_name="user_cards")
    op.drop_index(
        "ix_user_event_progress_leaderboard", table_name="user_event_progress"
    )
    op.drop_column("user_event_progress", "event_points")
    op.drop_column("user_cards", "event_id")
    op.drop_column("user_cards", "is_event_exclusive")
