"""Add due_date to tasks table

Revision ID: 002_add_due_date
Revises: 001_initial
Create Date: 2024-12-08 00:00:01

"""
from alembic import op
import sqlalchemy as sa
from datetime import date


# revision identifiers, used by Alembic.
revision = '002_add_due_date'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    # Add due_date column to tasks table
    op.add_column('tasks', sa.Column('due_date', sa.Date(), nullable=True))
    op.create_index(op.f('ix_tasks_due_date'), 'tasks', ['due_date'], unique=False)

    # Set default value for existing tasks (today's date)
    op.execute(f"UPDATE tasks SET due_date = CURRENT_DATE WHERE due_date IS NULL")


def downgrade():
    op.drop_index(op.f('ix_tasks_due_date'), table_name='tasks')
    op.drop_column('tasks', 'due_date')
