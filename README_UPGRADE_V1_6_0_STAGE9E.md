# Upgrade BerauLoad V1.6.0 — Stage 9e (Saran penanganan overload: tukar trafo / pindah beban)

Kumulatif: bisa dari Stage 8, 9a … 9d5. **Ada satu migrasi database baru (aditif, idempotent):** kolom `plan` pada `gardu_followups` dan dua jenis tindak lanjut baru (`tukar_trafo`, `pindah_beban`). Migrasi berjalan otomatis saat backend start. Tidak ada data yang dihapus atau diubah.

```bash
cd /opt/berauload/BerauLoad_V1_1_1 && cat VERSION
unzip -tq /opt/BerauLoad_V1_6_0_STAGE9E_Full_Source.zip
bash /opt/upgrade_to_stage9e.sh
curl -fsS http://127.0.0.1:8092/api/health   # harus 1.6.0-stage9e
```
Skrip membuat backup database, uploads, dan source di `backups/upgrade_stage9e_<waktu>/`, lalu build dan menjalankan versi baru. **Jangan pernah `docker compose down -v`.** Bila build gagal, versi lama tetap berjalan.

## Uji manual (staging)
1. Buka **Pengukuran Gardu → Analisa**, klik gardu berstatus Overload. Di rincian muncul **Saran penanganan overload** (daftar Tukar trafo dan Pindah beban, radius bisa diubah).
2. Klik **Tinjau** pada satu saran. Panel menampilkan sebelum/sesudah kedua gardu. Pada Pindah beban, geser persentase: di luar rentang aman tampil merah dan tombol dinonaktifkan.
3. **Jadikan tindak lanjut** → muncul di menu Tindak lanjut (jenis Tukar trafo / Pindah beban) dengan ringkasan rencana.
4. Untuk Tukar trafo: ubah status ke **Selesai**, lalu **Terapkan ke master…** (tanggal efektif + centang konfirmasi). Cek master kedua gardu (kVA tertukar) dan riwayat master.
5. Coba sebagai operator: tombol Terapkan tidak boleh berhasil (403).
6. Ukur ulang kedua gardu agar status di Analisa mengikuti trafo baru.

## Rollback
Pulihkan `source.tar.gz` dari folder backup, lalu `docker compose build && docker compose up -d`. Kolom `plan` dan dua jenis tindak lanjut tambahan tetap ada di database tetapi tidak berbahaya bagi 9d5. Dump database hanya perlu dipulihkan bila Anda ingin kembali ke keadaan persis sebelum upgrade (data tukar trafo yang sudah diterapkan ikut hilang).
