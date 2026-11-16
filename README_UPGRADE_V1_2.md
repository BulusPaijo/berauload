# Upgrade BerauLoad V1.1.2 → V1.2.0 (termasuk V1.1.3)

**Prasyarat:** instalasi aktif sudah V1.1.2 dan bisa login. Patch bersifat kumulatif dari V1.1.2; tidak perlu memasang V1.1.3 dahulu. Untuk versi lebih lama, upgrade ke V1.1.2 dahulu. Jangan jalankan `install.sh` atau perintah `docker compose down -v`.

1. Upload `BerauLoad_V1_2_0_Update_Patch.zip` ke `/opt/` di LXC Debian melalui WinSCP.
2. Jalankan terminal pada **root proyek yang aktif** (nama direktori bisa tetap `BerauLoad_V1_1_1` atau nama lain):

   ```bash
   cd /opt/berauload/BerauLoad_V1_1_1  # GANTI jika lokasi aktif berbeda
   docker compose ps
   ./deploy/backup.sh
   ls -lh backups/* | tail -4
   ```

3. Pastikan backup DB dan uploads ada, tidak kosong, serta simpan salinan source lama. Misalnya dari root aktif:

   ```bash
   mkdir -p /opt/berauload_source_backup
   tar -czf /opt/berauload_source_backup/source_before_v1_2.tar.gz \
     --exclude='./backups' --exclude='./node_modules' --exclude='./frontend/node_modules' .
   ```

4. Dari root proyek aktif, ekstrak **patch** dan lakukan build terlebih dahulu:

   ```bash
   unzip -o /opt/BerauLoad_V1_2_0_Update_Patch.zip -d .
   docker compose build
   docker compose up -d --no-build
   docker compose ps
   ./deploy/smoke-test.sh
   curl -fsS http://127.0.0.1:8092/api/health
   ```

   Jika APP_PORT pada `.env` bukan 8092, sesuaikan perintah `curl`. Status yang diharapkan: `version: 1.2.0`. Migrasi akan membuat tabel baru `historical_definitions` ketika backend start.

5. Uji manual di browser: Pengaturan → Master Peralatan (tambah/edit via drawer), Pengaturan → Parameter (Formula Engine V1.1 tetap ada), Dashboard (grafik H/J tetap sama), dan Analisis Beban → Perhitungan Historis (buat/simulasikan "Rata-rata Cadangan Daya Bulanan"). Coba bulan dengan data parsial untuk memeriksa coverage. Cek `docker compose logs --tail=100 backend web`.

## Rollback bila perlu

Jangan hapus volume PostgreSQL/Uploads. **Jika build gagal sebelum deploy**, perbaiki source atau kembalikan snapshot source sebelum upgrade tanpa menyentuh database. Jika sudah deploy, lakukan rollback source + rebuild ke versi sebelumnya; tabel baru bersifat additive dan tidak memodifikasi tabel historis. Pemulihan database dari backup hanya untuk kebutuhan pemulihan yang benar-benar diperlukan, dan sebaiknya dilakukan terpisah setelah verifikasi konsistensi.

## Batas pengujian

Tes API/backend dan import Excel asli sudah dilakukan pada database QA SQLite, bukan pada PostgreSQL produksi. Build Vite/npm dan Docker di LXC belum tervalidasi di lingkungan penyusunan patch karena dependensi npm tidak tersedia. **Build di atas wajib berhasil sebelum deployment.**
