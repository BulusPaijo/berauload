## Stage 8 — Global display branding (2026-11-17)

- `app_branding` adalah **satu baris global** (`id=1`, CHECK), terpisah dari master unit dan data operasional. Semuanya nullable; `modules/branding/defaults.py` authoritative, disalin ke `features/branding/branding.mjs` dengan pengujian kesamaan. `schema_migrations` menyimpan versi sekali jalan; tanpa backfill data historis.
- `GET /api/branding`, `/logo`, `/favicon` **publik** untuk login. `PUT`/`POST`/`DELETE` memerlukan admin + CSRF dan audit. Unggahan bukan SVG; magic bytes, Pillow decode, limit ukuran/dimensi, dan re-encode PNG sebelum atomic replace ke volume uploads.
- Context branding dipasang di `frontend/src/main.tsx` sebelum login, dengan fallback cache publik. UI hanya mengganti display labels, CSS brand vars, favicon/title/metadata, tanpa mengganti `berauload` compose, cookie, storage teknis, format Excel/JSON, atau data per unit.
- Renderer PDF/Excel mengambil snapshot identitas dari database saat export dipanggil. Logo PDF opsional/fault tolerant. Branding bersifat global tanpa pemanggilan rekap ulang ataupun mutasi angka.

## 1.6.0-stage7-hotfix1 — alat uji terisolasi (tanpa perubahan arsitektur aplikasi)

`deploy/loadtest/runner.py` dapat menjalankan ASGITransport/SQLite sementara atau HTTP loopback terhadap instans berpenanda `test_instance:true` (termasuk PostgreSQL 16 staging). Kedua jalur menolak port produksi 8092 dan membutuhkan `--confirm-isolated`. Fixture membuat ULP dengan dua peran utama, data tahun berjalan/lalu, diagram dan akun baca di unit terkait. Laporan runner menghitung latensi per endpoint dan semua status HTTP; hanya 409 sengaja pada skenario konflik diperbolehkan. Perbaikan Nginx hanya menyentuh tanda kutip regex hashed asset, dan permission smoke test. API, SQLAlchemy model, schema_migrations, izin dan rekap tetap identik dengan Stage 7.

## Stage 7 — Input transaksi dan sesi

`records/entry.py` mengunci `(unit_id,day,hour)` dengan `pg_advisory_xact_lock`
(hash BLAKE2b 64-bit dari string domain bertipe) pada PostgreSQL; SQLite tidak
memiliki kunci advisory. Di dalam satu transaksi: baca jam/unit, validasi kode,
bandingkan `base` (jika disertakan) hanya untuk nilai yang akan berubah, tolak
409 terstruktur bila usang, tulis hanya perubahan dan computed yang berbeda,
recalculate unit atas, audit dan commit. Rekap dan sumber rollback bersamaan.
Berbagai unit pada jam sama tidak memakai kunci yang sama; konflik unique
`HourRecord` global diatasi PostgreSQL `INSERT ON CONFLICT DO NOTHING`.

`modules/sessions` menambah indeks `login_attempts` dan nullable
`login_sessions.last_seen_at`; cleanup sesi kedaluwarsa terjadi startup/tiap
maksimal 1 jam saat login. Cookie renewal mengikuti idle expiry geser, dibatasi
absolute expiry. `UVICORN_WORKERS>1` ditolak startup: cache agregasi tetap
in-process dan setup/migrasi concurrent workers belum dituntaskan. Frontend
`input-form/autosave` memegang antrean, backup, konflik dan reauth; `App.tsx`
hanya menambahkan sesi heartbeat dan navigasi aman dari perubahan yang belum
tersimpan. Tidak ada perubahan formula, status sumber atau hak unit.

## V1.6.0 Stage 6 — Monitoring Lintas Unit (read-only)

- `modules/completeness/service.py` menyelesaikan hak baca unit target dengan warisan peran dari `org_units.context`, lalu menyusun ULP/KP aktif. Query master peran dan status hari bersifat tetap jumlahnya; **satu SQL COUNT(DISTINCT hour) CASE … GROUP BY metric.unit_id, hour_record.day** menghitung jam `system.load` atau jam minimal satu input aktif (hanya nilai non-NULL). Status hari dari `unit_day_states`; tanpa baris = draft. UP3 tidak punya baris. WITA menggunakan ZoneInfo Asia/Makassar; jam saat ini sudah dihitung sejak mulai, jam masa depan belum dihitung; hari depan expected 0. Tidak ada penulisan DB.
- `modules/completeness/export.py` memakai openpyxl yang sudah menjadi dependensi aplikasi, menulis dua sheet XLSX ke berkas sementara, dan memakai `FileResponse` dengan `BackgroundTask` untuk menghapusnya. Teks aman terhadap spreadsheet formula injection dengan sanitizer modul ekspor lama.
- `modules/topology/service.py` menambah `symbols[].link` opsional tepat `{unit_id, diagram_id}`. `modules/topology/links.py` memverifikasi diagram aktif, kepemilikan unit tujuan, hubungan keturunan ketat, dan siklus untuk semua create/update/restore. Layout lama tetap valid. Revisi menyimpan JSON link yang sama. Jika restore menemukan tujuan arsip, seluruh restore ditolak dengan simbol penyebab (HTTP 422). Tidak ada data/graf listrik yang dibuat oleh link.
- `GET /api/topology/browse` menampilkan diagram unit aktif yang boleh dibaca di bawah unit aktif; `GET /api/topology/link-targets` hanya memberi target keturunan yang boleh dibaca. Viewer tidak menampilkan marker tautan bila diagram tujuan tidak ada pada hasil hak baca. `TopologyPage` menggunakan pemilih unit yang ada dan mempertahankan hari/jam pada transisi; breadcrumb organisasi serta jejak kembali disimpan di state App. Tidak ada migrasi, indeks atau perubahan mesin hitung.
- Pengujian SQLite 62 hari × 6 unit × 24 jam: 8.928 pembacaan, 372 sel. 6 kali pengukuran dengan median ~0,01205 detik pada host QA. EXPLAIN SQLite menggunakan indeks `(day,hour)` di hour_records dan unique `(hour_id,metric_id)` di readings. **Belum diuji PostgreSQL 16.**

## V1.6.0 Stage 5 Hotfix 1 — Rekalkulasi Template Import

