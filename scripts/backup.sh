#!/bin/sh
# Database backup script for MoodSprint
# Runs daily via cron and maintains BACKUP_RETENTION_DAYS days of backups

set -e

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/moodsprint_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-7}

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Create compressed backup
echo "[$(date)] Starting backup..."
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    -h "${PGHOST}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    --no-owner \
    --no-acl \
    | gzip > "${BACKUP_FILE}"

# Check backup was created successfully
if [ -f "${BACKUP_FILE}" ]; then
    SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo "[$(date)] Backup completed: ${BACKUP_FILE} (${SIZE})"
else
    echo "[$(date)] ERROR: Backup failed!"
    exit 1
fi

# Remove old backups
echo "[$(date)] Cleaning up backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "moodsprint_*.sql.gz" -mtime +${RETENTION_DAYS} -delete

# List current backups
echo "[$(date)] Current backups:"
ls -lh "${BACKUP_DIR}"/moodsprint_*.sql.gz 2>/dev/null || echo "No backups found"

echo "[$(date)] Backup process completed."
