"""Add defeated monsters tracking and period-based monster rotation.

Revision ID: 000010
Revises: 000009
Create Date: 2024-12-12

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "000010"
down_revision = "000009"
branch_labels = None
depends_on = None


def upgrade():
    # Add period_start column to daily_monsters
    op.add_column(
        "daily_monsters",
        sa.Column("period_start", sa.Date(), nullable=True),
    )

    # Create defeated_monsters table
    op.create_table(
        "defeated_monsters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("monster_id", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("defeated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["monster_id"], ["monsters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "monster_id", "period_start", name="unique_user_monster_period"
        ),
    )
    op.create_index("ix_defeated_monsters_user_id", "defeated_monsters", ["user_id"])

    # Add unique constraint for period monsters
    # First drop old constraint if exists (wrapped in try-except for safety)
    try:
        op.drop_constraint("unique_daily_monster", "daily_monsters", type_="unique")
    except Exception:
        pass

    # Add new constraint for period-based uniqueness
    op.create_unique_constraint(
        "unique_period_monster",
        "daily_monsters",
        ["genre", "period_start", "slot_number"],
    )


def downgrade():
    op.drop_constraint("unique_period_monster", "daily_monsters", type_="unique")
    op.drop_index("ix_defeated_monsters_user_id", table_name="defeated_monsters")
    op.drop_table("defeated_monsters")
    op.drop_column("daily_monsters", "period_start")
