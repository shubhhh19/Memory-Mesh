#!/usr/bin/env bash
# Simple database backup helper for Postgres or SQLite.

set -euo pipefail

DATABASE_URL="${DATABASE_URL:-}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

if [[ -z "${DATABASE_URL}" ]]; then
  echo "DATABASE_URL is required" >&2
  exit 1
fi

mkdir -p "${BACKUP_DIR}"
timestamp="$(date -u +"%Y%m%dT%H%M%SZ")"

if [[ "${DATABASE_URL}" == postgres* ]] || [[ "${DATABASE_URL}" == postgresql* ]]; then
  outfile="${BACKUP_DIR}/memory_layer_${timestamp}.dump.gz"
  echo "Creating Postgres backup at ${outfile}"
  pg_dump --format=custom "${DATABASE_URL}" | gzip > "${outfile}"
elif [[ "${DATABASE_URL}" == sqlite* ]]; then
  db_path="${DATABASE_URL#sqlite:///}"
  outfile="${BACKUP_DIR}/memory_layer_${timestamp}.sqlite"
  echo "Creating SQLite backup at ${outfile}"
  cp "${db_path}" "${outfile}"
else
  echo "Unsupported DATABASE_URL scheme" >&2
  exit 1
fi

find "${BACKUP_DIR}" -type f -mtime +"${RETENTION_DAYS}" -delete
echo "Backup completed: ${outfile}"