Alur commit: `template_import/router.py::commit` menyiapkan arsip → `template_import/service.py::write` mengisi nilai input serta computed lokal yang *baru* per jam → kumpulkan hanya `Metric.code` yang benar-benar disisipkan → `unit_references/recalculation.py::recalculate(db, day, hour, unit_id, written_codes)` **sekali pada akhir jam** → `db.commit()` **sekali setelah seluruh jam berhasil**. Jika ada exception, router menjalankan `db.rollback()` dan menghapus file arsip yang baru dibuat; staging token dipertahankan untuk retry. Logika penghitungan dan aturan ULP verified/final, penanda `unit_source_changes`, serta rekap UP3 tetap milik modul Stage 5 sebelumnya. Jam/hari yang tidak menghasilkan pembacaan baru tidak memicu hitung ulang; sumber 0 tetap pembacaan valid. Tidak ada DDL/migrasi baru atau perubahan izin. Pengukuran SQLite sintetis 744 jam: baseline Stage 5 9,751 dtk (rekap ULP/UP3 tidak terisi), Hotfix 13,036 dtk (744 hasil ULP + 744 hasil UP3).

## V1.6.0 Stage 4c UI Hotfix 1 — Halaman Pengguna

`frontend/src/features/users/UserManager.tsx` mengelola form dan daftar pengguna; fungsi unit role/validasi/format akses dipisah ke `userAccess.mjs`. Admin membaca `GET /api/users`, `GET /api/org-units`, dan `GET /api/org-units/{id}/access` untuk setiap unit di organisasi. Tidak diperlukan perubahan kontrak backend dan tidak ada migrasi database. Akses yang dipilih untuk akun non-admin tetap dikirim melalui `POST /api/users` dengan struktur `accesses=[{unit_id, role}]`, sedangkan admin mengirim array kosong sesuai aturan Stage 4c. Metadata versi pada FastAPI dan health diselaraskan, tanpa mengubah izin.

## V1.6.0 Stage 4c — Antarmuka multi-unit dan akses pengguna

- **Klien:** `frontend/src/api.ts` menyediakan `apiFetch` bagi JSON, multipart, dan unduhan; semuanya menyisipkan `X-Unit-Id` terpilih, cookie sesi serta CSRF sesuai metode. `features/org-units/useActiveUnit.ts` mengelola daftar unit yang sudah disaring backend, pilihan per-user `localStorage` (try/catch), fallback ke unit aktif yang masih boleh dibaca, dan remount halaman ketika unit berganti agar state pembacaan tidak tercampur. Unit aktif, peran hanya lihat, dan aksi admin UP3 ditampilkan di shell.
- **Daftar unit:** `org_units.router.list_units()` mempertahankan filter otorisasi lama, menambahkan `roles` efektif untuk setiap unit. UI hanya menampilkan unit aktif yang boleh dibaca; admin melihat semua unit aktif dan dapat menggunakan pemilih yang sama untuk konfigurasi serta operasi data ULP/KP.
- **Manajemen pengguna:** pembuatan non-admin mensyaratkan setidaknya satu `accesses=[{unit_id,role}]` eksplisit; tidak ada default tersembunyi ke `legacy_home`. Akses boleh banyak unit, peran bisa berbeda. Admin tetap peran global dengan grant root historis; grant admin lama dipertahankan saat admin mengubah grant pengguna lain. Mutasi akses dicatat di audit yang sudah ada.
- **Aksi massal:** `records.service.tree_eligibility()` digunakan pada GET `days/{day}/tree-preview?action=verify|finalize` serta operasi POST; unit yang memenuhi syarat diproses, lainnya dilewati dengan alasan. Bila tak ada unit memenuhi syarat, HTTP 422. Transaksi tetap satu, audit tetap per unit terproses, akses verifier/admin global wajib, tanpa mengubah pembacaan. Endpoint `days/{day}/status` memuat nama verifikator/finalisator dan penanda admin global dari audit.
- **Preferensi pribadi non-home:** fallback pembacaan `scope='user'` hanya jika baris dengan kunci unit `u<id>` belum ada. Tidak ada DDL atau migrasi data; restart tidak menambah/mengubah preferensi yang tersimpan. Saat ada dua versi, kunci khusus unit tetap prioritas.
- **Copy Settings:** antarmuka pratinjau membaca endpoint Tahap 4b; commit memerlukan konfirmasi. Computed tanpa formula, readings, dan status hari tidak tersalin; role utama perlu diatur kembali.
- **Batas QA:** 125 tes backend SQLite lulus dan 4 tes Node lulus. `npm install` gagal DNS `EAI_AGAIN`; `npm run build` belum bisa menguji keseluruhan frontend karena modul React/Vite/tipe tidak terpasang. Browser/LXC dan PostgreSQL 16 belum diuji. Tidak mengubah data produksi, migrasi lama, atau formula.

## V1.6.0 Stage 4b — Konfigurasi Terisolasi per Unit

**Schema migration:** `backend/app/modules/org_units/migration_config.py`. `ensure_schema(engine)` menambah kolom `unit_id` nullable (FK) sebelum migrator lama membaca tabel. `backfill_once(engine)` setelah migrasi organisasi mengisi konfigurasi legacy ke ULP Tanjung Redeb dan menyimpan penanda versi sekali jalan. Audit historis tetap NULL. Foreign key dan unique constraints yang sudah ada dipertahankan; tab default unit baru memakai kode global unik `u<id>_<kode-tab>`.

**Request scope:** `X-Unit-Id` diperiksa oleh `org_units.context.unit_context('read'|'configure')`. Semua router saved configuration menyaring data menurut `unit_id` aktif; direct object ID lintas unit 404; perubahan oleh admin global. Form Input dan Template Import memakai tab/placement unit sendiri; UP3 tidak menerima tab input. Default charts/standard report mempertahankan constraint unik scope/owner lama dengan penyimpanan kunci scope internal berbeda per unit, tetapi respons API tetap konsisten.

**Copy Settings:** `org_units/copy_router.py` → `copy_settings.py` → CRUD pada tabel konfigurasi/asset/metrics; satu transaksi. Pratinjau memetakan code, commit memeriksa ulang. Formula expression dan referensi topologi dipetakan. Tidak menyentuh nilai pembacaan, status hari, revision history source, atau batch import; diagram dengan rule asing ditolak. Global equipment kind dan master satuan tetap global. Nomor peralatan/parameter source tetap permanen.

**Batas:** tidak ada pemilih unit frontend (4c), tidak ada referensi KPI/computed lintas unit (Stage5), tidak ada perubahan Formula Engine/SCADA atau pemutakhiran pembacaan historis. Konfigurasi UP3 selain computed/dashboard/topologi belum diperluas. Lihat QA_STATUS.md dan README_UPGRADE_V1_6_0_STAGE4B.md.

## V1.6.0 Stage 4a — Isolasi operasional per unit

### Pola security dan ownership
`backend/app/modules/org_units/context.py` adalah dependency FastAPI terpusat: `unit_context('read'|'write_data'|'configure')`. Header `X-Unit-Id` opsional, divalidasi sebagai ID unit aktif; tanpa header, default berasal dari akses pengguna (tertinggi) atau `legacy_home` khusus superadmin. `UnitContext` menyimpan actor, unit, role efektif, superadmin, serta helper audit. Hak baca/tulis diwariskan dari akses pada unit leluhur; management UP3 read-only. Akses konfigurasi global admin saja. Kode parameter yang dikirim sebagai input API harus di-resolve bersama `unit_id` atau 404.

