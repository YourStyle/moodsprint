"""Add scheduled_at field to tasks for reminders

Revision ID: 007_add_scheduled_at
Revises: 006_daily_suggestion_logs
Create Date: 2024-12-10 00:00:06

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007_add_scheduled_at'
down_revision = '006_daily_suggestion_logs'
branch_labels = None
depends_on = None


def upgrade():
    # Add scheduled_at column to tasks table for reminder notifications
    op.add_column('tasks', sa.Column('scheduled_at', sa.DateTime(), nullable=True))

    # Add reminder_sent flag to track if reminder was sent
    op.add_column('tasks', sa.Column('reminder_sent', sa.Boolean(), nullable=False, server_default='false'))

    # Create index for finding tasks that need reminders
    op.create_index('ix_tasks_scheduled_at', 'tasks', ['scheduled_at'], unique=False)


def downgrade():
    op.drop_index('ix_tasks_scheduled_at', table_name='tasks')
    op.drop_column('tasks', 'reminder_sent')
    op.drop_column('tasks', 'scheduled_at')
