"""Add reward_card_id and reward_shown to shared_tasks.

Revision ID: 20260217_000001
Revises: 20260216_000003
Create Date: 2026-02-17
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260217_000001"
down_revision = "b5c6d7e8f9a0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "shared_tasks",
        sa.Column("reward_card_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "shared_tasks",
        sa.Column(
            "reward_shown",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_shared_tasks_reward_card",
        "shared_tasks",
        "user_cards",
        ["reward_card_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint(
        "fk_shared_tasks_reward_card", "shared_tasks", type_="foreignkey"
    )
    op.drop_column("shared_tasks", "reward_shown")
    op.drop_column("shared_tasks", "reward_card_id")
