# QA — BerauLoad 1.6.0-stage9d4 — 18 November 2026

Dikerjakan langsung oleh Claude. Basis 1.6.0-stage9d3. **Kandidat staging.**

## Perbaikan dan perubahan
1. **Bug: Ubah master gardu selalu gagal (422).** Form mengirim seluruh isi baris (id, unit_id, created_at, …) yang ditolak API; pesan galat tertutup panel. Ada sejak 9a-fix. Kini hanya field yang boleh yang dikirim (`masterForm.mjs`) dan galat tampil di dalam panel.
2. **Form ponsel: cari gardu** dengan mengetik nomor/nama (pencarian di server, 30 hasil, panah + Enter), menggantikan daftar pilih panjang.
3. **Tegangan ujung diukur sekali per gardu.** Migrasi `20261118_23`: semua nilai per jurusan diarsipkan ke `substation_values_archive`, per pengukuran dipakai nilai TERENDAH (v_ujung_min dan jatuh tegangan tetap sama), penanda (PUTUS) dipertahankan bila tidak ada angka; rumus bawaan v_ujung_min disesuaikan hanya bila belum diubah admin. Kisi dan form ponsel menampilkan blok "Tegangan Ujung JTR" R-N S-N T-N di tingkat gardu.
4. **Warna samar per jurusan** di kisi (Jurusan 1 biru, 2 hijau, 3 kuning, 4 ungu, 5 merah muda, parameter gardu abu) dan di judul kartu form ponsel. Grounding trafo + arester satu blok.
5. **ULP – Kantor Pelayanan (KP):**
   - Gardu punya "Unit pemilik" (ULP atau KP di bawahnya). ULP melihat semua gardu ULP + KP; KP hanya miliknya.
   - Master (tambah/ubah/pindah/impor) boleh oleh **admin global dan verifikator ULP** (juga saat memilih unit KP di bawahnya). Operator tidak.
   - Pengukuran dan tindak lanjut gardu KP boleh diisi **KP pemilik dan ULP induknya**; data tetap tercatat milik KP.
   - Memindahkan gardu ikut memindahkan riwayat pengukuran dan tindak lanjutnya (tercatat di riwayat master + audit).
   - Penyulang dimiliki ULP dan dipakai gardu KP. Kode gardu unik se-ULP+KP.
   - Impor master: kolom baru `unit` (kode unit KP/ULP); template menuliskannya.
   - Endpoint `/api/substations/scope` memberi tahu UI unit mana yang boleh ditulis.

## Uji
| Pemeriksaan | Hasil |
|---|---|
| `pytest backend/tests` | **214 lulus** (5 tes baru: hak ULP/KP, pindah unit, impor kolom unit, migrasi tegangan ujung termasuk rumus admin tidak ditimpa) |
| `node --test` | **94 lulus** (regresi form master, blok tegangan ujung, grounding satu blok) |
| `npm run build` | Lulus (JS 1.315 kB, gzip 371 kB) |
| PostgreSQL 16 migrasi | data uji 9a–9c: dikonversi, 6 nilai diarsip; data besar sintetis 595.242 nilai tegangan ujung: 21 dtk sekali jalan, 297.621 baris hasil, semua terarsip; dijalankan ulang tidak berubah |
| Chrome | ubah gardu + pindah ke KP tersimpan (200), kolom Unit tampil, kisi berwarna per jurusan, cari gardu di ponsel 390 px, kartu Tegangan Ujung JTR |

## Belum diuji
Ponsel fisik, Docker di LXC, data nyata Anda (jumlah nilai tegangan ujung di jurusan 2+). Bila admin sudah mengubah rumus v_ujung_min dan memakai MIN_JURUSAN(v_end_…), rumus itu perlu disesuaikan manual di Rumus & Kategori.
