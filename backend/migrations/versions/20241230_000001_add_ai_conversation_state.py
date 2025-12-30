"""Add AI conversation state for genre-based dialogue generation.

Revision ID: 20241230_000001
Revises: 20241229_000001
Create Date: 2024-12-30
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "20241230_000001"
down_revision = "20241229_000001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_conversation_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("genre", sa.String(50), nullable=False, unique=True),
        sa.Column("last_response_id", sa.String(255), nullable=True),
        sa.Column("context_summary", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("ai_conversation_state")
