## Perbaikan filter Analisa gardu (Stage 9c-fix)

Di **Pengukuran Gardu → Analisa**, syarat angka pada kolom hitung (termasuk kolom kustom) mendukung ≥, ≤, antara, kosong, dan tidak kosong; angka **0 bukan kosong**. Pilih beberapa chip temuan untuk melihat **Salah satu** atau **Semua**, lalu hasil tabel/ringkasan/unduhan menggunakan filter yang sama. Filter disimpan pada URL; daftar temuan dapat muncul berulang sebagai parameter `findings`. Jika operator atau nilai syarat angka belum lengkap, server memberi pesan kesalahan, tidak mengabaikan filter. Ambang kategori/temuan tetap berasal dari pengaturan admin global.

## Analisa gardu — Tahap 9c

Buka **Pengukuran Gardu → Analisa**. Mode **Terakhir** memilih kunjungan terbaru
pada tiap sesi lalu sesi dengan nilai kolom acuan terbesar; bila NULL, sesi itu
berada setelah nilai terisi. Mode **Periode** memilih kunjungan terbaru pada sesi
dalam rentang; mode **Semua** menampilkan satu baris per pengukuran. Gardu aktif
tanpa pengukuran ditandai **Belum diukur**.

Gunakan pencarian, penyulang, unit, status, kategori, temuan atau **Syarat angka**
untuk menyaring. Pencarian aturan berasal dari definisi yang ditetapkan admin.
Klik judul kolom untuk sortir. Kolom hitung kosong ditampilkan `—`, angka nol
tetap `0`, `⚠` menyatakan ada sumber tidak lengkap. `Versi lama` menunjukkan
hasil yang menunggu hitung ulang setelah perubahan definisi.

Pilih **Atur kolom** untuk tampil/sembunyikan dan seret urutan kolom, termasuk
atribut tambahan gardu. **Simpan tampilan** menyimpan filter, kolom dan lebar
di server; admin dapat membagikan tampilan bersama, dan Anda dapat menyimpan
tampilan pribadi bawaan. Filter juga tercantum di URL untuk dibagikan kepada
pengguna lain sesuai hak akses unitnya.

**Unduh Excel** menghasilkan lembar Analisa Gardu dan Keterangan (versi definisi,
filter, rumus, aturan); **CSV** menambahkan baris keterangan di bagian akhir.
Centang baris untuk ekspor terpilih. Pilih nama gardu untuk membaca rincian ukur,
hasil hitung dan histori hingga 40 kunjungan; analisa tidak mengubah data ukur.
Nilai batas dan rumus seed bersifat sementara sampai disahkan pemilik.

## Rumus & Kategori Gardu (Stage 9b)

Buka **Pengukuran Gardu → Rumus & Kategori**. Operator/verifier/management dapat melihat definisi; hanya admin global boleh mengubah. Pilih kolom di kiri, ubah nama/satuan/desimal, pilih `batal` (jika ada satu sumber kosong → NULL) atau `lewati` (agregat mengabaikan sel kosong dan menandai tidak lengkap), dan tulis rumus di tengah. Kode permanen setelah dibuat. Tombol fungsi menyisipkan token, misalnya `SUM_JURUSAN(i_r)`, `AVG_JURUSAN(v_end_rn)`, `IF(fase = 3, ..., ...)`, `FLAG(ground_tr, PUTUS)`, `KOSONG(ground_tr)`, `MIN`, `MAX`, `AVG`, `SUM`, `ROUND`, `ABS`, `AND`, `OR`. Referensi langsung jurusan memakai `_j1`…`_j5`, misalnya `i_r_j1`. `kva`, `fase`, `jumlah_jurusan` adalah snapshot saat kunjungan. `0` sah; kosong dan flag berbeda dari nol. Formula bertingkat tidak boleh memiliki siklus.

Gunakan **Uji** pada pengukuran untuk membandingkan hasil sekarang/draf dan melihat sumber kosong, lalu **Pratinjau dampak** untuk melihat sampel dampak kategori/temuan tanpa menulis. Simpan dengan konfirmasi, kemudian gunakan **Hitung ulang / lanjutkan** untuk memproses hasil turunan per batch. Rekap progres menampilkan `selesai/total`. Hasil versi lama tetap dapat dibaca tetapi diberi tanda menunggu hitung ulang. Pengukuran terverifikasi tidak dapat diedit walau hasil turunannya dihitung ulang.

Aturan kategori dicek menurut urutan dan hanya mengambil kecocokan pertama; jika tidak ada yang cocok hasilnya “Tidak dapat dinilai”. Temuan dapat muncul bersamaan. **Jumlah hari belum diukur** dihitung sewaktu ditampilkan berdasarkan tanggal terakhir, bukan disimpan sebagai hasil hitung. Semua ambang bawaan **sementara**, bukan standar yang sudah disahkan.

## Stage 8 — Pengaturan Branding (hanya admin)

Admin membuka **Pengaturan → Branding**, mengubah nama aplikasi, nama pendek, tagline, teks login, organisasi/footer serta warna utama/aksen. Cek indikator kontras teks putih (minimal 4.5:1) dan pratinjau login/sidebar sebelum menekan **Simpan Branding**. Unggah logo PNG/JPEG/WebP maksimal 512 KB dan 1024 px; favicon PNG/ICO/WebP maksimal 128 KB dan 256 px. Berkas akan diproses ulang menjadi PNG; SVG unggahan tidak diizinkan. Gunakan tombol Hapus untuk kembali ke ikon bawaan dan tombol **Kembalikan semua ke bawaan** dengan konfirmasi untuk reset menyeluruh.

Perubahan langsung terlihat di halaman admin; pengguna lain melihat setelah memuat ulang. Perubahan nama hanya pada tampilan, tidak pada kode internal, data pengukuran, format template Excel/JSON, atau hak akses. Pemilik aplikasi bertanggung jawab atas penggunaan logo resmi organisasi. Browser mungkin memerlukan refresh tab untuk mengganti favicon.

## 1.6.0-stage7-hotfix1 — Pemeriksaan setelah upgrade

Tidak ada perubahan menu atau cara pengisian. Admin/operator tetap memakai Input Beban Harian, manajemen konflik dan autosave seperti Stage 7. Petugas teknis dapat memeriksa `docker compose exec web nginx -t`, `./deploy/smoke-test.sh`, dan menguji kinerja secara terisolasi mengikuti `deploy/loadtest/README.md`. Uji beban **tidak boleh** dijalankan pada aplikasi produksi atau data sungguhan.

## Stage 7 — Pengisian aman

1. Pilih ULP/KP, tanggal dan isi sel seperti biasa. Nilai **0** adalah angka
   nyata; sel kosong bukan nol. Indikator pada setiap jam menunjukkan
   belum disimpan, menyimpan, tersimpan (WITA), gagal, atau konflik.
2. Setelah berhenti mengetik tiga detik atau meninggalkan sel, penyimpanan
   otomatis berlangsung. Tombol **Simpan semua** tetap tersedia.
3. Bila jaringan gagal, jangan tutup tab sebelum memeriksa status; isian
   tersimpan di browser perangkat tersebut. Bila membuka kembali halaman dan
   muncul cadangan, pilih **Pulihkan** atau **Buang**; tidak pernah pulih diam-diam.
4. Bila parameter diubah pengguna lain, bandingkan nilai Anda dan server.
   Pilih **Pakai nilai server** atau **Timpa dengan nilai saya** untuk setiap
   parameter; tidak ada timpa otomatis.
5. Ketika sesi berakhir saat menyimpan, login ulang dengan **akun yang sama**.
   Isian tidak akan terkirim jika login memakai akun berbeda. Hari verified/final
   tidak dapat ditimpa.

## V1.6.0 Stage 6 — Monitoring → Kelengkapan Unit

Pilih unit aktif dari sidebar (UP3 menampilkan seluruh ULP/KP yang dapat dibaca, ULP menampilkan unit sendiri beserta KP; akun KP hanya melihat KP sendiri). Buka **Monitoring → Kelengkapan Unit**. Bawaan 14 hari, maksimal 62 hari termasuk kedua tanggal. Tiap sel `jam terisi/jam diharapkan` dengan `D` (Draf), `V` (Verified), atau `F` (Final). `system.load` menghitung jam yang mempunyai nilai beban sistem termasuk 0; jika peran belum ditetapkan, minimal satu input aktif per jam dihitung. Jam belum dimulai dan hari masa depan tidak diharapkan; jam yang saat ini sedang berlangsung WITA sudah diharapkan. Pilih sel untuk membuka **Input Beban Harian** pada unit/tanggal itu; pengguna management mendapat mode **Hanya lihat**. Tombol **Ekspor XLSX** menyimpan matriks dan sheet ringkasan/dasar.

### Topologi → Telusur Diagram

Admin dapat memilih simbol dalam editor dan menambah **Tautan ke diagram unit bawah**, pilih unit dan diagram tujuan, kemudian Simpan Perubahan. Ini **navigasi saja**, bukan sambungan listrik. Viewer menunjukkan ikon ↗ pada simbol bertautan apabila pembaca berhak melihat diagram tujuan. Klik untuk membuka diagram pada tanggal/jam yang sama; gunakan breadcrumb untuk kembali. Pada unit UP3, daftar diagram unit bawahan tersedia tanpa digambar otomatis. Jika diagram tujuan diarsipkan, ikon tidak muncul, dan restore versi lama dengan tautan itu ditolak sampai target valid.

## V1.6.0 Stage 5 Hotfix 1 — Import template untuk KP/ULP

Di unit KP atau ULP, buka **Import Excel → Template BerauLoad**, unduh dan isi jam yang diperlukan, lalu lakukan **Pratinjau → Commit**. Nilai yang berhasil ditulis akan memicu perhitungan formula eksplisit di unit atas secara otomatis pada jam tersebut; tidak perlu menginput ulang di ULP/UP3. Satu operand kosong membuat rekap NULL (bukan jumlah parsial), sedangkan angka 0 dihitung. Jika hari ULP sudah verified/final, rekapan ULP tidak ditimpa, melainkan ditandai ada sumber berubah; verifier/admin dapat memeriksa penanda sesuai alur Stage 5. Hari target KP/ULP yang bukan draft tetap dilewati oleh import. Perubahan ini tidak mengubah cara mengisi template atau hak akses.

## Pengaturan → Pengguna (V1.6.0 Stage 4c UI Hotfix 1)

Admin membuat pengguna melalui **Jenis akun** untuk memilih Role akun. Jika memilih Admin, keterangan **Admin berlaku untuk semua unit** muncul dan bagian Akses unit tidak ditampilkan. Jika memilih Operator, Verifier, atau Manajemen, pada bagian **Akses unit** centang minimal satu unit dan tentukan **Peran di [nama unit]** pada tiap unit terpilih. Unit UP3 hanya menerima peran Manajemen untuk akun non-admin. Tanpa unit terpilih, form memberi pesan validasi dan tidak mengirim permintaan.

