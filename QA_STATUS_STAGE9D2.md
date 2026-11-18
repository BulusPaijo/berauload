# QA — BerauLoad 1.6.0-stage9d2 — 17 November 2026

Dikerjakan langsung oleh Claude (bukan ChatGPT). Basis: `BerauLoad_V1_6_0_STAGE9D1_Rev1`. **Kandidat staging; belum disahkan produksi.**

## Isi tahap
1. **Bagian 0 — titik peta ringkas.** `/api/substations/map/points` kini hanya mengirim data penanda (kode, nama, koordinat, kode kategori, kode temuan, nilai acuan, status). Rincian dimuat saat titik diklik. Parameter baru `color_column` untuk pewarnaan per kolom hitung.
2. **Export Data Gardu** (menu Pengukuran Gardu → Export, dan Analisa → Ekspor → Export Data Gardu…): pilih kolom dari katalog (identitas, trafo, pengukuran, nilai ukur per parameter × jurusan, kolom hitung, kategori per kelompok, temuan daftar/per temuan, nilai acuan per sesi berdampingan, versi definisi); urut naik/turun; ganti judul; bentuk lebar atau panjang; XLSX/CSV (pemisah ; atau ,); contoh 20 baris + jumlah baris; template pribadi/bersama dengan versi (409 bila bentrok) dan arsip; lembar Keterangan (filter, versi definisi, rumus, aturan, catatan kosong≠0); audit tiap unduhan (tanpa isi data). Filter memakai relasi yang sama dengan Analisa. Batas 50.000 baris (lebar) / 200.000 (panjang). Ditulis bertahap ke berkas sementara.
3. **UI:** kisi input dengan header dua tingkat (Jurusan n digabung di atas R S T N; satuan sekali; titik warna fasa + huruf; hanya sebanyak jurusan terbanyak di halaman; urutan jurusan-dulu); Analisa tanpa slider lebar kolom, lebar tetap per jenis kolom, tanda urut yang jelas, menu Ekspor dan menu ⋯, filter lanjutan dilipat dengan jumlah aktif, klik baris membuka panel rincian samping (Esc menutup); Master: tambah/ubah gardu dan impor dalam panel samping berkelompok (Identitas · Trafo · Lokasi · Rincian), atribut tambahan sebagai daftar nama–nilai, area seret berkas. Komponen bersama di `features/substations/ui/` (Drawer dengan fokus terkunci, KeyValueEditor, FileDrop).

## Hasil uji yang benar-benar dijalankan
| Pemeriksaan | Hasil |
|---|---|
| `PYTHONPATH=.:backend pytest -q backend/tests` | **205 lulus** (termasuk 4 tes baru Export + tes peta ringkas) |
| `node --experimental-strip-types --test tests/*.test.mjs` | **85 lulus** (10 tes baru: spesifikasi ekspor, header dua tingkat) |
| `npm run build` (instal nyata) | **Lulus**. JS 1.284 kB (gzip 361 kB), CSS 136 kB. Sebelum: 1.260 kB / 355 kB / 130 kB |
| PostgreSQL 16, 5.029 gardu / 99.207 pengukuran — `/map/points` 4.480 titik | **1,6 MB / 0,6 dtk** (sebelum 12 MB / 4,2 dtk). Target <1,5 MB belum tercapai penuh |
| PG16 — jumlah baris Export = Analisa | 5.029 = 5.029; filter overload+temuan(all) 89 = 89 |
| PG16 — unduh 5.029 baris XLSX / CSV | 3,9 dtk / 3,7 dtk |
| PG16 — unduh 39.079 baris CSV / XLSX | 16,4 dtk / 18,1 dtk; memori proses naik ±14 MB |
| PG16 — 99.207 baris | ditolak 422 dengan pesan batas |
| PG16 — migrasi `20261117_21_stage9d2_export_templates` | tercatat sekali setelah beberapa kali start |
| Browser Chrome headless (Playwright) terhadap PG16 | kisi input, Analisa, panel rincian, menu Ekspor, halaman Export + contoh, panel Master tampil benar |

## Belum diuji
Ponsel fisik; Docker build di LXC; jaringan kantor/Cloudflare Tunnel; ekspor besar di perangkat LXC (CPU lebih lemah); pembaca layar. Ukuran bundel belum dipecah (code-splitting).
