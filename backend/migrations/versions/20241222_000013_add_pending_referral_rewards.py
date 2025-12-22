"""Add pending_referral_rewards table for deferred reward notifications.

Revision ID: 20241222_000013
Revises: 20241218_000012
Create Date: 2024-12-22 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20241222_000013"
down_revision = "20241218_000012"
branch_labels = None
depends_on = None


def upgrade():
    # Create pending_referral_rewards table
    op.create_table(
        "pending_referral_rewards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("friend_id", sa.Integer(), nullable=False),
        sa.Column("friend_name", sa.String(length=255), nullable=True),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("is_referrer", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_claimed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["friend_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["card_id"],
            ["user_cards.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pending_referral_rewards_user_id",
        "pending_referral_rewards",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_pending_referral_rewards_is_claimed",
        "pending_referral_rewards",
        ["is_claimed"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_pending_referral_rewards_is_claimed", table_name="pending_referral_rewards"
    )
    op.drop_index(
        "ix_pending_referral_rewards_user_id", table_name="pending_referral_rewards"
    )
    op.drop_table("pending_referral_rewards")
