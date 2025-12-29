"""Add image_url to campaign_chapters

Revision ID: 20241229_000001
Revises: 20241226_000018
Create Date: 2024-12-29

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20241229_000001"
down_revision = "20241226_000018"
branch_labels = None
depends_on = None


def upgrade():
    # Add image_url column to campaign_chapters
    with op.batch_alter_table("campaign_chapters", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("image_url", sa.String(length=500), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("campaign_chapters", schema=None) as batch_op:
        batch_op.drop_column("image_url")