`backend/app/modules/records/service.py` membaca dan mengubah `UnitDayState` sebagai sumber status; `HourRecord` tetap global sehingga kueri pembacaan selalu join ke `Metric.unit_id`. Perubahan status `legacy_home` juga menulis `DayState` historis dalam transaksi yang sama. Tindakan massal ULP+KP memakai transaksi atomik. Tidak ada migrasi DDL/data baru untuk Stage 4a: seluruh tabel multi-unit berasal dari versi 1.6.0 terdahulu.

### Modul domain
- `catalog_api/router.py`: katalog dan master asset/metric dibatasi ctx.unit; UP3 menolak pembuatan input/peralatan.
- `records/router.py`, `records/entry.py`, `records/service.py`: input harian, baca, status, massal.
- `analytics_core/router.py`, `monitoring/router.py`, `performance/router.py`, `legacy_reports/router.py`: semua memakai metric unit milik konteks aktif, tanpa filter HourRecord global saja.
- `template_import/{router,repository,service}.py`: preview/commit/riwayat serta pembacaan per unit; import laporan lama dikunci ke legacy_home.
- `org_units/router.py`: pohon unit yang dapat dibaca; aturan penetapan akses lama tidak lagi memaksa akses setiap non-admin ke legacy_home.
- Konfigurasi belum terikat unit (Topologi, dashboard-layout, historis, reports, form input, engineering) sementara diproteksi `legacy_home_scope` sampai migrasi & routing 4b. UP3 management tetap dapat membaca konfigurasi legacy sebagai induk apabila diizinkan.

### Batas tahap
Stage 4a hanya backend. Unit picker, reload katalog otomatis, mode read-only dan user-unit UI dikerjakan pada **4c**. `unit_id` pada konfigurasi, salin konfigurasi, tab baru tiap unit dikerjakan pada **4b**. Uji API unit baru dapat dilakukan dengan `X-Unit-Id`; beberapa konfigurasi non-home akan merespons 404 sampai 4b, **bukan** berarti seluruh halaman unit baru sudah beroperasi end-to-end.

# Arsitektur V1.6.0 Stage 3 — Resolver Peran Parameter

**Single source of truth:** `Metric.role_key` + `Metric.unit_id`. `backend/app/modules/org_units/roles.py::metric_for_role(db,unit_id,role_key) -> Metric|None` tidak memakai fallback kode dan hanya memilih parameter aktif pada unit tepat. `role_codes`/`main_pair` menjadi fungsi bersama, dengan `home_unit(db)` hanya dipanggil pada boundary API sampai pemilih unit diterapkan di Tahap 4. `GET /api/catalog.roles` mengirim peta role_key ke kode parameter tanpa menghilangkan field katalog lama.

**Backend:** modul baru `primary_metrics/router.py` GET/PUT role utama (admin+CSRF+audit); `org_units/usage.py` inventaris referensi sebelum nonaktif. Endpoint lama dipindah tanpa mengganti URL ke `analytics_core/router.py` (dashboard/analytics/compare), `records/router.py` (hari, status, verify/finalize/reopen), `legacy_reports/router.py`, `parameters/router.py` (update/usage/confirm), `users/router.py`. Modul monitoring/dashboard_settings/dashboard_builder/standard_reports kini membaca role dengan unit eksplisit. Pasangan role hanya memicu aturan visualisasi H/J bila keduanya aktif pada unit yang sama. `NULL` pada reading bukan angka nol; data tersimpan tidak di-rewrite.

**Frontend:** `primary-metrics/PrimaryMetricSettings.tsx` pada Settings admin; peta `Catalog.roles` digunakan untuk preset baru di Monitoring, Dashboard Builder, Historical, Engineering, Standard Report, Export, Formula Builder. Peringatan konfigurasi hilang dan tautan Settings tampil tanpa mengubah data. Perintah Topologi ‘Terapkan ke Peralatan Sejenis’ melakukan pencocokan `role_key` bila ada, fallback exact name+unit bila tidak; target harus sama asset kind dan `unit_id`.

**Kompatibilitas:** Initial role migration Stage 1 yang sudah ada tetap mengikat H/J legacy, sehingga respons numerik pengguna ULP Tanjung Redeb harus tetap sama. Saved dashboard/formula/analisis/report yang eksplisit menyimpan metric_code tetap apa adanya dan tidak dimigrasi diam-diam. Dashboard default seed versi 1 dapat diproyeksikan hanya dalam respons sesuai role aktif tanpa mengubah JSON/revisi database. Jika peran tidak lengkap, API bawaan mengembalikan 200 + `configured:false` dan nilai null/kosong, bukan mengarang hasil.

**Tidak ada migrasi Stage 3:** `schema_migrations` tidak ditambah, `day_states` tetap status baca resmi, `unit_day_states` dual-write lama tetap, `HourRecord(day,hour)` global, PostgreSQL 16 produksi belum diuji. Seluruh aturan otorisasi operasional yang sudah ada tetap berlaku; permission unit belum diaktifkan.

---

# Addendum V1.6.0 Stage 2 — Template Import

```text
backend/app/modules/template_import/
  migrations.py    # ADD COLUMN import_batches.kind; backfill sekali; index SHA256+unit
  repository.py    # input_form+metric per unit; status/reading historis per unit
  workbook.py      # XLSX 1–92 hari, metadata, proteksi, validasi sel
  validator.py     # strict read_only data_only validation; reject semua Excel formula
  service.py       # dry-run plan; insert-only reading, computed dari engine existing
  router.py        # download; preview staging; commit; config/history
frontend/src/features/template-import/
  TemplateImportPage.tsx
  template-import.css
```

