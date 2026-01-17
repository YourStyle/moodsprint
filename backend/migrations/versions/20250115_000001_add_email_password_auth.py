"""Add email/password authentication fields.

Revision ID: 20250115_000001
Revises:
Create Date: 2025-01-15

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250115_000001"
down_revision = "20250114_000001"
branch_labels = None
depends_on = None


def upgrade():
    # Add email and password_hash columns
    op.add_column("users", sa.Column("email", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))

    # Make telegram_id nullable (for email-only users)
    op.alter_column(
        "users",
        "telegram_id",
        existing_type=sa.BigInteger(),
        nullable=True,
    )

    # Add unique index on email
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade():
    op.drop_index("ix_users_email", table_name="users")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "email")
    op.alter_column(
        "users",
        "telegram_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
