## Status 1.6.0-stage9c-fix (17 November 2026)

Hotfix Stage 9c diterapkan pada kueri angka, filter temuan, SAWarning, dan deklarasi TypeScript tanpa migrasi baru. Tes lama dan baru lulus dalam kelompok (197 tes pada run awal dalam tiga kelompok + satu tes compiler SQL tambahan; run ulang kelompok lain 36 dan 50 lulus, tetapi run gabungan legacy terkena state SQLite antartes) serta 69 tes Node. Uji PostgreSQL 16 nyata dan build frontend masih **belum lulus/terverifikasi** karena server PG tidak tersedia dan npm registry `EAI_AGAIN`. Baca `QA_STATUS_STAGE9C_FIX.md` untuk rincian jujur. **Jangan langsung upgrade produksi sebelum staging**.

**QA Stage 9c (17 November 2026):** 186/186 tes backend utama, 7/7 tes load-test, 68/68 tes frontend Node lulus. `npm install` gagal DNS `EAI_AGAIN`; build React/PostgreSQL 16/browser belum diverifikasi. Masih kandidat staging. Lihat `QA_STATUS_STAGE9C.md`.


**QA tambahan per 17 November 2026:** backend utama 179/179 lulus (`--ignore=backend/tests/test_loadtest_runner.py`), load-test runner 7/7 lulus, frontend `node --experimental-strip-types --test frontend/tests/*.test.mjs` 61/61 lulus. Instalasi npm gagal DNS EAI_AGAIN sehingga Vite build masih belum terverifikasi; PostgreSQL 16 produksi, browser dan 100.000 data belum diuji. Lihat `QA_STATUS_STAGE9B.md`.

## Stage 9b (17 November 2026) — Status kandidat staging

Tambahan baru Stage 9b diperiksa dengan tes terfokus SQLite dan JS murni; lihat `QA_STATUS_STAGE9B.md`. Backend lama tidak diubah asersi tesnya. Build npm/Vite dan PostgreSQL 16 LXC belum lolos verifikasi; jangan klaim production-ready.

**Stage 9a (2026-11-17):** lihat `QA_STATUS_STAGE9A.md`. 11 tes backend khusus Stage 9a, 56 tes Node lulus; baseline dites per kelompok, tetapi suite final satu proses dan build Vite belum lulus. npm install gagal `EAI_AGAIN`. Rilis kandidat staging; PostgreSQL/browser belum diuji.

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

---

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

---

# QA STATUS — BerauLoad V1.6.0 Stage 7 (2026-11-16)

**STATUS: KANDIDAT STAGING. TIDAK TERVALIDASI UNTUK PRODUKSI.**

## Hasil yang benar-benar dijalankan

| Perintah / area | Hasil |
|---|---|
| `PYTHONPATH=backend python -m pytest -q` kelompok dasar (15 file) | **58 passed** |
| `PYTHONPATH=backend python -m pytest -q` kelompok Stage 4a–6 (6 file) | **36 passed** |
| `PYTHONPATH=backend python -m pytest -q` kelompok tahap akhir + Stage 7 (8 file, termasuk `test_api.py` sebagai inisialisasi lingkungan pengujian) | **62 passed** |
| Total tes backend unik | **155 passed** terpisah per kelompok; 58 + 36 + 62 − 1 tes `test_api` yang diulang = 155. **144 tes baseline + 11 tes baru**; tidak ada tes lama yang diedit. |
| Satu perintah pytest seluruh suite | Dicoba dua kali; batas sesi proses habis saat sekitar 63–64%, **tidak boleh diklaim full-run lulus**. Seluruh modul kemudian diverifikasi melalui kelompok di atas; pengelompokan perlu memulai modul `test_api.py` sebelum modul uji legacy dengan env DB global. |
| `node --experimental-strip-types --test frontend/tests/*.test.mjs` | **48 passed** (43 baseline + 5 Stage 7). |
| `python -m compileall -q backend/app deploy/loadtest` | Lulus |
| TypeScript `createSourceFile` parser untuk seluruh TS/TSX | 0 syntax diagnostics; **bukan type-check** |
| `cd frontend && npm install --no-audit --no-fund --fetch-retries=0 --fetch-timeout=15000` | **GAGAL**: DNS `EAI_AGAIN registry.npmjs.org` ketika mengunduh `@types/react`. Percobaan awal npm tanpa batas retry juga gagal terselesaikan dan dihentikan. |
| `cd frontend && npm run build` | **GAGAL** di `tsc -b`; modul React/tipe React, Lucide, Recharts tidak terpasang. Build tidak dapat dinyatakan lulus. |
| SQLite in-process local test (`runner.py --asgi-sqlite --duration 4 --writers 2 --readers 2 --exports 1`) | Berjalan, tanpa HTTP error, **0 nilai hilang**, uji tabrakan 2 akun True; dashboard GET dan export berhasil. **Uji logika, bukan benchmark kapasitas**. |
| PostgreSQL 16 LXC, `pg_advisory_xact_lock` runtime, 20 writers + 60 readers 5 menit, nginx `-t`, browser, Cloudflare | **BELUM DIUJI**. Tidak ada klaim p95 kapasitas atau kompatibilitas produksi. |

## Perilaku yang diuji

- PUT sparse menulis hanya input yang sungguh berubah dan computed yang berubah, tidak menyentuh ID/nilai/source parameter lain pada jam sama; input 0 tetap 0, null terpisah.
- `base` cocok -> 200, basi -> 409 daftar konflik (kode, nilai Anda/server, siapa, kapan), tanpa penulisan parsial. Override dicatat bersama nilai server sebelumnya. Tanpa perubahan -> `unchanged:true` dan tanpa audit/recalc. Recalc gagal -> rollback transaksi.
- Hari verified/final tetap 409. Batas hak per unit pada tes lama tetap lulus.
- Sesi `GET /api/auth/me` menyertakan `expires_at`, rolling 5 menit membatasi commit, absolute expiry membatasi sesi. Percobaan login per (IP, username) tersimpan di tabel, 5 percobaan/15 menit. Migrasi Stage 6 minimal -> Stage 7 serta pengulangan migrasi dua kali diuji, tanpa mengubah baris sesi lama.
- Tes Node menguji antrean per jam, request serial, retry hingga tiga kali, 4xx tanpa retry, jeda/pemulihan 401, konflik 409, backup lokal, kunci user/unit/hari, masa kedaluwarsa tujuh hari, string kosong vs 0, heartbeat dan banner sisa sesi.

## Rancangan dan keterbatasan

