# Upgrade BerauLoad V1.6.0 Stage 8 → Stage 9a

**Status: kandidat staging**. Stage 9a menambah modul terpisah **Pengukuran Gardu**. Tidak ada perubahan tabel pembacaan per jam, bisnis beban sistem, topologi, atau rekap. Satu-satunya migrasi baru `20261117_17_stage9a_substations` menciptakan tabel baru dan seed global sekali.

## 1. Sebelum upgrade

Server yang terakhir tervalidasi menggunakan `/opt/berauload/BerauLoad_V1_1_1`, port `8092`. Paket sumber dari Stage 8 dengan hotfix alat uji runner. Jangan melompati versi tanpa memastikan baseline.

```bash
cd /opt/berauload/BerauLoad_V1_1_1
cat VERSION
curl -fsS http://127.0.0.1:8092/api/health

# Backup DB & uploads; "bash" menghindari Permission denied
bash ./deploy/backup.sh
# Periksa benar-benar terbentuk dan dapat dibaca
ls -lh backups/ | tail -10

# Backup source, termasuk .env
mkdir -p /opt/berauload-backups
tar -czf "/opt/berauload-backups/source_before_stage9a_$(date +%Y%m%d_%H%M%S).tar.gz" \
  --exclude='./backups' --exclude='./frontend/node_modules' \
  --exclude='./frontend/dist' .
```

**Jangan lanjutkan bila backup database gagal.** Arsip source bukan pengganti PostgreSQL dump.

## 2. Ekstrak dan overlay ke direktori aplikasi

Unggah `BerauLoad_V1_6_0_STAGE9A_Full_Source.zip` ke `/opt/`.

```bash
mkdir -p /opt/berauload-stage9a-extract
unzip -o /opt/BerauLoad_V1_6_0_STAGE9A_Full_Source.zip -d /opt/berauload-stage9a-extract
rsync -a \
  --exclude='.env' --exclude='berauload.db' \
  --exclude='backups/' --exclude='uploads/' \
  --exclude='node_modules/' --exclude='dist/' \
  /opt/berauload-stage9a-extract/BerauLoad_V1_6_0_STAGE9A/ \
  /opt/berauload/BerauLoad_V1_1_1/
cd /opt/berauload/BerauLoad_V1_1_1
cat VERSION
```

Target `1.6.0-stage9a`. Tidak perlu memasang Node/Python di host bila pengujian menggunakan image Docker. **Sebaiknya jalankan dulu pada Compose staging dengan nama proyek, port, volume, dan `.env` terpisah** sebelum menyentuh instance produksi.

## 3. Pengujian sebelum deployment

```bash
cd /opt/berauload/BerauLoad_V1_1_1

# Node test tanpa instalasi Node pada host
docker run --rm -v "$PWD:/work" -w /work node:22-alpine \
  node --experimental-strip-types --test frontend/tests/*.test.mjs

# npm install dan build sungguhan, dari image Node
docker run --rm -v "$PWD/frontend:/web" -w /web node:22-alpine \
  sh -c 'npm install --no-audit --no-fund && npm run build'

# Backend SQLite sintetis, TIDAK memakai PostgreSQL produksi
docker run --rm -v "$PWD:/work" -w /work \
  -e PYTHONPATH=/work/backend:/work python:3.12-slim \
  sh -c 'pip install --no-cache-dir -r backend/requirements-dev.txt && python -m pytest -q backend/tests'
```

Jangan lanjut deploy bila tes/build gagal. Build awal di lingkungan pengembangan sebelumnya **tidak terverifikasi berhasil** karena dependensi npm tidak tersedia; tes Node dan backend lulus lokal. Jika perintah `npm install` gagal, tampilkan galat sebenarnya sebelum mengubah kode.

## 4. Build, up dan pemeriksaan

