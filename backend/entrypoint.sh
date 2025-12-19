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

# Run migrations with advisory lock (only one container runs migrations at a time)
echo "Attempting to acquire migration lock..."
python -c "
import os
import sys
import subprocess
from sqlalchemy import create_engine, text

db_url = os.environ.get('DATABASE_URL')
engine = create_engine(db_url)

LOCK_ID = 12345  # Unique lock ID for migrations

with engine.connect() as conn:
    # Try to acquire advisory lock (non-blocking)
    result = conn.execute(text(f'SELECT pg_try_advisory_lock({LOCK_ID})')).scalar()

    if result:
        print('Migration lock acquired - running migrations...')
        try:
            # Run migrations
            proc = subprocess.run(['flask', 'db', 'upgrade'], capture_output=True, text=True)
            print(proc.stdout)
            if proc.stderr:
                print(proc.stderr, file=sys.stderr)

            if proc.returncode != 0:
                print(f'ERROR: Migration failed with exit code {proc.returncode}', file=sys.stderr)
                # Release lock before exiting
                conn.execute(text(f'SELECT pg_advisory_unlock({LOCK_ID})'))
                conn.commit()
                sys.exit(1)

            print('Migrations completed successfully')

            # Show current revision
            proc = subprocess.run(['flask', 'db', 'current'], capture_output=True, text=True)
            print(f'Current revision: {proc.stdout.strip()}')

        finally:
            # Release lock
            conn.execute(text(f'SELECT pg_advisory_unlock({LOCK_ID})'))
            conn.commit()
            print('Migration lock released')
    else:
        print('Another container is running migrations - waiting...')
        # Wait for the other container to finish (blocking lock)
        conn.execute(text(f'SELECT pg_advisory_lock({LOCK_ID})'))
        conn.execute(text(f'SELECT pg_advisory_unlock({LOCK_ID})'))
        conn.commit()
        print('Other container finished migrations')

        # Verify migrations are applied
        proc = subprocess.run(['flask', 'db', 'current'], capture_output=True, text=True)
        print(f'Current revision: {proc.stdout.strip()}')
" || {
    echo "Migration process failed!"
    exit 1
}

echo "=== Starting application ==="
exec "$@"