- Lock yang dipilih: `pg_advisory_xact_lock` pada hash 64-bit dari `(unit_id,day,hour)`, dilepas otomatis saat commit atau rollback; **belum dieksekusi di PostgreSQL test**. Jam global baru menggunakan PG `INSERT ... ON CONFLICT DO NOTHING` untuk mencegah balapan pembuatan `HourRecord` dari dua unit.
- Rate limiter dipindah ke tabel; tambahan indeks `ix_login_attempts_identity_time` diperlukan untuk filter (IP, username, waktu). Indeks pembacaan historis **tidak diubah** karena belum tersedia bukti EXPLAIN pada PostgreSQL.
- Cache agregasi tetap in-process; `UVICORN_WORKERS>1` sengaja ditolak sebelum startup. Tidak ada klaim migrasi serentak multi-worker/cache invalidation lintas-proses. Hanya satu worker didukung.
- Belum ada lima hasil `EXPLAIN (ANALYZE)` PostgreSQL, pemetaan lima endpoint terburuk, atau pemeriksaan bottleneck PDF besar pada LXC. Jangan menambah indeks baru sebelum benchmark nyata.
- Keamanan loadtest: hanya loopback, port bukan 8092, `--confirm-isolated`, marker health `test_instance=true`; disediakan compose, port, volume berbeda. **Jangan** gunakan script itu ke data produksi.
- Migrasi `20261116_17_stage7_session_safety` bersifat additive/versioned (kolom `last_seen_at` dan tabel login attempts). Cleanup sesi expired pada startup adalah tindakan operasional yang diminta, bukan mutasi data historis; backup tetap wajib sebelum deploy.
- Audit UI browser seperti konflik per field, popup login, localStorage unavailable dan sesi realtime masih perlu test manual pada staging.

## Kesimpulan

**Kandidat saja.** Backend/Node smoke dan regresi kelompok lulus. `npm run build` belum lulus akibat npm tidak tersedia; PostgreSQL/advisory lock, load 20+60, browser, dan nginx belum terbukti. Jangan instal langsung ke LXC produksi. Jalankan `README_UPGRADE_V1_6_0_STAGE7.md` dan `deploy/loadtest/README.md` di staging dahulu.

---

# QA_STATUS — V1.6.0 Stage 6 (2026-11-16)

**STATUS: KANDIDAT STAGING.** Semua tes backend SQLite dan Node lulus. `npm install` tidak dapat mencapai registry npm (`EAI_AGAIN`), sehingga build frontend **GAGAL/BELUM TERVERIFIKASI**; PostgreSQL 16 dan browser LXC belum diuji. Jangan langsung deploy produksi.

- Baseline V1.6.0 Stage 5 Hotfix 1; **tidak ada migrasi**, perubahan baca-saja kelengkapan dan metadata link topologi JSON. Tidak ada perubahan pembacaan/final/formula produksi.
- `PYTHONPATH=backend python -m pytest -q backend/tests`: **144 passed** (66,15 detik). Termasuk 138 tes lama + 6 tes backend Stage 6: basis system.load/any_input, 0 dan jam masa depan, role nonaktif, peran/hak unit, ekspor XLSX/sanitasi, satu query agregasi, arah link/arsip/restore/cycle.
- `node --experimental-strip-types --test frontend/tests/*.test.mjs`: **43 passed**. Mencakup helper sel/ringkasan dan patch simbol link tanpa menyentuh garis. Pengujian TypeScript parser `createSourceFile`: 61 TS/TSX, **0 parse errors**; ini bukan type-check/build sukses.
- Benchmark SQLite sintetis `PYTHONPATH=backend python backend/tests/benchmark_stage6_completeness.py`: 62 hari × 24 jam × 1 ULP + 5 KP = 1.488 slot HourRecord, 8.928 readings, 372 sel. Waktu enam pengukuran: 0,01968; 0,01203; 0,01207; 0,01136; 0,01165; 0,01232 detik; median **0,01205 detik**. EXPLAIN: indeks `sqlite_autoindex_hour_records_1` pada hari dan `sqlite_autoindex_readings_1` pada hour_id dipakai; indeks baru tidak dibutuhkan pada data uji ini. PostgreSQL belum benchmark.
- Ekspor XLSX dibaca ulang dengan openpyxl (keduanya sheet tersedia), teks berawalan `=`, `+`, `-`, `@` dinetralkan, dan berkas sementara dihapus. Tautan ke atas/setingkat/diri/target arsip/tidak cocok ditolak, izin non-admin untuk menyimpan tetap 403, restore arsip ditolak menyebut simbol.
- **Belum diuji:** PostgreSQL 16, Docker Compose build/up, uji browser interaktif/ponsel, dan kesamaan data produksi ULP Tanjung Redeb. Tes lama tidak dimodifikasi. Tidak ada perubahan `schema_migrations` di Tahap 6.
- `cd frontend && npm install --no-audit --no-fund --fetch-retries=0 --fetch-timeout=15000` = **gagal** `EAI_AGAIN` untuk `registry.npmjs.org/@types/react`. `npm run build` = **gagal** pada TS2307 React, lucide-react, recharts dan types karena dependency belum tersedia. Tidak dianggap lulus.
- Benchmark SQLite sintetis: 62 hari × 24 jam × 1 ULP + 5 KP, 1.488 slot HourRecord, 8.928 readings, 372 sel. Enam pengukuran: 0,02486; 0,01287; 0,01165; 0,01163; 0,01398; 0,01364 detik. Median **0,01325 detik**. EXPLAIN menggunakan indeks tanggal unik HourRecord dan indeks unik Reading untuk hour_id; indeks baru tidak diperlukan pada sampel SQLite. **Tidak ada benchmark PostgreSQL.**
- Ekspor terbaca ulang dengan openpyxl, prefix `=` dinetralkan, dan file temp dihapus; target 422, izin 404, syarat final dan tautan arsip dipastikan pada tes.
- Belum diuji: Docker/PG16, browser (responsive dan klik interaktif), perbandingan data ULP Tanjung Redeb sebelum/sesudah upgrade; harus diuji di staging. Tes lama tidak diubah.

---

# QA_STATUS — V1.6.0 Stage 5 Hotfix 1 (2026-11-16)

**STATUS: KANDIDAT STAGING. Belum boleh dinyatakan lolos build frontend atau tervalidasi pada PostgreSQL/browser produksi.**

| Pemeriksaan aktual | Hasil |
|---|---|
| `PYTHONPATH=backend python -m pytest -q backend/tests` | **138 passed** dalam 56,56 detik; seluruh tes Stage 5 sebelumnya + 5 tes baru SQLite sintetis |
| `PYTHONPATH=backend pytest -q backend/tests/test_stage5_template_import_recalculation.py` | **5 passed**, mencakup computed KP→ULP→UP3, NULL dan kelengkapan, ULP final dan audit penanda, rollback saat jam ke-2 gagal dan hapus arsip, hari KP locked dilewati |
| `node --experimental-strip-types --test frontend/tests/*.test.mjs frontend/src/features/org-units/unitSelection.test.mjs` | **43 passed**, tanpa perubahan JS/TS/TSX komponen |
| `cd frontend && npm install` (env fetch retries 0, timeout 15s) | **GAGAL** `EAI_AGAIN` DNS registry.npmjs.org, `@types/react` tidak dapat diambil |
| `cd frontend && npm run build` | **GAGAL** modul React/Lucide/Recharts dan React types tidak tersedia; `tsc -b` tidak dapat menyelesaikan build |
| PostgreSQL 16, browser, Docker produksi, kesamaan angka ULP Tanjung Redeb | **BELUM DIUJI** di lingkungan LXC pengguna |

