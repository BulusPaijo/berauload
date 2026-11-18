#!/usr/bin/env bash
# BerauLoad Stage 8 .. 9d2 -> Stage 9d3. Data and Docker volumes are NEVER deleted.
# Data and Docker volumes are NEVER deleted. Staging first.
set -Eeuo pipefail
umask 077
APP="${APP_DIR:-/opt/berauload/BerauLoad_V1_1_1}"
ZIP="${ZIP_FILE:-/opt/BerauLoad_V1_6_0_STAGE9D3_Full_Source.zip}"
STAMP="$(date +%Y%m%d_%H%M%S)"
fail(){ printf 'GAGAL: %s\n' "$*" >&2; exit 1; }
for cmd in docker unzip rsync tar curl sha256sum; do
  command -v "$cmd" >/dev/null || fail "Perintah $cmd belum tersedia"
done
[[ -d "$APP" && -f "$APP/.env" && -f "$APP/VERSION" ]] || fail "APP_DIR/.env/VERSION tidak ada: $APP"
[[ -f "$ZIP" ]] || fail "ZIP tidak ditemukan: $ZIP"
CUR="$(cat "$APP/VERSION")"
case "$CUR" in
  1.6.0-stage8|1.6.0-stage9a|1.6.0-stage9a-fix|1.6.0-stage9b|1.6.0-stage9c|1.6.0-stage9c-fix|1.6.0-stage9d1|1.6.0-stage9d2|1.6.0-stage9d3) echo "Versi asal: $CUR" ;;
  *) fail "Versi asal $CUR belum didukung. Jangan paksa migrasi." ;;
esac
unzip -tq "$ZIP" >/dev/null || fail "ZIP rusak"
[[ "$(unzip -p "$ZIP" BerauLoad_V1_6_0_STAGE9D3/VERSION | tr -d '\r\n')" == '1.6.0-stage9d3' ]] || fail 'Isi ZIP bukan Stage 9d3'
cd "$APP"
docker compose config -q || fail 'Docker Compose lama tidak sah'
[[ -n "$(docker compose ps -q db)" && -n "$(docker compose ps -q backend)" ]] || fail 'Container db/backend belum berjalan'
BACKUP="$APP/backups/upgrade_stage9d3_$STAMP"
mkdir -p "$BACKUP"
echo "[1/6] Membuat backup wajib: $BACKUP"
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$BACKUP/database.dump"
[[ -s "$BACKUP/database.dump" ]] || fail 'Dump database kosong'
docker compose exec -T db pg_restore --list < "$BACKUP/database.dump" > "$BACKUP/database.contents" || fail 'Dump database tidak valid'
BACKEND_ID="$(docker compose ps -q backend)"
docker cp "$BACKEND_ID:/data/uploads" "$BACKUP/uploads" || fail 'Tidak bisa menyalin uploads dari backend'
tar -czf "$BACKUP/uploads.tar.gz" -C "$BACKUP" uploads
rm -rf "$BACKUP/uploads"
tar -czf "$BACKUP/source.tar.gz" --exclude='./backups' \
  --exclude='./frontend/node_modules' --exclude='./frontend/dist' -C "$APP" .
[[ -s "$BACKUP/source.tar.gz" && -s "$BACKUP/uploads.tar.gz" ]] || fail 'Backup tidak lengkap'
sha256sum "$BACKUP/database.dump" "$BACKUP/source.tar.gz" "$BACKUP/uploads.tar.gz" > "$BACKUP/SHA256SUMS"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
unzip -q "$ZIP" -d "$TMP"
SRC="$TMP/BerauLoad_V1_6_0_STAGE9D3"
[[ "$(cat "$SRC/VERSION")" == '1.6.0-stage9d3' ]] || fail 'Versi di dalam ZIP salah'
echo '[2/6] Overlay source; .env, backup, uploads dan database tidak ditimpa'
rsync -a --exclude='.env' --exclude='backups/' --exclude='uploads/' \
  --exclude='*.db' --exclude='node_modules/' --exclude='dist/' \
  --exclude='__pycache__/' "$SRC/" "$APP/"
[[ "$(cat VERSION)" == '1.6.0-stage9d3' ]] || fail 'Overlay source gagal'
docker compose config -q || fail 'Compose baru tidak valid'
echo '[3/6] Build image backend + web (container lama tetap berjalan saat build)'
docker compose build backend web || fail "Build gagal; jangan lanjutkan. Source lama tersimpan: $BACKUP/source.tar.gz"
echo '[4/6] Menjalankan versi baru tanpa menghapus volume'
docker compose up -d --no-build
echo '[5/6] Memeriksa kesehatan aplikasi'
docker compose ps
bash ./deploy/smoke-test.sh
PORT="$(grep -E '^APP_PORT=' .env | tail -1 | cut -d= -f2 | tr -d '"\r' || true)"
PORT="${PORT:-8092}"
curl -fsS "http://127.0.0.1:${PORT}/api/health"; echo
[[ "$(curl -fsS "http://127.0.0.1:${PORT}/api/health")" == *'1.6.0-stage9d3'* ]] || fail 'Health endpoint belum Stage 9d3'
echo "[6/6] Upgrade selesai. Backup: $BACKUP"
echo 'Uji Tindak lanjut, Pemantauan, laporan PDF/Excel, form ponsel, kisi input, Analisa, Peta, izin unit, dan fungsi input pada staging.'
echo 'Jangan jalankan docker compose down -v. Baca README_UPGRADE_V1_6_0_STAGE9D3.md.'
