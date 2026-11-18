# QA — BerauLoad 1.6.0-stage9c, 17 November 2026

**Status: kandidat staging, belum production-ready.** Pengujian dijalankan pada source ZIP 9b terlampir, pengukuran sintetis pada database SQLite sementara. Tidak menggunakan data/database PLN produksi.

## BAGIAN 0 — Hotfix 9b

- Serialisasi batch PostgreSQL via `pg_try_advisory_xact_lock`, saat busy return HTTP 200 dan `processed=0`; `FOR UPDATE OF measurement SKIP LOCKED`, hasil derivasi disimpan setelah mengunci parent. Upsert hapus/tulis ulang dalam savepoint; IntegrityError ditangani dengan retry sekali, lalu HTTP 409. SQLite memakai mutex di endpoint recalc.
- Evaluasi draft siklus ditolak 422 dengan rantai, fallback untuk definisi tersimpan rusak ditulis pada catatan. Jurusan yang melebihi jumlah snapshot tidak dinilai sebagai sumber kosong; IF malas tetap berlaku.
- Pratinjau dampak menyebut tidak ada perubahan aturan, contoh sampai 10 gardu dan keterbatasan scan. Batch recalc memuat definisi+parameter sekali dan seluruh nilai ukur via satu kueri. Bulk save memakai definisi bersama tetapi per-visit raw values tetap diambil secara individual.
- Pengurutan kategori kini satu transaksi dan satu bump versi definisi.
- Pengujian tambahan: SQLite mutex mengembalikan busy HTTP 200; angka 0 tetap terhitung dalam filter angka; kode penyuntikan rumus pada judul ekspor ikut disanitasi. Tes unit sintetis tidak menggantikan uji konkurensi PostgreSQL.
- **Belum diuji:** tabrakan transaksi PostgreSQL 16 nyata, konkurensi simpan vs hitung ulang dalam 2 koneksi PostgreSQL, fallback dari error jaringan/lock timeout, dan angka waktu *before/after*. Target 200 recalc <2 detik dan bulk 200 <5 detik **belum dapat dinyatakan lulus**.

## BAGIAN 9c — Analisa

- Mode terakhir/periode/semua dengan window SQL, pemilihan sesi nilai acuan tertinggi, mode sesi spesifik, gardu tanpa pengukuran, status belum/lama, nomor versi hasil.
- Filter dinamis SQL pada master, unit dan turunan, penyulang, kVA, kategori, temuan (any/all), sesi, state, status, kolom hitung/NULL, teks; sortir master/kolom hitung dengan NULL terakhir, paginasi maksimal 200.
- Ringkasan kategori/temuan/penyulang menggunakan relasi filter yang sama, batch materialisasi nilai satu halaman. Ekspor CSV/XLSX dibatasi 10.000 baris, sanitasi formula, dan metadata rumus/versi/filter.
- Tampilan pribadi/bersama server-side, pemulihan tampilan yang merujuk definisi terarsip dengan pemberitahuan, acuan kolom oleh admin, audit. Halaman React menampilkan chips dinamis, filter di URL, pilihan kolom, lebar dan urutan, pilihan ekspor, detail readonly dan histori.
- **Belum diuji:** `EXPLAIN (ANALYZE)` PostgreSQL 16 pada 5.000 gardu/100.000 pengukuran; UI di browser ponsel/desktop LXC, integrasi Nginx Docker nyata, akses per-unit lintas akun di PostgreSQL.

## Perintah dan hasil aktual

| Perintah | Hasil |
| --- | --- |
| `python -m compileall -q backend/app` | Lulus |
| `PYTHONPATH=backend pytest -q backend/tests/test_stage9c_analysis.py` | 5 lulus |
| `PYTHONPATH=backend pytest -q backend/tests/test_stage9c_analysis.py backend/tests/test_stage9b_calculations.py backend/tests/test_stage9a_hotfix.py` | 19 lulus |
| `node --test frontend/tests/garduAnalysis.test.mjs` | 6 lulus |
| `node --experimental-strip-types --test frontend/tests/*.test.mjs` | **68 lulus**, 0 gagal |
| `npm --prefix frontend install --no-audit --no-fund --fetch-retries=0 --fetch-timeout=7000` | GAGAL: DNS `EAI_AGAIN registry.npmjs.org/@types/react` |
| `npm --prefix frontend run build` | GAGAL: React/types/Vite tidak terunduh; bukan verifikasi TS nyata |
| `PYTHONPATH=backend pytest -q backend/tests --ignore=backend/tests/test_loadtest_runner.py` | **186 lulus**, 0 gagal |
| `PYTHONPATH=backend pytest -q backend/tests/test_loadtest_runner.py` | **7 lulus**, 0 gagal |

Tidak ada tes lama yang sengaja diubah atau dihapus. Definisi rumus seed maupun data 9a tidak berubah. **Konfirmasi teknis ambang kategori dan rumus bawaan tetap diperlukan.**