**Benchmark terisolasi (SQLite sintetis, commit 744 jam / 31 × 24, 1 KP + formula ULP + formula UP3):** Baseline Stage 5 = **9,751 dtk**, sumber KP 744 baris tetapi rekap ULP 0 dan UP3 0. Stage 5 Hotfix 1 = **13,036 dtk**, KP 744, ULP 744, UP3 744. Tambahan **3,285 dtk (33,7%)** untuk dua perhitungan lintas unit per jam. Pengukuran satu kali masing-masing dan bukan janji performa PostgreSQL. Perhitungan dilakukan sekali per jam, bukan per nilai input.

**Skema/rollback:** tidak ada migrasi baru; `schema_migrations` tidak berubah akibat patch. Semua data tes sementara; kegagalan pada jam ke-2 di endpoint commit menghasilkan rollback batch, readings, hour_records, rekap, audit commit, dan penghapusan arsip; staging tersisa untuk retry. File lama/akun/izin/formula tidak dimodifikasi oleh patch. Tes lama tidak diubah. Wajib backup dan uji pada staging sebelum produksi. Lihat `README_UPGRADE_V1_6_0_STAGE5_HOTFIX1.md`.

---

# QA_STATUS — BerauLoad V1.6.0 Stage 5 (16 November 2026)

**STATUS: KANDIDAT STAGING. BUILD FRONTEND BELUM LULUS; JANGAN DIPAKAI PADA DATA PRODUKSI TANPA BUILD DAN SMOKE TEST STAGING.**

## Perintah yang benar-benar dijalankan

| Perintah / pemeriksaan | Hasil aktual |
|---|---|
| `PYTHONPATH=backend python -m pytest -q backend/tests` | **133 passed**, 0 failed, SQLite sintetis, sebelum satu assertion tambahan untuk `1 dari 2` (assertion tambahan tersebut lulus di tes terarah). Tidak ada tes lama yang diubah. |
| `PYTHONPATH=backend python -m pytest -q backend/tests/test_stage5_unit_sources.py` | **8 passed**, 0 failed, termasuk migrasi restart, lintas konfigurasi, rollback transaksional, 0 vs NULL, rekap KP→ULP→UP3, ULP final, status sumber, topologi. |
| `node --experimental-strip-types --test frontend/tests/*.test.mjs frontend/src/features/org-units/unitSelection.test.mjs` | **43 passed**, 0 failed; tes frontend Stage 4c lama tidak diubah. |
| `python -m compileall -q backend/app` | **Lulus** (tanpa kesalahan kompilasi Python). |
| Transpilasi sintaks TypeScript/TSX di `frontend/src` dengan TypeScript global `transpileModule` | **Lulus secara sintaks**; pemeriksaan ini **bukan** typecheck/dependency build. |
| `cd frontend && npm install --no-audit --no-fund --fetch-retries=0 --fetch-timeout=12000` | **GAGAL**: `EAI_AGAIN registry.npmjs.org` saat mengambil `@types/react`. |
| `cd frontend && npm run build` | **GAGAL**: React, Recharts, Lucide serta tipe React tidak tersedia; banyak `TS2307`, `TS7026`, dan kesalahan turunan. Setelah perbaikan konflik impor `Status`, build dicoba ulang dan masih tidak lulus karena dependensi tidak terpasang. **Tidak boleh dianggap berhasil.** |
| PostgreSQL 16 / migration nyata, `docker compose build`, `docker compose up`, browser multi-role, angka produksi ULP Tanjung Redeb | **BELUM DIUJI** pada lingkungan pengembang. |

## Poin yang diverifikasi dengan SQLite sintetis

- Kode parameter milik ULP dapat merujuk KP di bawahnya; UP3 dapat merujuk ULP/KP, tetapi referensi ke induk atau sesama cabang ditolak. Pemeriksaan berlaku pada formula, dashboard, topologi, historical, engineering, report, export, dan performance.
- `SUM(0, 7) == 7`; operand belum terisi menghasilkan NULL (tidak ada nilai hasil) dan keterisian `1 dari 2 sumber terisi`, setelah dilengkapi `2 dari 2 sumber terisi`.
- Ketika pembacaan KP berubah, rumus ULP lalu rumus UP3 diperbarui dalam transaksi yang sama. Penyimpanan sumber yang sengaja digagalkan saat recalc **tidak meninggalkan pembacaan/hasil parsial**.
- ULP final tidak ditimpa, penanda `source_changed_after_final` muncul untuk verifier/admin; admin reopen memperbarui perhitungan. UP3 selalu memperbarui hasil dan menampilkan sumber yang draft.
- Finalisasi ULP dengan KP draft ditolak tanpa konfirmasi dan bisa dilakukan setelah konfirmasi; identitas perubahan masuk audit.
- Akun KP tidak membaca parameter induk, KP setingkat, atau mengubah konfigurasi. Test migration startup berulang tidak membuat baris baru atau memindahkan data pada startup kedua.

## Risiko residual sebelum produksi

1. **Build frontend belum bisa divalidasi** tanpa npm yang berfungsi. Jalankan `npm install` dan `npm run build` di server/staging yang dapat mengakses registry npm; tangani error TypeScript nyata (jika ada) sebelum deploy. Tes Node + transpile sintaks bukan pengganti build.
2. Belum diuji di **PostgreSQL 16** dengan migrasi pada clone produksi dan belum ada hasil browser nyata. Uji kasus antar role, override unit, GET/download dan status jam dengan data sintetis lebih dulu.
3. Belum ada pembandingan angka nyata ULP Tanjung Redeb sebelum/sesudah, dan tidak ada akses server produksi dari lingkungan QA ini.
4. Tabel baru `unit_source_changes` diharapkan hanya mendapat entri ketika sumber relevan berubah pada hari induk yang terkunci; tidak ada backfill atau mutasi startup. Verifikasi read-only sebelum/selesai deploy sesuai `README_UPGRADE_V1_6_0_STAGE5.md`.

## Model dan batas arsitektur

- Migrasi additive `20261116_16_stage5_source_changes`, tabel `unit_source_changes`, tanpa DROP/ALTER dan tanpa ubah isi kolom lama.
- Source `Reading`, formula computed, dan penanda lock berada pada transaksi SQLAlchemy yang sama. Tidak ada job background atau perubahan pada data verified/final.
- Tidak menyimpulkan listrik, topologi, ambang teknis, atau status breaker. Tidak membuat rekap otomatis; operand formula tetap eksplisit. Waktu slot global WITA.
- Laporan dalam tabel QA mengikuti hasil aktual; angka hasil uji di staging produksi belum tersedia.

---

# QA — V1.6.0 Stage 4c UI Hotfix 1 (16 November 2026)

**STATUS: KANDIDAT STAGING; BUILD FRONTEND BELUM LULUS.** Perubahan fungsi hanya frontend Pengaturan → Pengguna. Backend `main.py` hanya mengubah metadata `app.version` dan `/api/health`. Tidak ada migrasi, perubahan DB, hak izin, atau endpoint.

