"""Add star_conditions to campaign_levels

Revision ID: 20250111_000001
Revises: 20250107_000002
Create Date: 2025-01-11
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20250111_000001"
down_revision = "20250107_000002"
branch_labels = None
depends_on = None


def upgrade():
    # Add star_conditions column to campaign_levels
    # JSON format:
    # {
    #   "base": 1,  # Base stars for winning
    #   "conditions": [
    #     {"type": "rounds_max", "value": 5, "stars": 1},      # +1 if rounds <= 5
    #     {"type": "rounds_max", "value": 10, "stars": 0.5},   # +0.5 if rounds <= 10
    #     {"type": "cards_lost_max", "value": 0, "stars": 1},  # +1 if no cards lost
    #     {"type": "cards_lost_max", "value": 1, "stars": 0.5},# +0.5 if <=1 card lost
    #     {"type": "hp_remaining_min", "value": 50, "stars": 0.5},  # +0.5 if HP >= 50%
    #   ]
    # }
    op.add_column(
        "campaign_levels",
        sa.Column(
            "star_conditions",
            postgresql.JSONB(),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("campaign_levels", "star_conditions")
