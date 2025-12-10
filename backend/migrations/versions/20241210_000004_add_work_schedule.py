"""Add work schedule fields to user_profiles

Revision ID: 005_work_schedule
Revises: 004_task_classification
Create Date: 2024-12-10 00:00:04

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_work_schedule'
down_revision = '004_task_classification'
branch_labels = None
depends_on = None


def upgrade():
    # Add work schedule columns to user_profiles table
    op.add_column('user_profiles', sa.Column('work_start_time', sa.String(5), nullable=True, server_default='09:00'))
    op.add_column('user_profiles', sa.Column('work_end_time', sa.String(5), nullable=True, server_default='18:00'))
    op.add_column('user_profiles', sa.Column('work_days', sa.JSON(), nullable=True))
    op.add_column('user_profiles', sa.Column('timezone', sa.String(50), nullable=True, server_default='Europe/Moscow'))


def downgrade():
    op.drop_column('user_profiles', 'timezone')
    op.drop_column('user_profiles', 'work_days')
    op.drop_column('user_profiles', 'work_end_time')
    op.drop_column('user_profiles', 'work_start_time')
