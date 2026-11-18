# QA — BerauLoad 1.6.0-stage9d1 — 17 November 2026

**Kandidat staging; belum disahkan untuk produksi.** Basis `BerauLoad_V1_6_0_STAGE9C_FIX_Rev1_Full_Source.zip`; perubahan dalam Stage 9d1 tidak mengedit rumus/seed 9b maupun data ukur 9a. Pengaturan ubin hanya oleh admin global, dibatasi skema, dicatat audit, migrasi aditif dan restart-idempotent.

## Implementasi dan lingkup

- Backend: `/api/substations/map/points` menggunakan kueri filter 9c dan nilai+rule tersimpan 9b; gardu tanpa koordinat sah tidak digambar dan masuk daftar koreksi; `/map/tiles` GET/PATCH admin, migrasi `gardu_tile_settings`; `/analysis/charts` memberi sebar, pareto, perbandingan sesi, tren; `/analysis/stations/{id}/latest` untuk pemilihan baris grafik berhak akses.
- Frontend: Leaflet 1.9.4 dengan marker dikelompokkan berdasarkan kisi pada zoom, bentuk kategori, skala, titik saat ubin gagal; filter URL Analisa/Peta, rincian/grafik/posisi/terdekat. Recharts sudah merupakan dependency Stage 9c-fix, tidak ada tambahan library grafik. Penyempurnaan submenu, kepadatan tabel, kisi input, dialog konfirmasi, dan responsivitas.
- **Library peta**: Leaflet **1.9.4**, **BSD-2-Clause**, dibundel melalui npm (JS/CSS; tanpa CDN). Tambahan deklarasi TypeScript `@types/leaflet` versi **1.9.15**. URL ubin eksternal berasal dari konfigurasi admin; default OSM memerlukan koneksi internet.

## Daftar halaman yang disentuh dan alasan

| Halaman | Perubahan |
|---|---|
| Navigasi Pengukuran Gardu | Submenu jelas dengan ikon, label halaman dan kontrol unit aktif |
| Peta Gardu (baru) | Peta, kelompok titik, legenda definisi admin, filter terpadu, fallback ubin, koordinat hilang, panel rincian/terdekat |
| Analisa | Lima tipe grafik dengan ringkasan filter, CSV/PNG, simpan pilihan grafik, kepadatan nyaman/padat |
| Input Massal | Header dikelompokkan Arus/Tegangan/Grounding, sel fokus, bilah aksi dan status simpan tetap |
| Form Ponsel | Prefill gardu saat datang dari Peta |
| Master Gardu | Pencarian cepat kode dari daftar tanpa koordinat, konfirmasi aplikasi |
| Daftar Pengukuran | Konfirmasi aplikasi yang konsisten |
| Rumus & Kategori | Konfirmasi aplikasi yang konsisten, tanpa mengubah rumus dan nilai |

## Hasil uji yang dapat dikonfirmasi

| Perintah / pemeriksaan | Hasil |
|---|---|
| `PYTHONPATH=.:backend pytest -q backend/tests/test_stage9d1_map.py` | **3 lulus** (migrasi dua kali, config/role/audit/validasi, titik/filter/NULL/0, grafik baca-saja) |
| `PYTHONPATH=.:backend pytest -q backend/tests/test_stage9d1_map.py backend/tests/test_stage9c_analysis.py backend/tests/test_stage9c_fix.py backend/tests/test_stage9b_calculations.py backend/tests/test_stage9a_substations.py backend/tests/test_stage9a_hotfix.py` | **35 lulus** |
| `node --experimental-strip-types --test frontend/tests/*.test.mjs` | **75 lulus**, termasuk **6 tes Stage 9d1** tentang kisi marker, warna+bentuk, legenda, fallback, filter, pareto, scatter, densitas |
| `PYTHONPATH=.:backend pytest -q backend/tests` (satu proses) | **Belum selesai**: eksekusi melewati batas waktu pada sekitar 71% tanpa laporan akhir; tidak diklaim lulus |
| `python -m compileall -q backend/app` | **Lulus** |
| `typescript.transpileModule` semua file `.ts/.tsx` (86 file) | **0 kesalahan sintaks**. Ini *bukan* pemeriksaan tipe `tsc -b` |
| `bash -n deploy/upgrade_to_stage9d1.sh` | **Lulus** |
| `npm install --fetch-retries=0 --fetch-timeout=7500` | **Gagal**: npm registry tidak bisa dihubungi (`EAI_AGAIN` pada paket `@types/leaflet`) |
| `npm run build` | **Gagal** karena instalasi dependency belum selesai; `TS2307` untuk `react`/`react/jsx-runtime`/modul lain yang tidak tersedia. Ini tidak membuktikan bahwa kode bebas kesalahan tipe; build penuh tetap wajib di staging |
| Ukuran bundel JS sebelum/sesudah | **Tidak terukur**. Build Vite baseline dan Stage 9d1 tidak dapat dibuat secara sah dengan dependensi yang tersedia |

## Yang wajib diuji lagi di LXC

- PostgreSQL 16 dan migrasi nyata dari **9c-fix Rev1** (serta uji ulang), indeks dan akses role/unit, transaksi verified/final, query tanpa data dan koordinat tidak sah.
- `npm install`/`npm run build` **berhasil sungguhan**, Docker build/up/smoke, ukur ukuran `dist/assets` baseline vs baru (JS, gzip, CSS).
- Browser desktop/ponsel fisik: warna/bentuk marker, interaksi 5.000 titik, kinerja pengelompokan/tooltip, keyboard, bentuk legenda, pengambilan lokasi.
- Perilaku ubin ketika jaringan kantor memblokir OSM, reverse proxy/CSP, Cloudflare Tunnel, zoom, peta kosong, jaringan terputus.
- Keakuratan label kategori pada grup kustom, nilai >100%, kurva riwayat, ekspor PNG dan aturan browser canvas/SVG.
- Tes end-to-end antara operator mengukur dan admin hitung ulang; beban 5.000 gardu/100.000 pengukuran, bukan direka-reka.

Pengujian hanya menggunakan data sintetis dan SQLite sementara. Jangan menyebut rilis telah lolos PostgreSQL, UI browser, atau optimasi produksi sampai dilakukan pada LXC.
