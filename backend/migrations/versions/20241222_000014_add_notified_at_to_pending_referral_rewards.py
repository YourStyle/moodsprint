"""Add notified_at to pending_referral_rewards.

Revision ID: 20241222_000014
Revises: 20241222_000013_add_pending_referral_rewards
Create Date: 2024-12-22

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20241222_000014"
down_revision = "20241222_000013_add_pending_referral_rewards"
branch_labels = None
depends_on = None


def upgrade():
    """Add notified_at column to pending_referral_rewards table."""
    op.add_column(
        "pending_referral_rewards",
        sa.Column("notified_at", sa.DateTime(), nullable=True),
    )


def downgrade():
    """Remove notified_at column from pending_referral_rewards table."""
    op.drop_column("pending_referral_rewards", "notified_at")
