"""Add cards system and task difficulty.

Revision ID: 20241211_000008
Revises: 20241210_000007
Create Date: 2024-12-11 18:00:00

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20241211_000008"
down_revision = "20241210_000007"
branch_labels = None
depends_on = None


def upgrade():
    # Add difficulty column to tasks
    op.add_column("tasks", sa.Column("difficulty", sa.String(20), nullable=True))

    # Create card_templates table
    op.create_table(
        "card_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("genre", sa.String(50), nullable=False),
        sa.Column("base_hp", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("base_attack", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("emoji", sa.String(10), nullable=False, server_default="🃏"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create user_cards table
    op.create_table(
        "user_cards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=True),
        sa.Column("task_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("genre", sa.String(50), nullable=False),
        sa.Column("rarity", sa.String(20), nullable=False, server_default="common"),
        sa.Column("hp", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("attack", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("current_hp", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("emoji", sa.String(10), nullable=False, server_default="🃏"),
        sa.Column("is_in_deck", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_tradeable", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_destroyed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["template_id"], ["card_templates.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_cards_user_id", "user_cards", ["user_id"])

    # Create friendships table
    op.create_table(
        "friendships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("friend_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["friend_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "friend_id", name="uq_friendship"),
    )

    # Create card_trades table
    op.create_table(
        "card_trades",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("receiver_id", sa.Integer(), nullable=False),
        sa.Column("sender_card_id", sa.Integer(), nullable=False),
        sa.Column("receiver_card_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["receiver_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["sender_card_id"], ["user_cards.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["receiver_card_id"], ["user_cards.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("card_trades")
    op.drop_table("friendships")
    op.drop_index("ix_user_cards_user_id", "user_cards")
    op.drop_table("user_cards")
    op.drop_table("card_templates")
    op.drop_column("tasks", "difficulty")