**Daftar Pengguna** memiliki kolom **Akses unit** yang menampilkan setiap nama unit dan perannya (contoh: `ULP Tanjung Redeb: operator · KP Sambaliung: verifier`). Akun admin ditampilkan sebagai **Semua unit (admin global)**. Pengubahan/cabut akses tetap dilakukan melalui **Pengaturan → Struktur Organisasi**, sesuai fitur sebelumnya.

## Penggunaan multi-unit — V1.6.0 Stage 4c (kandidat staging)

Setelah masuk, pilih unit pada dropdown **Unit aktif** di sidebar. Struktur UP3 → ULP → KP berisi hanya unit yang berhak dibaca pengguna. Pilihan tersimpan pada browser per ID pengguna; bila hak berubah atau unit dinonaktifkan, aplikasi memilih unit yang masih valid. Ganti unit untuk memuat katalog/halaman baru.

- **Admin global:** pilih ULP/KP untuk mengisi, memverifikasi, atau memfinalkan. Admin dapat menggunakan menu Pengaturan → Struktur Organisasi dan Salin Pengaturan untuk memulai unit kosong. Di ULP/KP muncul penanda bahwa admin UP3 sedang bertindak pada unit itu.
- **Operator/verifier ULP:** isi dan periksa data ULP/KP sesuai penugasan. Pada Input Beban Harian ULP tersedia tombol *Verifikasi ULP beserta KP* / *Finalkan ULP beserta KP*. Pratinjau memperlihatkan unit yang akan diproses/dilewati sebelum konfirmasi; status hasil juga ditampilkan setelah aksi. KP tanpa data dilewati, bukan dianggap bernilai nol.
- **Management/hanya lihat:** penanda *Hanya lihat*; operasi simpan data yang didukung UI disembunyikan/dinonaktifkan. Penegakan hak tetap di backend. Saat memilih UP3, menu input dan import tidak ditampilkan.
- **Admin pengguna:** Pengaturan → Pengguna → pembuatan akun wajib pilih setidaknya satu unit dan perannya. Hak tambahan atau pencabutan dapat dilakukan pada Struktur Organisasi → Akses Pengguna.
- **Parameter utama:** jika `system.load` atau `system.capacity` tidak terkonfigurasi, lihat notifikasi menuju Pengaturan → Parameter utama unit. Unit baru yang belum memiliki peralatan/katalog tidak otomatis dianggap mempunyai data 0.

**Peringatan:** source Stage 4c masih kandidat staging; build Vite dan verifikasi browser produksi belum lulus. Ikuti README_UPGRADE sebelum menggunakan pada data nyata.

## Tahap 4b — Mengelola konfigurasi ULP/KP (tanpa pemilih unit UI)

Sampai pemilih unit antarmuka selesai pada Tahap 4c, admin mengatur unit tujuan melalui `X-Unit-Id` pada permintaan API yang terautentikasi. Tanpa header, admin berada pada ULP Tanjung Redeb; pengguna lain memakai unit bawaan menurut hierarki 4a. Pada unit baru, Form Input berisi lima tab bawaan yang belum memiliki parameter. Tidak ada pembacaan maupun peralatan yang dibuat otomatis.

Untuk menyalin pengaturan dari ULP Tanjung Redeb ke unit baru, lakukan **pratinjau** `POST /api/org-units/{id_tujuan}/copy-settings/preview` dengan JSON `{"source_unit_id": <ID sumber>, "include_topology": false}`. Periksa `assets`, `metrics`, `tabs`, dan `counts`; lalu kirim body identik ke `.../commit` hanya jika tidak ada bentrok. Pilih `include_topology:true` hanya bila diagram tidak membutuhkan Engineering Rule sumber yang tidak turut disalin. Kode legacy seperti `pltu_lati_cb33_kw` yang disalin ke `ulp_malinau` menjadi `ulp_malinau_pltu_lati_cb33_kw`; kode asli tidak berubah.

**Kewajiban:** login sebagai admin global dan gunakan CSRF untuk POST. Konfigurasi tujuan harus kosong (selain tab default). Jika commit gagal, transaksi batal total; tidak ada pemindahan pembacaan, status hari, atau batch import. Akun non-admin hanya bisa melihat konfigurasi unit yang boleh dibaca. UP3 boleh dashboard/topologi dan metric computed; tidak menerima Form Input. Pemilihan unit di UI akan dibuat pada 4c.

## V1.6.0 Stage 4a — Operasional per Unit (backend saja)

**Tidak ada pemilih unit pada antarmuka hingga 4c.** Pengguna yang sedang mengoperasikan ULP Tanjung Redeb tanpa header masih memakai BerauLoad dengan alur biasa. Untuk menguji ULP atau KP lain, pakai klien HTTP yang mempertahankan cookie login dan token CSRF, lalu tambahkan header `X-Unit-Id: <ID unit>` pada request terkait. ID unit dapat dilihat dari `GET /api/org-units` sesuai izin baca. Jangan menempelkan token, cookie, atau kata sandi ke laporan.

- Pengguna UP3 dengan role management: membaca data unit di bawahnya, tidak bisa mengubah konfigurasi atau mengisi/menyetujui data.
- Operator ULP: mengisi jam untuk ULP dan KP yang menjadi bawahannya; verifier ULP: memverifikasi/finalisasi harian ULP dan KP. Pengguna KP hanya mengakses KP sendiri. Admin global dapat mengisi/memverifikasi/finalisasi/membuka kembali di unit mana pun dengan audit aktor+unit; ketika memilih UP3 ia harus berpindah ke ULP/KP untuk input.
- Status ULP/KP berasal dari unit_day_states. Proses `verify-tree` / `finalize-tree` pada ULP menuntut setiap unit memenuhi syarat; semua perubahan batal jika satu unit gagal.
- Import laporan lama hanya untuk ULP Tanjung Redeb. Template BerauLoad dapat memakai unit operasional lain. `HourRecord` adalah slot jam global tetapi setiap peralatan dan parameter milik unitnya masing-masing.
- Konfigurasi lama untuk unit non-home belum tersedia sampai 4b, sedangkan UI pemilih unit serta pengaturan akun multiunit akan hadir pada 4c. Jangan melakukan input produksi di unit baru sebelum fitur terkait teruji di staging.

# Panduan V1.6.0 Tahap 3 — Parameter Utama Unit

**Admin:** buka **Pengaturan → Parameter utama unit**, pilih *Beban Sistem (`system.load`)* dan *Daya Mampu (`system.capacity`)* dari parameter aktif ULP Tanjung Redeb, kemudian **Simpan Parameter Utama**. Kode parameter tidak berubah, yang diperbarui hanya kunci peran. Tidak boleh memilih parameter sama untuk keduanya. Secara default kedua peran tetap merujuk kode H dan J yang lama sehingga angka monitoring harus identik.

**Pengguna:** Dashboard, Perbandingan Kapasitas vs Beban, Analytics, Compare, laporan standar dan preset baru memakai pilihan peran tersebut. Bila belum dikonfigurasi, sistem menampilkan **Parameter utama belum diatur** alih-alih nol palsu atau error; admin dapat membukanya dari Pengaturan. Konfigurasi dashboard/formula yang sudah disimpan secara eksplisit tidak diubah otomatis. Tidak ada pembatasan unit yang aktif atau pemilih unit baru pada tahap ini.

**Sebelum nonaktif parameter:** buka Pengaturan → Parameter → Ubah. Jika parameter masih dipakai dalam Dashboard, Topologi, Formula, Historical, Engineering Rules, template laporan/export, atau Form Input, aplikasi meminta konfirmasi disertai daftar penggunaan. Penonaktifan berdampak pada hasil bawaan yang menggunakan peran tersebut; telaah daftar dahulu. Endpoint penggunaan dapat dibaca oleh pengguna yang login (`GET /api/metrics/{id}/usage`), perubahan hanya admin dan wajib CSRF. **Tidak ada penghapusan data historis.**

**Topologi:** tombol “Terapkan ke Peralatan Sejenis” kini mencocokkan parameter target berdasarkan kunci peran pada unit dan jenis asset yang sama bila tersedia; bila role tidak terisi, pencocokan lama *nama+satuan persis* tetap digunakan. Tidak ada koneksi listrik otomatis.

Lihat `README_UPGRADE_V1_6_0_STAGE3.md` dan `QA_STATUS.md` untuk prosedur instalasi serta uji kesetaraan hasil setelah upgrade. Status paket ini **kandidat staging**, tidak dinyatakan sudah berjalan di LXC Anda.

---

# Panduan Import Template BerauLoad — V1.6.0 Stage 2

1. Buka **Import Excel → Template BerauLoad**. Perhatikan unit tujuan otomatis **ULP Tanjung Redeb** hingga tahap pemilih unit tersedia.
2. Pilih tanggal mulai dan selesai (maks. 92 hari inklusif), centang tab Form Input yang ingin diisi, lalu klik **Unduh .xlsx**. Template berisi Petunjuk, satu sheet per tab aktif terpilih, dan `_meta` tersembunyi.
3. Isi hanya sel kuning mulai **C4**. Kolom A tanggal WITA (`YYYY-MM-DD`), kolom B jam 0–23. Baris 1 nama, baris 2 satuan, baris 3 kode parameter. Nama boleh diganti, kode wajib tetap sesuai konfigurasi. Jangan masukkan rumus Excel. **Kosong** berarti tidak ada pembacaan; angka **0** adalah pengukuran sah.
4. Simpan XLSX, unggah melalui tombol file, pilih mode **Isi sel yang masih kosong (`fill_empty`, bawaan)** atau **Hanya jam baru (`new_hours`)**, klik **Periksa File**.
5. Periksa angka akan disisipkan, sama, berbeda, terkunci, jam dilewati, tabel per-parameter, dan perbedaan maksimal 200. Kesalahan file tampil dengan nama sheet/alamat sel dan membatalkan keseluruhan file.
6. Klik **Konfirmasi Import**. Tidak ada timpa. Pembacaan existing, hari verified/final, termasuk computed historis tidak pernah diganti. Berkas identik SHA256 untuk unit yang sama ditolak HTTP 409. Hasil baru ditandai sumber `template_import` dan tercatat dalam audit.
7. Buka **Riwayat Import (Semua Jenis)** untuk melihat apakah batch berupa `Template BerauLoad` atau `Laporan lama`. Tab **Laporan lama** tetap mendukung impor arsip laporan bulanan seperti sebelum upgrade.

**Perhatian:** Import Template tidak memiliki fungsi membuka hari terkunci ataupun memaksa overwrite. Untuk koreksi data yang sudah tercatat, gunakan prosedur resmi lama. Import Template adalah **data historis per jam**, bukan pembacaan real-time atau SCADA.

---

# Tambahan Panduan V1.6.0 Tahap 1.2 — Startup Aman

Tidak ada tombol, menu, atau prosedur input baru pada versi ini. Pengaturan → Struktur Organisasi tetap menampilkan UP3 Berau dan ULP Tanjung Redeb serta unit tambahan yang sudah dibuat. Setelah upgrade, restart tidak lagi memindahkan parameter computed yang sengaja ditempatkan di UP3, tidak memindahkan akses pengguna ke ULP asal, dan tidak menambahkan akses baru untuk pengguna yang hanya bertugas di ULP lain.

