# BerauLoad Stage 8 — Hotfix Alat Uji Beban (tanpa perubahan aplikasi)

Hotfix untuk dua tes `test_loadtest_runner.py` yang gagal akibat pengujian sangat
singkat (1 detik) memakai ambang p95 kapasitas 5 menit dan kadang tidak sempat
mengambil sampel dashboard. Tidak ada perubahan aturan bisnis, skema database,
frontend, konfigurasi Docker, atau versi aplikasi (`1.6.0-stage8`).

## Perubahan

- `deploy/loadtest/runner.py`: opsi `--logic-only`; validasi respons, payload,
  sampel request, nilai akhir, serta 409 tetap wajib. Hanya pemeriksaan batas p95
  yang dilewati pada mode tersebut, dengan penanda laporan yang eksplisit.
  Mode uji kapasitas **tanpa** `--logic-only` tetap menggunakan batas p95.
  Reader dan writer harus menyelesaikan paling sedikit satu siklus.
- `backend/tests/test_loadtest_runner.py`: dua tes jalur SQLite ASGI/HTTP lokal
  memakai `--logic-only`; dua tes tambahan menjamin mode logika tetap gagal jika
  dashboard tidak dicoba dan mode kapasitas tetap ketat.
- `deploy/loadtest/README.md`: penjelasan pemisahan logika dan kapasitas.

## Upgrade source yang sedang dipakai

Simpan ZIP patch di `/opt/` lalu jalankan pada source Stage 8 yang diuji:

```bash
cd /opt/berauload-stage8-extract/BerauLoad_V1_6_0_STAGE8
unzip -o /opt/BerauLoad_V1_6_0_STAGE8_TestRunner_Hotfix_Patch.zip -d .
# Pengujian di image Python yang sudah memiliki persyaratan dev:
PYTHONPATH=backend:. python3 -m pytest -q backend/tests/test_loadtest_runner.py
```

Jika ingin source instalasi aktif juga memiliki alat uji terbaru:

```bash
cd /opt/berauload/BerauLoad_V1_1_1
unzip -o /opt/BerauLoad_V1_6_0_STAGE8_TestRunner_Hotfix_Patch.zip -d .
```

Jangan jalankan load test terhadap database produksi atau port 8092. Untuk
benchmark kapasitas, gunakan PostgreSQL staging terpisah, `--duration 300`,
20 writer, 60 reader, tanpa flag `--logic-only`. Pengujian singkat mode logika
**bukan bukti** bahwa p95 memenuhi SLA.

Rollback hotfix cukup mengembalikan tiga file dari source Stage 8 sebelumnya.
Tidak ada migrasi, restart database, ataupun perubahan API.

## Hasil verifikasi saat membuat patch

`PYTHONPATH=backend:. pytest -q backend/tests/test_loadtest_runner.py`:
**7 passed**. `node --experimental-strip-types --test frontend/tests/*.test.mjs`:
**51 passed**. Belum dijalankan suite backend penuh, build npm, PostgreSQL,
atau browser pada revisi ini. Dua tes yang semula gagal telah lulus di lingkungan
pengujian ini; hasil pada server pengguna masih harus diverifikasi.
