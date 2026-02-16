"""Add retention features: streak milestones, comeback card, friend activity logs.

Revision ID: 20260216_000001
Revises: 20260214_000001
Create Date: 2026-02-16

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260216_000001"
down_revision = "20260214_000001"
branch_labels = None
depends_on = None


def _column_exists(table, column):
    """Check if a column exists in a table."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table, "column": column},
    )
    return result.fetchone() is not None


def _table_exists(table):
    """Check if a table exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = :table"),
        {"table": table},
    )
    return result.fetchone() is not None


def upgrade():
    # F2: Streak milestone tracking
    if not _column_exists("users", "last_streak_milestone_claimed"):
        op.add_column(
            "users",
            sa.Column(
                "last_streak_milestone_claimed",
                sa.Integer(),
                server_default="0",
                nullable=False,
            ),
        )

    # F5: Comeback card pending flag
    if not _column_exists("users", "comeback_card_pending"):
        op.add_column(
            "users",
            sa.Column(
                "comeback_card_pending",
                sa.Boolean(),
                server_default="false",
                nullable=False,
            ),
        )

    # F4: Friend activity logs
    if not _table_exists("friend_activity_logs"):
        op.create_table(
            "friend_activity_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("activity_type", sa.String(50), nullable=False),
            sa.Column("activity_data", sa.JSON(), nullable=True),
            sa.Column("notified", sa.Boolean(), server_default="false", nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("NOW()"),
                nullable=False,
            ),
        )

        op.create_index(
            "idx_fal_unnotified",
            "friend_activity_logs",
            ["notified", "created_at"],
        )


def downgrade():
    if _table_exists("friend_activity_logs"):
        op.drop_index("idx_fal_unnotified", table_name="friend_activity_logs")
        op.drop_table("friend_activity_logs")
    if _column_exists("users", "comeback_card_pending"):
        op.drop_column("users", "comeback_card_pending")
    if _column_exists("users", "last_streak_milestone_claimed"):
        op.drop_column("users", "last_streak_milestone_claimed")
