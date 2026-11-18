# QA — BerauLoad V1.6.0 Stage 9b (2026-11-17)

**Status kandidat staging, belum production-ready**. Berdasar ZIP source 9a-fix pengguna, tidak menggunakan database produksi. Semua data uji sintetis dan SQLite sementara. Tahap 9c/9d tidak dikerjakan.

## Pengujian aktual

| Perintah / tindakan | Hasil |
| --- | --- |
| `PYTHONPATH=backend python -m pytest -q backend/tests/test_stage9b_calculations.py backend/tests/test_formulas.py backend/tests/test_stage9a_substations.py backend/tests/test_stage9a_hotfix.py` | **25 passed** setelah koreksi validasi aturan dan pembatasan cakupan pembacaan unit |
| `node --test frontend/tests/garduCalculations.test.mjs` | **4 passed** |
| `python -m compileall -q backend/app` | Lulus |
| Parser TypeScript global `createSourceFile` pada `frontend/src/features/substations/` | **11 TS/TSX** tanpa error sintaks; bukan type-check asli |
| `npm --prefix frontend install --no-audit --no-fund --fetch-retries=0 --fetch-timeout=9000` | **GAGAL** DNS EAI_AGAIN `registry.npmjs.org/@types/react` |
| `npm --prefix frontend run build` | **GAGAL** modul React/ReactDOM/lucide-react dan deklarasi JSX tidak tersedia, akibat npm install gagal |
| `PYTHONPATH=backend python -m pytest -q backend/tests --ignore=backend/tests/test_loadtest_runner.py` | **179 passed, 0 failed** dalam 71,67 detik (seluruh backend non-loadtest) |
| `PYTHONPATH=backend python -m pytest -q backend/tests/test_loadtest_runner.py` | **7 passed, 0 failed** dalam 16,75 detik; SQLite in-process dan HTTP lokal terisolasi |
| `node --experimental-strip-types --test frontend/tests/*.test.mjs` | **61 passed, 0 failed**; semua uji frontend termasuk pengujian lama |
| `node --test frontend/tests/*.test.mjs` (tanpa flag) | 51 passed, 2 gagal karena tes lama mengimpor `.ts` sehingga Node perlu `--experimental-strip-types`; dengan flag seluruh tes berhasil |

## Cakupan tes baru

Parser AST aman (import, subscript, atribut, lambda, string, kedalaman/ukuran), IF malas, pembagian nol, 0 vs NULL, agregat jurusan `batal`/`lewati`, seed+idempotent, data ukur tidak berubah, `FLAG(PUTUS)`, penyimpanan hasil/versi, kategori/temuan ganda, izin, CSRF, pemeriksaan rumus, graf siklus langsung, pratinjau non-mutatif, uji draf, resume recalc dan audit. Frontend: label Bawaan/Diubah/Kustom, penyisipan token, format 0/NULL/tidak lengkap, dan galat teks.

## Belum diuji atau belum memenuhi

- PostgreSQL **16** nyata, migrasi & lock pada database yang berisi data historis produksi.
- `docker compose build/up`, browser grafis, mobile interaction, auto-timer dan penggunaan concurrency pada LXC.
- Performa hitung ulang pada **100.000** pengukuran, background processing di luar request aktif, dan performa penghitungan 100.000 data; suite backend utama telah lulus, tetapi bukan uji produksi.
- Build NPM/Vite nyata dengan dependensi React 19; **tidak diklaim lulus**.
- Dua baris Excel pengukuran asli sebagai acuan numerik; hanya perbandingan sintetis yang tersedia.
- Validasi kelistrikan/konfirmasi pemilik atas rumus `beban_kva`, angka Excel lama vs arus nominal, dan ambang temuan. Nilai awal **sementara**.

Tidak boleh menganggap tahap ini sudah siap dipasang pada produksi hanya berdasarkan tes SQLite. Simpan source/DB/uploads sebelumnya dan jangan menghapus volume pada rollback.
