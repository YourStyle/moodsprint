"""Convert energy rewards to max_energy and add tracking column.

Revision ID: 20260214_000001
Revises: 20260212_000001
Create Date: 2026-02-14

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260214_000001"
down_revision = "20260212_000001"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Convert existing "energy" rewards to "max_energy"
    op.execute(
        """
        UPDATE level_rewards
        SET reward_type = 'max_energy'
        WHERE reward_type = 'energy'
        """
    )

    # 2. Add tracking column for retroactive energy limit catch-up
    op.add_column(
        "user_profiles",
        sa.Column(
            "energy_limit_updated_to_level",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade():
    op.drop_column("user_profiles", "energy_limit_updated_to_level")

    # Revert max_energy rewards back to energy
    op.execute(
        """
        UPDATE level_rewards
        SET reward_type = 'energy'
        WHERE reward_type = 'max_energy'
        """
    )