```bash
cd /opt/berauload/BerauLoad_V1_1_1
docker compose build
docker compose up -d --no-build
docker compose ps
bash ./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

Respon health tetap mengandung `"app":"BerauLoad"`, `"version":"1.6.0-stage9a"`.

## 5. Migrasi (hanya SELECT untuk pemeriksaan)

```bash
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT version, applied_at FROM schema_migrations WHERE version = '\''20261117_17_stage9a_substations'\'';"'
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT COUNT(*) FROM substation_params;"'
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT COUNT(*) FROM substation_measurements;"'
```

Migrasi aditif dan idempotent (dijalankan berulang tanpa memperbanyak seed atau mengubah data lama). Nilai bawaan: 15 parameter, 2 sesi, 3 flag, 2 status kepemilikan dan 2 peruntukan. Kode permanen. Tidak ada tabel `hour_records`, `readings`, `unit_day_states` yang diubah oleh Stage 9a.

## 6. Penggunaan

- Pilih **ULP atau KP** di sidebar → Operasional → **Pengukuran Gardu**.
- Admin membuat master penyulang dan master gardu (kode unik per unit); dapat mengimpor master Excel/CSV melalui **Pratinjau** lalu konfirmasi. Penyulang baru dari berkas harus dikonfirmasi; perubahan gardu lama juga harus diizinkan eksplisit.
- Admin mengatur parameter/sesi/flag/atribut global pada tab **Definisi Global**. Tidak ada akun admin unit: hanya admin global yang bisa mengubah definisi/master. Operator mengisi, verifier memverifikasi/membuka kunci (alasan wajib), management hanya membaca.
- Input massal: pilih tanggal, sesi, penyulang, dan petugas. Gunakan Tab/Enter/panah untuk navigasi atau tempel blok dari Excel. Kolom lebih dari `line_count` tidak aktif. Angka 0 valid; kosong tetap kosong; flag melalui pilihan di sel.
- Autosave per baris dengan cadangan browser per user/unit/tanggal/sesi; saat ada cadangan, **pilih Pulihkan/Buang**. Konflik revision 409 memerlukan pilihan pengguna. Kisi menggunakan **pagination 100 baris** per halaman (bukan render 300 sekaligus).
- Daftar pengukuran: filter dan halaman, pilih banyak lalu aksi verify/reopen/delete draft/update tanggal-sesi-petugas; hasil dikembalikan per baris. Input mobile tersedia melalui tab **Form Ponsel**.
- Template pengukuran XLSX: pilih tanggal/sesi dan penyulang, unduh. Saat impor gunakan preview, default hanya isi sel kosong; overwrite harus eksplisit dan tidak bisa menimpa verified.
- Batas backend: halaman <=200, simpan massal <=200 pengukuran, edit master massal <=500, file impor <=4 MB, preview berlaku 30 menit. Kode teknis/format lama tetap sama.

## 7. Rollback aman

1. Hentikan penggunaan modul baru dan pastikan backup sumber + DB tersimpan di luar container.
2. Pulihkan source versi Stage 8 Hotfix Runner dari backup source sebelum upgrade (atau ZIP versi Stage 8 yang sudah diverifikasi), tanpa menimpa `.env`, volume DB, uploads.
3. `docker compose build && docker compose up -d --no-build` dari source lama; `docker compose down -v` **dilarang**.
4. Tabel baru Stage 9a tetap berada di DB secara inert; rollback source **tidak** men-drop tabel/mengembalikan DB ke skema lama. Jika perlu point-in-time database rollback, lakukan pemulihan dump hanya setelah mempertimbangkan perubahan operasional yang terjadi setelah backup.
5. Periksa health dan data ULP Tanjung Redeb setelah rollback.

## 8. Pembatasan dan pemeriksaan lanjutan

Pengujian dari source telah menggunakan SQLite sintetis, bukan PostgreSQL 16 dan browser produksi. Khususnya cek ulang transaksionalitas dan `pg_advisory_xact_lock` PostgreSQL, kerja 300 baris dengan paste Excel, ponsel, serta performa/respons server pada LXC. Tidak ada rumus, % beban, diagnosis, notifikasi, atau analisis gardu Stage 9b.
