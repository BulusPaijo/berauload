# Upgrade BerauLoad V1.6.0 — Stage 9d-5 (Rincian pengukuran, warna tegangan rel, temuan)

Kumulatif: bisa dari Stage 8, 9a, 9a-fix, 9b, 9c, 9c-fix, 9d1, 9d2, 9d3, atau 9d4. **Tidak ada migrasi database baru** di 9d-5 (bila naik dari versi sebelum 9d4, migrasi 9d4 tetap berjalan saat start).

```bash
cd /opt/berauload/BerauLoad_V1_1_1 && cat VERSION
unzip -tq /opt/BerauLoad_V1_6_0_STAGE9D5_Full_Source.zip
bash /opt/upgrade_to_stage9d5.sh
curl -fsS http://127.0.0.1:8092/api/health   # harus 1.6.0-stage9d5
```
Skrip membuat backup database, uploads, dan source di `backups/upgrade_stage9d5_<waktu>/`, lalu build dan menjalankan versi baru. **Jangan pernah `docker compose down -v`.** Bila build gagal, versi lama tetap berjalan.

## Uji manual
1. Input: geser kisi ke kanan, lalu cek blok Tegangan Rel F-N (hijau toska), Tegangan Rel F-F (biru), Tegangan Ujung JTR (kuning), dan Grounding (abu). Form ponsel memakai warna yang sama.
2. Pengukuran: kolom Gardu menampilkan kode + nama. Klik **Detail & riwayat** pada pengukuran yang pernah diubah:
   - Tab Tabel nilai: sel oranye adalah sel yang berubah; arahkan kursor untuk melihat nilai lama.
   - Tab Riwayat: berisi kalimat seperti "Jurusan 1 · Arus R 120 → 125 A".
   - **Unduh Excel**: sel oranye dengan komentar nilai lama.
3. Rumus & Kategori: kategori bernomor. Seret ⋮⋮ atau pakai ↑↓ untuk mengubah urutan, lalu kembalikan urutannya.
4. Analisa → Filter lanjutan, dan Export: pilih dua temuan, ganti **salah satu / semua**, lalu pastikan kalimat contoh dan jumlah gardu ikut berubah.

## Rollback
Pulihkan `source.tar.gz` dari folder backup, lalu `docker compose build && docker compose up -d`. Database tidak berubah di 9d-5, jadi rollback ke 9d-4 tidak perlu memulihkan dump.
