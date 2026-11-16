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
