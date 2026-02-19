"""Add decomposition_templates table for AI cache template library.

Revision ID: 20260218_000001
Revises: 20260217_000001
Create Date: 2026-02-18
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260218_000001"
down_revision = "20260217_000001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "decomposition_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title_pattern", sa.String(500), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("strategy", sa.String(20), nullable=False, server_default="standard"),
        sa.Column("mood_min", sa.Integer(), nullable=True),
        sa.Column("mood_max", sa.Integer(), nullable=True),
        sa.Column("energy_min", sa.Integer(), nullable=True),
        sa.Column("energy_max", sa.Integer(), nullable=True),
        sa.Column("subtasks", sa.JSON(), nullable=False),
        sa.Column("no_new_steps", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("usage_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_decomposition_templates_category",
        "decomposition_templates",
        ["category"],
    )
    op.create_index(
        "ix_decomposition_templates_active",
        "decomposition_templates",
        ["is_active"],
    )


def downgrade():
    op.drop_index("ix_decomposition_templates_active")
    op.drop_index("ix_decomposition_templates_category")
    op.drop_table("decomposition_templates")
