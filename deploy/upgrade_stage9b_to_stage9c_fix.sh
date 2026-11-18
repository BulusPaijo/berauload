#!/usr/bin/env bash
# Stage 9b -> Stage 9c-fix. Backups are mandatory and volumes are never deleted.
set -Eeuo pipefail
umask 077
APP="${APP_DIR:-/opt/berauload/BerauLoad_V1_1_1}"
ZIP="${ZIP_FILE:-/opt/BerauLoad_V1_6_0_STAGE9C_FIX_Full_Source.zip}"
STAMP="$(date +%Y%m%d_%H%M%S)"
fail(){ echo "GAGAL: $*" >&2; exit 1; }
for cmd in docker unzip rsync tar curl sha256sum; do command -v "$cmd" >/dev/null || fail "Perintah $cmd belum tersedia"; done
[[ -d "$APP" && -f "$APP/.env" ]] || fail "APP_DIR tidak valid / .env tidak ditemukan: $APP"
[[ -f "$ZIP" ]] || fail "ZIP tidak ada: $ZIP"
[[ "$(cat "$APP/VERSION")" == '1.6.0-stage9b' ]] || fail 'Versi terpasang bukan 1.6.0-stage9b. Jangan paksa upgrade.'
unzip -tq "$ZIP" >/dev/null || fail 'ZIP rusak'
cd "$APP"
docker compose config -q || fail 'Konfigurasi Compose lama tidak sah'
[[ -n "$(docker compose ps -q db)" && -n "$(docker compose ps -q backend)" ]] || fail 'Container db/backend harus berjalan sebelum backup'
BACKUP="$APP/backups/upgrade_stage9c_fix_$STAMP"
mkdir -p "$BACKUP"
echo "[1/6] Backup database PostgreSQL (custom format), uploads, dan source: $BACKUP"
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$BACKUP/database.dump"
[[ -s "$BACKUP/database.dump" ]] || fail 'Dump database kosong'
docker compose exec -T db pg_restore --list < "$BACKUP/database.dump" > "$BACKUP/database.contents" || fail 'Dump database tidak valid'
BACKEND_ID="$(docker compose ps -q backend)"
docker cp "$BACKEND_ID:/data/uploads" "$BACKUP/uploads" || fail 'Backup uploads gagal'
tar -czf "$BACKUP/uploads.tar.gz" -C "$BACKUP" uploads
rm -rf "$BACKUP/uploads"
tar -czf "$BACKUP/source.tar.gz" --exclude='./backups' \
    --exclude='./frontend/node_modules' --exclude='./frontend/dist' -C "$APP" .
[[ -s "$BACKUP/source.tar.gz" && -s "$BACKUP/uploads.tar.gz" ]] || fail 'Arsip backup tidak lengkap'
sha256sum "$BACKUP"/*.dump "$BACKUP"/*.gz > "$BACKUP/SHA256SUMS"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
unzip -q "$ZIP" -d "$TMP"
SRC="$TMP/BerauLoad_V1_6_0_STAGE9C_FIX"
[[ -f "$SRC/VERSION" && "$(cat "$SRC/VERSION")" == '1.6.0-stage9c-fix' ]] || fail 'Isi ZIP tidak sesuai versi'
echo '[2/6] Memasang source, tanpa menghapus data, backups, uploads, .env'
rsync -a --exclude='.env' --exclude='backups/' --exclude='uploads/' \
  --exclude='*.db' --exclude='node_modules/' --exclude='dist/' \
  --exclude='__pycache__/' "$SRC/" "$APP/"
[[ "$(cat VERSION)" == '1.6.0-stage9c-fix' ]] || fail 'Versi source tidak sesuai'
docker compose config -q || fail 'Compose tidak valid setelah overlay'
echo '[3/6] Build image backend & web; container lama tetap berjalan sampai build selesai'
docker compose build backend web || fail "Build gagal; container lama belum diganti. Kembalikan source dari $BACKUP/source.tar.gz sebelum percobaan ulang."
echo '[4/6] Menjalankan container baru (tanpa menghapus volume)'
docker compose up -d --no-build
sleep 3
echo '[5/6] Health/smoke test'
docker compose ps
bash ./deploy/smoke-test.sh
set -a; source .env; set +a
curl -fsS "http://127.0.0.1:${APP_PORT:-8092}/api/health"
echo
echo '[6/6] Upgrade source selesai. Uji filter angka/findings melalui browser staging.'
echo "Backup aman di: $BACKUP"
echo 'PENTING: jangan gunakan docker compose down -v. Jika gagal, lihat README_UPGRADE_V1_6_0_STAGE9C_FIX.md.'
