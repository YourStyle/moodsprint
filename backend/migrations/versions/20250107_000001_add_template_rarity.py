"""Add rarity field to card_templates

Revision ID: 20250107_000001
Revises: 20241231_000001
Create Date: 2025-01-07
"""

import sqlalchemy as sa
from alembic import op

revision = "20250107_000001"
down_revision = "20241231_000001"
branch_labels = None
depends_on = None


def upgrade():
    # Add rarity column to card_templates (nullable - NULL means universal template)
    op.add_column(
        "card_templates",
        sa.Column(
            "rarity",
            sa.String(20),
            nullable=True,
            comment="If set, template only drops for this rarity. NULL = universal",
        ),
    )

    # Add index for faster lookups
    op.create_index(
        "ix_card_templates_genre_rarity",
        "card_templates",
        ["genre", "rarity", "is_active"],
    )


def downgrade():
    op.drop_index("ix_card_templates_genre_rarity", table_name="card_templates")
    op.drop_column("card_templates", "rarity")
