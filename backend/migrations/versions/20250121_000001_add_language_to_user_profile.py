"""Add language field to user_profiles.

Revision ID: 20250121_000001
Revises: 20250119_000001
Create Date: 2025-01-21

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250121_000001"
down_revision = "20250119_000001"
branch_labels = None
depends_on = None


def upgrade():
    # Add language column with default 'ru'
    op.add_column(
        "user_profiles",
        sa.Column("language", sa.String(5), nullable=False, server_default="ru"),
    )


def downgrade():
    op.drop_column("user_profiles", "language")
