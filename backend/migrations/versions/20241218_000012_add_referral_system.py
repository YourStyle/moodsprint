"""Add referral system and healing tracking fields.

Revision ID: 20241218_000012
Revises: 20241213_000011
Create Date: 2024-12-18 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20241218_000012"
down_revision = "20241213_000011"
branch_labels = None
depends_on = None


def upgrade():
    # Add referral system fields to users table
    op.add_column(
        "users",
        sa.Column("referred_by", sa.Integer(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "referral_reward_given",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    # Add foreign key constraint
    op.create_foreign_key(
        "fk_users_referred_by",
        "users",
        "users",
        ["referred_by"],
        ["id"],
    )

    # Add healing tracking fields to user_profiles table
    op.add_column(
        "user_profiles",
        sa.Column("heals_today", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "user_profiles",
        sa.Column("last_heal_date", sa.Date(), nullable=True),
    )


def downgrade():
    # Remove healing tracking fields
    op.drop_column("user_profiles", "last_heal_date")
    op.drop_column("user_profiles", "heals_today")

    # Remove referral fields
    op.drop_constraint("fk_users_referred_by", "users", type_="foreignkey")
    op.drop_column("users", "referral_reward_given")
    op.drop_column("users", "referred_by")