| Pengujian aktual | Hasil |
|---|---|
| `node --experimental-strip-types --test frontend/tests/*.test.mjs frontend/src/features/org-units/unitSelection.test.mjs` | **43 passed**, 0 failed; termasuk 4 tes baru di `frontend/tests/userAccess.test.mjs` |
| `PYTHONPATH=backend python -m pytest -q backend/tests` | **125 passed**, 0 failed; data uji SQLite sintetis; tidak ada tes backend yang diubah |
| TypeScript `transpileModule` untuk `App.tsx` dan `UserManager.tsx` | **0 diagnostics sintaks**; ini bukan typecheck/build |
| `cd frontend && npm install --no-audit --no-fund --fetch-retries=0 --fetch-timeout=15000` | **GAGAL** DNS `EAI_AGAIN registry.npmjs.org` pada `@types/react` |
| `cd frontend && npm run build` | **GAGAL** — React, tipe React, Recharts, Lucide tidak terpasang; TypeScript/Vite build tidak dapat dinyatakan lulus |
| PostgreSQL 16, Docker Compose, browser dengan akun admin dan pengguna | **BELUM DIUJI** |
| Nilai data asli ULP Tanjung Redeb | **BELUM DIUJI**; tidak ada akses produksi di lingkungan ini |

Backend menyediakan seluruh data melalui GET `/api/users`, GET `/api/org-units`, GET `/api/org-units/{id}/access`; UI merangkum hasil tiap unit tanpa endpoint baru. Admin ditampilkan sebagai akses global. Grant UP3 non-admin dibatasi ke management, mengikuti aturan backend. Pengiriman pembuatan akun tetap memakai `accesses` yang sudah berlaku. Tes Node memeriksa default grant per level, validasi tanpa grant, pemisahan akses per pengguna, dan label admin global. Review perilaku browser dan keterbacaan responsif tetap wajib di staging.

**Sebelum produksi:** lakukan `npm install`, `npm run build`, `docker compose build`, smoke test, lalu cek akses per unit di browser dan buat backup seperti panduan upgrade. Jangan mengklaim hotfix lulus build hanya dari kelulusan tes Node.

---

# QA Status — V1.6.0 Stage 4c (2026-11-15)

**STATUS: KANDIDAT STAGING, BELUM SIAP PRODUKSI.** Build frontend belum berhasil karena dependensi tidak dapat diunduh; belum uji browser ataupun PostgreSQL 16 LXC pengguna. Tidak pernah menyentuh volume/data pengguna.

| Pengujian | Perintah / hasil |
|---|---|
| Python syntax | `python -m compileall -q backend/app` — lulus |
| Backend regresi dan baru | `cd backend && PYTHONPATH=. pytest -q tests --disable-warnings --maxfail=1` — **125 passed** |
| Tes Node seleksi unit | `node --test frontend/src/features/org-units/unitSelection.test.mjs` — **3 passed** |
| TS/TSX syntax-only | TypeScript global `transpileModule` atas 56 file — 0 syntax errors; **bukan** typecheck dan bukan Vite build |
| Install frontend | `npm install --fetch-retries=0 --fetch-timeout=8000 --no-audit --no-fund` — **gagal**, DNS `EAI_AGAIN registry.npmjs.org` |
| Build frontend | `cd frontend && npm run build` — **gagal**, package React, Recharts, dan tipe React belum tersedia akibat install gagal. Lulusnya TypeScript tidak dapat dinyatakan |
| Browser/API riil | **Belum diuji** di Docker/LXC target |
| PostgreSQL 16 | **Belum diuji**; backend tests memakai SQLite sementara |
| Data operasional ULP Tanjung Redeb | **Tidak diuji dengan data nyata**; tidak boleh diasumsikan hasil angka sama tanpa smoke test pengguna |

Tes lama yang dimodifikasi terbatas pada (1) `test_stage4a_units.py` dengan asersi massal 422→pemrosesan parsial sesuai keputusan 4c, dan (2) fixture pembuatan pengguna di `test_dashboard_builder.py`, `test_org_units.py`, `test_equipment_kinds.py`, `test_input_forms.py`, `test_report_builder_v146.py`, `test_dashboard_settings.py`, `test_org_units_home.py`, `test_v144_export_management.py`, `test_topology.py`, dan `test_standard_reports_v1461.py` untuk menyediakan grant unit secara eksplisit (aturan 4c). Tes lainnya tidak diubah.

Tes tambahan memeriksa unit tanpa data dilewati, 422 bila semua dilewati, audit per unit, grant ganda, pencabutan, penolakan akun baru non-admin tanpa grant, daftar unit terbatas hak, fallback scope pribadi pada unit non-home, serta `setup()` dua kali tanpa penambahan/pemindahan preferensi. Tes browser per peran dan unduhan antar-unit masih wajib dilakukan.

# QA BerauLoad V1.6.0 Stage 4b — Konfigurasi per Unit (2026-11-15)

**KANDIDAT STAGING**. Pengguna menyatakan Stage 4a berjalan di LXC dengan data sungguhan. Build dan pengujian Stage 4b **belum** dijalankan pada Docker/PostgreSQL/browser LXC pengguna. Tidak boleh menyebut Stage 4b production-tested.

| Perintah aktual di lingkungan build | Hasil |
|---|---|
| `PYTHONPATH=backend python -m pytest -q backend/tests --disable-warnings` | **122 passed** (112 tes Stage 4a dengan penyesuaian asersi 4b + 10 tes baru) |
| `node --experimental-strip-types --test frontend/tests/*.test.mjs` | **31 passed** |
| `python -m compileall -q backend/app backend/tests` | **Lulus** |
| `npm install --prefer-offline --no-audit --no-fund --fetch-retries=0` dalam `frontend/` | **GAGAL** DNS `EAI_AGAIN registry.npmjs.org` |
| `npm run build` dalam `frontend/` | **GAGAL** dependensi `react/jsx-runtime`, `lucide-react`, dan tipe React tidak tersedia; belum membuktikan build/Vite production |
| SQLite legacy schema → Stage 4b + `setup()` berulang | **Lulus** (tes sementara sintetis) |
| PostgreSQL 16, `docker compose build/up`, browser, concurrency produksi | **BELUM DIUJI** |

### Bukti pengujian sintetis
`backend/tests/test_stage4b_config.py` mencakup migrasi schema SQLite pre-4b dan audit legacy tidak dibackfill; pemilik konfigurasi pribadi dengan akses tepat satu ULP/KP dan fallback UP3 ambigu; `setup()` dua kali tanpa baris berpindah/bertambah; scope Topologi per unit, direct-ID 404 pada Dashboard/Historical/Engineering/Report/Export; unit baru dengan tab default; UP3 menolak tab Form Input tetapi menerima Dashboard/Topologi; copy settings preview/commit dan pemetaan kode; zero copy pada Reading/HourRecord/UnitDayState; CSRF; serta rollback semua objek setelah kegagalan sintetis di tengah copy.