Admin sebaiknya memeriksa `schema_migrations`, jumlah data, dan beberapa penugasan akses sebelum dan setelah restart menggunakan `README_UPGRADE_V1_6_0_STAGE1_2.md`. Grafik H/J, Topologi, input, laporan, dan aturan izin lama tidak berubah. Tidak ada pemilih unit pada tahap ini.

---

# Tambahan Panduan V1.6.0 Tahap 1.1

Pada **Pengaturan → Struktur Organisasi**, setelah upgrade admin melihat UP3 Berau dengan satu anak bawaan **ULP Tanjung Redeb** (`ulp_tanjung_redeb`, ditandai sebagai asal data lama). Seluruh peralatan, parameter, arsip import, dan cermin status harian existing dianggap milik ULP Tanjung Redeb; admin tidak perlu menginput atau mengimpor ulang data. UP3 menjadi induk administrasi, bukan pemilik pengukuran lama. Data kerja, Dashboard, Laporan, dan Topologi seharusnya sama dengan sebelum upgrade.

Akun admin global tetap terhubung ke UP3. User operator/verifier/management lama terhubung ke ULP Tanjung Redeb dengan role global yang sama. Hak akses operasional **belum** dibatasi berdasarkan unit; Pengaturan hanya menyimpan penugasan untuk tahap berikut. Membuat asset/metric/formula/input/import baru lewat UI lama tetap memakai ULP Tanjung Redeb secara otomatis. Tidak ada pemilih unit pada tahap ini.

Sebelum penggunaan, verifikasi proses backup dan lakukan smoke test serta query kepemilikan sesuai `README_UPGRADE_V1_6_0_STAGE1_1.md`.

---

# BerauLoad V1.6.0 Tahap 1 — Panduan Struktur Organisasi

Admin: buka **Pengaturan → Struktur Organisasi**. Awalnya hanya ada **UP3 Berau** (`up3_berau`) dan data/akun lama tetap berfungsi seperti biasa. Gunakan **+ ULP** pada UP3 untuk membuat ULP berdasarkan identitas resmi; setelah ULP dibuat, gunakan **+ KP** pada ULP yang tepat. Tidak ada KP langsung di bawah UP3.

Kode unit hanya bisa ditetapkan saat membuat dan tidak bisa diubah. Nama, urutan dan status aktif bisa diedit. UP3 tidak bisa dinonaktifkan; unit yang memiliki anak aktif tidak bisa dinonaktifkan. Tidak ada tombol hapus permanen. Gunakan kolom kanan untuk mengelola akses per unit; UP3 tetap mencerminkan role global pengguna lama. Perubahan hak unit baru **belum membatasi menu, data atau kewenangan operasional pada tahap ini**.

Admin juga bisa membuka **Pengaturan → Parameter → Ubah** dan mengisi **Kunci peran** opsional, misalnya `system.load` atau `feeder.arus_r`, dengan pola huruf kecil/titik/underscore. Key harus unik dalam satu unit dan belum digunakan mesin analisis. Dua key awal sistem sudah terisi untuk beban sistem (REKAP J) dan daya mampu sistem (REKAP H).

Operator, verifikator dan manajemen: tetap gunakan seluruh halaman, angka, input dan persetujuan sesuai role global sebelumnya. Tidak ada filter UP3/ULP/KP yang diterapkan pada tahap ini. `day_states` lama tetap sumber tampilan status draft/verified/final.


---

# Panduan Pengguna BerauLoad V1.4.2

# Tambahan Panduan Pengguna — V1.4.1

## Dashboard utama
Buka **Dashboard** untuk melihat panel dashboard default. Jika mempunyai default pribadi, dashboard tersebut yang ditampilkan; jika tidak, dashboard default sistem milik admin. Klik **Kelola Dashboard** untuk membuka editor. Gunakan **Tampilan Klasik** bila ingin melihat dashboard bawaan V1.0–V1.4.0.

## Mode edit Dashboard Builder
Klik **Edit Layout**. Atur nama, deskripsi, panel, ukuran, dan urutan. Klik **Simpan Perubahan** untuk menyimpan; klik **Batal** untuk mengembalikan seluruh draft, atau **Reset ke Tersimpan** untuk membuang edit dan tetap berada di mode edit. Keluar halaman ketika ada perubahan yang belum disimpan akan meminta konfirmasi. Semua ini hanya mengubah konfigurasi dashboard, tidak pernah menghapus data beban.

## Daftar yang semakin banyak
**Perhitungan Historis:** default hanya Aktif, gunakan Arsip/Semua untuk mencari formula lama. **Engineering Rules:** Aktif, Draft, Arsip, atau Semua. **Master Peralatan** dan **Parameter:** Aktif, Nonaktif, atau Semua. Semua daftar dapat dicari menggunakan nama/kode dan dibagi per 20 entri.

## Master Jenis Peralatan
Admin membuka **Pengaturan → Jenis Peralatan** lalu memilih **Tambah Jenis**. Isi nama dan kode unik. Kode hanya dapat ditentukan saat pertama dibuat. Untuk perubahan nama atau status, pilih **Ubah**. Kategori yang nonaktif tidak muncul untuk pembuatan peralatan baru; peralatan lama tetap mengacu kode historis. Tidak tersedia hapus permanen untuk menjaga integritas data.

---

# Panduan Pengguna BerauLoad V1.4.0

**Sistem Monitoring & Analisis Beban Kelistrikan Berau**  
Untuk operator, verifier/pengawas, admin, dan manajemen.  
Zona waktu operasional: **WITA (Asia/Makassar)**.  
Dokumen ini menjelaskan kemampuan yang tersedia pada paket source V1.4.0 dan batasan yang perlu diperhatikan.

> **Penting:** BerauLoad merupakan aplikasi pencatatan dan analisis historis, bukan sistem SCADA, alat ukur real-time, atau perangkat kendali pembangkit/jaringan. Semua keputusan operasi tetap mengikuti prosedur dan kewenangan PLN yang berlaku.

## Daftar isi

1. Memulai dan masuk aplikasi
2. Hak akses dan peran pengguna
3. Memahami struktur data dan parameter
4. Input Beban Harian
5. Verifikasi, Finalisasi dan Reopen
6. Import Excel laporan bulanan lama
7. Dashboard Operasi Berau
8. Grafik Daya Mampu vs Beban Sistem
9. Dashboard Builder V1.4
10. Formula Engine V1.1
11. Analisis Data Historis dan Perhitungan Historis V1.2
12. Engineering Rules V1.3
13. Monitoring Pembangkit/Feeder
14. Laporan dan ekspor data
15. Pengaturan Master Peralatan/Parameter/Pengguna
16. Backup, upgrade, troubleshooting (admin)
17. FAQ, batasan, glosarium

---

## 1. Memulai dan masuk aplikasi

1. Buka browser Chrome/Edge/Firefox melalui jaringan internal yang diperbolehkan.
2. Masukkan alamat `http://IP-LXC:8092`, mengganti `IP-LXC` dengan alamat aktual server. Bila organisasi menyediakan HTTPS dan domain internal, gunakan alamat HTTPS tersebut.
3. Masukkan username dan password yang diberikan admin. Setelah berhasil, halaman Dashboard tampil.
4. Sidebar menampilkan menu berdasarkan fungsi operasional: Dashboard, Dashboard Builder, Input Beban Harian, Data Historis, Analisis Beban, Pembangkit, Monitoring Feeder, Laporan & Perbandingan, Import Excel, Pengaturan, dan Panduan Pengguna.
5. Tekan tombol **Keluar** setelah bekerja, terutama pada komputer bersama. Jangan membagikan akun pribadi.

**Jika gagal login:** periksa huruf besar/kecil, jaringan, dan status akun. Hubungi admin; jangan mengirim password melalui chat atau screenshot.

## 2. Peran pengguna

| Peran | Tugas utama | Batasan |
|---|---|---|
| Operator | Input data draft, import sesuai hak akses, melihat laporan | Tidak memfinalisasi atau mengubah master kritis tanpa izin |
| Verifier | Pemeriksaan, verifikasi/finalisasi, koreksi sesuai alur | Tidak dapat mengubah data final tanpa mekanisme reopen yang sah |
| Management | Melihat dashboard, analisis, grafik, dan laporan | Tidak mengubah data pencatatan/aturan |
| Admin | Kelola akun, master, formula, Engineering Rules, dashboard sistem | Harus menjaga audit, backup dan hak akses |

Semua peran dapat membuat **Dashboard Pribadi** di V1.4. Hanya admin yang dapat membuat/mengedit **Dashboard Sistem**. Penerapan pembatasan akses dilakukan di backend.

## 3. Data dan parameter yang dipakai

BerauLoad menyimpan **tanggal, jam, kode titik ukur, nilai, sumber data, serta audit perubahan**; tidak lagi membuat satu database baru setiap bulan. Seluruh data dapat dianalisis untuk periode harian, bulanan, atau tahunan.

- **Input:** nilai pengukuran yang dicatat operator atau dari file Excel yang diproses.
- **Computed:** nilai yang dihitung dari parameter lain menggunakan Formula Engine. Perhitungan bawaan V1 mengikuti rumus pada template yang disepakati.
- **Imported:** menunjukkan asal data tertentu pada versi lama; secara konseptual sebaiknya dibedakan dari jenis parameter.
- **Kosong** bukan angka **0**. Parameter tanpa pembacaan tidak dipaksakan menjadi nol, terutama pada analisis beban dan kualitas data.
- Nilai daya harus dibaca berdasarkan **satuan**: kW, MW, kVA, A, Hz, kV, dan sebagainya. Jangan menjumlahkan parameter beda satuan.

**Pemetaan resmi grafik utama:** pada sheet rekap laporan, **kolom H = Daya Pasok Pembangkit = Daya Mampu Sistem** (`daya_pasok_pembangkit_kw`), sedangkan **kolom J = Beban Sistem** (`beban_sistem_kw`). Parameter `daya_mampu_sistem_kw` dari V1.1 merupakan legacy dan **bukan** sumber grafik utama.

## 4. Input Beban Harian

1. Pilih menu **Input Beban Harian**.
2. Pilih tanggal. Periode ditafsirkan menurut **WITA**.
3. Pilih kelompok: **Pembangkit**, **Frekuensi & Tegangan**, **Feeder**, **Rekap Sistem**, atau **Rekap Tambahan**.
4. Di tabel 24 jam, isikan hanya parameter bertipe Input yang benar-benar diketahui pada jam tersebut. Gunakan angka nol hanya jika pengukuran memang nol.
5. Periksa kembali nilai desimal dan satuan. Jangan menyalin nilai perkiraan tanpa sumber.
6. Klik **Simpan Perubahan**. Periksa hasil computed pada jam tersebut dan peringatan perhitungan apabila muncul.
7. Jika terjadi koreksi, ulangi pada jam yang masih berstatus draft. Semua perubahan penting tercatat pada audit.

