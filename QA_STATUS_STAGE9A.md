# QA BerauLoad 1.6.0-stage9a — 17 November 2026

**Status: KANDIDAT STAGING, bukan siap produksi.** Basis source: Stage 8 dengan hotfix test-runner yang sebelumnya diberikan pengguna. Pengujian menggunakan file SQLite sintetis/temporer, tidak menggunakan DB PostgreSQL produksi.

## Tes yang selesai dan hasilnya

| Perintah / langkah | Hasil |
|---|---|
| `PYTHONPATH=backend:. pytest -q backend/tests/test_stage9a_substations.py` | **11 passed** pada source akhir (8,45 detik) |
| `node --experimental-strip-types --test frontend/tests/*.test.mjs` | **56 passed**, mencakup 5 tes Stage 9a (sekitar 0,5 detik) |
| `python -m compileall -q backend/app` | Lulus |
| Transpile/parser TypeScript semua `frontend/src/**/*.ts(x)` dengan TypeScript global | **74 file**, 0 parsing diagnostic; **bukan** type-check |
| Migrasi SQLite sintetis: Stage 8 `setup()` → Stage 9a `setup()` dua kali | Lulus, jumlah seed tetap 15 parameter/2 sesi, counts unchanged setelah restart, 0 baris HourRecord/Reading berubah |
| Uji pertama terpisah empat kelompok tes backend (sebelum tambahan 3 tes Stage 9a terakhir) | Kelompok A 45 passed, B 49 passed, C 73 passed, D 7 passed = **174 tes unik selesai**; termasuk 166 tes baseline + 8 tes Stage 9a saat itu |
| Uji kelompok C ulang setelah tambahan satu tes snapshot | Semua assertion sampai 100% terlihat lulus, **tetapi proses tidak selesai sebelum timeout**; jangan hitung sebagai regression suite final lulus |
| `npm install --no-audit --no-fund --fetch-retries=0 --fetch-timeout=10000` | **GAGAL**: `getaddrinfo EAI_AGAIN registry.npmjs.org/@types/react` |
| `npm run build` | **GAGAL**: dependensi React dan tipe TS belum terpasang akibat npm install gagal |

Regresi backend `pytest -q backend/tests` satu proses juga pernah terhenti pada sekitar 41% karena batas durasi. Tes baseline awal selesai per kelompok terpisah, tetapi **suite final tunggal belum lulus dengan terminasi normal**. Rerun terarah Stage 9a terbaru 11 passed, meliputi sanitasi keluaran Excel dan pemeriksaan ZIP Excel tidak valid.

## Cakupan tes baru

- Migrasi `schema_migrations` idempotent dan seed tidak menimpa perubahan admin, restart berulang.
- Master gardu/pemindahan penyulang/rename, kunci kode pasca-pengukuran, histori dan snapshot, `line_count` snapshot setelah master berubah.
- `NULL`/angka 0/flag, line_no, revision stale 409, draft/verified/reopen alasan, `unchanged`, audit.
- Bulk batas 200; hasil row bercampur sah/konflik/validasi, item sah tetap tersimpan.
- Hak akses KP tidak melihat induk, ULP membaca bawahannya, UP3 melihat, operator tidak dapat memverifikasi, non-admin tidak mengubah master, tanpa login ditolak.
- Impor CSV dengan desimal koma, pratinjau tanpa DB write, pembuatan penyulang memerlukan konfirmasi, mode hanya sel kosong tidak menimpa 0/flag, impor verified ditolak.
- Berkas rusak dan formula injection pada output Excel, serta tidak ada penulisan HourRecord/Reading.
- Node: parse angka desimal/kosong/nol, paste blok/sel di luar line_count, key backup user-unit-tanggal-sesi, pemakaian antrean autosave Stage 7 per baris.

## Hasil yang BELUM diuji

1. Build frontend `tsc -b` dan `vite build` lengkap; kegagalan instalasi dependensi bukan kesimpulan bahwa source frontend sudah bebas error tipe.
2. PostgreSQL 16 (migrasi, unique concurrent insert, `pg_advisory_xact_lock`, batch savepoint) di Docker/LXC produksi atau staging.
3. Browser nyata (tempel dari Excel, autosave interaksi cepat, retry/401/409, tampilan 300 gardu lewat beberapa halaman, Firefox/Chrome, responsif ponsel).
4. Import Excel riil pengguna (file contoh Excel tidak dilampirkan ke tugas Stage 9a). Seed hanya berdasarkan daftar eksplisit di instruksi, **bukan** pemetaan sel formula Excel tertentu.
5. Upgrade/rollback dengan volume dan data asli ULP Tanjung Redeb. Tidak ada angka produksi yang diubah di lingkungan QA.

