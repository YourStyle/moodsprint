"""Idempotent migration helpers.

These helpers allow migrations to be safely re-run without failing
if objects already exist or don't exist.
"""

from alembic import op
from sqlalchemy import text


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = op.get_bind()
    result = conn.execute(
        text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :table_name)"
        ),
        {"table_name": table_name},
    )
    return result.scalar()


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    result = conn.execute(
        text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :table_name "
            "AND column_name = :column_name)"
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return result.scalar()


def index_exists(index_name: str) -> bool:
    """Check if an index exists."""
    conn = op.get_bind()
    result = conn.execute(
        text(
            "SELECT EXISTS (SELECT 1 FROM pg_indexes "
            "WHERE schemaname = 'public' AND indexname = :index_name)"
        ),
        {"index_name": index_name},
    )
    return result.scalar()


def constraint_exists(table_name: str, constraint_name: str) -> bool:
    """Check if a constraint exists on a table."""
    conn = op.get_bind()
    result = conn.execute(
        text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.table_constraints "
            "WHERE table_schema = 'public' AND table_name = :table_name "
            "AND constraint_name = :constraint_name)"
        ),
        {"table_name": table_name, "constraint_name": constraint_name},
    )
    return result.scalar()


def create_table_if_not_exists(table_name: str, *columns, **kwargs):
    """Create a table only if it doesn't exist."""
    if not table_exists(table_name):
        op.create_table(table_name, *columns, **kwargs)
        return True
    return False


def drop_table_if_exists(table_name: str):
    """Drop a table only if it exists."""
    if table_exists(table_name):
        op.drop_table(table_name)
        return True
    return False


def add_column_if_not_exists(table_name: str, column):
    """Add a column only if it doesn't exist."""
    if not column_exists(table_name, column.name):
        op.add_column(table_name, column)
        return True
    return False


def drop_column_if_exists(table_name: str, column_name: str):
    """Drop a column only if it exists."""
    if column_exists(table_name, column_name):
        op.drop_column(table_name, column_name)
        return True
    return False


def create_index_if_not_exists(index_name: str, table_name: str, columns, **kwargs):
    """Create an index only if it doesn't exist."""
    if not index_exists(index_name):
        op.create_index(index_name, table_name, columns, **kwargs)
        return True
    return False


def drop_index_if_exists(index_name: str, table_name: str = None):
    """Drop an index only if it exists."""
    if index_exists(index_name):
        op.drop_index(index_name, table_name=table_name)
        return True
    return False
