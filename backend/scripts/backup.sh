#!/bin/bash
# Backup script for MemoryMesh database

set -e

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

DB_URL="${MEMORY_DATABASE_URL:-sqlite+aiosqlite:///./memory_layer.db}"

# Extract database connection details
if [[ $DB_URL == postgresql* ]]; then
    # PostgreSQL backup
    DB_NAME=$(echo $DB_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')
    DB_USER=$(echo $DB_URL | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
    DB_PASS=$(echo $DB_URL | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')
    DB_HOST=$(echo $DB_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo $DB_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p' || echo "5432")
    
    export PGPASSWORD="$DB_PASS"
    BACKUP_FILE="$BACKUP_DIR/memorymesh_${TIMESTAMP}.sql.gz"
    
    mkdir -p "$BACKUP_DIR"
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" | gzip > "$BACKUP_FILE"
    
    echo "Backup created: $BACKUP_FILE"
    
    # Cleanup old backups
    find "$BACKUP_DIR" -name "memorymesh_*.sql.gz" -mtime +$RETENTION_DAYS -delete
    
elif [[ $DB_URL == sqlite* ]]; then
    # SQLite backup
    DB_FILE=$(echo $DB_URL | sed -n 's/.*:\/\/\/\(.*\)/\1/p')
    BACKUP_FILE="$BACKUP_DIR/memorymesh_${TIMESTAMP}.db"
    
    mkdir -p "$BACKUP_DIR"
    cp "$DB_FILE" "$BACKUP_FILE"
    gzip "$BACKUP_FILE"
    
    echo "Backup created: ${BACKUP_FILE}.gz"
    
    # Cleanup old backups
    find "$BACKUP_DIR" -name "memorymesh_*.db.gz" -mtime +$RETENTION_DAYS -delete
else
    echo "Unsupported database type: $DB_URL"
    exit 1
fi

echo "Backup completed successfully"

