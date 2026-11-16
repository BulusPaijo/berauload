#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
if ! command -v docker >/dev/null 2>&1; then
  echo 'Docker belum terpasang. Instal Docker Engine dan docker compose plugin pada LXC terlebih dahulu.' >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo 'docker compose plugin tidak ditemukan.' >&2
  exit 1
fi
if [ ! -e .env ]; then
  DBPASS="$(python3 -c 'import secrets;print(secrets.token_hex(24))')"
  ADMINPASS="$(python3 -c 'import secrets;print(secrets.token_urlsafe(24))')"
  cat > .env <<CONFIG
APP_PORT=8092
POSTGRES_USER=berauload
POSTGRES_PASSWORD=${DBPASS}
POSTGRES_DB=berauload
ADMIN_USERNAME=admin
ADMIN_PASSWORD=${ADMINPASS}
# Gunakan true hanya jika diakses lewat HTTPS (reverse proxy).
COOKIE_SECURE=false
CONFIG
  chmod 600 .env
  printf '\nCredential awal dibuat di .env (chmod 600).\nUsername: admin\nPassword: %s\n\n' "$ADMINPASS"
else
  echo 'File .env sudah ada: tidak diubah; kredensial lama dipertahankan.'
fi
echo 'Membangun dan menjalankan BerauLoad...'
docker compose up -d --build
echo 'Status container:'
docker compose ps
echo 'URL: http://IP-LXC:8092'
echo 'PENTING: batasi akses melalui firewall/VPN; jangan langsung expose ke internet.'