### Penyesuaian tes lama akibat aturan baru, bukan pengurangan pemeriksaan
- `test_dashboard_builder.py::test_permissions_duplication_and_archive`: management UP3 harus meminta unit home lewat `X-Unit-Id`, dan konfigurasi tidak bisa diubah non-admin.
- `test_dashboard_settings.py::test_chart_defaults_permissions_and_validation`: home config perlu header eksplisit untuk management UP3; preferensi konfigurasi non-admin kini dilarang.
- `test_standard_reports_v1461.py::test_preference_scope_auth_and_reset`: scoped read dan admin-only config.
- `test_topology.py::test_bad_csrf_and_non_admin_write`: direct ID home dari konteks UP3 404; fixture Rule harus membawa `unit_id` home.
- `test_stage4a_units.py::test_unit_catalog_scope_and_legacy_config_guard`: unit baru mengembalikan 200 + daftar konfigurasi kosong, bukan 404 dari legacy_home_scope.
- `test_report_builder_v146.py::test_report_auth_and_validation`: management UP3 menggunakan header ULP home untuk membaca template ULP.
- `test_v144_export_management.py` (dua tes): template/report/share bersifat unit-scoped; non-admin tidak boleh mengubah konfigurasi.
- `test_template_import.py::test_hidden_tab_and_inactive_metrics_never_exported`: fixture penempatan form baru harus menyertakan `unit_id` supaya data tes milik unit yang benar.

### Hal yang wajib diperiksa di LXC sebelum 4c
Verifikasi hasil migrasi per tabel melalui SQL read-only pada panduan upgrade; nol konfigurasi orphan `unit_id IS NULL`; nol tab/placement milik UP3; jumlah `readings`, `hour_records`, `day_states`, `import_batches` tetap; status hari dan hasil Dashboard H/J ULP Tanjung Redeb tetap. Uji seluruh halaman konfigurasi ULP lain dengan header terotorisasi, cek CSRF, admin-only, 404 direct-ID; lakukan uji copy pada staging kosong, termasuk rollback. Kirim hasil build, smoke, SQL dan browser untuk memperbarui QA. Jangan memodifikasi data produksi dengan tes sintetis.

---

# QA BerauLoad V1.6.0 Stage 4a (2026-11-15)

**KANDIDAT STAGING.** BerauLoad versi sebelumnya dipakai dengan data nyata pada LXC pengguna, tetapi **Stage 4a belum dibangun/diuji di LXC**, PostgreSQL 16, atau browser. Bukti smoke test produksi masih harus dikirim pengguna.

| Perintah yang dijalankan pada lingkungan build | Hasil |
|---|---|
| `PYTHONPATH=backend python -m pytest -q backend/tests` | **112 passed**, 0 gagal (108 baseline + 4 kasus Stage 4a; fixture lama disesuaikan karena aturan baru) |
| `node --experimental-strip-types --test frontend/tests/*.test.mjs` | **31 passed** |
| `python -m compileall -q backend/app backend/tests` | **Lulus** |
| `npm install --no-audit --no-fund --fetch-retries=0` (`frontend/`) | **GAGAL** DNS `EAI_AGAIN registry.npmjs.org` |
| `npm run build` (`frontend/`) | **GAGAL** karena dependensi React/@types/JSX belum terpasang; tidak membuktikan kompilasi produksi berhasil |
| PostgreSQL 16 / Docker Compose / autentikasi browser / CSRF di LXC | **BELUM DILAKUKAN** |

### Tes Stage 4a dengan SQLite sementara
`backend/tests/test_stage4a_units.py` mencakup isolasi metrik satu slot jam lintas ULP/KP, kode parameter eksplisit lintas unit 404, penolakan akses KP ke induk/ULP lain, management UP3 hanya baca, operator ULP mengisi KP, verifier ULP finalisasi KP, admin global reopen, audit unit+peran, transaksi bulk rollback bila KP tidak lengkap, dan perlindungan konfigurasi legacy. Tidak ada data nyata pengguna yang dipakai pada tes.

### Asersi/fixture lama yang harus mengikuti keputusan baru
- `backend/tests/test_org_units_home.py::test_legacy_api_new_asset_metric_user_and_dashboard_unchanged_on_replay`: pengguna **management UP3** sekarang otomatis mengakses UP3 (bukan home ULP), sesuai keputusan Stage 4a; pemeriksaan asset, metric, Dashboard/Compare dan migrasi ulang tetap dilakukan.
- `backend/tests/test_template_import.py`: fixture status final menggunakan `UnitDayState` milik home (bukan DayState global); fixture `ImportBatch` synthetic memakai `unit_id` agar riwayat scoped tetap terlihat; pengujian lock/conflict/rollback dan respons role tetap dipertahankan.
- `backend/tests/test_org_units.py`: asersi `can_write` menguji hak operator ULP pada KP keturunan sesuai aturan inherited write; tetap melarang KP menulis ke atas.

### Belum terverifikasi atau di luar Tahap 4a
- Build asli Vite/React tidak berhasil karena jaringan; coba pada LXC yang memiliki dependensi npm dan jalankan `docker compose build` sebelum up.
- Migrasi konfigurasi ke masing-masing unit (4b) dan pemilih unit UI, read-only UX, manajemen penugasan user (4c) belum dibuat. Endpoint konfigurasi legacy pada unit lain sengaja dibatasi dan belum semuanya menampilkan halaman kosong 200.
- Uji PostgreSQL 16, concurrency, sesi/CSRF dengan pengguna sungguhan, ekspor import besar, akses lintas seluruh endpoint, dan angka H/J legacy nyata tetap wajib sebelum produksi.
- Tidak ada skema migrasi Stage 4a, tidak ada klaim sukses pada database produksi, dan belum ada hasil pemeriksaan LXC dari pengguna.

# QA BerauLoad V1.6.0 Stage 3 — Parameter Utama per Unit (2026-11-15)

**KANDIDAT STAGING**, bukan rilis yang sudah diverifikasi production. Pengguna sebelumnya telah menggunakan BerauLoad di LXC dengan data nyata; **Stage 3 belum terpasang dan belum diuji di LXC pengguna** menurut informasi yang tersedia.

| Perintah / pemeriksaan di lingkungan source build | Hasil |
|---|---|
| `PYTHONPATH=backend python -m pytest -q backend/tests --disable-warnings --maxfail=1` | **108 passed**, 103 regresi lama tidak diubah + 5 kasus Stage 3 |
| `node --experimental-strip-types --test frontend/tests/*.test.mjs` | **31 passed**: 29 tes lama, termasuk 2 tes layout geometry `.ts`, + 2 tes baru role-first/fallback Topologi |
| `python -m compileall -q backend/app` | **Lulus** |
| Parser TypeScript 5.8.3 terhadap 53 source TS/TSX | **0 kesalahan sintaks**; ini **bukan** build typechecker penuh |
| `npm install --no-audit --no-fund --fetch-retries=0 --fetch-timeout=10000` | **GAGAL** DNS `EAI_AGAIN registry.npmjs.org` |
| `npm run build` | **GAGAL** `TS2307`/dependensi React/Vite/@types belum tersedia setelah install gagal; tidak dapat menyatakan build Vite lulus |
| PostgreSQL 16, Docker Compose build/up, smoke test browser di LXC | **BELUM DIJALANKAN** |

