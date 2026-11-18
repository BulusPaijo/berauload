# Upgrade BerauLoad V1.6.0 — Stage 9d-3 (Export Data Gardu + UI)

Kumulatif: bisa dari Stage 8, 9a, 9a-fix, 9b, 9c, 9c-fix, 9d1, atau 9d2. Migrasi aditif (tabel `gardu_followup_types`, `gardu_followups`; jenis tindak lanjut diisi sekali), berjalan saat start. Jalankan dulu di staging.

```bash
cd /opt/berauload/BerauLoad_V1_1_1 && cat VERSION
unzip -tq /opt/BerauLoad_V1_6_0_STAGE9D3_Full_Source.zip
bash /opt/upgrade_to_stage9d3.sh
curl -fsS http://127.0.0.1:8092/api/health   # harus 1.6.0-stage9d3
docker compose restart backend                # uji idempotensi migrasi
```
Skrip membuat backup database, uploads, dan source di `backups/upgrade_stage9d3_<waktu>/`, lalu build dan menjalankan versi baru. **Jangan pernah `docker compose down -v`.** Bila build gagal, versi lama tetap berjalan.

## Uji manual
1. Input: geser kisi ke kanan — kolom Gardu tetap terlihat; centang baris → Isi ke bawah / Tandai PUTUS / Verifikasi.
2. Form ponsel (buka di HP): kartu per jurusan, warna R S T N, tombol ⋯ untuk PUTUS, Simpan di bawah.
3. Analisa: klik baris → panel rincian → "+ Buat tindak lanjut"; kolom Tindak lanjut terisi; Unduh ▾ → Laporan PDF/Excel.
4. Tindak lanjut: filter status, centang beberapa, ubah status/penanggung jawab sekaligus. Operator unit induk hanya bisa membaca.
5. Pemantauan: cakupan per unit, daftar perlu diukur, lembar kerja PDF untuk gardu terpilih.
6. Peta: kartu ringkasan, klik titik → panel rincian di samping.

## Rollback
Pulihkan `source.tar.gz` dan bila perlu `database.dump` dari folder backup, lalu `docker compose build && docker compose up -d`. Tabel tindak lanjut tidak dipakai versi lama sehingga aman dibiarkan.