- Registrasi router dan migrasi dilakukan dari `main.py`, tanpa mengubah `importer.py` atau endpoint `/api/imports/*`. Navigasi Import Excel dalam `App.tsx` membungkus `LegacyImportsPage` yang tetap apa adanya.
- Sampai Tahap Multi-Unit 4, endpoint memilih `home_unit(db)` (ULP Tanjung Redeb). Seluruh helper menerima `unit_id`, tidak mengandalkan root/UP3 global. Form input saat ini memiliki konfigurasi tab/placement global; pilihan metric difilter `Metric.unit_id == unit_id`, `active`, `input_mode=input`, `visible`, dan tab aktif. Legacy `daya_mampu_sistem_kw` selalu dikecualikan.
- XLSX mengandung `Petunjuk`, sheet data per tab, dan sheet `_meta` tersembunyi; data di baris 4+, baris 3 satu-satunya sumber kode parameter (nama kolom boleh diubah). Nilai finite numeric/0 diterima, kosong tidak menulis, formula di mana pun ditolak.
- Preview bersifat read-only terhadap database; data file sementara dipisah dari folder staging import lama, token UUID dan SHA256 dipasangkan ke pemilik sesi dan unit, TTL 1 jam. Commit membaca ulang file dan menghitung ulang konflik berdasarkan data DB terbaru. Arsip disimpan sebelum commit DB; jika transaksi gagal, file arsip baru dibersihkan. Catatan audit meliputi unit, pelaku, dan hasil import.
- `new_hours` memeriksa apakah ada Reading untuk Metric milik unit tersebut pada slot global HourRecord. Jam yang sudah berisi pembacaan milik unit lain tidak otomatis dianggap terisi. `fill_empty` hanya menambah Reading pada slot yang belum memiliki pasangan (hour_id,metric_id); `day_states` tetap sumber status, verified/final tidak ditulis, computed existing tidak diubah.
- Database: hanya tambah `import_batches.kind` nullable+default legacy, backfill sekali ketika versi migrasi belum tercatat, serta unique partial index `(unit_id,sha256)` untuk batch template. Readings/hour_records/day_states tidak berubah saat migration.

---

# Koreksi V1.6.0 Tahap 1.2 — Migrasi Sekali Jalan

`setup()` tetap menjalankan migrasi organisasi pada startup dengan urutan Stage 1 → Stage 1.1, tetapi **data backfill hanya berlaku saat penanda versinya belum ada**. Pada Stage 1, `migrations.run` tetap memeriksa/menambah kolom/index dan memperbaiki `assets/metrics/import_batches.unit_id IS NULL` ke `legacy_home` bila perlu; `_copy_states_and_users` berjalan hanya saat `20261115_11_org_units_stage1` pending. Pada Stage 1.1, `migration_home.run` selalu menjamin kolom/index `legacy_home` tersedia, lalu **langsung selesai** jika versi `20261115_12_legacy_home_ulp_tanjung_redeb` sudah tercatat. Jika pending, seed/pemindahan dan pemeriksaan dilakukan satu transaksi lalu versi dicatat bersama audit.

Setelah migrasi tercatat, parameter computed UP3 dan penugasan user lintas unit valid tidak dipindahkan lagi saat restart; konflik role UP3 dan home ULP tidak menggagalkan startup. `HourRecord` tetap global, `day_states` tetap sumber resmi, role global tetap dasar izin operasional. **Tidak ada migrasi schema versi baru** dan tidak ada SQL yang menulis `readings/hour_records/day_states`.

---

# Arsitektur V1.6.0 Stage 1.1 — Pemindahan Pemilik Data Legacy

Unit organisasi tetap dimodelkan di `backend/app/modules/org_units` dan tidak mengubah identitas slot waktu `HourRecord(day, hour)` global. `repository.root(db)` mencari `OrgUnit.level='up3'`; `repository.home_unit(db)` mencari `legacy_home=TRUE`. UP3 adalah induk, ULP Tanjung Redeb adalah pemilik data lama. Pada tahap ini belum ada enforcement akses unit.

**Urutan startup:** `precreate_org_units` → create_all legacy → migrasi domain lama → migrasi organisasi Stage 1 (`migrations.run`) → migrasi Stage 1.1 (`migration_home.run`). Stage 1.1 menambah kolom boolean `legacy_home` default false + indeks unik parsial; jika perlu membuat ULP tetap dengan kode `ulp_tanjung_redeb`. Dalam satu transaksi SQL, `unit_id` milik UP3 di `assets`, `metrics`, `import_batches`, dan `unit_day_states` dipindahkan ke ULP; akses non-admin UP3 dipindah ke ULP, akses admin tetap UP3; audit migrasi sekali ketika versi baru dicatat. Semua tabel pembacaan/slot/status harian asli dipertahankan.

Stage 1 migrator kini mendeteksi `legacy_home` saat startup berikutnya agar tidak menambahkan lagi mirror hari/akses non-admin ke UP3. `setup()` serta endpoint create Asset/Metric, computed Formula, ImportBatch, dan mirror status menggunakan `home_unit(db)`. `attach_new_user` memilih UP3 bagi admin dan ULP bagi non-admin. Pengaturan `PUT /api/org-units/{id}/access` mengharuskan mapping non-admin global tetap tersedia pada unit legacy_home; untuk UP3 aturan lama dihapus. Hubungan data antar-unit dan otorisasi hierarkis **belum diterapkan**.

`role_key` pada metric dan grafik capacity-vs-load H (`daya_pasok_pembangkit_kw`) / J (`beban_sistem_kw`) dipertahankan. Konflik FK/unik dan duplikasi status hari yang tidak cocok menggagalkan transaksi dengan error jelas; tidak ada perubahan parsial pada `readings/hour_records/day_states`.

---

# V1.6.0 Tahap 1 — Fondasi Multi-Unit (2026-11-15)

Struktur hierarki: tepat satu UP3 tanpa induk (`up3_berau`), maksimal 100 ULP langsung pada UP3, maksimal 100 KP per ULP. Perpindahan parent/level/code dan hard delete tidak tersedia; kode `org_units.code` dan kode asset/metric lama tidak berubah. Admin boleh mengubah nama, display_order, status dan unit-access; ini **belum** membatasi data.

```text
backend/app/modules/org_units/
  models.py       OrgUnit, UnitDayState, UserUnitAccess
  migrations.py   precreate sebelum create_all, ALTER additive, backfill
  repository.py   ROOT lookup, access, role_key duplicate check, status mirror
  service.py      pure validation/hierarchy/read/write (not in live auth)
  router.py       GET tree, admin POST/PUT/status/access + audit
frontend/src/features/org-units/
  OrgUnitManager.tsx   admin tree and ULP/KP management
  UnitAccess.tsx       assignment configuration (not enforced yet)
  org-units.css       scoped CSS
```

Migrasi dicatat di `schema_migrations` dengan versi `20261115_11_org_units_stage1`; `org_units` dibuat lebih dahulu agar FK kolom nullable baru di `assets`, `metrics`, `import_batches` aman pada PostgreSQL fresh install. `readings`/`hour_records` dan `day_states` tidak diubah. `metrics.role_key` nullable, indeks unik `(unit_id, role_key)` dengan NULL berulang. Backfill eksklusif `beban_sistem_kw` → `system.load` dan `daya_pasok_pembangkit_kw` → `system.capacity`, tidak menghitung ulang REKAP H/J.

Setelah penambahan schema, `unit_day_states` mendapat salinan UP3 untuk seluruh legacy `day_states`; `user_unit_access` mendapat role tiap user lama pada UP3. Create Asset/Metric/Computed Formula/ImportBatch/User lewat API lama otomatis mengaitkan UP3. Pada verify/finalize/reopen, `mirror_day_state` memakai *Session* yang sama sebelum `db.commit()`, sehingga kegagalan transaksi menggagalkan kedua perubahan; GET status tetap dari `day_states`.

