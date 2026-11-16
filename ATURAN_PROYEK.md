## Perubahan otoritatif V1.6.0 Tahap 1.1

- Tepat satu UP3 induk. Unit `ulp_tanjung_redeb` adalah satu-satunya `legacy_home`, sebagai anak langsung UP3.
- Data lama BerauLoad menjadi milik ULP Tanjung Redeb. UP3 tidak mempunyai asset, metric, batch import, atau unit day state pada tahap ini.
- Admin baru diberi akses UP3; pengguna lain diberi akses ULP sesuai role global. Belum ada pemilih unit maupun pembatasan akses unit di endpoint operasional.
- `readings`, `hour_records`, `day_states` dan nilai H/J tidak diubah; `day_states` tetap sumber baca. Dual-write hari mengarah ke ULP tanpa mengubah transaksi.
- Jika pedoman lama menyebut semua data legacy milik UP3, aturan Stage 1.1 ini yang berlaku.

## Tambahan Wajib V1.6.0 Tahap 1 — Multi-Unit tanpa perubahan perilaku

- Jangan menerapkan filter pembacaan berdasarkan `unit_id` sebelum tahap otorisasi multi-unit disetujui dan teruji. `User.role` global tetap dasar semua izin lama.
- UP3 tunggal → ULP → KP; tidak boleh KP langsung pada UP3 atau tingkat keempat. Kode unik permanen, nonaktif bukan hapus; jangan seed ULP/KP tanpa sumber otoritatif.
- FK `assets/metrics/import_batches.unit_id` nullable dan di-backfill ke UP3. Tidak menyentuh `readings`, `hour_records` atau tabel `day_states`.
- `unit_day_states` hanya mirror UP3, dual-write satu transaksi pada verify/finalize/reopen. Source of truth baca Stage 1 tetap `day_states`.
- Role Key semantik boleh null, validasi pola dan uniqueness per unit, tidak menjadi dasar rumus, H/J, izin, atau grafik.
- Lakukan backup SQL, uploads, source dan pengujian LXC sebelum deploy; jangan pernah `docker compose down -v`.


---

# Aturan Proyek BerauLoad (Ringkas)

- Pilih modular monolith; fitur disusun per domain, jangan memperbesar `main.py`/`App.tsx` tanpa alasan.
- File ideal maksimal 400 baris dan fungsi maksimal 50 baris; service rumus murni tanpa akses database.
- Nilai dan rumus teknis tidak ditebak. Daya mampu = data REKAP kolom H, beban sistem = REKAP kolom J; jangan ubah tanpa persetujuan.
- Data kosong tidak sama dengan nol; data final dan histori rumus tidak ditimpa diam-diam.
- Kode unik jenis, peralatan, parameter serta formula yang telah digunakan bersifat stabil; gunakan revisi/arsip.
- Konfigurasi rahasia di `.env`, jangan dalam source; database lewat migrasi additive dan aman untuk diulang.
- Selalu backup PostgreSQL + uploads sebelum patch, lakukan build sebelum up, rollback tanpa menghapus volume.
- Setiap fitur diuji dengan data sintetis terisolasi dan regresi. Laporkan dengan jujur bila Docker/npm/browser belum diuji.
- Jangan menambah fitur di luar scope patch, catat keputusan/risiko di CHANGELOG dan QA_STATUS.


## Tambahan V1.4.3

- [ ] Satuan baru menggunakan Master Satuan; dimensi dan faktor tidak boleh di-hardcode pada komponen tampilan.
- [ ] Satuan yang sudah digunakan tidak boleh diubah faktor/kode/dimensinya diam-diam.
- [ ] Konversi UI tidak boleh mengubah nilai historis atau snapshot laporan final.
- [ ] kW/kVA dan kW/kWh tidak dianggap konversi langsung. Satuan berbeda dimensi harus ditolak.
- [ ] Grafik H/J tidak di-*stack*, dan sumber Excel H/J serta agregasi jam berpasangan harus dipertahankan.
- [ ] Pengaturan grafik tambahan harus disimpan sebagai konfigurasi panel yang tervalidasi.


