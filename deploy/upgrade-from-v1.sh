#!/usr/bin/env bash
# Safe on-host upgrade to V1.1 from an existing V1.0 deployment.
set -euo pipefail
cd "$(dirname "$0")/.."
HERE="$PWD"
V1="$(dirname "$HERE")/BerauLoad_V1_0"
if [ ! -f "$V1/.env" ]; then
  echo "Deployment V1 tidak ditemukan di $V1/.env" >&2
  echo 'Gunakan prosedur patch overlay di README bila folder V1 berbeda.' >&2
  exit 1
fi
if [ -e "$HERE/.env" ]; then
  echo 'File .env V1.1 sudah ada. Tidak akan ditimpa; periksa konfigurasi manual.' >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo 'docker compose belum tersedia' >&2
  exit 1
fi
echo '[1/4] Membuat backup database dan file upload dari V1.0...'
(cd "$V1" && bash deploy/backup.sh)
echo '[2/4] Menyalin konfigurasi V1.0 (tanpa mengganti password)...'
cp -p "$V1/.env" "$HERE/.env"
chmod 600 "$HERE/.env"
echo '[3/4] Membangun dan menjalankan V1.1 pada project Docker yang sama...'
docker compose up -d --build
echo '[4/4] Memeriksa layanan...'
docker compose ps
bash deploy/smoke-test.sh
printf '\nUpgrade selesai. Backup berada di %s/backups\n' "$V1"
printf 'Jangan menghapus direktori V1 atau volume Docker sebelum verifikasi selesai.\n'
