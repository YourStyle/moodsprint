"""Add is_final flag to campaign_levels

Revision ID: 20250107_000002
Revises: 20250107_000001
Create Date: 2025-01-07
"""

import sqlalchemy as sa
from alembic import op

revision = "20250107_000002"
down_revision = "20250107_000001"
branch_labels = None
depends_on = None


def upgrade():
    # Add is_final column to campaign_levels
    # If True, completing this level ends the chapter and shows outro
    op.add_column(
        "campaign_levels",
        sa.Column(
            "is_final",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="If true, completing this level ends the chapter and shows outro",
        ),
    )


def downgrade():
    op.drop_column("campaign_levels", "is_final")
