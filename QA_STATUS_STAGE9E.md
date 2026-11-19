# QA — BerauLoad 1.6.0-stage9e — 19 November 2026

Dikerjakan langsung oleh Claude. Basis 1.6.0-stage9d5. **Kandidat staging.** Ada 1 migrasi aditif baru (`20261119_30_stage9e_advice`).

## Perubahan
1. **Saran penanganan overload** pada rincian gardu berkategori Overload: kandidat Tukar trafo dan Pindah beban dalam satu ULP, diurutkan jarak lurus dari koordinat.
2. **Satu mesin rumus.** Simulasi memakai `calculation_service` yang sama dengan Analisa; ambang overload dari aturan kategori admin (tidak ada ambang kedua). Hanya-baca: simulasi tidak menulis apa pun.
3. **Tukar trafo**: syarat fase sama; gardu X dan Z dihitung ulang dengan kVA tertukar; layak bila keduanya tidak overload. NULL tidak pernah dianggap aman.
4. **Pindah beban**: rentang persen jurusan yang dipindah dicari dengan bisection per persen bulat; layak bila X dan Z sama-sama di bawah ambang. Sebagian jurusan berarti sebagian pelanggan/cabang dan perlu survei.
5. **Tinjau** (sebelum/sesudah, slider), **Jadikan tindak lanjut** (rencana tersimpan sebagai snapshot, dihitung ulang server, duplikat terbuka ditolak 409), **Terapkan ke master** untuk Tukar trafo berstatus Selesai (hak master admin/verifikator ULP; tukar field trafo, dua baris riwayat master, audit).
6. Perbaikan kecil: Esc pada tumpukan drawer hanya menutup yang teratas.

## Penyimpangan / perilaku yang perlu diketahui
- Beban gardu = pengukuran terakhir tiap sesi, dipakai sesi dengan beban tertinggi (sama dengan Analisa), bukan sekadar yang terbaru. Bila Anda membuka dari pengukuran tertentu, pengukuran itu didahulukan.
- Pengukuran draft ikut dipakai dan diberi penanda.
- Setelah tukar trafo diterapkan, Analisa masih menampilkan Overload lama sampai gardu diukur ulang (snapshot kVA pengukuran tidak diubah).
- Saran memakai kVA master saat ini. Kandidat diperiksa 200 terdekat, `limit` 8–20 dievaluasi.
- Pindah beban tidak mengubah master (model belum punya pemetaan jurusan→gardu).
- Hanya saran: tanpa impedansi, jatuh tegangan, rugi-rugi, atau pertumbuhan beban. Jarak lurus, bukan rute jaringan. Gardu tanpa koordinat tidak jadi kandidat (di data uji ±4.531 dari 5.028 punya koordinat).
- Tes lama 9d3 diubah: jumlah jenis tindak lanjut bawaan 7 → 9 (7 kode asli tetap diperiksa ada).
- Teks "WITA" belum dihapus (permintaan terpisah).

## Uji
| Pemeriksaan | Hasil |
|---|---|
| `pytest backend/tests` | **225 lulus** (9 tes baru) |
| `node --test` | 105 lulus (6 baru) |
| `tsc -b`, `npm run build` | lulus |
| Chrome + PostgreSQL 16 (±5.000 gardu) | saran dihitung ±0,4 dtk; alur saran → tinjau (tukar & pindah, slider) → tindak lanjut → selesai → terapkan; master DM-01/DM-02 tertukar 100↔200 kVA, 2 riwayat master, audit beralasan "tukar trafo" |

## Belum diuji
Docker di LXC, data nyata, ponsel fisik, ukuran pengukuran lama (>hari), dan keputusan teknis lapangan (saran bukan pengganti survei).