Tambahan V1.4.4: pembuatan fitur export harus dibatasi berdasarkan periode/jumlah kolom, tidak menduplikasi data historis, wajib mencegah formula injection CSV/XLSX, setiap import JSON layout divalidasi pada server dan tidak boleh memuat kode/SQL mentah. Share hanya baca-saja dan perlu izin pemilik; restore layout selalu menghasilkan revisi baru dengan expected_version. Jangan menganggap hasil agregasi parsial sebagai periode lengkap.

## Tambahan Topologi V1.5.0 Tahap 1

- [ ] Modul `topology` terpisah dari `dashboard_builder`; tidak ada kode kelistrikan di UI.
- [ ] Tanpa seed koneksi; layout awal kosong dan tidak mengklaim topologi Berau.
- [ ] Perubahan hanya konfigurasi; jangan menulis `readings`/`hour_records`/formula/rules.
- [ ] Koordinat snap grid; level/jenis simbol whitelist; data JSON ditolak jika mengandung HTML/kode/SQL bebas.
- [ ] Aksi write admin + CSRF + audit; optimistic concurrency dan revisi immutable.
- [ ] Tidak ada status/perintah PMT; Engineering Rule aktif adalah satu-satunya sumber indikator status.
- [ ] Nilai kosong = `null`, angka nol tetap valid; REKAP H/J tidak berubah.
- [ ] Tahap 1 backend saja; jangan mengklaim frontend selesai.

## Tambahan V1.5.0 Tahap 2

- [ ] Viewer hanya memanggil GET; jangan menulis layout maupun pembacaan.
- [ ] Jangan menambahkan seed sambungan atau angka dummy yang disangka data resmi.
- [ ] Satu-satunya konteks waktu adalah hari dan jam WITA; jangan menyebut real-time.
- [ ] Pertahankan nilai nol, celah NULL dan status rule yang benar-benar aktif.
- [ ] Breaker tidak berfungsi sebagai tombol kontrol peralatan.
- [ ] Editor/palet dan properti hanya boleh diluncurkan setelah Tahap 3/4 diuji.
- [ ] Komponen Topologi dan CSS hanya berada di domain `features/topology`; App.tsx hanya import, menu, render.
- [ ] Build npm/Vite dan pengujian browser harus dilaporkan terpisah dari tes backend.

## Checklist tambahan Topologi V1.5.0 Tahap 3

- [ ] Tidak menebak rangkaian/gardu/pembangkit/feeder maupun status saklar; draf aset tidak membuat garis.
- [ ] Kotak hanya menyimpan referensi parameter aktif (kecuali legacy daya_mampu_sistem_kw).
- [ ] Pengguna biasa Mode Lihat; semua penulisan divalidasi server sebagai admin dan wajib CSRF.
- [ ] Undo/Redo dan Batal hanya memengaruhi state lokal. Simpan memakai expected_version, 409 harus terlihat jelas.
- [ ] Revisi terdahulu immutable; restore membuat versi baru; tidak menulis pembacaan, formula, atau rules.
- [ ] Build React dengan dependency asli di staging LXC sebelum aktivasi production.

## Checklist tambahan Topologi V1.5.0 Tahap 4

- [ ] Delapan simbol hanya glyph visual. Klik simbol PMT tidak boleh berfungsi sebagai kontrol buka/tutup.
- [ ] Garis harus digambar manual, tidak auto-connect atau auto-energize. Pilihan warna dibatasi label tegangan whitelist.
- [ ] Hapus simbol tidak menghapus pembacaan/histori. Anchor kotak dilepas bila simbol dihapus; garis tetap independen.
- [ ] Kotak Summary tidak menghitung campuran dimensi; Ranking hanya nilai per jam dengan satuan identik. Tidak ada ambang baru.
- [ ] Grafik mini 24 jam mempertahankan nol dan celah NULL, bukan hasil interpolasi.
- [ ] Draft hanya di client hingga Simpan; audit/revisi/CSRF/admin/409 berlaku seperti Tahap 3.
- [ ] Uji build frontend dan smoke browser nyata sebelum production; hasil QA offline tidak setara dengan validasi LXC.
