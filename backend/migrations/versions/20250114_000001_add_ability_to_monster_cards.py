"""Add ability column to monster_cards table.

Revision ID: 20250114_000001
Revises: 20250111_000001
Create Date: 2025-01-14

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250114_000001"
down_revision = "20250111_000001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "monster_cards",
        sa.Column("ability", sa.String(50), nullable=True),
    )


def downgrade():
    op.drop_column("monster_cards", "ability")
