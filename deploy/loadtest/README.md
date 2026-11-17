# BerauLoad Stage 7 Hotfix 1 — load test (ONLY isolated instances)

**DILARANG menjalankan uji beban pada produksi.** Runner membutuhkan flag
`--confirm-isolated`, alamat `http://127.0.0.1`/`localhost` (port 8092 ditolak),
dan untuk jalur HTTP tanpa `--asgi-sqlite` memeriksa
`/api/health.test_instance == true`. Fixture juga menolak DB tanpa
`BERAULOAD_TEST_INSTANCE=true`.

## Dataset sintetis

`fixture.py` membuat 20 ULP uji, masing-masing 60 parameter input termasuk
`system.load` dan `system.capacity`, 20 operator, 60 pembaca management pada ULP
yang benar-benar memiliki data (bukan UP3 kosong), dan akun peer untuk tabrakan.
Tiga tanggal sintetis (hari dua hari lalu, hari sebelumnya, dan periode sama tahun
sebelumnya) diisi 4–12 jam contoh untuk setiap ULP. Ada satu diagram topologi
sintetis per ULP. Semua kode dan unit berasal dari fixture, bukan nilai produksi.

Pembaca memanggil **semua** endpoint setiap siklus, lalu mengulang dengan jeda
3–8 detik: dashboard, analytics, compare, kelengkapan, topologi (`GET /api/topology`),
dan ekspor XLSX kelengkapan. Tiga eksportir tambahan secara bersamaan mengambil
`GET /api/reports/export`. Pengisi melakukan PUT 60 parameter pada delapan jam
secara berurutan tiap 3–5 detik. Pemeriksaan akhir membaca ulang nilai dan
menguji dua akun pada parameter berbeda, lalu parameter yang sama dengan `base`
basi (409 diharapkan). HTTP non-2xx selain 409 yang memang diharapkan selalu
membuat hasil GAGAL; payload kosong/`configured:false` juga gagal.

## SQLite in-process: uji logika, bukan kapasitas

```bash
PYTHONPATH=backend:. python3 -m deploy.loadtest.runner \
  --confirm-isolated --asgi-sqlite --fixture /tmp/ignored.json \
  --duration 8 --writers 2 --readers 2 --exports 1 --logic-only
```

Tidak membutuhkan PostgreSQL. Hasil p95 SQLite bukan SLA produksi.

## PostgreSQL 16 staging TERPISAH di LXC

Lakukan hanya pada server yang memang boleh dipakai menguji beban, dengan
resource/port/volume yang **terpisah**. Jangan gunakan volume atau backup
produksi. Dari root source proyek:

```bash
docker compose -f deploy/loadtest/compose.test.yaml build
docker compose -f deploy/loadtest/compose.test.yaml up -d
# Buat fixture SEKALI pada database pengujian yang masih kosong.
docker compose -f deploy/loadtest/compose.test.yaml exec backend \
  python -m loadtest.fixture /data/uploads/loadtest-fixture.json
docker compose -f deploy/loadtest/compose.test.yaml exec -T backend \
  cat /data/uploads/loadtest-fixture.json > /tmp/berauload-stage7-test-users.json
chmod 600 /tmp/berauload-stage7-test-users.json
PYTHONPATH=backend:. python3 -m deploy.loadtest.runner \
  --confirm-isolated --base-url http://127.0.0.1:18093 \
  --fixture /tmp/berauload-stage7-test-users.json \
  --duration 300 --writers 20 --readers 60 --exports 3
```

Pada terminal lain, pantau:

```bash
docker stats
docker compose -f deploy/loadtest/compose.test.yaml exec db \
  psql -U stage7 -d berauload_stage7_test -c \
  'SELECT state,count(*) FROM pg_stat_activity GROUP BY state;'
```

Setelah selesai, hapus **hanya** stack pengujian:

```bash
docker compose -f deploy/loadtest/compose.test.yaml down -v
rm -f /tmp/berauload-stage7-test-users.json
```

Perintah `down -v` **hanya boleh** digunakan dengan file Compose uji tersebut,
**JANGAN** untuk Compose produksi BerauLoad.

## Kriteria dan laporan

Tabel mencatat jumlah respons, p50/p95/p99 (ms) serta HTTP status per endpoint.
`HTTP codes` mencatat semua kode termasuk 409 uji konflik; error jaringan dan
payload tidak valid dicatat tersendiri. Keputusan akhir `LULUS` hanya jika:

- tidak ada HTTP error tak diharapkan atau error jaringan;
- tidak ada 5xx dan tidak ada respons pembaca `configured:false` / tanpa data;
- `PUT records p95 < 1000 ms` dan `GET dashboard p95 < 2000 ms`;
- tidak ada pembaruan hilang dan tabrakan berjalan benar.

Ambang dapat disesuaikan dengan `--put-p95-ms` dan `--dashboard-p95-ms`.
Kehabisan connection pool umumnya muncul sebagai 5xx/timeout; pantau
`pg_stat_activity` dan log backend untuk verifikasi. Uji kapasitas nyata dan
EXPLAIN (ANALYZE) lima query terburuk harus dilakukan di PostgreSQL staging,
bukan disimpulkan dari SQLite.

## Tes otomatis jalur HTTP non-ASGI

`backend/tests/test_loadtest_runner.py` menjalankan `uvicorn` lokal pada port
loopback acak, dengan database SQLite dan fixture baru, lalu memanggil CLI **tanpa
`--asgi-sqlite`**. Tes ini menangkap bug `UnboundLocalError: Path` dan memvalidasi
jalur HTTP (auth, marker, seluruh endpoint, write readback, konflik). Ini tetap
bukan pengganti pengujian PostgreSQL 16 di LXC.

## Pemisahan smoke test dan pengujian kapasitas

`--logic-only` hanya untuk uji logika singkat SQLite/HTTP staging: semua endpoint
wajib memiliki sampel, tidak boleh ada HTTP/network error atau payload invalid,
serta data akhir dan konflik harus benar. Ambang p95 **tidak dinilai** pada mode
ini, karena waktu SQLite di CI bukan representasi kapasitas PostgreSQL.

Tanpa `--logic-only`, batas p95 PUT dan dashboard tetap wajib, dan pengujian
kapasitas 300 detik terhadap PostgreSQL staging tetap memakai aturan semula.
Setiap pembaca dan penulis kini menyelesaikan minimal satu siklus, sehingga
durasi singkat tidak menghasilkan sampel kosong secara diam-diam.
