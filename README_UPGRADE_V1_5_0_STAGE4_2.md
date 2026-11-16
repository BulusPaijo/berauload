# Upgrade BerauLoad V1.5.0 Stage 4.1 → Stage 4.2

Patch **hanya** untuk server dengan `/api/health` = `1.5.0-stage4.1`. Tidak mengubah skema PostgreSQL atau perhitungan kelistrikan. Group Area tersimpan sebagai atribut opsional dalam JSON layout Topologi; layout lama tetap dapat dibaca.

## 1. Backup sebelum menyentuh source

```bash
cd /opt/berauload/BerauLoad_V1_1_1
curl -fsS http://127.0.0.1:8092/api/health
./deploy/backup.sh
cd /opt/berauload
tar -czf "BerauLoad_source_before_stage4_2_$(date +%Y%m%d_%H%M%S).tar.gz" \
  --exclude='node_modules' --exclude='.qa-venv' --exclude='backups' BerauLoad_V1_1_1
```

Pastikan SQL, uploads, dan arsip source berhasil dibuat; simpan nama backup. Jangan menghapus `.env`/volume dan jangan menjalankan `install.sh` ulang.

## 2. Pasang patch dan uji sebelum deployment

Upload `BerauLoad_V1_5_0_STAGE4_2_Patch_From_STAGE4_1.zip` ke `/opt/`, lalu:

```bash
cd /opt/berauload/BerauLoad_V1_1_1
unzip -o /opt/BerauLoad_V1_5_0_STAGE4_2_Patch_From_STAGE4_1.zip -d .
./deploy/test.sh
node --test frontend/tests/topology*.test.mjs
docker compose build
```

**Berhenti bila salah satu gagal**, terutama error `npm run build` pada layer Docker web. Jangan menghidupkan image yang gagal build. Baca error TS/NPM yang pertama; jangan hapus database atau container lama.

Jika lulus:

```bash
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

Respons API seharusnya `"version":"1.5.0-stage4.2"` dan service healthy. Hard refresh browser `Ctrl+Shift+R`.

## 3. Smoke test browser

1. Mode Lihat: toolbar satu baris saat layar lebar, tanggal/jam WITA, Play/Pause, Focus, Fit, zoom tetap bisa dipakai. Kotak 2 parameter: klik masing-masing baris dan pastikan mini chart berganti judul dan seri; klik **Lihat tren 24 jam** untuk pop-up lama. Bandingkan hanya satuan sama, data null membentuk celah dan angka 0 tidak hilang.
2. Mode Edit admin: buat Group Area, ubah Solid/Dashed/Dotted, warna, opasitas dan judul; drag tepi, resize sudut, kunci; save/reload. Pastikan garis listrik/simbol tidak ikut berubah. Uji Batal, Undo/Redo, revisi, 409.
3. Uji kanvas mendekati tepi, input ukuran manual, Fit, zoom dan scroll pada diagram besar. Pengguna non-admin hanya Mode Lihat.
4. Pastikan monitoring H/J, laporan, import Excel dan input harian tetap normal. Periksa console browser untuk error.

## 4. Rollback tanpa menghapus volume PostgreSQL

Jika **belum pernah menyimpan layout dengan Group Area** setelah upgrade, pulihkan arsip source sebelum Stage 4.2 (jangan menimpa `.env`/backups), lalu `docker compose build && docker compose up -d --no-build` dan jalankan smoke test. Simpan backup source Stage 4.2 untuk investigasi.

Jika **sudah menyimpan Group Area**, gunakan UI Stage 4.2 untuk **memulihkan revisi diagram sebelum Group Area dibuat**, sebagai revisi baru, *sebelum* downgrade source. Stage 4.1 validator belum mengenal field `areas`, sehingga diagram Stage 4.2 tidak bisa disimpan menggunakan Stage 4.1 selama `areas` masih ada. Alternatif restore DB sebelum upgrade hanya jika diperhitungkan dampaknya terhadap seluruh data yang berubah setelah backup; jangan restore massal secara otomatis.

Jangan pernah menjalankan `docker compose down -v` atau menghapus volume PostgreSQL.

## Batas uji

QA offline Python/Node berjalan; build frontend asli dan browser/Docker perlu divalidasi di LXC. Referensi: `QA_STATUS.md`.