**Fungsi kebijakan masa depan** `descendants/ancestors/can_read/can_write` murni dan diuji. Pada V1.6.0 Tahap 1 tidak ada dependency auth API lain yang menggunakan fungsi ini. Otorisasi tetap sesi cookie, CSRF dan `User.role` global. Peran `management` adalah baca-saja di helper; aksi tulis helper hanya pada unit yang secara eksplisit ditugaskan dan role admin/operator/verifier. Penegakan akses unit baru Tahap 2+, setelah mapping unit disetujui.


---

# Arsitektur BerauLoad — hingga V1.5.0 Tahap 4.2

## Prinsip

Modular monolith, akses data dipisahkan dari HTTP dan UI, satu mesin Formula Engine V1.1, tidak ada duplikasi data historis. Satu konfigurasi form global untuk Sistem Kelistrikan Berau; khusus admin yang bisa mengubah.

## Domain V1.4.2

```text
backend/app/modules/input_forms/
  models.py       # InputFormTab, InputFormPlacement, InputFormRevision
  migrations.py   # migrasi additive/idempotent, seeding 5 tab legacy
  repository.py   # query terpusat
  service.py      # fallback untuk parameter baru, validasi config
  router.py       # GET/PUT /api/input-form/config, audit, optimistic lock
frontend/src/features/input-form/
  types.ts        # kontrak DTO TypeScript
  InputFormEditor.tsx # urutan tab/parameter, show/hide, preview, save/cancel
  InputPage.tsx   # tabel 24 jam membaca konfigurasi GET dari server
  input-form.css  # style terisolasi
```

`backend/app/main.py` hanya menambahkan router, migrasi, dan dukungan pilihan `input_tab_code` saat membuat Metric jenis input. Pembacaan disimpan melalui API `/api/records/...` yang sudah ada; Formula Engine dan importer tidak diubah.

## Alur data

1. Admin membuat Asset/Metric. Metric tetap menyimpan `group_name` (kelompok sumber/laporan) dan `code` permanen.
2. Admin mengatur tab operator yang *terpisah* dari kelompok sumber. Model `InputFormPlacement` menghubungkan `metric_code` ke satu `tab_code`, `visible`, dan urutan. Tidak ada penulisan nilai kelistrikan pada tabel pengaturan.
3. User membuka Input Harian. `GET /api/input-form/config` mengembalikan tab dan penempatan; jika Metric baru belum punya penempatan eksplisit, `service.form_data` menggunakan `group_name` sebagai default. Legacy manual daya mampu disembunyikan secara default. Data jam tetap dibaca dari `/api/records/day`.
4. Operator mengisi parameter Input pada jam yang relevan. Computed/imported tampil read-only. Menyembunyikan kolom tidak menghapus pengukuran.
5. Admin menyimpan seluruh layout melalui `PUT /api/input-form/config` dengan `expected_version`. Ketika versi sudah berubah, API menolak HTTP 409; UI meminta reload. Semua tindakan di-audit.

## Penambahan fitur mendatang

- Atribut tampilan baru: tambahkan ke model `input_forms`, migrasi additive, validasi service, kontrak TS, tes, dokumentasi.
- Jangan menaruh rumus kelistrikan dalam `InputFormEditor` atau `InputPage`.
- `required` perlu efektivitas tanggal dan kebijakan data historis/final, jadi belum berlaku pada V1.4.2.
- Mapping import Excel adalah domain `importer.py`, bukan konfigurasi tab; jangan otomatis mengubah pemetaan file sumber.

## Invarian

- Kode Metric, kelompok sumber dan riwayat reading tetap.
- `daya_pasok_pembangkit_kw` (REKAP H) adalah Daya Mampu Sistem; `beban_sistem_kw` (REKAP J) adalah Beban Sistem.
- `NULL` tidak otomatis menjadi 0; data Final tidak dapat diedit melalui input biasa.
- Tab yang sudah ada tidak di-hard-delete, hanya dinonaktifkan; penempatan tetap tersimpan.

## V1.4.2.1 — Master Satuan & Formula yang sadar dimensi

`backend/app/modules/units/` berisi `models.py`, `migrations.py`, `router.py`, `service.py` dan `formula.py` sebagai domain tersendiri.

- `unit_definitions(code, name, dimension, factor, builtin, active)` menyimpan konversi relatif ke satuan dasar tiap besaran. Semua unit standar dikunci. Unit custom boleh dinonaktifkan selama tidak direferensikan parameter.
- Identitas Metric.unit (varchar) lama tidak diubah. Pembacaan asli tetap disimpan dalam satuan asal. Migrasi idempotent mengimpor kode unit existing dan menyemai unit standar.
- Formula Engine existing tetap mem-parsing AST aman. `units/formula.py` memperluas validasi dimensi dan evaluasi saat satuan sumber/hasil berbeda; konstanta numerik perbandingan mengikuti satuan operand yang relevan, misalnya `IF(tegangan_kv > 20, ...)`.
- Rasio/% tetap mengikuti konvensi V1.1: `beban/daya_mampu * 100` menghasilkan angka persentase. `1`↔`%` pada API konversi memakai faktor 1↔0,01.
- Formula yang sudah ada dengan satuan input/hasil sama tetap memakai evaluasi asli V1.1. Tidak ada perhitungan ulang terhadap hasil final/historis setelah upgrade.

## V1.4.3 — Advanced Visualization

`backend/app/modules/dashboard_builder/visualization.py` memvalidasi konfigurasi yang tersimpan (warna, legend, decimal, display_unit, chart kind). `frontend/src/features/dashboard-builder/unitPresentation.ts` mengubah satuan pada salinan data untuk grafis, tanpa database write.

Panel menerima pilihan opsional `legend`, `colors`, `decimals`, `display_unit`, `show_points`; panel lama tanpa field tersebut otomatis memakai default. Tipe grafik tambahan: `step` dan `stacked_bar`. Panel H/J tidak bisa ditumpuk; grafik existing tetap menghitung rata-rata berpasangan. Cache dan materialisasi agregat belum diubah.


## Domain tambahan V1.4.4

```text
backend/app/modules/data_export/
  models.py       ExportTemplate (konfigurasi saja)
  migrations.py   tabel export_templates additive / idempotent
  service.py      validasi tanggal/kolom/satuan; query streaming jam/agregasi
  renderer.py     file XLSX write-only dan CSV streaming ke temp file
  router.py       preview, download, template CRUD & audit
frontend/src/features/data-export/
  ExportBuilder.tsx   form ekspor, urutan kolom, preview, template
  export-builder.css
backend/app/modules/dashboard_builder/
  models.py       DashboardLayout + DashboardShare + DashboardRevision
  migrations.py   backfill revision current, tabel shares/revisions
  repository.py   list yang dapat dilihat & snapshot versi
  router.py       share, revisi/restore, template, import/export JSON
frontend/src/features/dashboard-builder/
  DashboardManagement.tsx   toolbar manajemen terpisah dari editor panel
```