**Contoh kerja:** pada tanggal 4 November, operator menginput data pukul 19.00, lalu memeriksa nilai **Daya Mampu** dan **Beban Sistem** di tab Rekap. Jika jam 20.00 belum diukur, biarkan kosong.

## 5. Verifikasi, Finalisasi, Reopen

Urutan umum: **Draft → Verified → Final**.

1. Operator memastikan kelengkapan dan keakuratan data draft.
2. Verifier membuka hari terkait dan memilih **Verifikasi**, lalu mengisi alasan/catatan.
3. Setelah pemeriksaan final, verifier/admin melakukan **Finalisasi** dengan catatan.
4. Hari verified/final dikunci untuk penyuntingan biasa maupun import yang bertentangan.
5. Jika perlu koreksi atas hari yang telah dikunci, admin melakukan **Reopen** dengan alasan audit, perbaikan dicatat, kemudian dilakukan verifikasi/finalisasi ulang sesuai prosedur.

Finalisasi tidak berarti sistem otomatis memvalidasi semua interpretasi teknis; pemeriksaan manusia tetap wajib.

## 6. Import Excel historis

Cocok untuk arsip lama yang biasanya dibuat dengan menyalin workbook laporan beban dari bulan sebelumnya.

1. Siapkan file `.xlsx` sumber asli. Pastikan periode bulan dan tahun benar.
2. Buka **Import Excel**, pilih file (bisa beberapa bila UI mendukung pemrosesan massal), serta pilih/deteksi periodenya.
3. Klik **Pratinjau**. Periksa **jam terbaca, nilai terdeteksi, konflik, file duplikat, dan peringatan**.
4. Bandingkan beberapa sampel penting dengan Excel, terutama **REKAP kolom H dan J**, puncak beban, dan hari yang tidak lengkap.
5. Jika hasil pratinjau benar, lakukan **Commit**. Simpan catatan dan arsip file sumber.
6. Periksa Dashboard dan Data Historis pada bulan yang baru dimasukkan.

**Menghindari kesalahan:** sheet 31 pada bulan 30 hari tidak boleh dihitung; sel formula dengan hasil kosong/0 tidak otomatis berarti pengukuran; import berulang tidak boleh membuat jam/parameter duplikat; konflik dengan data yang sudah final harus ditolak atau diperiksa manual.

## 7. Dashboard Operasi

Menu **Dashboard** adalah ringkasan standar: puncak beban, rata-rata, jam terisi, cakupan data, grafik H/J, kurva harian, serta rekap tabel.

- Pilih tahun/bulan di bagian atas untuk mengganti periode.
- Perhatikan **kelengkapan data** sebelum menyimpulkan rata-rata, puncak, atau pertumbuhan.
- Klik tanggal pada rekap harian untuk melihat data input terkait.
- Grafik dan status memakai **pencatatan yang tersimpan**, bukan data streaming live dari perangkat jaringan.

## 8. Grafik Daya Mampu vs Beban Sistem

- **Daya Mampu Sistem** berasal dari kolom H REKAP (`daya_pasok_pembangkit_kw`).
- **Beban Sistem** berasal dari kolom J REKAP (`beban_sistem_kw`).
- Kedua nilai dibandingkan pada **jam berpasangan** agar tidak mencampurkan populasi pembacaan berbeda.
- Jam tanpa daya mampu atau beban yang diperlukan tetap kosong; sistem tidak membuat nilai sintetis.
- Pada grafik konfigurabel, kedua seri bersama hanya menggunakan **rata-rata jam berpasangan**. Puncak, minimum, dan metode lain harus ditampilkan pada panel terpisah atau sesuai aturan agregasi terdefinisi.

**Contoh indikator matematis:** `Cadangan Daya (kW) = Daya Mampu (kW) − Beban Sistem (kW)`. Nilai positif/negatif bukan keputusan operasi final tanpa standar yang ditetapkan.

## 9. Dashboard Builder V1.4.0

Fitur **Dashboard Builder** memberikan tampilan seperti Grafana-lite tanpa SQL/Python.

### A. Membuat dashboard pribadi

1. Buka **Dashboard Builder**.
2. Klik **Dashboard Baru**, isi nama mis. `Monitoring Beban Harian Saya`.
3. Pilih **Pribadi**, lalu **Buat**.
4. Klik **Edit Layout** dan **Tambah Panel**.
5. Isi judul, sumber data, jenis grafik, parameter, dan lebar/tinggi panel.
6. Ulangi untuk panel lain, atur urutan dengan **drag-and-drop** di desktop atau **tombol panah** di header panel.
7. Pilih lebar `1/3`, `1/2`, `2/3`, atau **Penuh** melalui pemilih pada header panel.
8. Klik **Simpan Perubahan**. Jika muncul konflik versi, muat ulang dashboard; perubahan pengguna lain tidak akan ditimpa diam-diam.
9. Klik **Jadikan Default** untuk menjadikan dashboard pribadi sebagai pilihan awal di Dashboard Builder.

### B. Sumber data panel

| Sumber | Pilihan panel | Arti |
|---|---|---|
| Parameter Pengukuran / Computed | Garis, Area, Batang, KPI, Gauge, Tabel | Pengukuran asli dan computed dari Parameter Manager |
| Perhitungan Historis V1.2 | Garis, Area, Batang, KPI, Tabel | Evaluasi formula historis yang sudah disimpan |
| Engineering Rules V1.3 | Status | Jumlah jam normal/waspada/kritis berdasarkan aturan **aktif** |

**Jenis grafik:** untuk multi-seri parameter, maksimal 4 seri dan **satuan harus sama**. KPI/Gauge memakai satu parameter. Gauge non-persen menggunakan maksimum teramati hanya sebagai skala visual, **bukan batas aman teknis**. Grafik H/J ditampilkan berdasarkan pasangan jam dan metode AVG, tidak boleh digabung dengan parameter ketiga dalam panel tersebut.

### C. Periode dan resolusi

Di toolbar Dashboard Builder, pilih **Hari Ini (24 Jam)**, **Bulan Ini**, **Tahun Ini**, atau **Rentang Khusus**.

- `Hari Ini` → resolusi per jam.
- `Bulan Ini` → resolusi harian.
- `Tahun Ini` → resolusi bulanan.
- `Kustom` → pilih tanggal mulai/akhir dan resolusi jam/hari/bulan/tahun.
- Resolusi jam dibatasi maksimal 31 hari; resolusi harian mengikuti batas API; evaluasi Engineering Rules maksimal 366 hari per permintaan.
- Jika sumber formula historis memiliki resolusi sendiri, hasilnya mengikuti definisi historis yang tersimpan, bukan selalu filter tampilan umum.

### D. Sistem vs pribadi

- **Dashboard Sistem:** dibuat admin dan dapat dibuka seluruh pengguna yang memiliki akses BerauLoad.
- **Dashboard Pribadi:** hanya terlihat oleh pembuat, dapat diduplikasi dari dashboard sistem.
- **Default Sistem:** acuan bila pengguna belum memilih default pribadi.
- **Default Pribadi:** dipakai lebih dulu pada pembukaan Dashboard Builder bagi pembuatnya.

**Penghapusan:** tombol Hapus pada suatu **panel** hanya menghapusnya dari layout setelah disimpan, bukan menghapus data. Tombol **Arsipkan** pada dashboard menyembunyikan dashboard dari daftar aktif; histori pengukuran, formula, dan peralatan tetap aman. V1.4.0 belum menyediakan pemulihan dashboard terarsip melalui UI: minta bantuan admin dan lakukan melalui prosedur perubahan terkontrol, bukan mengubah DB manual.

### E. Pengendalian versi layout

Simpan dengan tombol **Simpan Perubahan**. Backend memakai `expected_version` untuk mencegah penimpaan bila dashboard sudah diubah pada sesi lain. Hindari menutup halaman ketika masih muncul tanda perubahan belum disimpan.

## 10. Formula Engine V1.1

Pengaturan → Parameter → Tambah → **Computed** membuka editor formula yang menggunakan evaluator server yang sama dengan V1.1.

1. Beri nama dan kode parameter hasil, pilih satuan dan kelompok.
2. Pilih parameter input/computed yang tersedia.
3. Susun operasi tambah, kurang, kali, bagi, serta fungsi terdukung seperti `SUM`, `AVG`, `MIN`, `MAX`, `IF`.
4. Klik **Simulasi/Uji**, amati hasil dan peringatan.
5. Simpan jika benar. Periksa dampaknya pada perhitungan bertingkat.

Contoh (bergantung izin satuan/jenis parameter): `daya_pasok_pembangkit_kw - beban_sistem_kw` dapat memberi **Cadangan Daya kW**.

Pengaman: referensi melingkar, nilai hilang, pembagian nol, dan mismatch satuan tidak boleh dianggap valid. Jangan membuat rumus untuk meniru data pembacaan yang seharusnya dicatat langsung.

## 11. Analisis Beban & Perhitungan Historis V1.2

### Analisis Beban

1. Buka **Analisis Beban** dan pilih parameter.
2. Pilih periode (mulai/sampai), resolusi (jam/hari/bulan/tahun), lalu amati kurva dan tabel.
3. Untuk pembangkit atau penyulang, gunakan menu **Pembangkit** / **Monitoring Feeder** sebagai filter parameter.
4. Pertimbangkan coverage dan durasi data kosong.

### Perhitungan Historis

1. Buka tab **Perhitungan Historis**.
2. Pilih preset atau buat definisi baru, isi nama/kode/ekspresi, agregasi, resolusi, mode (`period`, `moving_avg`, `yoy`), dan pembatasan jam jika perlu.
3. **Uji/Preview**, lalu simpan melalui hak admin.
4. Jika rumus salah, klik **Edit/Revisi** dan masukkan alasan. Server menyimpan **versi baru**, tidak menimpa versi lama.
5. Buka **Riwayat Versi** untuk menghitung ulang versi tertentu. Gunakan **Arsipkan/Pulihkan** untuk menyembunyikan/mengembalikan definisi.

**Interpretasi penting:** YoY memerlukan periode pembanding; data yang hanya tersedia sebagian harus ditandai parsial. SUM dalam engine historis dibatasi pada indikator tanpa dimensi karena penjumlahan kW antarjam bukan otomatis energi kWh.

## 12. Engineering Rules V1.3

1. Buka **Analisis Beban → Engineering Rules**.
2. Admin memilih **Tambah Rule**, memberi nama, formula, arah batas (`below` atau `above`), batas waspada, batas kritis, tanggal berlaku, dan **dasar ketentuan**.
3. Klik **Simulasi** menggunakan nilai contoh, lalu **Simpan sebagai Draft**.
4. Setelah diverifikasi sesuai ketentuan teknis, gunakan **Aktifkan** dengan alasan.
5. Evaluasi histori berdasarkan rentang waktu yang mendukung perhitungan; hasil menampilkan jam normal/waspada/kritis, missing/invalid, serta contoh kejadian abnormal.
6. Untuk koreksi formula/batas, gunakan **Edit/Revisi**. Revisi kembali menjadi draft; perlu uji dan aktivasi baru. Untuk menonaktifkan aturan, pilih **Arsipkan**.

