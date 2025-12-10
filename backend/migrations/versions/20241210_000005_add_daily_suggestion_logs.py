"""Add daily_suggestion_logs table

Revision ID: 006_daily_suggestion_logs
Revises: 005_work_schedule
Create Date: 2024-12-10 00:00:05

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "006_daily_suggestion_logs"
down_revision = "005_work_schedule"
branch_labels = None
depends_on = None


def upgrade():
    # Create daily_suggestion_logs table
    op.create_table(
        "daily_suggestion_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "date", name="uq_daily_suggestion_user_date"),
    )

    # Create index for faster lookups
    op.create_index(
        "ix_daily_suggestion_logs_user_date",
        "daily_suggestion_logs",
        ["user_id", "date"],
    )


def downgrade():
    op.drop_index(
        "ix_daily_suggestion_logs_user_date", table_name="daily_suggestion_logs"
    )
    op.drop_table("daily_suggestion_logs")
