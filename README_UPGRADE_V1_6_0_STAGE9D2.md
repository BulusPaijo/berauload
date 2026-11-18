# Upgrade BerauLoad V1.6.0 — Stage 9d-2 (Export Data Gardu + UI)

Kumulatif: bisa dari Stage 8, 9a, 9a-fix, 9b, 9c, 9c-fix, atau 9d1. Migrasi aditif (tabel `gardu_export_templates`), berjalan saat start. Jalankan dulu di staging.

```bash
cd /opt/berauload/BerauLoad_V1_1_1 && cat VERSION
unzip -tq /opt/BerauLoad_V1_6_0_STAGE9D2_Full_Source.zip
bash /opt/upgrade_to_stage9d2.sh
curl -fsS http://127.0.0.1:8092/api/health   # harus 1.6.0-stage9d2
docker compose restart backend                # uji idempotensi migrasi
```
Skrip membuat backup database, uploads, dan source di `backups/upgrade_stage9d2_<waktu>/`, lalu build dan menjalankan versi baru. **Jangan pernah `docker compose down -v`.** Bila build gagal, versi lama tetap berjalan.

## Uji manual
1. Input → chip "Arus jurusan": header Jurusan 1..n dengan R S T N di bawahnya; sel jurusan yang tidak ada bergaris dan tidak bisa diisi; tempel dari Excel mengikuti urutan kolom yang tampak.
2. Analisa: tidak ada slider di judul kolom; klik baris → panel rincian; Ekspor ▾ → Export Data Gardu.
3. Export: pilih kolom, ganti judul, Lihat contoh, unduh XLSX dan CSV; jumlah baris sama dengan Analisa; simpan template pribadi; admin simpan template bersama; operator tidak bisa.
4. Master: + Tambah gardu dan Impor dari Excel terbuka di panel samping.
5. Peta: titik muncul; klik titik menampilkan rincian dan temuan.

## Rollback
Pulihkan `source.tar.gz` dan bila perlu `database.dump` dari folder backup, lalu `docker compose build && docker compose up -d`. Tabel template tidak dipakai versi lama sehingga aman dibiarkan.