**Tidak ada standar ambang operasi yang dihardcode.** Rumus/ambang pada contoh pelatihan tidak otomatis menjadi aturan resmi. Kategori dari UI adalah **advisory** dan tidak mengoperasikan perangkat.

## 13. Monitoring Pembangkit dan Feeder

- **Pembangkit:** filter dan analisis parameter output unit dan total sesuai data/rumus yang tersedia.
- **Monitoring Feeder:** lihat arus fasa R/S/T dan perubahannya; periksa kesesuaian satuan A.
- Nilai rasio pembebanan trafo atau ketidakseimbangan fasa memerlukan master kapasitas dan formula resmi yang disetujui; jangan menebak ambang.

## 14. Laporan & Perbandingan

1. Buka **Laporan & Perbandingan**.
2. Pilih rentang waktu/tahun pembanding sesuai jenis output yang tersedia.
3. Pastikan kelengkapan data dan definisi parameter sesuai.
4. Gunakan **Ekspor Excel / PDF** untuk arsip atau bahan pemeriksaan.
5. Simpan tanggal pembuatan, periode, dan status verifikasi saat mengirim laporan resmi.


### Perbandingan Parameter Antar-Tahun (V1.4.6.1)

1. Buka **Laporan & Perbandingan → Laporan Standar**, lalu temukan **Perbandingan Parameter Antar-Tahun**.
2. Klik **Pilih Parameter**. Cari satu parameter Input/Computed dari Master Parameter. Misalnya **Daya Mampu Sistem (kolom H)** atau **Beban Sistem (kolom J)**.
3. Pilih **Metode agregasi**: Maksimum (beban puncak), Rata-rata, atau Minimum. Tidak tersedia SUM untuk kW karena penjumlahan daya bukan energi.
4. Pilih **Tahun A** dan **Tahun B** di kanan atas grafik. Diagram batang dan tabel 12 bulan langsung mengikuti periode dan satuan parameter.
5. Kolom **Perubahan** memakai metode agregasi yang dipilih. Saat tahun pembanding kosong/0, kolom perubahan adalah `—`; jika satu/both bulan tidak lengkap, status tetap **Parsial/tidak ada** dan bukan YoY resmi.
6. Tekan **Simpan Pilihan Saya** untuk menyimpan parameter dan metode untuk akun sendiri. Admin dapat memakai **Jadikan Default Sistem**. Gunakan **Reset Pribadi** agar mengikuti default sistem. Pemilihan tahun tidak disimpan sebagai default.
7. Untuk kebutuhan tabel ekspor kolom bebas, tetap gunakan **Export Data Excel/CSV**; untuk dokumen tersusun tetap gunakan tab **Laporan Kustom**.

## 15. Pengaturan Admin

### Master Peralatan

Gunakan **Tambah/Edit** untuk nama, kode, jenis (pembangkit, feeder, incoming, dll.) dan status aktif. Kode yang sudah dipakai historis harus dipertahankan. Jika terjadi penggantian fisik, evaluasi apakah membutuhkan kode peralatan baru agar histori tidak menyatu secara keliru.

### Master Parameter

Gunakan drawer Tambah/Edit Parameter untuk nama, kode, satuan, kelompok, tipe Input/Computed, keterkaitan peralatan, dan status aktif. Formula dihitung melalui engine yang sudah ada; jangan menyisipkan Python/SQL bebas.

### Pengguna

Admin membuat username, nama, role, dan password kuat. Penggantian password memutus sesi lama jika diatur oleh endpoint. Jangan menonaktifkan satu-satunya admin aktif. Hasil log/audit dapat digunakan untuk investigasi koreksi.

## 16. Backup, upgrade, dan troubleshooting — admin server

### Backup

Dari **folder proyek aktif** (yang mempunyai `compose.yaml` dan `.env`):

```bash
cd /opt/berauload/BerauLoad_V1_1_1 # sesuaikan dengan lokasi yang benar
./deploy/backup.sh
ls -lh backups/berauload_*.gz | tail -4
```

Periksa bahwa **backup database** dan **arsip Excel uploads** sama-sama dibuat dan berukuran masuk akal. Lakukan salinan ke storage lain sesuai kebijakan organisasi dan uji restore di lingkungan staging.

### Upgrade patch

Pastikan sumbernya dari versi **1.3.0** untuk patch V1.4.0. Upload ZIP patch ke `/opt/` dan:

```bash
cd /opt/berauload/BerauLoad_V1_1_1 # sesuaikan dengan folder aktif
curl -fsS http://127.0.0.1:8092/api/health
./deploy/backup.sh
unzip -o /opt/BerauLoad_V1_4_0_Update_Patch_From_V1_3_0.zip -d .
docker compose build  # HARUS berhasil sebelum menjalankan versi baru
docker compose up -d --no-build
docker compose ps
./deploy/smoke-test.sh
curl -fsS http://127.0.0.1:8092/api/health
```

Hasil `health` yang diharapkan: `version: 1.4.0`. Jangan menjalankan `install.sh` ulang pada instalasi existing, jangan melakukan `docker compose down -v` atau menghapus volume `pgdata`/`uploads`.

### Pemeriksaan masalah

| Gejala | Pemeriksaan awal |
|---|---|
| HTTP 502/503 | `docker compose ps`, `docker compose logs --tail=100 backend web db` |
| Build React gagal | Periksa error TypeScript pada `npm run build` dan kompatibilitas dependensi; **jangan** lanjut `up` jika build gagal |
| Dashboard kosong | Pastikan periode benar, dataset ada, parameter aktif, dan login valid |
| Tidak bisa menyimpan layout | Periksa role/owner, validasi panel, error 409 (versi berubah), atau CSRF |
| Rule status tidak tampil | Pastikan rule aktif dan tanggal dashboard setelah tanggal berlaku rule |
| Grafik H/J kosong | Periksa apakah kedua kolom terisi pada **jam yang sama** |
| Import tidak masuk | Baca detail preview, konflik, status final, dan log import |
| Port 8092 tak bisa dibuka | Periksa APP_PORT, firewall, reverse proxy, dan IP LXC |

Untuk laporan masalah, kirim **teks error tanpa password, cookie, `.env`, token, atau data operasional sensitif**.

## 17. FAQ dan glosarium

**Apakah Dashboard Builder menambah atau menghapus data beban?**  
Tidak. Ia hanya menyimpan konfigurasi panel. Grafik mengambil data dari API historis.

**Mengapa pengguna tidak bisa mengedit dashboard sistem?**  
Hanya admin berwenang. Pengguna dapat memakai tombol **Duplikat** untuk membuat salinan pribadi.

**Apakah dashboard pribadi bisa dijadikan default?**  
Ya, untuk akun pembuat. Default pribadi didahulukan dari default sistem di menu Dashboard Builder.

**Apakah Formula Historis dan Engineering Rule dapat dihapus?**  
Definisi yang sudah dipakai disarankan **diarsipkan**, bukan dihapus permanen. Formula Historis menyediakan edit/revisi dan arsip/pulihkan; Engineering Rules mendukung revisi dan arsip versi aktif.

**Mengapa data di gauge belum menunjukkan normal/kritis?**  
Gauge pada V1.4 menampilkan nilai dan skala visual. Status teknis hanya boleh berasal dari **Engineering Rules aktif** berdasarkan aturan yang disetujui.

**Mengapa nilai kosong bukan 0?**  
Karena 0 adalah pengukuran yang bermakna; kosong berarti belum ada pembacaan atau tidak valid.

**Apakah data dapat dipakai 20–30 tahun?**  
Struktur timestamp dan PostgreSQL mendukung histori panjang; tetap perlu kebijakan backup, pengarsipan, indeks, performa dan retensi.

**Glosarium singkat:**

- **Daya Mampu:** kolom H REKAP untuk konteks format laporan kelistrikan Berau.
- **Beban Sistem:** kolom J REKAP.
- **Computed:** parameter hasil rumus.
- **Coverage:** jumlah pengukuran lengkap dibanding jam yang diharapkan.
- **Rule:** aturan interpretasi teknis, bukan kendali otomatis.
- **Default Sistem:** dashboard bersama yang ditetapkan admin.
- **Default Pribadi:** dashboard pilihan suatu akun.
- **Draft/Verified/Final:** status pengelolaan data harian.

---

**Versi panduan:** 1.4.0. Isi panduan harus diperbarui bila perilaku UI, rumus, atau hak akses berubah di versi mendatang.


## 13. Cara mengatur tab/kolom Input Beban Harian (V1.4.2)

**Untuk admin:** Pengaturan → Mulai di sini → Tab & Kolom Input. Pada kolom kiri, pilih tab, ubah nama, urutkan dengan panah, atau tambahkan tab baru. Pada bagian kanan, pilih tab tujuan untuk tiap parameter; gunakan Tampilkan/Sembunyikan dan naik/turun untuk urutan kolom. Gunakan **Simpan Perubahan** untuk membuatnya berlaku bagi operator. **Batal** membuang semua perubahan draft yang belum disimpan. Parameter yang disembunyikan tidak dihapus dan tidak berhenti menjadi sumber rumus/laporan.

**Untuk menambahkan parameter Input:** Pengaturan → Parameter → Tambah Parameter → Input. Masukkan nama, kode, satuan, dan kelompok data sumber. Pilih **Tab di Input Beban Harian** secara terpisah, lalu simpan. Buka Input Beban Harian dan pilih tab yang sesuai; parameter baru akan muncul untuk 24 jam. Parameter `Computed` selalu read-only pada tabel.

**Perlu diketahui:** Kelompok parameter lama tetap digunakan oleh analisis dan pemetaan Excel; tab hanya memengaruhi tampilan. Menonaktifkan tab tidak menghapus nilai lama. Jangan memasukkan nol untuk jam yang belum ada pengukuran. Hari Final tetap terkunci. V1.4.2 belum menyediakan aturan `wajib isi` per parameter; jika perlu, harus ditetapkan efektivitas tanggal dan efeknya terhadap finalisasi terlebih dahulu.

---

# Tambahan Panduan V1.4.2.1 / V1.4.3

## A. Menyiapkan Master Satuan

1. Buka **Pengaturan → Master Satuan**. Satuan standar seperti kW, MW, kVA, kWh, kV, A, Hz, dan % sudah tersedia.
2. Pilih **Tambah Satuan** bila simbol yang diperlukan belum tersedia. Isi **kode**, **nama**, **jenis besaran**, serta **faktor ke satuan dasar**. Contoh: GW untuk daya aktif memakai faktor 1.000.000 bila satuan dasarnya kW.
3. Baca pratinjau atau verifikasi konversinya. Periksa faktor dengan penanggung jawab teknis sebelum memakai satuan baru pada pengukuran operasional.
4. Tekan **Simpan**. Kode, jenis dimensi, dan faktor tidak bisa diedit diam-diam. Untuk satuan baru yang salah, nonaktifkan jika belum dipakai dan buat definisi baru yang benar.
5. Satuan custom dengan jenis `Lainnya` diperlakukan sebagai dimensi sendiri; tidak bisa dikonversi otomatis dengan satuan custom lain.