Alur ekspor: UI menyimpan konfigurasi pilihan kolom -> backend mengecek CSRF, hak akses, tanggal, parameter, dimensi satuan -> query berdasarkan tanggal dan parameter yang dipilih -> render XLSX/CSV ke temporary file -> unduh -> temporary file dihapus. File bukan sumber data; pengukuran historis tetap di tabel `hour_records` dan `readings`. Query memakai filter tanggal/parameter, tidak mengambil seluruh database tanpa batas.

Alur dashboard: pemilik memilih layout -> semua revisi layout baru disimpan sebagai snapshot immutable -> share baca-saja melalui tabel penghubung -> admin tetap mengelola dashboard sistem. Import JSON divalidasi terhadap kontrak panel dan dibuat sebagai dashboard pribadi; tidak boleh memuat SQL ataupun kode bebas.

Batas V1.4.4: ekspor perhitungan yang belum memiliki snapshot nilai di `readings` tidak diisi hasil tebakan. Agregasi adalah per-parameter pada jam valid yang tersedia; perbandingan H/J berpasangan tetap diproses khusus oleh endpoint monitoring. Engine V1.4.5 dapat melanjutkan optimasi indeks, rekap, streaming pekerjaan besar, dan export job queues.


## V1.4.5 — Visual Layout & Performance

- `frontend/src/features/dashboard-builder/layoutGeometry.ts`: matematik snap ukuran panel yang murni; `PanelCard.tsx`: resize via pointer di sudut dan drag pegangan, draft tetap disimpan hanya melalui `DashboardBuilder.tsx`. Tidak menggunakan library grid tambahan.
- `backend/app/modules/dashboard_builder/service.py`: validasi ukuran 3–12 kolom / 1–4 tingkat secara backward-compatible; layout tetap disimpan JSON dengan revision history dan expected_version.
- `backend/app/modules/performance/router.py` dan `service.py`: endpoint baca agregasi untuk 1–4 parameter dalam satu query SQL, otorisasi user, validasi periode.
- `backend/app/modules/performance/cache.py`: cache singkat terkunci thread dengan pembatasan ukuran; `main.py` memanggil `clear_reading_cache` sesudah commit input harian dan import Excel. Jika backend memakai multi-worker, cache in-memory bukan solusi final untuk sinkronisasi antar-worker.
- Export besar tetap mengikuti modul streaming `data_export` V1.4.4. Tidak menambah database/volume atau menyimpan duplikat pembacaan.


## V1.4.6 — Report Builder dan Panel Presentation

- Backend `app/modules/report_builder/{models,schemas,migrations,service,router,renderers}.py`: model `report_templates`, kontrol scope personal/sistem, validasi blok, query baca-saja data per jam, render PDF/XLSX. Frontend `features/report-builder/` mengatur template, komponen, pratinjau, dan unduhan.
- Tabel `report_templates` terpisah dari `dashboard_layouts`, `readings`, `formula_definitions`, dan `historical_definitions`. Blok report hanya menyimpan kode parameter dan opsi presentasi, bukan salinan nilai listrik.
- Alur: Pengguna → Laporan Kustom → validasi report config → query HourRecord/Reading → agregasi pada slot waktu WITA → preview/PDF/XLSX. Untuk dua seri, hanya jam berpasangan yang dibandingkan; interval tanpa nilai tetap `null`.
- Panel Styling: `dashboard_builder/panel_style.py` memvalidasi preset, font, ukuran, warna hex sebelum menyimpan JSON dalam layout. UI `PanelEditor.tsx` untuk edit; `PanelCard.tsx` untuk render menggunakan CSS variables.
- Persyaratan ke depan: jangan menggabungkan rumus pelaporan dengan render UI; fungsi render tidak boleh menjalankan ekspresi Python/JS/SQL dari pengguna. Perluas render melalui domain `report_builder`, bukan dengan menambah blok fungsi di `App.tsx` atau `main.py`.
- Endpoint versi `GET /api/health` merupakan sumber resmi label versi frontend (Footer, Pengaturan, Panduan).

## Standard Report Selector — V1.4.6.1

`backend/app/modules/standard_reports/` berisi model preferensi, migrasi additive, layanan agregasi (satu query/bulan) dan router pengaturan. `GET /api/compare` tetap di `main.py` sebagai compatibility wrapper yang memanggil `compare_years`; tidak ada logika hitung baru di React. `frontend/src/features/standard-reports/StandardComparison.tsx` hanya menangani UI pilihan parameter, periode, agregasi dan visualisasi. Preferensi hanya menyimpan kode parameter/agregasi per akun atau default sistem; seluruh reading dan hasil formula tetap milik modul existing.

## V1.5.0 Tahap 1 — Topologi Single Line (backend saja)

```text
backend/app/modules/topology/
  models.py         TopologyDiagram, TopologyRevision (konfigurasi JSON)
  migrations.py     dua tabel additive/idempotent, tanpa seed topologi
  repository.py     akses konfigurasi, revisi, query baca measurement
  service.py        validator layout murni & whitelist tanpa SQL/DB
  data_service.py   DTO jam/24 jam, evaluasi memakai Engineering Rules existing
  router.py         GET dan admin-only POST/PUT/archive/restore
backend/tests/test_topology.py  QA SQLite sintetis
```

Kontrak layout: `canvas` + `symbols` + `wires` + `boxes`; max 200/300/100; ID unik lintas lapisan; koordinat/panjang pada grid 10 px. `asset_code` dan `metric_codes` baru harus aktif; semua kotak `metric` wajib 1–6 parameter berbeda. `anchor_symbol_id` perlu simbol yang valid. `rule_id` hanya boleh mengacu ke Engineering Rule aktif, hasil status dibaca melalui evaluator V1.3, tidak diimplementasi ulang. Parameter legacy `daya_mampu_sistem_kw` ditolak. Mapping resmi: `daya_pasok_pembangkit_kw` = REKAP H dan `beban_sistem_kw` = REKAP J.

Untuk sketsa jalur, level yang diizinkan pada Tahap 1 hanya `20kv` (seperti contoh kontrak) dan `unspecified` (netral). Ini pilihan tampilan, **bukan** status energized dan bukan pengakuan tegangan aktual; perlu persetujuan untuk menambah level sebelum Tahap 4. Tidak ada warna hex bebas dalam layout dan tidak ada status pemutus/operasi SCADA.

