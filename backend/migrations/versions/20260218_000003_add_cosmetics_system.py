"""Add cosmetics system (card frames, profile frames).

Adds cosmetic fields to user_profiles:
- owned_cosmetics: JSON list of owned cosmetic IDs
- equipped_card_frame: currently equipped card frame
- equipped_profile_frame: currently equipped profile frame

Revision ID: 20260218_000003
Revises: 20260218_000002
Create Date: 2026-02-18
"""

import sqlalchemy as sa
from alembic import op

revision = "20260218_000003"
down_revision = "20260218_000002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user_profiles",
        sa.Column("owned_cosmetics", sa.JSON(), server_default="[]", nullable=False),
    )
    op.add_column(
        "user_profiles",
        sa.Column("equipped_card_frame", sa.String(50), nullable=True),
    )
    op.add_column(
        "user_profiles",
        sa.Column("equipped_profile_frame", sa.String(50), nullable=True),
    )


def downgrade():
    op.drop_column("user_profiles", "equipped_profile_frame")
    op.drop_column("user_profiles", "equipped_card_frame")
    op.drop_column("user_profiles", "owned_cosmetics")
