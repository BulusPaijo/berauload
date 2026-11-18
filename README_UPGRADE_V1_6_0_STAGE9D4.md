# Upgrade BerauLoad V1.6.0 — Stage 9d-4 (Export Data Gardu + UI)

Kumulatif: bisa dari Stage 8, 9a, 9a-fix, 9b, 9c, 9c-fix, 9d1, 9d2, atau 9d3. Migrasi: tabel arsip `substation_values_archive`; tegangan ujung dipindah ke tingkat gardu (nilai per jurusan diarsip, nilai terendah dipakai — sekali jalan, bisa beberapa puluh detik bila datanya banyak), berjalan saat start. Jalankan dulu di staging.

```bash
cd /opt/berauload/BerauLoad_V1_1_1 && cat VERSION
unzip -tq /opt/BerauLoad_V1_6_0_STAGE9D4_Full_Source.zip
bash /opt/upgrade_to_stage9d4.sh
curl -fsS http://127.0.0.1:8092/api/health   # harus 1.6.0-stage9d4
docker compose restart backend                # uji idempotensi migrasi
```
Skrip membuat backup database, uploads, dan source di `backups/upgrade_stage9d4_<waktu>/`, lalu build dan menjalankan versi baru. **Jangan pernah `docker compose down -v`.** Bila build gagal, versi lama tetap berjalan.

## Uji manual
1. Master → Ubah gardu → ganti nama → Simpan: berhasil.
2. Beri akses **verifier** di ULP kepada petugas ULP (menu pengguna/unit). Pilih unit ULP → Master: muncul kolom Unit dan pilihan "Unit pemilik"; pindahkan beberapa gardu ke KP (satu per satu atau Aksi massal → Pindahkan ke unit).
3. Login operator KP: hanya gardu KP-nya yang tampil. Login operator ULP: bisa mengisi pengukuran gardu KP tanpa ganti unit.
4. Form ponsel: ketik nomor gardu → pilih → kartu Jurusan berwarna, Tegangan Ujung JTR satu kali.
5. Rumus & Kategori: v_ujung_min = MIN(v_end_rn, v_end_sn, v_end_tn).

## Rollback
Pulihkan `source.tar.gz` dan bila perlu `database.dump` dari folder backup, lalu `docker compose build && docker compose up -d`. Perhatian: rollback ke 9d-3 setelah migrasi tegangan ujung memerlukan pemulihan `database.dump` (lingkup parameter berubah). Nilai asli per jurusan ada di tabel `substation_values_archive`.