`GET /api/topology/{id}/data?day=&hour=` mengambil semua parameter yang dirujuk kotak serta variabel ekspresi rule dalam satu SELECT readings, kemudian memakai evaluator Engineering Rules V1.3. `GET /series?day=` menghasilkan 24 slot dengan `null` jika tidak ada reading. `DayState` tanpa baris mengikuti kebijakan lama `draft`. Nilai tersimpan dan formula tidak dimodifikasi.

Penulisan memakai cookie login, CSRF, `require('admin')`, update CAS dengan `expected_version`, snapshot immutable dan audit. Perubahan terpusat pada `main.py` berupa dua import, pendaftaran router, migrasi, serta label versi; `App.tsx` belum diubah. Tahap 2: viewer. Tahap 3: editor. Tahap 4: simbol/garis/kotak lanjutan.

## V1.5.0 Tahap 2 — Viewer Topologi (React/SVG)

```text
frontend/src/features/topology/
  types.ts                 # DTO sesuai schema JSON backend Tahap 1
  topologyApi.ts           # GET saja, memakai transport cookie existing
  TopologyPage.tsx         # orkestra pemilih diagram, jam, fetch, playback
  ViewerToolbar.tsx        # header, pemilih diagram, zoom, refresh
  Canvas.tsx               # SVG read-only; garis, simbol dan kotak terpisah
  symbols.tsx              # simbol netral, tidak ada aksi switching
  ParamBox.tsx             # nilainya dari /data; status hanya dari rule aktif
  TimeBar.tsx              # 00–23 WITA + status hari
  TrendDrawer.tsx          # tren /series 24 jam; connectNulls=false
  viewerFormatting.mjs     # helper murni (zero/null, slot 24 jam)
  viewerFormatting.d.mts   # tipe bagi helper .mjs
  topology.css             # tema gelap terisolasi
frontend/tests/topologyViewer.test.mjs
```

Alur data: sesi login BerauLoad → `GET /api/topology` → detail `/{id}` → pilihan tanggal/jam memanggil `/data` → kotak baca-saja. Klik kotak memanggil `/series?day=` sekali untuk seluruh parameter hari yang dipilih, lalu tren menampilkan 24 slot. Tidak ada cache pembacaan baru atau write endpoint dari Viewer.

Kanvas disimpan sebagai JSON konfigurasi di backend Tahap 1. Viewer menggunakan `foreignObject` di SVG agar kotak HTML mandiri dapat diposisikan pada koordinat kanvas; tidak ada pointer edit sampai Tahap 3. Panel legend/ranking/summary lanjutan tetap bagian Tahap 4. Tidak ada pengubahan struktur DB atau migrasi baru di Tahap 2.


## V1.5.0 Tahap 3 — Visual Editor Topologi

- Domain `topology` masih terpisah dari `dashboard_builder`, memakai model `topology_diagrams` / `topology_revisions` dari Tahap 1; **tidak ada migrasi baru**.
- File baru: `frontend/src/features/topology/{TopologyEditor,EditorCanvas,PropertiesPanel,useTopologyDraft}.tsx/ts` serta `editorState.mjs` dan deklarasi TS. React tidak menggunakan pustaka tambahan; pointer events SVG, snap grid 10.
- `TopologyPage.tsx` hanya mengoordinasikan daftar diagram, Viewer, pemilihan waktu, CRUD diagram kosong, dan pergantian mode. `App.tsx` hanya menyalurkan katalog peralatan serta guard draf untuk navigasi sidebar.
- Draf editor disimpan di memory React. Satu drag menghasilkan satu perubahan riwayat; Undo/Redo tidak menulis database. `PUT /api/topology/{id}` baru dipanggil pada Simpan, memakai `expected_version` dari dokumen terakhir untuk menolak konflik 409. Riwayat versi tersimpan dipulihkan lewat `/restore-version` sebagai versi baru.
- `editorState.mjs` berupa fungsi murni clone JSON, update kotak, aturan koordinat, draf simbol dari master aktif **tanpa wires**, dan pencocokan parameter lintas peralatan hanya jika nama+satuan sama persis (tidak membuat sumber kelistrikan atau rule baru).
- `PropertiesPanel` menerima metric dan asset yang sudah ada di katalog, tanpa query mentah dari UI. Backend Tahap 1 tetap memvalidasi whitelist layout, referensi aktif, kode legacy, batas objek, dan rule aktif.
- Editor tidak mempunyai API tulis `Reading`, `HourRecord`, atau kendali pemutus. Untuk melihat pembacaan kotak baru, simpan lalu muat ulang data jam dari endpoint Tahap 1. NULL ≠ 0.
- Tahap 4 sudah menyediakan simbol/garis manual dan kotak summary/ranking/legend/sparkline. Tidak ada relasi listrik yang disimpulkan dari metadata peralatan.


## V1.5.0 Tahap 4 — Topology Builder Manual

Modul terisolasi `frontend/src/features/topology/` ditambah `Palette.tsx` (8 simbol dan 5 kotak), `SymbolProperties.tsx`, `WireProperties.tsx`, `EditorWires.tsx`, serta helper murni `stage4State.mjs` (geometri & wire) dan `boxView.mjs` (peringkat & mini-tren). `EditorCanvas.tsx` menangani pointer SVG dan drop simbol. Tidak ada dependency UI baru, migrasi database, atau perubahan App.tsx untuk Tahap 4.

Alur edit: hanya admin → palet simbol/kotak → draf React dengan Undo/Redo → periksa validitas → PUT dengan expected_version → revisi immutable dan audit dari backend Tahap 1. Garis dibentuk dari titik yang ditempatkan manual, tanpa auto-connect. Simbol PMT adalah glyph netral, bukan switch interaktif. Penghapusan simbol melepas anchor box tetapi tidak menebak apakah garis independen harus ikut terhapus.

Kotak jenis summary hanya menghitung banyaknya parameter yang memiliki pembacaan per jam dan menampilkan nilai aslinya, bukan nilai teknis turunan. Ranking membandingkan nilai numerik saja setelah whitelist backend memastikan satuan identik. Legend menjelaskan label visual jalur, bukan energisasi. Text memakai judul biasa yang dibatasi panjangnya. Semua status warna khusus Rule aktif menggunakan evaluator Engineering Rules yang sudah ada.

`/api/topology/{id}/data` dan `/series` membaca data mentah dan NULL; setelah penyimpanan layout, klien refetch untuk menampilkan metric yang baru dipilih. Backend `topology/service.py` memperketat validasi level/point/kind/ranking tanpa menambahkan skema maupun rumus listrik.

Batas: output adalah diagram monitoring historis per jam, **bukan SCADA**. Konektivitas visual memerlukan pemeriksaan manusia terhadap Single Line Diagram otoritatif, tidak boleh dibaca sebagai konektivitas terverifikasi otomatis. Contoh level 20kV adalah label garis yang dapat dipilih, bukan status tegangan aktual.

## V1.5.0 Tahap 4.1 — Layout layar dan busbar

