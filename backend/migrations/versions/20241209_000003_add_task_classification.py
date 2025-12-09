"""Add task classification fields and postpone_logs table

Revision ID: 004_task_classification
Revises: 003_add_focus_task_id
Create Date: 2024-12-09 00:00:03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_task_classification'
down_revision = '003_add_focus_task_id'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to tasks table
    op.add_column('tasks', sa.Column('task_type', sa.String(50), nullable=True))
    op.add_column('tasks', sa.Column('preferred_time', sa.String(20), nullable=True))
    op.add_column('tasks', sa.Column('postponed_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('tasks', sa.Column('original_due_date', sa.Date(), nullable=True))

    # Create postpone_logs table
    op.create_table(
        'postpone_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('tasks_postponed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('priority_changes', sa.JSON(), nullable=True),
        sa.Column('notified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'date', name='uq_user_date_postpone')
    )
    op.create_index(op.f('ix_postpone_logs_user_id'), 'postpone_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_postpone_logs_date'), 'postpone_logs', ['date'], unique=False)


def downgrade():
    # Drop postpone_logs table
    op.drop_index(op.f('ix_postpone_logs_date'), table_name='postpone_logs')
    op.drop_index(op.f('ix_postpone_logs_user_id'), table_name='postpone_logs')
    op.drop_table('postpone_logs')

    # Remove columns from tasks table
    op.drop_column('tasks', 'original_due_date')
    op.drop_column('tasks', 'postponed_count')
    op.drop_column('tasks', 'preferred_time')
    op.drop_column('tasks', 'task_type')
