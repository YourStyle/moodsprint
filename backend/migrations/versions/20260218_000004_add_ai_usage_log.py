"""Add AI usage log table for tracking OpenAI API costs.

Revision ID: 20260218_000004
Revises: 20260218_000003
Create Date: 2026-02-18
"""

import sqlalchemy as sa
from alembic import op

revision = "20260218_000004"
down_revision = "20260218_000003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_usage_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("service_name", sa.String(100), nullable=False),
        sa.Column("model", sa.String(50), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "completion_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "estimated_cost_usd", sa.Float(), nullable=False, server_default="0.0"
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("endpoint", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_usage_log_user_id", "ai_usage_log", ["user_id"])
    op.create_index("ix_ai_usage_log_service_name", "ai_usage_log", ["service_name"])
    op.create_index("ix_ai_usage_log_endpoint", "ai_usage_log", ["endpoint"])
    op.create_index("ix_ai_usage_log_created_at", "ai_usage_log", ["created_at"])


def downgrade():
    op.drop_index("ix_ai_usage_log_created_at", table_name="ai_usage_log")
    op.drop_index("ix_ai_usage_log_endpoint", table_name="ai_usage_log")
    op.drop_index("ix_ai_usage_log_service_name", table_name="ai_usage_log")
    op.drop_index("ix_ai_usage_log_user_id", table_name="ai_usage_log")
    op.drop_table("ai_usage_log")
