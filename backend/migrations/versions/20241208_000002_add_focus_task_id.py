"""Add task_id to focus_sessions table

Revision ID: 003_add_focus_task_id
Revises: 002_add_due_date
Create Date: 2024-12-08 00:00:02

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_add_focus_task_id'
down_revision = '002_add_due_date'
branch_labels = None
depends_on = None


def upgrade():
    # Add task_id column to focus_sessions table
    op.add_column('focus_sessions', sa.Column('task_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_focus_sessions_task_id',
        'focus_sessions',
        'tasks',
        ['task_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    op.drop_constraint('fk_focus_sessions_task_id', 'focus_sessions', type_='foreignkey')
    op.drop_column('focus_sessions', 'task_id')