**Pengujian Stage 3 (`backend/tests/test_primary_metrics_stage3.py`):** SQLite sementara dan data sintetis; perbandingan hasil Dashboard, Analytics, Compare, Monitoring dengan role lama vs role baru berisi nilai sama; role kosong HTTP 200 `configured:false` untuk endpoint utama dan konfigurasi laporan; CSRF, admin, peran ganda; daftar usage dan konfirmasi nonaktif; aturan dua seri H/J sesuai pasangan role. Tes frontend tambahan `frontend/tests/primaryMetricRoles.test.mjs` memastikan pemilihan role lebih dulu dan fallback nama+satuan pada unit yang sama.

**Catatan runner JS:** tanpa `--experimental-strip-types`, `node --test frontend/tests/*.test.mjs` menghasilkan 29 passed, 1 failed pada loader `.ts` (ERR_UNKNOWN_FILE_EXTENSION) untuk tes layout lama; dengan Node v22.16.0 + opsi tersebut seluruh **31/31** lulus.

**Compat:** Kode H/J lama tetap pada seed, default role Stage 1 tetap; tidak ada migrasi DB baru, penulisan ulang readings/hour_records/day_states, atau revisi formula/dashboard. Modul backend lama dipecah menjadi router kecil tanpa mengganti URL. Tidak ada pengubahan tes regresi sebelumnya. Saved dashboard eksplisit tidak ditimpa meskipun role berubah. Jika role kosong, default endpoint mengembalikan `configured:false`, bukan nilai nol yang direkayasa. Verifikasi **kesamaan angka data nyata** dan cakupan semua antarmuka pada LXC masih wajib.

**Risiko lanjutan:** npm/Vite dengan dependensi asli belum berhasil, browser interaksi admin belum diuji, perubahan role pada data nyata dapat mengubah pemilihan sumber (tindakan admin eksplisit, bukan migrasi), inventaris usage dibangun dari referensi konfigurasi aktif dan harus diperiksa sampelnya, serta PostgreSQL 16 concurrency/constraint perlu divalidasi. Lakukan backup database+uploads, source, dan role snapshot; staging smoke test sebagaimana `README_UPGRADE_V1_6_0_STAGE3.md`. Kirim hasil LXC tanpa kredensial untuk memperbarui QA secara jujur.

---

# QA BerauLoad V1.6.0 Tahap 2 — Template Import (2026-11-15)

**KANDIDAT STAGING**, source tidak boleh disebut sudah production-tested. Pengguna sebelumnya menyatakan BerauLoad berjalan di LXC, tetapi belum ada uji nyata V1.6.0 Stage 2 di LXC/PostgreSQL 16.

| Perintah aktual di lingkungan build | Hasil |
|---|---|
| `PYTHONPATH=backend python -m pytest -q backend/tests` | **103 passed, 0 failed, 0 skipped** (80 lama + 23 baru) |
| `PYTHONPATH=backend python -m pytest -q backend/tests/test_template_import.py` | **23 passed** (parameterized tests) dengan SQLite sementara: metadata/format, formula injection seluruh sheet, unit salah, duplikat, konflik/lock, computed built-in dan custom, CSRF/role, arsip dan rollback |
| `node --test frontend/tests/topology*.test.mjs` | **27 passed** |
| `npm install --no-audit --no-fund --fetch-retries=0 --fetch-timeout=8000` | **GAGAL** DNS `EAI_AGAIN registry.npmjs.org` |
| `npm run build` | **GAGAL** dependensi React/@types/lucide-react belum tersedia; **bukan** bukti build TypeScript/Vite lulus |
| Parser TypeScript global 5.8.3 | **52 TS/TSX, nol error sintaks** |
| PostgreSQL 16, Docker Compose build/up, uji browser di LXC | **BELUM DIJALANKAN** |

**Pengujian database:** SQLite sementara dengan data sintetis, tidak mengakses data LXC atau tabel produksi. Tes lama dipertahankan tanpa modifikasi. Validasi LXC harus memastikan endpoint lama dan angka per jam tetap sama; backup database+uploads sebelum menerapkan patch. `day_states` tetap status resmi. `ImportBatch.kind` mengklasifikasi metadata tanpa mengubah baris `readings` atau `hour_records` saat migrasi.

**Risiko belum diverifikasi:** build npm dengan dependency asli, Postgres transaction isolation dan concurrency import, integrasi file ZIP di Docker, UI browser dan batas ukuran Excel 15MB/92 hari pada perangkat nyata. Tindakan berikut: minta output `./deploy/test.sh`, `docker compose build`, `docker compose ps`, `./deploy/smoke-test.sh`, query backfill `kind` dan satu siklus preview/commit file sintetis (bukan data operasional), tanpa kredensial; perbarui QA_STATUS dari hasil tersebut.

---

# QA BerauLoad V1.6.0 Tahap 1.2 — Guard Migrasi Startup (2026-11-15)

**Status KANDIDAT STAGING.** Perbaikan diuji terhadap SQLite sintetis dan source lokal; **belum** ada pengujian PostgreSQL 16, Docker Compose, atau browser pada LXC pengguna untuk versi Stage 1.2. Pengguna sebelumnya melaporkan BerauLoad berjalan di LXC, tetapi itu bukan bukti bahwa patch baru sudah terpasang/berjalan.

| Pemeriksaan/perintah aktual | Hasil |
|---|---|
| `PYTHONPATH=backend python -m pytest -q backend/tests --disable-warnings --tb=short` | **80 passed, 0 skipped** (76 tes sebelumnya, 4 kasus Stage 1.2) |
| `PYTHONPATH=backend python -m pytest -q backend/tests/test_org_units_stage12.py` | **4 passed** (1 restart nyata `setup()` + 3 jalur migrasi) |
| `node --test frontend/tests/topology*.test.mjs` | **27 passed** |
| `python -m compileall -q backend/app` | **Lulus** |
| `npm install --no-audit --no-fund --fetch-retries=0 --fetch-timeout=7000 --package-lock=false` (di `frontend/`) | **GAGAL** `EAI_AGAIN registry.npmjs.org` |
| `npm run build` (di `frontend/`) | **GAGAL** karena React/@types/lucide-react dan `react/jsx-runtime` tidak tersedia setelah npm install gagal; ini **bukan** validasi build Vite yang berhasil |
| PostgreSQL 16, Docker Compose build/up, uji UI browser LXC | **Belum dijalankan** |

## Detail regresi

- **Tes lama yang diubah:** `backend/tests/test_org_units.py::test_api_hierarchy_csrf_access_and_audit` — asersi `root.children == []` diubah agar memverifikasi satu anak ULP Tanjung Redeb (`legacy_home`), dan asersi akses user operator baru berubah dari unit root ke unit home, sesuai keputusan Stage 1.1. Seluruh pengujian CSRF, hak admin, hirarki, konflik, status, audit dan user non-admin tetap ada.
- Tes baru `backend/tests/test_org_units_stage12.py` membuat database SQLite sementara, menjalankan `main.setup()` sebelum dan dua kali setelah membuat data sah, lalu membandingkan snapshot penuh tabel organisasi/data. Diperiksa khusus parameter `computed` UP3, akses non-admin di UP3, role berbeda UP3 versus legacy_home, dan pengguna ULP lain yang tidak mendapat akses ke legacy_home.
- Jalur **Stage 4.2 → Stage 1.2**, **Stage 1 → Stage 1.2**, dan **Stage 1.1 → Stage 1.2** diuji secara sintetis; `readings`, `hour_records`, `day_states` identik sebelum/sesudah, dan kedua versi migrasi masing-masing tercatat sekali.
- Saat kedua versi sudah tercatat, `migration_home.run` hanya menjamin DDL; `migrations.run` tidak menyalin status atau akses. Hanya perbaikan owner `unit_id IS NULL` pada asset/metric/import_batch tetap diizinkan oleh aturan tugas.

