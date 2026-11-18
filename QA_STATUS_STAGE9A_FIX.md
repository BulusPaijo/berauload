# QA — BerauLoad V1.6.0 Stage 9a-fix

**Status: kandidat staging — belum dinyatakan siap produksi.** Source dasar: Stage 9a. Referensi UI: `BerauLoad Stage 9 - Pengukuran Gardu.html` (berisi juga mockup Stage 9b yang **tidak** diterapkan). Scope: UI pengukuran gardu, validasi kode ganda, konfirmasi pengurangan jurusan, konflik pengisian, dialog definisi. Database Stage 9a digunakan tanpa migrasi baru.

## Tes yang benar-benar dijalankan

| Perintah | Hasil nyata |
| --- | --- |
| `PYTHONPATH=backend:. python3 -m pytest -q backend/tests --ignore=backend/tests/test_loadtest_runner.py` | **174 passed**, 63,06 detik |
| `PYTHONPATH=backend:. python3 -m pytest -q backend/tests/test_loadtest_runner.py` | **7 passed**, 15,93 detik |
| `PYTHONPATH=backend:. python3 -m pytest -q backend/tests/test_stage9a_hotfix.py` (sesudah penyesuaian akhir guard code) | **4 passed**, 3,87 detik |
| `PYTHONPATH=backend:. python3 -m pytest -q backend/tests/test_stage9a_hotfix.py backend/tests/test_stage9a_substations.py` | **15 passed**, 10,06 detik |
| `node --experimental-strip-types --test frontend/tests/*.test.mjs` (kode final) | **57 passed**, 0 failed |
| Parse TSX TypeScript `createSourceFile()` pada 5 komponen diubah | **5/5 tanpa kesalahan parsing**; **bukan** type-check |
| `python3 -m compileall -q backend/app backend/tests` | Lulus |
| `cd frontend && npm install --no-audit --no-fund --prefer-offline --fetch-retries=0` | **GAGAL**: DNS `EAI_AGAIN` dari `registry.npmjs.org/@types/react` |
| `cd frontend && npm run build` | **GAGAL**: React, ReactDOM dan tipe/JSX tidak ditemukan karena dependensi gagal dipasang. Type-check/Vite **belum lulus** |
| `PYTHONPATH=backend:. python3 -m pytest -q backend/tests` (satu proses) | Sempat mencapai sekitar 39% lalu terhenti karena batas eksekusi; **bukan** satu suite lulus. Semua tes akhirnya dicakup oleh dua kelompok di atas |

Jumlah tes backend **unik** yang berhasil selesai per kelompok: **181 lulus** (174 + 7). Jumlah tes frontend unik: **57 lulus**. Tes lama tidak diubah; 4 tes backend baru + satu tes murni JS baru. Tidak menganggap syntax parsing sebagai hasil build Vite.

Cuplikan keluaran:

```text
........................................................................ [ 41%]
........................................................................ [ 82%]
..............................                                           [100%]
174 passed in 63.06s (0:01:03)
.......                                                                  [100%]
7 passed in 15.93s
# tests 57
# pass 57
# fail 0
```

## Skenario khusus hotfix

- Master PATCH kode gardu yang dipakai entri lain ditolak HTTP 409; POST duplikat dan feeder/definisi duplikat juga 409, bukan 500. Log/histori tidak bertambah pada penolakan.
- Pengurangan `line_count` dengan data historis memerlukan persetujuan eksplisit 409 dan menyebut jumlah nilai terdampak. Setelah konfirmasi, record master berubah sedangkan `snapshot_line_count` dan nilai historis (termasuk 0) tetap.
- Bulk master memisahkan hasil `updated`, `needs_confirmation`, dan `error`.
- Definisi `min_value > max_value` ditolak 422, baik saat edit langsung maupun dengan nilai lawas yang dipertahankan.
- JS pembanding konflik membedakan kosong dan 0, menampilkan flag dan hanya sel berbeda, bukan JSON mentah.
- Tidak ada edit skema, pembacaan per jam, rekap Stage 1–8, perubahan izin, atau rumus 9b.

## Perlu divalidasi sebelum produksi

1. `npm install && npm run build` pada lingkungan yang memiliki registry npm dan lock dependency; hasil build belum lulus di lingkungan pembuat paket.
2. Uji PostgreSQL 16 `unique code` dan optimistic revision dua pengguna; validasi audit di DB sesungguhnya.
3. Uji UI browser nyata dengan tampilan desktop/ponsel, scrolling 100–300 gardu, paste Excel, konfirmasi pengurangan jurusan dan konflik 409 dengan dua sesi browser.
4. Backup database produksi dan volume uploads; jalankan smoke test LXC staging lebih dahulu.
5. Konfirmasi visual relatif terhadap contoh HTML. Peta dan modul Analisa/Rumus contoh adalah Stage 9b, sengaja tidak diimplementasi.
