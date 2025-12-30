"""Add Sparks currency and TON wallet support.

Revision ID: 20241230_000003
Revises: 20241230_000002
Create Date: 2024-12-30

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20241230_000003"
down_revision = "20241230_000002"
branch_labels = None
depends_on = None


def upgrade():
    # Add sparks to users table (internal currency)
    op.add_column("users", sa.Column("sparks", sa.Integer(), nullable=True))
    op.execute("UPDATE users SET sparks = 0")
    op.alter_column("users", "sparks", nullable=False, server_default="0")

    # Add TON wallet address to users
    op.add_column(
        "users", sa.Column("ton_wallet_address", sa.String(48), nullable=True)
    )
    op.create_index("ix_users_ton_wallet_address", "users", ["ton_wallet_address"])

    # Create sparks_transactions table
    op.create_table(
        "sparks_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        # Types: card_sale, card_purchase, campaign_reward, ton_deposit, stars_purchase
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("reference_type", sa.String(30), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_sparks_transactions_user_id", "sparks_transactions", ["user_id"]
    )

    # Create ton_deposits table for tracking TON blockchain deposits
    op.create_table(
        "ton_deposits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),  # Null if user not found
        sa.Column("tx_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("sender_address", sa.String(48), nullable=False),
        sa.Column("amount_nano", sa.BigInteger(), nullable=False),  # In nanoTON
        sa.Column("amount_ton", sa.Numeric(20, 9), nullable=False),  # In TON
        sa.Column("memo", sa.String(200), nullable=True),  # User ID or comment
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("sparks_credited", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_ton_deposits_tx_hash", "ton_deposits", ["tx_hash"])
    op.create_index("ix_ton_deposits_user_id", "ton_deposits", ["user_id"])
    op.create_index("ix_ton_deposits_status", "ton_deposits", ["status"])

    # Update marketplace to use sparks (rename price_stars to price_sparks)
    op.add_column(
        "market_listings", sa.Column("price_sparks", sa.Integer(), nullable=True)
    )
    op.execute("UPDATE market_listings SET price_sparks = price_stars")
    op.alter_column("market_listings", "price_sparks", nullable=False)


def downgrade():
    op.drop_column("market_listings", "price_sparks")
    op.drop_table("ton_deposits")
    op.drop_table("sparks_transactions")
    op.drop_index("ix_users_ton_wallet_address", table_name="users")
    op.drop_column("users", "ton_wallet_address")
    op.drop_column("users", "sparks")
