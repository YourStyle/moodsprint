"""Fix campaign_chapters number constraint to be unique per genre.

Revision ID: 20241230_000002
Revises: 20241230_000001
Create Date: 2024-12-30
"""

from alembic import op

# revision identifiers
revision = "20241230_000002"
down_revision = "20241230_000001"
branch_labels = None
depends_on = None


def upgrade():
    # Drop the global unique constraint on number
    op.drop_constraint(
        "campaign_chapters_number_key", "campaign_chapters", type_="unique"
    )

    # Add composite unique constraint (genre, number)
    op.create_unique_constraint(
        "unique_chapter_number_per_genre",
        "campaign_chapters",
        ["genre", "number"],
    )


def downgrade():
    # Drop composite constraint
    op.drop_constraint(
        "unique_chapter_number_per_genre", "campaign_chapters", type_="unique"
    )

    # Restore global unique constraint
    op.create_unique_constraint(
        "campaign_chapters_number_key", "campaign_chapters", ["number"]
    )