## Risiko dan tindak lanjut LXC

1. Validasi `docker compose build`, `docker compose up -d --no-build`, `docker compose ps`, dan `./deploy/smoke-test.sh` di staging LXC.
2. Bandingkan hasil query owner, akses user, parameter UP3, status, dan hitungan Reading/HourRecord/DayState **sebelum/sesudah satu restart** (tanpa input berjalan). Cek juga respons Dashboard/H-J.
3. Jangan melakukan downgrade source ke Stage 1.1 pada database dengan akses UP3/ULP yang berbeda, sebab migrator lama dapat memindahkan akses atau menghentikan startup.
4. Kirim hasil command dan query tanpa kredensial agar status QA diperbarui berdasarkan pengujian nyata.

---

# QA BerauLoad V1.6.0 Stage 1.1 — Migrasi ULP Tanjung Redeb (2026-11-15)

**KANDIDAT STAGING.** BerauLoad versi sebelumnya pernah dilaporkan berjalan di LXC pengguna. Upgrade Stage 1.1 pada LXC/PostgreSQL **belum** diuji atau dikonfirmasi.

| Perintah yang dijalankan pada source build | Hasil |
|---|---|
| `PYTHONPATH=backend python -m pytest -q backend/tests` | **75 passed, 1 failed** |
| `PYTHONPATH=backend python -m pytest -q backend/tests -k 'not test_api_hierarchy_csrf_access_and_audit'` | **75 passed, 1 deselected** |
| `node --test frontend/tests/topology*.test.mjs` | **27 passed** |
| `PYTHONPATH=backend python -m pytest -q backend/tests/test_org_units_home.py` | **5 passed** |
| `python -m compileall -q backend/app` | Lulus |
| `npm install --no-audit --no-fund --fetch-retries=0 --fetch-timeout=12000` | **GAGAL** DNS `EAI_AGAIN registry.npmjs.org` |
| `npm run build` | **GAGAL** modul React/@types/lucide-react tidak ada (akibat instalasi gagal) |
| PostgreSQL 16 / Docker Compose / browser staging LXC | **Belum diuji** |

**Konflik tes lama (dibiarkan tidak diubah):** `test_org_units.py::test_api_hierarchy_csrf_access_and_audit` menguji UP3 tanpa anak. Stage 1.1 secara eksplisit mewajibkan seed ULP Tanjung Redeb, sehingga asersi lama salah untuk skema baru. Fungsi role non-admin pada UP3 di bagian lanjutan tes yang sama juga tidak relevan. Tes lama perlu direvisi pada tahap QA terpisah atas persetujuan pengguna. Jangan menyebut 76/76 lulus atau mengubah kode production supaya asersi lama lulus.

**Tes baru** (`test_org_units_home.py`) memakai SQLite sintetis terisolasi, menempuh dua jalur migrasi, menguji migrasi berulang, jumlah/isi `readings`,`hour_records`,`day_states`, dua `role_key`, unique UP3/home, owner default API dan helper, user admin/non-admin, dan kesamaan output `/api/dashboard` serta `/api/monitoring/capacity-vs-load` sebelum/sesudah pengulangan migrasi. Pengecekan perbandingan API bukan uji nilai data produksi.

**Yang wajib diminta setelah upgrade:** hasil `docker compose build`, `docker compose ps`, `./deploy/smoke-test.sh`, health, pemeriksaan query jumlah data & unit_owner dan grafik H/J di LXC, tanpa kredensial. Jangan mengklaim rilis production sebelum validasi nyata.

---

# QA V1.6.0 Tahap 1 — Fondasi Multi-Unit (2026-11-15)

**Status: KANDIDAT STAGING, BELUM DIUJI DI LXC PENGGUNA.** Pengguna telah melaporkan BerauLoad hingga Stage 4.2 berjalan di Debian LXC, tetapi hasil upgrade V1.6.0 Tahap 1 belum dikirim.

Dijalankan di lingkungan build (bukan server pengguna):

- `PYTHONPATH=backend python -m pytest -q backend/tests` → **71 passed**, mencakup 66 regresi Stage 4.2 dan 5 tes baru `test_org_units.py` (migrasi SQLite legacy berisi pembacaan, idempotent, hierarchy/scope, API admin/CSRF/audit, role_key, dual-write).
- `node --test frontend/tests/topology*.test.mjs` → **27 passed** (JS existing), tidak mengubah logic JS topologi.
- `python -m compileall -q backend/app` → **lulus**.
- Parser TypeScript 5.8.3 `createSourceFile` untuk **51 TS/TSX** → **0 kesalahan sintaks**.
- `npm --prefix frontend install --offline --no-audit --no-fund --ignore-scripts` → **GAGAL ENOTCACHED**.
- `npm --prefix frontend install --no-audit --no-fund --fetch-retries=0 --fetch-timeout=8000` → **GAGAL EAI_AGAIN**. Karena dependensi asli tidak terpasang, **`npm run build`/Vite belum tervalidasi di lingkungan ini**.
- **Belum dijalankan:** PostgreSQL 16 aktual, Docker build/up, browser interaksi UI, dan pemeriksaan data hasil backfill di LXC pengguna.

Invarian yang diuji: isi `readings`, `hour_records`, `day_states` sebelum/sesudah migrasi sama, baseline H/J tidak berubah, legacy role tetap dasar akses, unit baru hanya metadata. Jika hasil build/QA nyata LXC sudah tersedia, **mohon kirim `./deploy/test.sh`, `docker compose build`, `docker compose ps`, `./deploy/smoke-test.sh` dan query cek backfill** agar QA_STATUS dapat dilengkapi berdasarkan bukti production/staging yang nyata.


---

# BerauLoad V1.5.0 Tahap 4.2 — QA Status (2026-11-15)

**KANDIDAT STAGING.** Hasil dari lingkungan build saat ini, bukan bukti deployment pengguna.

- `PYTHONPATH=backend python -m pytest -q backend/tests`: **66 passed** (64 regresi + 2 tes Group Area/CRUD/revisi/data tetap aman).
- `node --test frontend/tests/topology*.test.mjs`: **27 passed** (21 regresi + 6 tes pure JS area, dynamic sizing, comparative trends, null/0 dan UI source).
- Parser TypeScript global 5.8.3 `createSourceFile` untuk **49 TS/TSX**: tidak ada parse error.
- `npm --prefix frontend install --no-audit --no-fund --fetch-retries=0 --fetch-timeout=8000`: **GAGAL** DNS `EAI_AGAIN registry.npmjs.org`; karena itu `npm run build` React/Vite **belum** dijalankan dengan dependency asli.
- Belum dijalankan: `docker compose build/up` dan browser drag/popup/scroll aktual pada LXC, PostgreSQL production, uji performa 20.000 px atau 100 area.

