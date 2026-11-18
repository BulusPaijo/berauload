# QA — BerauLoad 1.6.0-stage9d3 — 17 November 2026

Dikerjakan langsung oleh Claude. Basis: 1.6.0-stage9d2. **Kandidat staging; belum disahkan produksi.**

## Isi
- **Perbaikan:** kolom Gardu kini tetap beku saat kisi input digeser (sebelumnya sub-judul pertama ikut beku dan menutupi Gardu). Kolom Status dipindah ke kanan.
- **Form ponsel:** kartu per jurusan (dipisah per satuan: arus A, tegangan ujung V), baris berwarna fasa R merah · S kuning · T hitam · N biru dengan huruf, hitungan terisi per kartu, penanda (PUTUS, dll.) lewat tombol ⋯, bilah simpan menempel di bawah.
- **Kisi input:** judul dua tingkat per jurusan + per satuan, blok parameter gardu di akhir, Ω untuk ohm, centang baris, Isi ke bawah, Tandai PUTUS, Verifikasi (verifikator/admin), Urungkan, ringkasan status, kartu bantuan, tombol Unduh template / Unggah Excel.
- **Tindak lanjut (baru):** jenis diatur admin (bawaan 7, dengan daftar temuan pemicu usulan), prioritas, status terbuka/dikerjakan/selesai/batal, penanggung jawab, target; hanya unit pemilik yang mengubah, induk membaca; tanpa hapus; versi + 409; audit; aksi massal; usulan dari temuan hanya teks (tidak pernah membuat sendiri). Tampil di kolom Analisa, panel rincian, dan halaman **Tindak lanjut** (Daftar Kerja).
- **Pemantauan (baru):** cakupan per unit untuk rentang tanggal, daftar perlu diukur (pengaturan hari atau 30/90/365), lembar kerja lapangan PDF/Excel untuk gardu terpilih.
- **Laporan:** PDF dan Excel (ringkasan, daftar per kategori/temuan beserta syaratnya, belum diukur, tindak lanjut terbuka, ambang yang dipakai, logo/organisasi dari branding).
- **Tampilan sesuai rancangan pemilik:** Analisa (grafik penyulang + siang vs malam + Perlu perhatian, kolom Siang/Malam dengan batang pada sesi tertinggi, × pada nilai yang memicu temuan, Kondisi, Tindak lanjut, panel rincian); Peta (kartu terdaftar/diukur 90 hari/belum diukur + kategori/temuan, panel rincian di samping peta).
- Endpoint ringan baru `/analysis/stations/{id}/trend` untuk riwayat di panel rincian.

## Uji yang dijalankan
| Pemeriksaan | Hasil |
|---|---|
| `pytest backend/tests` | **209 lulus** (4 tes baru 9d-3) |
| `node --test tests/*.test.mjs` | **91 lulus** (tes baru: status baris, chip kolom, form ponsel, panel rincian, judul per satuan) |
| `npm run build` | **Lulus**. JS 1.311 kB (gzip 370 kB), CSS 156 kB |
| PostgreSQL 16, 5.029 gardu / 99.207 pengukuran | buat/usul tindak lanjut 0,01–0,02 dtk; cakupan 0,04 dtk (cocok dengan SQL langsung: 4.900 dari 5.029); perlu diukur 0,05 dtk; laporan Excel 5,4 dtk / PDF 5,2 dtk; lembar kerja 200 gardu 0,3 dtk; baris Analisa 1,4 dtk |
| Chrome (Playwright) | kisi input digeser kanan (Gardu tetap terlihat), form ponsel 390 px, Analisa, panel rincian, Peta + panel, Tindak lanjut, Pemantauan |

## Belum diuji
Ponsel fisik; Docker di LXC; ubin peta di jaringan kantor; pembaca layar. Halaman Rumus & Kategori belum diubah tampilannya pada tahap ini (fungsi uji contoh dan pratinjau dampak sudah ada sejak 9b). Bundel JS belum dipecah.
