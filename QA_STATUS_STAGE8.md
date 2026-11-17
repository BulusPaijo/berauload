# QA — BerauLoad V1.6.0 Stage 8 (2026-11-17)

**STATUS: KANDIDAT STAGING. BELUM LULUS BUILD FRONTEND / BELUM DIUJI DI LXC POSTGRESQL.**

## Lingkup perubahan

- Migrasi global aditif `app_branding` (maksimal satu baris id=1), default tetap BerauLoad; tidak mengubah data pengukuran dan hak akses per unit.
- Public GET branding/logo/favicon, PUT admin, upload/delete/reset admin, CSRF + audit, cache/ETag, unggahan diproses ulang sebagai PNG aman.
- Frontend provider publik sebelum login, fallback penyimpanan lokal dan metadata, teks login/sidebar/footer/help, admin settings dan preview.
- Report PDF/XLSX dan nama file unduhan mengikuti branding; metadata workbook Excel dan format dashboard JSON **tetap**.
- Pillow terpin 12.3.0 (versi QA terinstal diperiksa melalui `PIL.__version__`). Image Docker belum tersedia untuk dicek.

## Perintah nyata dan hasil

| Pengujian/perintah | Hasil |
|---|---|
| `PYTHONPATH=backend:. python -m pytest -q backend/tests` | Dicoba, tetapi proses gabungan **timeout**, tidak dihitung sebagai lulus single-run |
| Kelompok 1 `test_api, core, dashboard_builder, dashboard_settings, equipment_kinds, formulas, historical, input_forms, management_rules, org_units, org_units_home, org_units_stage12` | **45 passed** (9,03 detik) |
| Kelompok 2 `test_api, stage4b_config, stage5_unit_sources, stage6_completeness` | **22 passed** (26,72 detik) |
| Kelompok 3 `test_api, stage5_template_import_recalculation, stage6_topology_links, stage7_records, stage7_sessions` | **20 passed** (21,42 detik) |
| Kelompok 4 `test_api, stage4a_units, stage8_branding` | **12 passed** (14,40 detik) |
| Kelompok 5 `test_api, report_builder_v146, standard_reports_v1461, v144_export_management` | **16 passed** (5,45 detik) |
| Kelompok 6 `test_api, loadtest_runner, performance_v145, primary_metrics_stage3, units_visualization_v143` | **18 passed** (26,24 detik) |
| Kelompok 7 `test_api, topology, template_import` | **37 passed** (18,51 detik) |
| **Total backend unik** | **164 passed** (170 per kelompok dikurangi `test_api.py` yang sama diuji 7 kali, jadi 6 duplikasi): **160 lama + 4 baru** |
| `node --experimental-strip-types --test frontend/tests/*.test.mjs` | **51 passed** (48 lama + 3 branding) |
| Parser TypeScript `createSourceFile` pada `frontend/src` | **67 file TS/TSX, 0 syntax diagnostics**; ini bukan typecheck/build |
| `cd frontend && npm install --no-audit --no-fund --fetch-retries=0 --fetch-timeout=12000` | **GAGAL**, DNS `EAI_AGAIN registry.npmjs.org/@types%2freact` |
| `cd frontend && npm run build` | **GAGAL**, React/@types/react dan dependency lain tidak terpasang; berbagai TS2307/TS7026/TS2875 turunan tidak membuktikan kode UI ter-typecheck |

Semua tes backend dilakukan di database SQLite sintetis melalui fixture sementara,
bukan ke data PLN/produksi. Seluruh 30 file `test_*.py` tercakup dalam kelompok
tersebut; tidak ada tes lama yang diubah.

## Skenario Stage 8 yang teruji

- Tanpa row branding, nilai bawaan dan SVG bawaan ditampilkan, termasuk ETag dan 304; GET publik tidak mengembalikan informasi akun.
- Migrasi dua kali pada database SQLite yang telah memiliki skema Stage 7: satu penanda versi, **tidak ada** row `app_branding` otomatis di startup kedua.
- PUT tersimpan, teks trim, audit nilai lama/baru, nama terlalu panjang/karakter kontrol ditolak, warna primary kontras rendah dan format hex salah ditolak.
- 401 untuk sesi belum login, 403 untuk CSRF salah/non-admin, GET tetap publik.
- PNG re-encoded dan metadata dibuang, path client `../../...` tidak berpengaruh. SVG, ZIP, HTML, PHP, GIF/BMP, ukuran/dimensi berlebih ditolak. ICO favicon diterima lalu disimpan sebagai PNG. Hapus dan reset kembali ke bawaan.
- Laporan XLSX default tetap memiliki sheet `Pembacaan Per Jam`; setelah nama pendek berubah menjadi `Rekap/UP3` muncul sheet `Data Rekap_UP3`, PDF valid. Marker `berauload_hourly` dan JSON `berauload-dashboard-v1` tidak berubah.
- JS: salinan default frontend sama dengan backend, slug aman, kontras/metadata serta localStorage tidak tersedia/rusak tidak menggagalkan aplikasi.

## Batas belum diuji dan keputusan

- **Belum:** `npm install` berhasil, `tsc -b`, Vite build berhasil, Docker Compose build, PostgreSQL 16 nyata, browser langsung/favicon cache/kontras visual, Cloudflare Tunnel, dan penggunaan logo korporat resmi.
- **Keputusan:** pengujian regresi SQLite dan logika Node **lulus**. Persyaratan build frontend dan verifikasi staging **belum lulus**; **jangan deploy ke produksi tanpa build, smoke test, uji browser dan backup asli**.
