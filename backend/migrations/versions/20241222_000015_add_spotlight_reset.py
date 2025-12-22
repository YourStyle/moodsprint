"""Add spotlight_reset_at field to user_profiles.

Revision ID: 20241222_000015
Revises: 20241222_000014
Create Date: 2024-12-22

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20241222_000015"
down_revision = "20241222_000014"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user_profiles",
        sa.Column("spotlight_reset_at", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_column("user_profiles", "spotlight_reset_at")
