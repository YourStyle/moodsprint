"""Add multi-card trades support.

Revision ID: 000014
Revises: 000013
Create Date: 2024-12-22

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "000014"
down_revision = "000013"
branch_labels = None
depends_on = None


def upgrade():
    # Add JSON columns for multiple cards
    op.add_column(
        "card_trades",
        sa.Column(
            "sender_card_ids",
            postgresql.JSONB(),
            nullable=True,
            comment="Array of sender card IDs for multi-card trades",
        ),
    )
    op.add_column(
        "card_trades",
        sa.Column(
            "receiver_card_ids",
            postgresql.JSONB(),
            nullable=True,
            comment="Array of receiver card IDs for multi-card exchanges",
        ),
    )


def downgrade():
    op.drop_column("card_trades", "receiver_card_ids")
    op.drop_column("card_trades", "sender_card_ids")
