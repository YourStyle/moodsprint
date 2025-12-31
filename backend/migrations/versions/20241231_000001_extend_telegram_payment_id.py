"""Extend telegram_payment_id column to 255 chars.

Revision ID: 20241231_000001
Revises: 20241230_000003
Create Date: 2024-12-31
"""

import sqlalchemy as sa
from alembic import op

revision = "20241231_000001"
down_revision = "20241230_000003"
branch_labels = None
depends_on = None


def upgrade():
    # Extend telegram_payment_id to accommodate longer Telegram payment IDs
    op.alter_column(
        "stars_transactions",
        "telegram_payment_id",
        existing_type=sa.String(100),
        type_=sa.String(255),
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        "stars_transactions",
        "telegram_payment_id",
        existing_type=sa.String(255),
        type_=sa.String(100),
        existing_nullable=True,
    )
