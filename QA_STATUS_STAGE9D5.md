# QA — BerauLoad 1.6.0-stage9d5 — 18 November 2026

Dikerjakan langsung oleh Claude. Basis 1.6.0-stage9d4. **Kandidat staging.** Tidak ada migrasi database baru.

## Perubahan
1. **Tegangan rel dipisah dan diberi warna.**
   - Blok gardu kini terdiri dari Tegangan Rel F-N (R-0 S-0 T-0), Tegangan Rel F-F (R-S S-T T-R), Tegangan Ujung JTR (R-N S-N T-N) dan Grounding.
   - Warna tiap blok: toska, biru, kuning dan abu, di kepala kolom, sel kisi, kartu form ponsel dan kartu rincian.
   - Pengelompokan dibaca dari nama parameter: "Tegangan Rel" + pasangan fasa X-Y menjadi F-F, sisanya F-N. Kata "Tegangan Ujung" dan "Grounding/Arester" dikenali dengan cara yang sama. Parameter yang namanya diubah total kembali ke pengelompokan lama.
2. **Rincian pengukuran.** Panel samping lebar dengan:
   - Kepala: kode · nama gardu, unit, kVA, jurusan, penyulang, tanggal, sesi, status, revisi, petugas, dan siapa yang terakhir mengubah.
   - Tab *Tabel nilai*: seperti Excel, baris Jurusan 1..n dan kolom Arus R S T N, ditambah kartu rel F-N, rel F-F, ujung dan grounding. Sel yang berubah di revisi terakhir berwarna oranye dan nilai lama muncul saat kursor diarahkan. Hasil hitung dan temuan ikut ditampilkan.
   - Tab *Riwayat*: kalimat seperti "Administrator mengubah 3 nilai · rev 2" lalu "Jurusan 1 · Arus R 120 → 125 A". Nilai yang dikosongkan tertulis "kosong", bukan 0. Verifikasi dan buka kunci menampilkan alasannya.
   - Tab *Data teknis*: JSON mentah, disembunyikan sampai tombol ditekan.
   - **Unduh Excel** satu pengukuran (`GET /api/substations/measurements/{id}/xlsx`): sel berubah oranye dengan komentar nilai lama, plus hasil hitung dan temuan.
   - Riwayat dibangun dari audit yang sudah ada, jadi perubahan lama sebelum 9d-5 ikut terbaca.
3. **Daftar Pengukuran** menampilkan kode + nama gardu + unit, bukan "#ID". Datanya diambil dalam 2 kueri per halaman, tanpa N+1.
4. **Urutan kategori** mengikuti gaya daftar kolom hitung: nomor urut, pegangan seret ⋮⋮ dan panah ↑↓ kecil (nonaktif di ujung daftar). Panah lama di daftar Temuan yang tidak berfungsi sudah dibuang.
5. **Pemilih temuan** dipakai bersama di Analisa (Filter lanjutan) dan Export:
   - Chip temuan dengan warna.
   - Saklar "salah satu / semua".
   - Kalimat contoh, misalnya "Gardu dengan Belum isi ATAU Putus — cukup satu temuan saja yang cocok" atau versi "… DAN …".

## Uji
| Pemeriksaan | Hasil |
|---|---|
| `pytest backend/tests` | **216 lulus**. 2 tes baru: kepala + riwayat + sel berubah (termasuk kosong ≠ 0 dan verifikasi tidak menghapus penanda), Excel per pengukuran (warna, komentar, tanpa 0 palsu, KP lain 404) |
| `node --test` | **99 lulus**. 5 tes baru: blok F-N/F-F/ujung/grounding beserta warnanya, tabel nilai, kalimat riwayat, seret urutan, kalimat temuan. 3 tes lama diperbarui karena judul berubah ("Tegangan Rel" → "Tegangan Rel F-N") |
| `tsc -b`, `npm run build` | Lulus (JS 1.326 kB, gzip 374 kB) |
| Chrome + PostgreSQL 16 (salinan data uji 5.029 gardu) | Kisi digeser ke kanan menampilkan 4 blok berwarna. Form ponsel 400 px menampilkan 4 kartu berwarna. Rincian: 3 sel oranye dengan tooltip "Sebelumnya: 120"; riwayat 2 entri. Unduh Excel menghasilkan `pengukuran_BG1_2026-11-18_SIANG.xlsx`. Kategori diseret Overload→1 lalu dikembalikan dengan ↓. Analisa: 2 temuan + "semua" menyaring jadi 1 gardu. Tidak ada galat konsol |

## Belum diuji
Ponsel fisik, Docker di LXC, dan data nyata Anda dengan riwayat audit panjang. Panel hanya membaca 100 audit terakhir per pengukuran, sama seperti sebelumnya.