**Invarian:** Tidak ada migrasi DB, tidak menulis/membuat pengukuran, formula, rules atau switch status; Group Area adalah konfigurasi murni. Identitas dan geometrinya tervalidasi; layout lama tanpa `areas` tetap sah. Peak chart data NULL tidak dibuat 0 dan H/J REKAP tetap tidak berubah.

**Catatan rollback:** Source Stage 4.1 tidak dapat menerima `areas` saat menyimpan layout; pulihkan revisi sebelum `areas` di Stage 4.2 terlebih dahulu, atau restore DB terencana dengan mempertimbangkan semua perubahan aplikasi setelah backup.

---

# BerauLoad V1.5.0 Tahap 4.1 — QA Status

**Status: KANDIDAT STAGING.** Patch UX atas Stage 4; belum diklaim production-tested.

Pengujian yang telah dijalankan pada source tahap ini:
- `PYTHONPATH=backend python -m pytest -q backend/tests` → **64 passed**.
- `node --test frontend/tests/topology*.test.mjs` → **21 passed**, termasuk empat tes baru panjang busbar, grid, keamanan simbol selain busbar, dan keberadaan kontrol UX.
- `tsc -p /tmp/berauload_stage4_ux_tsconfig.json` → lulus pemeriksaan tipe fokus modul Topologi memakai deklarasi tiruan (bukan tipe dependensi npm asli).
- TypeScript parser (`createSourceFile`) → **46 TS/TSX tanpa parse error**.
- Compile Python dan checksum ZIP diperiksa saat packaging.

Belum diuji: build npm/Vite dengan dependensi React 19 asli, pengujian browser drag/scroll nyata, Docker Compose/PostgreSQL 16 aktual, dan uji regresi antarmuka di LXC. Pengujian tersebut wajib dilakukan sebelum digunakan operasional.

Invarian: Tidak ada migrasi DB; perubahan hanya konfigurasi simbol/layout. Tidak menyimpulkan status PMT, tidak membuat sambungan listrik, null tetap berbeda dari nol, izin admin untuk edit dan optimistic lock/revisions tetap dari Tahap 3/4.

---


**Status: KANDIDAT STAGING.** Jangan menyebut production-tested sampai berhasil membangun dan melakukan uji browser pada LXC pengguna.

## Pengujian yang benar-benar dijalankan di lingkungan build

- `PYTHONPATH=backend python -m pytest -q backend/tests` → **64 passed** dari database QA SQLite terpisah. Tes baru: simpan simbol/garis/summary/ranking/legend/text, referensi read-only, nilai null dan count Reading tidak berubah, penolakan titik garis ganda, ranking mixed-unit dan jenis kotak invalid.
- `node --test frontend/tests/topologyViewer.test.mjs frontend/tests/topologyEditor.test.mjs frontend/tests/topologyStage4.test.mjs` → **17 passed** (9 legacy + 8 baru). Termasuk delapan simbol, geometris snap, drag vertex murni, whitelist level, kotak tampilan, ranking dengan nol, unit mixed, grafik mini dengan celah 24 jam.
- `python -m compileall -q backend/app` → lulus.
- Parser TypeScript 5.8.3 `createSourceFile` untuk **46 file TS/TSX** di `frontend/src` → 0 parse diagnostics.
- `tsc -p /tmp/berauload_stage4_tsconfig.json` dengan deklarasi tiruan React/lucide/Recharts → lulus untuk modul Topologi. **Ini bukan build atau typecheck dependency asli**, dan file shims tidak dikirim ke LXC.
- `npm --prefix frontend install --offline --no-audit --no-fund` → gagal ENOTCACHED; `npm --prefix frontend install --no-audit --no-fund --fetch-retries=0 --fetch-timeout=8000` → gagal EAI_AGAIN ke registry.npmjs.org. Karena dependency asli tidak tersedia, **`npm run build`/`docker compose build` belum dijalankan dan belum bisa dinyatakan berhasil**.

## Invarian keselamatan dan data

- Tidak ada perubahan schema database/migrasi Stage 4; konfigurasi hanya pada `topology_diagrams` dan snapshot revisi. Readings, hour_records, Formula Engine, Historical Calculations, H/J Excel, dan Engineering Rules tidak ditulis/diubah.
- Tanpa topologi seed maupun auto-connect. Semua wire dan simbol hanya gambar manual dari admin; tidak menyatakan status saklar/energisasi. Level garis dibatasi whitelist.
- Satu-satunya status aktif dari evaluator Engineering Rule yang telah ada. Summary adalah jumlah metric terisi pada jam dipilih; ranking membandingkan raw value antar-code dengan satuan identik. Tidak ada nilai teknis baru/fiktif.
- NULL tetap `—`, 0 tetap sah. Sparkline 24 jam memiliki break pada missing hours, tidak interpolasi. Sesi cookie, CSRF, role admin-only, audit, immutable revisions, dan concurrency HTTP 409 tetap dari Tahap 1/3.
- Batas geometri tetap 200 simbol/300 garis/100 kotak, 2–32 vertex, snap grid 10; data layout ditolak oleh backend jika salah.

## Kewajiban di server LXC sebelum dipakai operasional

1. Backup database, uploads dan source Tahap 3; cek `/api/health` = `1.5.0-stage3`.
2. Lulus `./deploy/test.sh`, tes JS murni, `docker compose build` (TypeScript/Vite dengan dependensi asli), lalu `up -d --no-build` dan smoke test.
3. Di browser admin lakukan uji gambar dan pindah simbol/garis, vertex drag, ringkasan/ranking/legenda/teks, sparkline, save/reload/revisi, dan peringatan keluar draf. Verifikasi status kosong/nol.
4. User non-admin hanya dapat melihat diagram. Uji H/J, input, import, formula, rule, dashboard, laporan dan tidak ada error console.

**Belum dilakukan:** pengujian React DOM/drag otomatis di browser nyata, build frontend asli, PostgreSQL 16 runtime, Docker pada LXC, dan load test ratusan simbol. Hasil uji ini belum menyatakan performa/keberhasilan production.

## Stage 9a-fix — 2026-11-17

Validasi regresi dilakukan per kelompok: 174 backend + 7 runner lulus; 57 tes Node frontend lulus. `npm install` gagal DNS EAI_AGAIN, `npm run build` masih gagal dependensi React/tipe belum tersedia. Build nyata, PostgreSQL 16 staging, dan pengujian browser belum dinyatakan lulus. Detail dan batas: `QA_STATUS_STAGE9A_FIX.md`.

## Stage 9d1 — 2026-11-17

Peta Leaflet, grafik Analisa, perapian UI, endpoint titik, pengaturan ubin admin/migrasi aditif, dan regression tests. **Kandidat staging, belum dinyatakan siap produksi**. Lihat `QA_STATUS_STAGE9D1.md` untuk hasil terukur dan keterbatasan npm/PostgreSQL/browser.
