# Upgrade BerauLoad V1.6.0 Stage 9a-fix → 9b

**Status: kandidat staging**. Upgrade dari `1.6.0-stage9a-fix` ke `1.6.0-stage9b`. Tidak disarankan langsung memasang ke production tanpa hasil build TypeScript asli, migrasi PostgreSQL 16, dan smoke test LXC yang valid.

## 1. Cadangkan sebelum menyalin source

Contoh berikut harus disesuaikan nama container, kredensial, database, dan direktori aktual di LXC Anda:

```bash
cd /opt/berauload
mkdir -p backups
# Jalankan pg_dump pada database aplikasi dengan kredensial dari environment Compose.
docker compose exec -T db pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > backups/berauload-before-stage9b.dump
# Cadangkan juga volume uploads dan source menggunakan mekanisme backup LXC yang berlaku.
tar -czf backups/source-before-stage9b.tgz --exclude=backups .
```

**Jangan menyalin perintah `pg_dump` mentah tanpa menyesuaikan cara environment Compose Anda**, terutama jika variabel `POSTGRES_USER/POSTGRES_DB` hanya tersedia di dalam container. Simpan hasil backup di luar LXC dan lakukan pemeriksaan ukuran/integritasnya.

## 2. Build dan jalankan

Pertahankan `.env`, data PostgreSQL dan upload. Jangan menimpa file rahasia saat ekstraksi ZIP.

```bash
cd /opt/berauload
# Salin source Stage9b di atas source 9a-fix, pertahankan .env dan data lokal.
cd frontend && npm install && npm run build && cd ..
PYTHONPATH=backend python -m pytest -q backend/tests/test_stage9b_calculations.py
# Lakukan rollout hanya bila QA berhasil
sudo docker compose build
sudo docker compose up -d --no-build
sudo docker compose ps
./deploy/smoke-test.sh
curl --fail http://127.0.0.1:8090/api/health
```

**Sesuaikan port health dengan Compose Anda**. Jangan pernah `docker compose down -v`.

## 3. Cek migrasi dan hasil pertama

Migration ID `20261117_18_stage9b_gardu_calculations` disimpan sekali di `schema_migrations`. Delapan tabel baru dimulai dengan `gardu_calc_`.

```sql
SELECT version FROM schema_migrations WHERE version='20261117_18_stage9b_gardu_calculations';
SELECT COUNT(*) FROM gardu_calc_columns;
SELECT COUNT(*) FROM gardu_calc_rules;
SELECT COUNT(*) FROM gardu_calc_constants;
SELECT version, stale_days FROM gardu_calc_settings WHERE id=1;
SELECT COUNT(*) FROM gardu_calc_marks;
SELECT COUNT(*) FROM substation_measurements;
```

Pada instalasi baru jumlah awal adalah **13 kolom**, **11 aturan**, dan **3 konstanta**. Pengukuran historis belum otomatis di-backfill pada startup; buka **Pengukuran Gardu → Rumus & Kategori** dengan akun admin dan jalankan **Hitung ulang / lanjutkan** hingga sisa 0. Tombol dapat ditekan lagi setelah interupsi. Anda juga dapat memanggil `POST /api/substations/calculations/recalculate?limit=100` dengan cookie/CSRF admin. Proses ini hanya menulis tabel hasil, tidak mengubah `substation_values`, `hour_records`, atau status verified.

## 4. Smoke test operasional

1. Masuk admin UP3, buka Rumus & Kategori. Pastikan data bawaan tampil dan peringatan ambang sementara tersedia.
2. Cek akses operator/verifier: dapat membaca definisi/hasil, tidak bisa memodifikasi atau menghitung ulang.
3. Uji rumus `IF(fase = 3, kva * 1000 / (1.732 * v_ll_nominal), kva * 1000 / v_ln_nominal)` pada satu pengukuran sintetis, dan cek NULL vs 0/flag.
4. Ubah satu rumus pada data uji, jalankan pratinjau dampak, simpan dengan konfirmasi, cek kenaikan versi dan audit, jalankan batch, pastikan raw measurement tetap.
5. Cek input massal, impor, form ponsel, status verified, H/J harian, histori, dashboard dan pengaturan lama tidak berubah.

## 5. Rollback tanpa menghapus volume

Simpan source sebelumnya dan backup database sebelum upgrade. Jika upgrade gagal, hentikan traffic, kembalikan source Stage 9a-fix, lalu `docker compose build && docker compose up -d --no-build`. **Jangan** menghapus volume. Delapan tabel 9b yang bersifat aditif tidak akan digunakan oleh kode 9a-fix; definisi dan hasil 9b tetap berada di database untuk rollback operasional yang ringan. Jika perlu restore database secara penuh, lakukan hanya dari backup terverifikasi sambil mempertimbangkan pengukuran yang dibuat sesudah backup agar tidak hilang. Pastikan `GET /api/health` kembali `1.6.0-stage9a-fix` dan lakukan smoke test.

## 6. Perbandingan rumus Excel lama dan bawaan

Rumus Excel lama (referensi): `kva * 1000 / 380 * 1.732 / 3`. Rumus bawaan Stage9b untuk tiga fasa: `kva * 1000 / (1.732 * v_ll_nominal)` dengan `v_ll_nominal=400` V. Rumus satu fasa: `kva * 1000 / v_ln_nominal`, `v_ln_nominal=231` V. Nilai pembanding sintetis:

| Kapasitas | Excel lama (A) | Bawaan Stage9b 3-fasa (A) | Selisih |
| --- | ---: | ---: | ---: |
| 100 kVA | 151,930 | 144,342 | −4,994% |
| 200 kVA | 303,860 | 288,684 | −4,994% |

**Dua baris Excel pengukuran asli tidak disertakan dalam upload Tahap 9b** sehingga belum ada validasi angka dari Excel asli. Perbedaan formula ini harus diputuskan dan disetujui pemilik. Rumus `beban_kva` dan seluruh ambang awal juga perlu verifikasi aturan engineering pemilik sebelum dijadikan keputusan PLN.
