"""Add shared_tasks table.

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
Create Date: 2026-02-16 00:00:03
"""

import sqlalchemy as sa
from alembic import op

revision = "b5c6d7e8f9a0"
down_revision = "a4b5c6d7e8f9"
branch_labels = None
depends_on = None


def upgrade():
    # Idempotent: check if table exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "shared_tasks" in inspector.get_table_names():
        return

    op.create_table(
        "shared_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("assignee_id", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(length=20), server_default="pending", nullable=False
        ),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True
        ),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "assignee_id", name="unique_shared_task"),
    )

    op.create_index("ix_shared_tasks_task_id", "shared_tasks", ["task_id"])
    op.create_index("ix_shared_tasks_owner_id", "shared_tasks", ["owner_id"])
    op.create_index("ix_shared_tasks_assignee_id", "shared_tasks", ["assignee_id"])


def downgrade():
    op.drop_table("shared_tasks")
