#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for database..."
python -c "
import time
import os
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

db_url = os.environ.get('DATABASE_URL')
engine = create_engine(db_url)

for i in range(30):
    try:
        engine.connect()
        print('Database is ready!')
        break
    except OperationalError:
        print(f'Waiting for database... ({i+1}/30)')
        time.sleep(1)
else:
    print('Could not connect to database')
    exit(1)
"

# Run migrations with lock to prevent race condition with multiple replicas
echo "Running database migrations..."
python -c "
import os
import sys
from sqlalchemy import create_engine, text

db_url = os.environ.get('DATABASE_URL')
engine = create_engine(db_url)

# Use advisory lock to ensure only one instance runs migrations
with engine.connect() as conn:
    # Try to acquire lock (lock_id = 1 for migrations)
    result = conn.execute(text('SELECT pg_try_advisory_lock(1)')).scalar()
    if result:
        print('Acquired migration lock, running migrations...')
        conn.execute(text('COMMIT'))  # Release transaction to allow DDL

        # Run flask db upgrade
        import subprocess
        exit_code = subprocess.call(['flask', 'db', 'upgrade'])

        # Release lock
        conn.execute(text('SELECT pg_advisory_unlock(1)'))
        print('Migrations completed, lock released')
        sys.exit(exit_code)
    else:
        print('Another instance is running migrations, skipping...')
        # Wait a bit for migrations to complete
        import time
        time.sleep(5)
"

echo "Starting application..."
exec "$@"