**Penting:** kW adalah daya aktif; kVA adalah daya semu. Keduanya tidak dapat dikonversi hanya dengan penggantian satuan tanpa faktor daya dan data yang sesuai. Jangan gunakan MW sebagai pengganti MWh.

## B. Menambahkan Parameter Input dan Computed

1. Pengaturan → Parameter → Tambah Parameter.
2. Untuk **Input**, pilih satuan dari Master Satuan. Pilih tab tujuan agar muncul pada Input Beban Harian. Jangan mengubah satuan historis parameter lama hanya untuk merapikan tampilan.
3. Untuk **Computed**, pilih Formula Builder. Contoh jika tersedia dua parameter berbeda satuan: Daya Mampu 50 MW dikurangi Beban 45.000 kW menghasilkan 5 MW. Simulasi lalu simpan.
4. Data kosong tetap menjadi belum lengkap; nilai nol yang diukur benar-benar berbeda dari kosong. Pembagian nol akan menghasilkan error, bukan 0.
5. Perhitungan Historis dan Engineering Rules juga menawarkan satuan hasil dari Master Satuan. Aturan harus melalui proses draft/aktivasi yang disetujui sebelum dianggap berlaku.

## C. Mengatur Visualisasi Lanjutan

1. Masuk **Dashboard Builder**, pilih dashboard, lalu **Edit Layout**.
2. Pilih panel dan klik ikon pensil, atau **Tambah Panel**.
3. Pilih grafik Garis, Area, Batang, **Tangga**, atau **Batang Bertumpuk**, lalu pilih parameter.
4. Pada **Pengaturan Grafik & Tampilan**, pilih satuan tampilan (misalnya MW untuk data kW), warna masing-masing seri, posisi legenda, angka desimal, dan tampil/sembunyikan titik grafik.
5. Agregasi: rata-rata, maksimum/puncak, atau minimum. Menjumlahkan kW untuk menghasilkan kWh **tidak** didukung oleh pilihan agregasi dashboard biasa.
6. Tekan **Terapkan ke Dashboard** lalu **Simpan Perubahan**. Jika tidak jadi, gunakan **Batal** (edit dashboard) untuk mengembalikan keadaan tersimpan.
7. Arahkan pointer ke grafik untuk membaca tooltip periode **WITA** dan nilai pada satuan tampilan. Titik yang tidak tercatat tidak akan dibuat-buat.

**Daya Mampu vs Beban Sistem:** tetap bersumber dari kolom **H** dan **J** bagian REKAP file Excel. Grafik H/J menggunakan pembacaan jam berpasangan, dan tidak boleh dipakai sebagai stacked-bar yang menjumlahkan keduanya.

## D. Contoh pengujian aman oleh admin

- Ubah tampilan panel H/J dari kW menjadi MW; jika salah satu nilai 48.000 kW, layar harus menampilkan 48 MW. Nilai database dan laporan asli tetap 48.000 kW.
- Ubah warna Daya Mampu, lalu tekan Batal di Dashboard Builder; warna lama harus kembali.
- Buat unit custom yang belum dipakai kemudian nonaktifkan. Unit yang digunakan parameter harus ditolak untuk dinonaktifkan.
- Uji formula campuran unit dengan nilai contoh melalui Simulasi; jangan gunakan data final untuk percobaan.


## BerauLoad V1.4.4 — Kelola Dashboard

Buka **Dashboard Builder → Kelola Dashboard → Buka Pengaturan**. Pilih template Monitoring Operasi Berau, Analisis Output PLTU Lati, atau Arus Penyulang 1 untuk membuat dashboard pribadi baru. Ketiga template menggunakan parameter resmi dan tidak menggandakan data.

Gunakan **Unduh Konfigurasi JSON** untuk menyimpan susunan panel (bukan data pengukuran). Untuk mengimpor, pilih file JSON BerauLoad. Dashboard hasil impor selalu baru dan bertipe pribadi; ubah nama dan layout setelah impor jika diperlukan.

Untuk membagikan dashboard pribadi: buka bagian **Bagikan Dashboard**, ketik *username* penerima, klik Bagikan. Penerima hanya dapat melihat dashboard tersebut, tidak dapat mengubahnya. Pemilik dapat mencabut akses kapan pun. Dashboard sistem tetap diatur admin.

Pada bagian **Riwayat Layout**, pilih versi sebelumnya dan klik **Pulihkan**. Sistem mencatat revisi baru; konfigurasi versi sebelumnya tetap tersedia. Jika ada perubahan bersamaan dari sesi lain, server menolak dengan HTTP 409.

## BerauLoad V1.4.4 — Export Data Excel / CSV

1. Buka **Laporan → Export Data Excel / CSV**.
2. Pilih tanggal mulai/selesai dan resolusi: per jam, harian, bulanan, atau tahunan. Untuk resolusi selain jam pilih agregasi AVG, MAX atau MIN. Jika data hanya mencakup sebagian hari/periode, jangan menganggap hasil itu sebagai periode lengkap.
3. Di **Pilih Kolom**, cari dan tambahkan parameter yang ingin diekspor. **Tanggal (WITA) wajib dipilih**; Anda dapat mengubah urutan kolom menggunakan panah naik/turun. Anda juga dapat mengubah judul kolom agar sesuai laporan kerja.
4. Jika ada satuan setara, pilih satuan tampilan pada masing-masing parameter. Contoh 48.000 kW ditampilkan sebagai 48 MW; kW dan kVA **tidak** dapat dikonversi langsung.
5. Klik **Preview 10 Baris** untuk memastikan urutan, isi, dan nilai kosong. Klik **Unduh XLSX** atau **Unduh CSV**. Data nol yang benar-benar tercatat tetap angka 0, data kosong tetap kosong. CSV menggunakan UTF-8 dengan BOM dan delimiter semikolon (;).
6. Isi nama template lalu klik **Simpan sebagai Template Baru** untuk digunakan bulan berikutnya. Template pribadi terlihat pemilik saja, template bersama dibuat admin dan dapat digunakan pengguna lain. Untuk memperbaiki template, pilih dari dropdown kemudian **Perbarui Template Terpilih**; untuk membersihkan daftar, **Arsipkan Template**.

**Batasan dan keamanan:** maksimum 45 kolom dan rentang 10 tahun per permintaan. Ekspor dilakukan dengan data yang tersimpan di database; parameter Computed tanpa snapshot pembacaan dapat menghasilkan sel kosong. Laporan Perhitungan Historis/Engineering Rules lintas waktu tetap dilihat melalui menu Analisis; V1.4.4 belum membuat format export tersendiri untuk dua sumber tersebut. File unduhan hanya boleh dipakai menurut hak akses data internal organisasi.


## V1.4.5 — Mengatur ukuran panel Dashboard Builder

1. Buka **Dashboard Builder** dan pilih dashboard yang memiliki izin edit. Klik **Edit Layout**.
2. Untuk **memindah panel**, tarik ikon titik/pegangan pada kiri nama panel lalu lepas di panel tujuan. Tombol panah tetap dapat digunakan.
3. Untuk **mengubah ukuran**, arahkan mouse ke **sudut kanan bawah panel** dan tarik secara mendatar untuk lebar atau vertikal untuk tinggi. Panel akan mengikuti kotak grid (lebar 3–12 dari 12 kolom, tinggi 1–4 tingkat); tidak dapat menumpuk panel lain.
4. Klik **Simpan Perubahan** bila cocok. Klik **Batal** untuk mengabaikan perubahan, atau **Reset ke Tersimpan** untuk membatalkan perubahan draft saat masih mode edit.
5. Pada perangkat HP, panel disusun satu kolom. Gunakan tombol panah dan dropdown untuk mengubah layout bila grip/resize sulit dipakai.
6. Bila data pada grafik tidak berubah setelah menginput nilai, muat ulang layar. Cache pengukuran yang dibaca aplikasi dihapus saat penyimpanan berhasil; data kosong tidak berubah menjadi nol.

**Perhatian:** Ini monitoring data yang terakhir diinput, bukan kontrol SCADA secara real-time.


## V1.4.6 — Laporan Kustom & Gaya Panel

### Membuat laporan kustom

1. Buka **Laporan & Perbandingan → Laporan Kustom**. Pilih Template Baru atau template yang tersedia.
2. Isi nama/deskripsi. Admin dapat membuat **Template Sistem** (baca-saja bagi pengguna lain); pengguna lain membuat **Template Pribadi**.
3. Klik tambah bagian: **Judul Bagian**, **Paragraf**, **KPI**, **Grafik**, atau **Tabel**. Untuk blok data, pilih parameter BerauLoad; tidak perlu menulis Python atau SQL.
4. Atur metode rata-rata, maksimum, atau minimum. Untuk grafik/tabel pilih resolusi Jam, Hari, atau Bulan. Dua parameter dalam grafik harus memiliki satuan yang sama dan diambil dari jam pengukuran berpasangan.
5. Susun urutan bagian menggunakan tombol naik/turun. Tentukan tanggal mulai dan selesai, kemudian klik **Pratinjau**. Nilai kosong tetap kosong, bukan nol.
6. Setelah sesuai, klik **Simpan**. Selanjutnya klik **PDF** atau **Excel** untuk mengunduh. Untuk CSV dan pilihan kolom bebas, gunakan menu **Export Data Excel/CSV**.
7. Gunakan **Duplikasi** untuk membuat salinan pribadi. **Arsipkan** menyembunyikan template tanpa menghapus data kelistrikan.

### Mengubah tampilan panel Dashboard

1. Buka **Dashboard Builder → Edit Layout → ikon pensil** pada panel.
2. Pada **Gaya Panel & Tipografi**, pilih preset **Klasik**, **Gelap**, atau **Lembut**.
3. Sesuaikan font Sans-serif/Monospace, ukuran judul 11–24 px, angka KPI 18–54 px, warna teks/latar/bingkai. Tombol **Otomatis** mengembalikan pilihan ke preset.
4. Klik **Terapkan ke Dashboard**, lalu **Simpan Perubahan**. **Batal** membuang perubahan yang belum disimpan.
5. Gaya panel hanya mengubah presentasi. Seluruh angka pengukuran, formula dan data historis tidak berubah.

### Verifikasi versi

Nomor versi di footer, Informasi Sistem, serta panduan diambil dari API `/api/health`. Setelah upgrade, pastikan menunjukkan **V1.4.6.1**.

## Persiapan Topologi Single Line (V1.5.0 Tahap 1)

Fitur Topologi masih **backend-only**. Menu dan antarmuka editor/viewer belum dipasang. Administrator tidak perlu menggambar topologi sekarang. Dua tabel konfigurasi baru otomatis ditambahkan ketika server diupgrade, tanpa membuat skema sambungan listrik otomatis.

