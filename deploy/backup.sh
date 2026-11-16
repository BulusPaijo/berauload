#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || { echo 'File .env belum tersedia' >&2; exit 1; }
set -a; source .env; set +a
umask 077
mkdir -p backups
STAMP="$(date +%Y%m%d_%H%M%S)"
DBFILE="backups/berauload_db_${STAMP}.sql.gz"
UPLOADFILE="backups/berauload_uploads_${STAMP}.tar.gz"
docker compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl | gzip > "$DBFILE"
docker run --rm -v berauload_uploads:/data:ro -v "$PWD/backups:/backup" alpine:3.20 sh -c "cd /data && tar -czf /backup/berauload_uploads_${STAMP}.tar.gz ."
chmod 600 "$DBFILE" "$UPLOADFILE"
find backups -maxdepth 1 -name 'berauload_*.gz' -type f -mtime +30 -delete
printf 'Backup sukses:\n%s\n%s\n' "$DBFILE" "$UPLOADFILE"
