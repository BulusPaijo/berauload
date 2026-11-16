# QA STATUS — BerauLoad V1.6.0 Stage 7 Hotfix 1

Tanggal 16 November 2026. **KANDIDAT STAGING.** Bukan hasil pengujian kapasitas PostgreSQL produksi.

## Perubahan yang dibatasi

- `deploy/loadtest/runner.py`: impor Path tunggal di tingkat modul; jalur HTTP yang sebelumnya `UnboundLocalError` sekarang bisa digunakan. Penghitungan status/latensi, enam endpoint pembaca berulang, pengujian konflik, strict verdict.
- `deploy/loadtest/fixture.py`: dataset sintetis dengan peran system.load/capacity, data historis tahun sekarang/tahun sebelumnya, satu diagram per ULP, 60 pembaca manajemen pada ULP yang memiliki data.
- `frontend/nginx.conf`: regex lokasi asset ber-hash dibungkus tanda kutip agar tidak ditafsirkan sebagai directive yang keliru.
- `deploy/smoke-test.sh`: mode dari 0644 menjadi 0755 (tanpa mengubah isi).
- `backend/tests/test_loadtest_runner.py`: lima tes baru, termasuk HTTP server lokal tanpa --asgi-sqlite.
- Metadata versi/dokumen saja selain perubahan di atas. **Tidak ada perubahan aturan aplikasi atau database.**

## Perintah yang benar-benar dijalankan

| Perintah | Hasil |
|---|---|
| `PYTHONPATH=backend:. python -m pytest -q backend/tests/test_loadtest_runner.py` | 5 passed (15,67 detik) |
| `PYTHONPATH=backend:. python -m pytest -q` kelompok dasar (18 file) | 72 passed (10,48 detik) |
| Kelompok Stage 4a–6 (6 file) | 36 passed (24,39 detik) |
| Kelompok Stage 7 (2 file) | 11 passed (8,00 detik) |
| Kelompok import template + topologi (2 file) | 36 passed (11,94 detik) |
| **Total backend unik** | **160 tes lulus** dari lima kelompok: 155 baseline + 5 baru; tes lama tidak diubah |
| `PYTHONPATH=backend:. python -m pytest -q backend/tests` | Dijalanan; **timeout** dan belum selesai sebagai satu proses, tidak diklaim lulus single-run |
| `PYTHONPATH=backend:. python -m deploy.loadtest.runner --confirm-isolated --asgi-sqlite --fixture /tmp/ignored.json --duration 8 --writers 2 --readers 2 --exports 1` | **LULUS** uji logika SQLite: setiap endpoint pembaca 5 HTTP 200; total 41 HTTP 200, 1 HTTP 409 disengaja; 0 nilai hilang, tidak ada payload invalid |
| Tes jalur HTTP tanpa `--asgi-sqlite` | **LULUS** pada server Uvicorn loopback **SQLite terisolasi** melalui `test_http_branch_with_local_isolated_server`; bukan PostgreSQL |
| `nginx -t` dengan frontend nginx.conf di dalam HTTP wrapper dan alias backend digantikan 127.0.0.1 | Syntax **lulus**; DNS nama service `backend` pada Docker belum diuji |
| `cd frontend && npm install --no-audit --no-fund --fetch-retries=0 --fetch-timeout=10000` | **GAGAL** EAI_AGAIN `registry.npmjs.org/@types%2freact` |
| `cd frontend && npm run build` | **GAGAL**, modul React dan @types/react tidak tersedia akibat npm install gagal; TypeScript/Vite build tidak boleh diklaim lulus |

## Batas yang belum dapat diuji

- **PostgreSQL 16 nyata** belum diuji: lingkungan QA tidak memiliki Docker maupun binary PostgreSQL 16. Jalur runner tanpa `--asgi-sqlite` **telah dieksekusi** pada HTTP Uvicorn/SQLite, bukan PostgreSQL; jangan menyamakan keduanya.
- Skenario **20 writer + 60 reader, 5 menit, 3 export** di staging PostgreSQL LXC belum dieksekusi. Karena itu tidak ada angka p95 yang layak disebut SLA.
- `docker compose build`, `docker compose exec web nginx -t`, browser nyata di port 8092, Cloudflare Tunnel, dan verifikasi data produksi belum dilakukan.
- Paket bersifat source-only; file .env, database, `node_modules`, hasil build, cache tidak dikemas.

## Keputusan

Dari tes logika SQLite dan endpoint HTTP lokal: **LULUS**. Dari persyaratan rilis produksi (npm/Vite + PostgreSQL kapasitas + browser): **BELUM LULUS / belum diverifikasi**. Uji staging di LXC sesuai `README_UPGRADE_V1_6_0_STAGE7_HOTFIX1.md` dan `deploy/loadtest/README.md` sebelum produksi.