Pada tahap berikutnya operator dapat memilih diagram, tanggal, dan jam untuk melihat pengukuran WITA. Jam kosong akan tampil sebagai `—`, bukan `0`. Tidak akan ada perintah menutup/membuka PMT; tampilan pemutus bersifat netral. Diagram hanya boleh disusun berdasarkan hubungan aktual yang diverifikasi. Tindakan perubahan akan dibatasi hanya untuk admin dan dicatat di audit.

## Topologi Single Line — Panduan Mode Lihat (V1.5.0 Tahap 2)

1. Login, buka **MONITORING → Topologi**. Halaman gelap ini hanya Viewer; menu lain tetap seperti biasa.
2. Pilih **Diagram** pada toolbar. Jika daftar kosong, halaman akan menampilkan **Belum ada diagram**. Hal ini normal: sampai Tahap 3, tidak ada fitur menggambar dan aplikasi sengaja tidak membuat sambungan jaringan otomatis.
3. Pilih tanggal menggunakan input tanggal di bilah bawah (zona operasional WITA), lalu geser slider 00–23 untuk memilih jam. Judul **Data jam HH:00 WITA** selalu menunjukkan pembacaan yang sedang dilihat.
4. Tombol **Putar** melangkah maju satu jam dalam interval singkat; **Jeda** menghentikan. Pemutaran berhenti pada jam 23. Tombol panah memilih jam sebelumnya/berikutnya.
5. Gunakan tombol **+/−** untuk zoom dan area scroll untuk melihat kanvas besar. Simbol, garis dan kotak mengikuti layout yang telah disimpan. Klik **Lihat tren 24 jam** pada kotak berparameter untuk grafik per jam.
6. Nilai **—** berarti tidak ada pembacaan pada jam yang dipilih, **0** berarti pembacaan tercatat bernilai nol. Grafik tidak menyambungkan jam yang kosong.
7. Warna kondisi hanya muncul jika kotak merujuk **Engineering Rule aktif**, dan bukan keputusan operasi otomatis. Simbol PMT/pemutus tidak interaktif dan tidak dapat digunakan mengoperasikan peralatan.
8. Tombol **Muat ulang** membaca ulang daftar dan versi diagram; tidak menyimpan data. Akun operator/manajemen/verifier boleh melihat diagram, tetapi seluruh perubahan konfigurasi hanya untuk admin melalui editor Tahap 3.

**Batasan:** Tahap 2 belum membuat/edit simbol atau hubungan listrik, belum menyediakan palet, ranking, editor properti dan grafik mini permanen pada kotak. Itu cakupan Tahap 3/4. Data adalah data historis per jam, bukan SCADA real-time.


## Topologi Single Line V1.5.0 Tahap 3 — Membuat dan mengedit diagram

1. Login sebagai **admin**. Buka **Monitoring → Topologi → Diagram Baru**. Isi nama dan keterangan. Diagram baru sengaja **kosong**.
2. Pilih diagram dan klik **Edit Diagram**. Di kiri, pilih peralatan aktif (atau Semua Peralatan), lalu pilih satu parameter dan tekan **Tambah Kotak**. Jangan menyamakan data kosong dengan nol.
3. Klik kotak pada kanvas. Panel **Properti Kotak** di kanan menyediakan judul, sumber peralatan, parameter 1–6 item, urutan dengan ↑/↓, lebar, posisi X/Y, angka desimal, satuan, garis jangkar, rule aktif, serta kunci posisi.
4. Geser kotak menggunakan mouse/layar sentuh. Titik mengikuti grid 10 px. Kotak tidak menggeser jalur listrik. Bisa pula mengatur X/Y dari panel properti.
5. Tombol **Buat draf dari daftar peralatan** hanya menempatkan simbol untuk kategori yang bisa dipetakan secara jelas. Tidak ada garis sambungan, relay, atau dugaan status pemutus. Pada tahap ini penggambaran garis manual belum tersedia.
6. **Terapkan susunan ke peralatan sejenis** hanya bekerja jika peralatan aktif lain memiliki parameter dengan **nama dan satuan identik**. Peralatan yang tidak cocok dilewati, rule dan garis tidak ikut disalin. Tinjau semua hasil sebelum Simpan.
7. Gunakan **Urungkan**, **Ulangi**, atau **Reset ke Tersimpan** untuk koreksi; **Batal** membuang perubahan. **Simpan Perubahan** membuat revisi baru dengan audit log. Jika ada pesan bahwa diagram berubah oleh pengguna lain, muat ulang agar data pengguna lain tidak tertimpa.
8. Panel kiri memiliki **Riwayat Revisi**. Memulihkan revisi lama membuat versi baru, bukan menghapus riwayat. Pastikan tidak ada perubahan draf yang ingin dipertahankan sebelum pulihkan.
9. Kembali ke **Mode Lihat** untuk memeriksa data pada jam WITA yang dipilih. Kotak baru dapat menampilkan “—” hingga pembacaan tersedia atau sampai layout disimpan dan pembacaan dimuat ulang. Status warna hanya dari Engineering Rules aktif.
10. Pengguna operator/manajemen hanya dapat melihat dan membuka grafik tren. Topologi bukan SCADA, tidak dapat mengoperasikan PMT atau menyimpulkan keadaan peralatan dari nilai 0.

**Catatan:** Tahap 4 sekarang menyediakan alat-alat tersebut di palet kiri. Lihat petunjuk Tahap 4 di bawah.

## Topologi Single Line V1.5.0 Tahap 4 — Menggambar diagram dan kotak informasi

1. Admin masuk **Monitoring → Topologi → Edit Diagram**. Pada palet kiri pilih **Pilih / Geser**, **Gambar Garis**, salah satu dari delapan simbol kelistrikan, atau jenis Kotak Informasi.
2. **Tambah simbol:** klik nama simbol (Pembangkit, Incoming, Busbar, PMT netral, Transformator, Penyulang, Beban, Kapasitor) lalu klik titik kanvas; alternatif seret simbol dari palet ke kanvas. Gunakan alat Pilih/Geser untuk memindahkan. Panel kanan menyediakan label, jenis, peralatan opsional, posisi, rotasi dan Hapus Simbol.
3. **Gambar garis:** pilih alat Gambar Garis; pilih label visual `Belum ditentukan` atau `20 kV`; klik setiap vertex pada kanvas (maksimal 32), lalu klik **Selesaikan Garis** setelah minimal dua titik berbeda. Gunakan **Batalkan Garis** untuk membuang draf belum tersimpan. Garis tidak tersambung ke peralatan secara semantik; periksa diagram teknis sebelum dipakai.
4. **Ubah garis:** kembali ke Pilih/Geser, klik garis, lalu seret titik kontrol atau gunakan panel properti garis untuk posisi koordinat, tambah titik, hapus titik dan hapus garis. Sistem tidak menebak aliran listrik atau status PMT.
5. **Kotak:** pilih sumber Peralatan dan Parameter di palet, lalu pilih Parameter / Ringkasan / Peringkat / Legenda / Teks. Posisi kotak bebas dipindahkan dan diubah pada panel kanan. Kotak Ringkasan menampilkan jumlah parameter tersedia beserta pembacaan asli. Kotak Peringkat mengurutkan nilai pada jam dipilih dari terbesar ke terkecil, **hanya jika satuan sama**. Kotak Legenda hanya menjelaskan arti garis dan bukan tegangan terukur. Kotak Teks adalah catatan pendek berbasis judul.
6. **Grafik mini:** pada kotak Parameter/Ringkasan/Peringkat, centang Grafik Mini 24 Jam. Grafik membaca `/series` dan menunjukkan celah untuk jam tanpa nilai; nilai nol tetap sah. Klik kotak Mode Lihat untuk grafik 24 jam lebih besar.
7. **Simpan/Batal:** Simpan Perubahan menulis konfigurasi baru dan membuat revisi immutable. Urungkan/Ulangi/Reset/Batal tidak menyentuh database; perubahan pengguna lain ditolak dengan konflik 409. Pilihan waktu tetap berbasis hari dan jam WITA.
8. Pada Mode Lihat, pengguna biasa hanya dapat memilih diagram/waktu, zoom dan melihat pengukuran. Tidak ada fitur operasi PMT atau perubahan nilai listrik. Jika tidak ada pembacaan tampil `—`, bukan nol.

**Batas keselamatan:** tidak ada topologi bawaan, auto-connect, estimasi status PMT, atau ambang teknis baru. Semua garis adalah layout manual yang harus dikonfirmasi terhadap diagram otoritatif.


## Tahap 4.1 — Memaksimalkan Topologi

Pada **Monitoring → Topologi**, halaman otomatis mengisi lebar ruang kerja. Klik **Layar Fokus** untuk sementara menyembunyikan sidebar dan menggunakan hampir seluruh layar; klik **Tampilkan Menu** atau tekan `Esc` untuk kembali. Gunakan **Sesuaikan Lebar** agar diagram sesuai ruang yang tersedia atau tombol +/− untuk zoom. Tanggal/jam pada bilah bawah tetap berbasis historis WITA, bukan SCADA langsung.

**Edit Diagram (admin):** saat memilih kotak parameter, panel kanan menampilkan parameter terpilih dan daftar pilihan yang dapat digulir secara terpisah; masukkan nama atau kode ke kotak **Cari parameter** agar lebih mudah menemukan pilihan. Tidak ada pengukuran yang diubah.

**Mengubah panjang Busbar:** pilih simbol Busbar di kanvas, lalu pada panel **Properti Simbol** atur **Panjang busbar (px)** dengan input atau slider. Panjang mengikuti grid 10 px dan tidak melampaui batas kanvas. Sesuaikan garis secara manual bila diperlukan—pengubahan panjang busbar tidak menyambungkan atau memindahkan garis secara otomatis. Gunakan Simpan Perubahan untuk membuat revisi baru, atau Batal/Reset bila belum sesuai.


## Tahap 4.2 — Ruang kerja ringkas dan pengelompokan area

**Mode Lihat:** toolbar dipadatkan tanpa menghapus pemilih diagram, Fit, zoom, refresh dan Layar Fokus. Di bawah kanvas, tanggal WITA, pemutaran, jam dan status hari tetap tersedia. Klik **Fit** untuk menyesuaikan zoom berdasarkan bentang diagram. Data historis per jam, bukan SCADA real-time.

**Kotak dengan banyak parameter:** klik baris metrik, misalnya *PLTU Lati CB-31*, untuk mengganti **hanya** grafik mini di kotak tersebut. Judul tren dan indeks (contoh 2/3) mengidentifikasi parameter yang tergambar. **Lihat tren 24 jam** tetap membuka pop-up lama. Di pop-up, pilih parameter atau aktifkan **Bandingkan semua** apabila semua satuan persis sama. Metrik berbeda satuan hanya dapat ditinjau bergantian. Nol tetap ditampilkan sebagai nol; jam kosong tetap celah.

