# QA — BerauLoad 1.6.0-stage9c-fix — 17 November 2026

**Status: kandidat staging, belum production-ready**. Basis: paket full source Stage 9c. Paket kumulatif untuk upgrade langsung dari Stage 9b; **tidak ada migrasi baru untuk fix**, migrasi Stage 9c tetap berlaku. Tidak mengubah rumus/seed, mesin rumus, izin admin global, atau data ukur 9a.

## Empat perbaikan

1. `analysis/helpers.d.mts::applyView` kini menerima argumen kedua `definitions` sesuai implementasi `helpers.mjs` dan pemanggil React. `analysis/types.ts` sekarang menyatakan `fields[].active:boolean` sesuai respons API. Audit export/deklarasi `.d.mts` turut menambah deklarasi `autosave/core.d.mts::pause` yang memang diekspor dari `.mjs`.
2. Filter angka `analysis_queries.py` memakai `EXISTS` dengan `GarduCalcValue.measurement_id = chosen.mid` yang **berkorelasi**, bukan scalar subquery. Operator gte/lte/antara/kosong/ada, NULL vs 0, kolom kustom, sortir dan seluruh endpoint memakai relasi terpilih yang sama. Validasi query yang salah/kurang lengkap → 422.
3. FastAPI membaca `findings:list[str]` dari dependency query khusus (bukan field model `Depends`), menerima berulang dan dipisah koma. Kode tidak dikenal → 422; `finding_mode=any|all`, ringkasan/ekspor menggunakan opsi yang sama.
4. `IN (SELECT...)` untuk kategori `tidak_dapat_dinilai` menggunakan `select()` eksplisit, menghilangkan SAWarning koersi subquery.

## Uji yang benar-benar dijalankan

| Perintah | Hasil |
| --- | --- |
| `PYTHONPATH=.:backend pytest -q backend/tests/test_stage9c_analysis.py` | **7 lulus** |
| `PYTHONPATH=.:backend pytest -q backend/tests/test_stage9c_fix.py` | **5 lulus** (operator angka, nilai 0/NULL, 3 kunjungan/gardu, kustom, temuan SQL vs manual, CSV/XLSX, validasi 422, kompilasi SQL PG) |
| `node --experimental-strip-types --test frontend/tests/*.test.mjs` | **69 lulus**, 0 gagal |
| `PYTHONPATH=.:backend pytest -q backend/tests` | Percobaan satu proses tidak selesai sebelum timeout lingkungan; pengulangan sebagian gabungan mengungkap **1 kegagalan legacy terpengaruh state SQLite antar-tes** (`test_standard_reports_v1461.py::test_preference_scope_auth_and_reset`: default expected max tetapi database uji yang telah terisi berisi avg). Berkas `berauload.db` dibuat oleh tes di root proyek; kelompok legacy ini lulus sendiri 50/50. **Jangan klaim suite gabungan penuh lulus** |
| `PYTHONPATH=.:backend pytest -q` per tiga kelompok file (1–17, 18–24, 25–35) | **72 + 40 + 85 = 197 lulus**, 0 gagal pada eksekusi awal; sesudah tes compiler ditambah, kelompok yang terkait diuji ulang secara terpisah (36 + 50 = 86 lulus), sehingga total tes terkumpul 198 |
| `npm install --no-audit --no-fund --prefer-offline --fetch-retries=0 --fetch-timeout=10000` | **GAGAL: `EAI_AGAIN registry.npmjs.org/@types/react`** |
| `npm run build` (dijalankan ulang setelah koreksi tipe) | **GAGAL**: `src/App.tsx(1,49): error TS2307: Cannot find module 'react' or its corresponding type declarations`, `TS2875: ... react/jsx-runtime ... could not be found`, serta banyak error karena node_modules kosong. Kesalahan `TS2345` di `AnalysisPage.tsx(33,76)` dari build pertama tidak muncul lagi setelah tipe `fields[].active` diperbaiki; kompilasi penuh tetap belum terverifikasi. |
| Audit kesamaan nama `exports` JS vs `.d.mts` | Dilakukan; tipe deklarasi konsisten pada modul `analysis`, deklarasi `pause` ditambahkan pada modul autosave |

### Batas pembuktian

- **PostgreSQL 16 tidak tersedia** pada lingkungan ini: query PG berhasil dikompilasi melalui SQLAlchemy dialect, tetapi belum ada pengujian eksekusi terhadap PostgreSQL nyata, termasuk 500 CardinalityViolation dan SAWarning di PG. Pengujian SQLite mampu mendeteksi kesalahan pemilihan baris pertama karena menggunakan minimal tiga pengukuran per gardu.
- **Browser LXC, migrasi nyata dari DB Stage 9b, Nginx/Docker build, pengukuran 5.000/100.000, dua transaksi konkuren**: belum diuji di sini.
- `npm run build` **belum lulus sungguhan**. Lingkungan yang memiliki dependensi harus menjalankan `npm ci` (jika lockfile tersedia) atau `npm install` lalu `npm run build` sebelum pemasangan produksi.
- Semua pengujian menghasilkan data sintetis dan SQLite sementara, bukan data PLN produksi. Tes lama tidak diubah.

Lihat `README_UPGRADE_V1_6_0_STAGE9C_FIX.md` untuk backup, upgrade, smoke test, dan rollback langsung dari Stage 9b.

## Revisi reviewer (Rev1, 17 Nov 2026)
Satu baris diubah oleh pemeriksa setelah `npm run build` sungguhan gagal dengan `AnalysisPage.tsx(67,33): TS2345` (argumen `defs` bertipe `AnalysisDefinitions | null` diteruskan ke `applyView(view, definitions?: ...)`): `applyView(view,defs)` → `applyView(view,defs??undefined)`. Sesudahnya `npm run build` berhasil (tsc -b && vite build). Tidak ada perubahan lain. Catatan di atas yang menyebut kegagalan build karena lingkungan tidak lengkap untuk berkas ini tidak benar: kegagalan itu galat kode nyata.
