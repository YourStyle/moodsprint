#!/bin/bash
set -e

echo "=== Backend entrypoint starting ==="
echo "Environment: ${FLASK_ENV:-production}"

# Wait for database to be ready
echo "Waiting for database..."
python -c "
import time
import os
from sqlalchemy import create_engine, text

db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print('ERROR: DATABASE_URL not set!')
    exit(1)

engine = create_engine(db_url)

for i in range(30):
    try:
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        print('Database is ready!')
        break
    except Exception as e:
        print(f'Waiting for database... ({i+1}/30) - {e}')
        time.sleep(1)
else:
    print('ERROR: Could not connect to database after 30 attempts')
    exit(1)
" || {
    echo "Database connection check failed"
    exit 1
}

# Run migrations
echo "Running database migrations..."
flask db upgrade 2>&1 | tee /tmp/migration.log
MIGRATION_EXIT_CODE=${PIPESTATUS[0]}

if [ $MIGRATION_EXIT_CODE -ne 0 ]; then
    echo "=== MIGRATION FAILED ==="
    cat /tmp/migration.log
    echo "========================"
    # Don't exit - let the app start anyway, maybe migrations were already applied
    echo "WARNING: Migration failed but continuing startup..."
else
    echo "Migrations completed successfully"
fi

# Show current migration state
echo "Current database revision:"
flask db current 2>&1 || echo "Could not get current revision"

echo "=== Starting application ==="
exec "$@"