**Admin → Edit Diagram → Alat Gambar → Area / Kelompok:** klik alat kemudian klik kanvas untuk menambah group frame. Pilih frame dengan klik tepi, seret tepi untuk memindahkan atau tarik kotak kecil di sudut kanan bawah untuk mengubah ukuran. Properti kanan: Judul, X/Y, lebar/tinggi, gaya garis Solid/Putus-putus/Titik, preset warna, isi transparan (0%) hingga 40%, dan Kunci posisi. Bingkai tersebut hanyalah penanda visual dan tidak menghubungkan feeder, PMT atau busbar di dalamnya.

**Kanvas besar:** posisi simbol/kotak/area yang mendekati tepi memperluas kanvas. Untuk ukuran manual lihat palet **Ukuran Kanvas**: lebar dan tinggi 200–20.000 px, kelipatan 10. Klik Terapkan Ukuran atau Sesuaikan ke Objek. Sistem menolak kanvas yang terlalu kecil sampai memotong objek. Zoom/scroll/Fit untuk navigasi. Semua perubahan baru permanen setelah Simpan Perubahan; gunakan Undo/Redo/Batal bila perlu.

**Catatan upgrade balik:** revisi yang memiliki Group Area sebaiknya dipulihkan ke versi sebelum area ditambahkan menggunakan Stage 4.2 sebelum mengembalikan source Stage 4.1, karena validator Stage 4.1 belum mengenal `areas`. Backup database dan source tetap wajib.

## V1.6.0 Stage 5 — Rekap Unit Bawah

**Sumber data tidak perlu diketik ulang.** Pilih unit aktif menggunakan pemilih UP3/ULP/KP. Admin global menyiapkan parameter hasil hitung di ULP atau UP3. Pilih operand dari unit sendiri atau unit bawahannya; dropdown menyajikan kelompok unit dan label `Unit - Parameter`.

1. Masuk **Pengaturan → Formula Builder**, pilih ULP atau UP3 yang akan memiliki rekap. Susun rumus misalnya `SUM(kp_a_load, kp_b_load)` dengan kode parameter yang ada di katalog (nama contoh saja, bukan parameter otomatis). Untuk mempercepat, pilih **peran parameter** (contohnya `system.load`) lalu **Tambah parameter berperan sama dari unit di bawah**; cek daftar operand satu per satu sebelum simpan. Daftar eksplisit ini tidak akan menambahkan KP baru secara otomatis. Hindari menghitung ganda bila beban KP sudah terukur dalam beban ULP.
2. Bila salah satu jam belum memiliki operand, hasil rekap jam tersebut kosong (`—`/NULL), bukan 0; angka 0 yang tercatat tetap sah. API `/api/formulas/completeness?day=YYYY-MM-DD&hour=H` memberikan keterisian sumber pada jam tersebut.
3. Dashboard, topologi, perhitungan historis, engineering rules, laporan, dan export dapat menunjuk parameter dari bawah; perhatikan nama unit asal. Klik **Sumber: x final, y terverifikasi, z draf** untuk melihat unit dan statusnya. Orang yang boleh membaca konfigurasi unit induk boleh melihat nilai sumber yang dirujuk, tetapi tidak diberi akses mengubah sumber.
4. Verifier ULP dapat memfinalkan hari ULP ketika KP masih draf dengan membaca daftar KP lalu **mengonfirmasi**. Audit menyimpan keputusan tersebut. Jika pembacaan KP diperbaiki setelah ULP verified/final, hasil ULP tetap terkunci. Verifier/admin melihat **Sumber berubah setelah final/verifikasi** pada status hari; admin dapat membuka kembali hari bila memang disetujui untuk memperbarui perhitungan. UP3 mengikuti pembacaan terkini tanpa status hari.
5. Akun KP tetap hanya melihat KP tersebut; tidak dapat memilih parameter induk atau unit setingkat. Tidak ada tombol tulis pembacaan sumber melalui dashboard rekap.



## Pengukuran Gardu — Stage 9a

Buka **Operasional → Pengukuran Gardu** setelah memilih ULP/KP pada sidebar.
Admin global membuat Master Penyulang dan Master Gardu, menetapkan definisi
parameter/sesi/flag global pada tab **Definisi Global**. Kode tidak dapat diubah
setelah gardu berpengukuran, sedangkan nama, daya, fase, merek, nomor seri,
tap, dan penyulang dapat diperbarui; histori/snapshot pengukuran tidak berubah.

**Input Massal:** pilih tanggal dan sesi (contoh Siang/Malam), penyulang bila ingin
membatasi, nama petugas, lalu isi sel seperti spreadsheet. Enter/Tab/panah berpindah,
tempel TSV dari Excel, pilih flag dari dropdown sel. `0` bukan sel kosong.
Jurusan melebihi jumlah yang disetel dinonaktifkan. Penyimpanan otomatis per baris
3 detik, blur langsung; tanda status muncul di baris. Pada sesi kadaluarsa login
ulang dengan akun yang sama, dan saat konflik pilih nilai server atau nilai sendiri.
Backup tersimpan lokal hingga 7 hari; konfirmasi Pulihkan/Buang sebelum menggunakannya.
Halaman 100 gardu sekaligus; halaman berikutnya melalui navigasi bawah tabel.
**Form Ponsel** untuk satu gardu tersedia tersendiri.

**Daftar & Verifikasi:** gunakan filter tanggal/sesi/status/penyulang, pilih baris
untuk aksi massal. Verifier/Admin memverifikasi; pengukuran verified terkunci;
reopen memerlukan alasan audit. Penghapusan hanya draft. Sistem menyimpan snapshot
kVA/fase/jumlah jurusan/penyulang pada saat kunjungan pertama dibuat.

**Impor Excel/CSV:** unduh template dari Master atau Daftar Pengukuran. Unggah dan
periksa validasi per baris sebelum konfirmasi. Penyulang baru dan update master
harus dipilih eksplisit. Pengukuran impor default hanya mengisi sel yang kosong;
mode timpa hanya untuk draft. Kolom/teks sembarang tidak diinterpretasikan sebagai
nilai 0. Lihat `README_UPGRADE_V1_6_0_STAGE9A.md` untuk batas dan rollback.

## Tambahan Stage 9a-fix

**Tampilan Pengukuran Gardu** menampilkan filter tanggal/sesi/penyulang/petugas, pilihan kelompok pengukuran dan input massal dalam tabel spreadsheet. Penanda jumlah gardu, status setiap baris dan petunjuk navigasi ditempatkan berdampingan dengan kisi. Tab *Form Ponsel*, *Master Gardu*, *Daftar & Verifikasi*, dan *Definisi Global* tetap tersedia sesuai izin lama. Referensi HTML juga memuat mockup Peta/Analisa/Rumus, tetapi ketiganya belum menjadi fitur Stage 9a.

**Mengurangi jurusan:** ketika data pernah dicatat di jurusan yang akan dinonaktifkan, sistem menampilkan jumlah nilai terdampak dan meminta konfirmasi. Konfirmasi mengubah master untuk pengukuran berikutnya saja; riwayat dan snapshot pengukuran lama tidak dihapus. Perubahan massal mengembalikan hasil berhasil, gagal, dan butuh konfirmasi per gardu.

**Konflik saat simpan:** dialog menampilkan sel berbeda (nama parameter, jurusan, nilai lokal/server), pengubah, waktu dan status. *Muat ulang data server* menyimpan ketikan konflik dalam cadangan lokal untuk opsi salin ulang, bukan menerapkannya diam-diam. *Pertahankan ketikan saya* mencoba kembali memakai revisi terkini. Pengukuran terverifikasi tidak dapat ditimpa.

**Definisi global:** admin mengedit melalui dialog; kode pengukuran ditampilkan terkunci, nama/satuan/minimum/maksimum/urutan/status bisa diperbarui sesuai kategori. Batas minimum lebih besar daripada maksimum ditolak. Operator dan verifier tidak mendapat izin konfigurasi baru.

## Pengukuran Gardu — Peta, Grafik dan Tampilan (Stage 9d1)

Pilih **Pengukuran Gardu → Peta**. Filter pencarian, unit, penyulang, sesi, kategori dan temuan berlaku pada gardu yang terlihat sesuai hak unit; kategori, warna, simbol, dan angka berasal dari pengaturan administrator serta hasil hitung tersimpan. Gunakan **Warna penanda** untuk kategori, umur ukur, atau kolom hitung. Titik mengelompok saat zoom kecil; klik kelompok untuk memperbesar, klik satu titik untuk menampilkan panel rincian. Pilih **Ukur ulang** untuk membuka form ponsel gardu tersebut, **Riwayat lengkap** ke Analisa, atau **Buka di Google Maps** untuk peta luar.

Jika ada **gardu tanpa koordinat**, daftar kode muncul di bawah peta; klik untuk membuka Master dan memperbaiki koordinat. Ketika ubin tidak tersedia, latar polos dan titik/skala tetap muncul. **Lokasi saya** meminta izin lokasi browser dan hanya bekerja melalui HTTPS atau localhost; jarak **Terdekat** adalah garis lurus, bukan rute jalan.

Pilih **Pengukuran Gardu → Analisa** untuk melihat grafik sebar kategori per penyulang, perbandingan sesi, pareto dan tren. Grafik mengikuti filter yang sama dengan tabel. Gunakan **Unduh CSV/PNG** untuk grafik, dan **Simpan tampilan** untuk menyimpan jenis grafik, kolom, dan filter. Pilih kepadatan **Nyaman/Padat** pada tabel; pengaturan ini diingat untuk pengguna browser yang sama.

Admin global dapat membuka tombol **Atur ubin peta**, mengaktifkan/menonaktifkan ubin, serta memasukkan URL dan atribusi milik penyedia ubin. Konfigurasi awal menggunakan ubin OpenStreetMap (`https://tile.openstreetmap.org/{z}/{x}/{y}.png`) dengan atribusi `© OpenStreetMap contributors`. Penggunaan ubin tunduk pada kebijakan penyedia. Kode gardu dan hasil ukur tetap berada dalam database BerauLoad, bukan diubah oleh peta/grafik.

## Saran penanganan overload — Stage 9e
Di **Pengukuran Gardu → Analisa**, buka gardu berstatus **Overload**. Bagian *Saran penanganan overload* menampilkan:
- **Tukar trafo**: gardu lain sefasa di ULP yang sama yang trafonya bisa ditukar sehingga kedua gardu tidak overload.
- **Pindah beban**: rentang persen jurusan yang boleh dipindah ke gardu terdekat agar keduanya di bawah ambang overload.

Klik **Tinjau** untuk melihat sebelum/sesudah. **Jadikan tindak lanjut** menyimpan rencana di menu Tindak lanjut. Setelah tukar trafo dikerjakan dan statusnya **Selesai**, admin/verifikator ULP dapat **Terapkan ke master** (tanggal efektif + konfirmasi); riwayat master dan audit tercatat. Ukur ulang kedua gardu agar Analisa mengikuti trafo baru.

Catatan: ini saran hitungan dari data ukur terakhir. Tidak memperhitungkan jatuh tegangan, impedansi, rugi-rugi atau pertumbuhan beban; jarak adalah garis lurus. Pindah sebagian jurusan perlu survei lapangan. Gardu tanpa koordinat atau tanpa pengukuran tidak menjadi kandidat.