- **Panel parameter:** kolom properti lebih lebar, daftar terpilih dan pilihan parameter memiliki scroll terpisah; cari parameter berdasarkan nama atau kode.
- **Layar:** halaman Topologi tidak lagi mengikuti batas lebar dan margin putih aplikasi umum. Mode Lihat dan Editor mengisi tinggi viewport dengan panel waktu WITA tetap ada. Tombol **Layar Fokus** menyembunyikan sidebar sementara; tekan tombol Tampilkan Menu atau Escape untuk kembali.
- **Busbar:** admin dapat menyesuaikan panjang dari panel Properti Simbol (input angka/slider, grid 10 px), dibatasi kanvas dan maksimal 1200 px. Panjang hanya mengubah simbol; garis lain tetap manual.
- **Zoom:** tombol zoom di Editor dan Sesuaikan Lebar di Viewer; tidak mengubah koordinat layout atau pembacaan listrik.
- Tidak ada migrasi baru, perubahan pada readings/hour_records, formula, Engineering Rules, atau koneksi otomatis.

Topologi Viewer (`TopologyPage`, `ViewerToolbar`, `Canvas`) dan Editor (`TopologyEditor`, `SymbolProperties`, `PropertiesPanel`) tetap satu domain `frontend/src/features/topology/`. CSS global hanya mendapat class kondisional `workspace-topology` / `content-topology` dan `topology-focus` pada `App.tsx`; style terisolasi dalam `topology.css`. `stage4State.patchSymbol` memproses `w` hanya untuk busbar, dengan snap dan clamp. Backend validator sudah menerima `w` untuk simbol sesuai batas kanvas.

## V1.5.0 Tahap 4.2 — Visual Group & Dynamic Canvas

`topology_diagrams.layout` tetap menyimpan konfigurasi saja. Struktur baru opsional:

```json
"areas": [{"id":"area-1","x":100,"y":100,"w":500,"h":300,
           "title":"GH Kantor","border":"dashed","color":"blue",
           "opacity":15,"locked":false}]
```

- `service.validate_area()` memeriksa limit 100, ID unik lintas simbol/garis/kotak/area, koordinat dalam canvas 10 px, title teks biasa, warna dan border preset, opasitas 0–40% step 5. Canvas kini 200–20.000 px per sisi; tidak ada perubahan skema PostgreSQL.
- `frontend/src/features/topology/workspaceState.mjs` memuat operasi murni Group Area, expand, resize dan hitungan bounding box. `AreaFrame.tsx`, `AreaProperties.tsx`, `CanvasSettings.tsx` berada di domain Topologi. Objek area dirender di belakang wires/symbols/parameter boxes; tidak memiliki asset_code, metric_codes, atau data.
- Mode Lihat menggunakan `ViewerToolbar.tsx` + `TimeBar.tsx` ringkas; `ParamBox.tsx` memilih satu mini-tren eksplisit, tanpa mengganti data. `TrendDrawer.tsx` mempertahankan modal lama dan memakai `trendCompare.mjs` untuk memeriksa satuan identik sebelum grafik gabungan.
- Nilai berasal dari endpoint read-only `/api/topology/{id}/data` dan `/series`; konfigurasi disimpan lewat PUT dengan CSRF, admin, audit, expected_version 409 dan revisions. NULL bukan nol. Tidak ada koneksi/keadaan PMT yang ditebak.
- Kompatibilitas mundur: Stage 4.2 membaca layout lama tanpa `areas`. Namun **rollback kode ke Stage 4.1 setelah menyimpan layout dengan `areas`** menyebabkan layout baru tidak dapat divalidasi untuk penyimpanan oleh versi lama. Pulihkan revisi topology pra-area saat masih di Stage 4.2 sebelum downgrade, atau gunakan prosedur DB restore terencana; jangan otomatis hapus area.

## V1.6.0 Tahap 5 — Rujukan parameter vertikal dan recalc transaksional

- **Hierarki tetap:** UP3 → ULP → KP. `backend/app/modules/org_units/references.py` menyediakan daftar unit turunan, katalog parameter, validasi owner/descendant, asal nama unit, dan ringkasan status sumber. `unit_context` tetap mengotorisasi hak baca konfigurasi unit yang dipilih; referensi baca hanya dipakai *di dalam* konfigurasi tersebut. Tidak ada perluasan hak KP ke unit induk maupun sesama KP.
- `backend/app/modules/unit_references/`: router `/api/unit-references/metrics`, `/status`, dan `/same-role` bersifat baca-saja; `recalculation.py` memproses dependensi rumus eksplisit menurut `active_plan` dan urutan ancestor KP→ULP→UP3; `models.py` + `migrations.py` menambah `unit_source_changes` untuk audit deferred parent hours.
- **Batas transaksi:** entri dan import melakukan `recalculate(db, day, hour, owner_id, changed_codes)` sebelum commit sumber, pada *Session* SQLAlchemy yang sama. Kegagalan transaksi merollback perubahan pembacaan, hasil formula, dan penanda. Tidak ada worker asynchronous atau penghitungan startup yang mengubah data historis. Mengulang save identik tidak membuat hasil baru bila tidak berubah.
- `HourRecord` tetap slot waktu global per `day+hour` WITA; `Metric.unit_id` tetap menentukan kepemilikan. Formula rujukan melalui **kode parameter global unik**, tidak menyalin `Reading`. UP3 hanya target `computed`, tidak menerima pembacaan input.
- **Pengamanan status:** untuk target ULP/KP tidak berstatus draft, formula target tidak diubah; perubahan sumber dari bawah dicatat satu penanda per `(unit_id, source_unit_id, day, hour)` tanpa memasukkan angka palsu. Ketika admin membuka kembali, penanda jam terulang diperhitungkan dan dibersihkan bersama transaksi perubahan status. Target UP3 dihitung tanpa lock; tidak ada status hari UP3.
- **Null:** formula memiliki daftar operand eksplisit; jika satu operand tidak memiliki `Reading`, hasil disimpan sebagai absen/NULL, tidak dijumlahkan parsial; `Decimal('0')` tetap nilai valid. Completeness mendaftar keterisian operand langsung `n/m` untuk jam tersebut.
- **Status sumber:** API pembacaan/dashboard/topologi/historis/engineering/report/export mengembalikan `source_status={date,counts,units}`, didasarkan pada unit tempat operand berasal (termasuk referensi formula turunan), bukan mengubah status sumber. Verifier/admin ULP melihat `source_changed_after_final` dalam status hari.
- `schema_migrations` mencatat versi skema baru; DDL menggunakan `create(checkfirst=True)`, tanpa DROP/ALTER kolom lama, tanpa pemindahan baris produksi. PostgreSQL 16 dan SQLite menggunakan model SQLAlchemy yang sama. Tes restart berulang menjamin idempotensi.