## Perubahan tabel

Tabel baru: `substation_feeders`, `substation_choices`, `substations`, `substation_master_history`, `substation_params`, `substation_sessions`, `substation_value_flags`, `substation_fields`, `substation_measurements`, `substation_values`.

**Tidak** ada perubahan kolom/constraint/tipe atau data pada tabel lama. `APP/health.app` tetap `BerauLoad` (pengenal teknis), version `1.6.0-stage9a`.

## Rencana validasi staging wajib

- Jalankan `npm install`, `npm run build`, seluruh pytest dan tes Node pada instance bersih di LXC.
- Gunakan PostgreSQL 16 staging volume/Compose terpisah untuk dua penulis same-visit, validasi 409 dan tidak ada partial write, langkah migrasi dua kali serta snapshot lama.
- Uji peran admin/operator/verifier/management dan pengguna KP/ULP/UP3 di browser.
- Uji spreadsheet 300 gardu dan 5 jurusan, paste kolom campuran angka/flag, save/reopen, conflict, dan output Excel.
- Backup sebelum upgrade produksi; jangan deploy source kandidat hanya karena unit test lulus.

## Usulan teknis untuk Stage 9b (BELUM DIIMPLEMENTASIKAN)

Daftar parameter eksplisit memiliki arus fasa R/S/T/N, tegangan rel fase-netral dan antar-fasa, tegangan ujung per jurusan, serta grounding. **File Excel contoh berisi kolom hitung tidak dilampirkan**; karena itu rumus kolom dan ambang di Excel belum dapat diverifikasi. Usulan awal yang harus disetujui engineering/admin:

- `I_avg = (I_R + I_S + I_T)/3` **per jurusan**, hanya saat ketiga fasa angka tersedia; bila NULL atau flag, hasil NULL.
- `ketidakseimbangan_% = max(|I_R-I_avg|, |I_S-I_avg|, |I_T-I_avg|)/I_avg × 100` bila `I_avg > 0`; jika semua 0, status perlu didefinisikan tanpa membagi nol. Tentukan dulu definisi resmi (mis. IEEE/NEMA) dan ambangnya.
- Perkiraan `I_nom` **3 fase** berdasarkan `S_kVA × 1000/(√3 × V_LL)` menggunakan nominal/tegangan pengukuran yang dikonfigurasi; untuk 1 fase, `I_nom = S_kVA × 1000/V_LN`. Jangan hardcode 400 V atau 230 V tanpa acuan. Perhitungan arus total harus memperhatikan topologi beberapa jurusan agar tidak menggandakan pengukuran.
- `drop_tegangan_% = (V_rel - V_ujung)/V_rel × 100` hanya untuk pasangan fasa/periode yang sebanding, `V_rel > 0`; pembacaan beda waktu atau ketidaksamaan referensi tegangan membuat perbandingan tidak valid.
- Jangan menghitung kW dari kVA atau arus saja tanpa faktor daya dan tegangan yang sesuai; jangan menjumlah `I_R+I_S+I_T+I_N` sebagai beban, jangan menyamakan `PUTUS`/`TIDAK_TERUKUR` dengan 0.
- Ambang kewajaran, % beban, ketidakseimbangan, tegangan minimum, dan grounding harus master versioned/configurable. Tidak ada angka/penilaian yang boleh dipaksakan tanpa standar dan arahan pengguna.

## Lampiran QA Stage 9a-fix (2026-11-17)

Hotfix hanya modul `substations`: penyesuaian tampilan input/master/definisi mengikuti referensi HTML, validasi kode ganda 409, konfirmasi pengurangan jumlah jurusan historis, dialog konflik dengan backup ketikan, dan validasi min <= max. Tidak ada migrasi/tabel baru. Hasil tes terbaru: **174 backend (tanpa runner) + 7 runner lulus**, **57 Node lulus**; suite backend satu proses melewati batas eksekusi. `npm install` gagal DNS EAI_AGAIN dan `npm run build` gagal tanpa dependencies, sehingga **TypeScript/Vite belum lulus build**. Detail lengkap `QA_STATUS_STAGE9A_FIX.md`.
