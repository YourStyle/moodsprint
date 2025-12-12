"""Add turn-based battle system tables.

Revision ID: 000009
Revises: 000008
Create Date: 2024-12-12

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "000009"
down_revision = "000008"
branch_labels = None
depends_on = None


def upgrade():
    # Create monster_cards table
    op.create_table(
        "monster_cards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("monster_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("hp", sa.Integer(), default=50, nullable=False),
        sa.Column("attack", sa.Integer(), default=15, nullable=False),
        sa.Column("emoji", sa.String(10), default="👾"),
        sa.Column("image_url", sa.String(512), nullable=True),
        sa.Column("rarity", sa.String(20), default="common"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["monster_id"], ["monsters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_monster_cards_monster_id", "monster_cards", ["monster_id"])

    # Create active_battles table
    op.create_table(
        "active_battles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("monster_id", sa.Integer(), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), default="active"),
        sa.Column("current_round", sa.Integer(), default=1),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["monster_id"], ["monsters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_active_battles_user_id", "active_battles", ["user_id"])


def downgrade():
    op.drop_index("ix_active_battles_user_id", table_name="active_battles")
    op.drop_table("active_battles")
    op.drop_index("ix_monster_cards_monster_id", table_name="monster_cards")
    op.drop_table("monster_cards")
