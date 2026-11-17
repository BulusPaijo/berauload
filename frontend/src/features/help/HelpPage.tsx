import {useBranding} from '../branding/BrandingContext';
import {useState} from 'react';
import {BookOpen,Printer,Search} from 'lucide-react';
import './help.css';

type Topic={name:string;summary:string;items:string[]};
const TOPICS:Topic[]=[
 {name:'1. Masuk & Navigasi',summary:'Login dan pengenalan menu',items:[
  'Buka http://IP-LXC:8092 atau alamat internal resmi, lalu masuk menggunakan akun yang diberikan admin.',
  'Sidebar memuat Dashboard, Input Beban, Data Historis, Analisis Beban, Pembangkit, Feeder, Laporan, Import, Pengaturan, dan Dashboard Builder.',
  'Zona waktu pencatatan adalah WITA (Asia/Makassar). Gunakan tombol Keluar setelah selesai, terutama pada komputer bersama.']},
 {name:'2. Peran Pengguna',summary:'Operator, verifier, management dan admin',items:[
  'Operator menginput dan memperbaiki data draft. Verifier memeriksa serta memfinalisasi; admin mengelola master, pengguna, dan aturan.',
  'Management menggunakan dashboard, analisis, dan laporan secara baca-saja. Hak akses dinilai oleh server, bukan hanya tombol UI.',
  'Dashboard pribadi dapat dikelola masing-masing pengguna. Dashboard sistem hanya dapat diubah admin.']},
 {name:'3. Input Beban Harian',summary:'Pencatatan tiap jam dan koreksi',items:[
  'Buka Input Beban Harian, pilih tanggal, lalu pilih tab yang diatur admin. Nama dan urutannya bisa berbeda dari template lama.',
  'Isi pembacaan per jam untuk parameter bertipe Input. Nilai Computed dihitung engine; tanda kosong (—) tidak sama dengan angka nol.',
  'Klik Simpan. Periksa data 24 jam dan pastikan jam kosong tidak diisi nol kecuali benar-benar hasil pembacaan.',
  'Hari draft dapat diperbaiki. Hari verified/final terkunci. Pembukaan kembali memerlukan admin dan alasan yang tercatat.']},
 {name:'4. Import Excel Historis',summary:'Migrasi workbook bulanan',items:[
  'Buka Import Excel; unggah workbook bulanan yang menggunakan format laporan {branding.app_name} dan pilih periode yang benar.',
  'Klik Pratinjau sebelum commit. Teliti jumlah jam, nilai, peringatan, duplikat, serta konflik dengan data yang sudah tercatat.',
  'File dengan format berbeda perlu diperiksa/manual mapping. Jangan menganggap semua sheet kosong berisi angka nol.',
  'Commit hanya setelah pratinjau benar. Simpan workbook asli sebagai bukti; proses tidak boleh menimpa data final secara diam-diam.']},
 {name:'5. Dashboard Operasi',summary:'KPI dan grafik H/J',items:[
  'Dashboard utama sekarang mengikuti dashboard default dari Dashboard Builder (default pribadi bila ada, jika tidak maka default sistem). Tombol Tampilan Klasik tetap menyediakan dashboard lama.',
  'Daya mampu historis bersumber dari kolom H REKAP dan beban sistem dari kolom J. Parameter utama kini ditentukan oleh kunci peran system.capacity dan system.load per unit.',
  'Kedua seri dibandingkan berdasarkan jam berpasangan. Data yang belum ada tetap kosong; grafik bukan monitoring SCADA real-time.',
  'Gunakan Pilih Parameter untuk mengubah seri grafik lama dan menyimpan preferensi pribadi atau default sistem.']},
 {name:'6. Pengaturan Peralatan & Parameter',summary:'Tambah master dan sumber data',items:[
  'Admin membuka Pengaturan → Master Peralatan untuk Tambah/Edit menggunakan drawer. Daftar menampilkan Aktif secara default; pilih Nonaktif atau Semua untuk arsip operasional.',
  'Pengaturan → Jenis Peralatan memungkinkan admin membuat kategori sendiri, mengganti nama, atau menonaktifkannya. Kode unik yang sudah dibuat tidak berubah.',
  'Pengaturan → Parameter digunakan menambah Input atau Computed. Input berisi nilai operator/import; Computed dihitung oleh Formula Engine.',
  'Kelompok sumber data (untuk laporan/Excel) berbeda dengan tab Form Input yang bisa dibuat sendiri. Parameter Input baru dapat langsung ditempatkan pada tab pilihan. Jangan mengubah kelompok sumber lama hanya untuk mengubah tampilan.',
  'Parameter daya mampu manual legacy dari V1.1 bukan sumber grafik resmi; gunakan parameter kolom H.']},
 {name:'6A. Mengatur Tab & Kolom Input Harian (V1.4.2)',summary:'Admin mengatur formulir tanpa mengubah pembacaan',items:[
  'Buka Pengaturan → Mulai di sini untuk urutan langkah. Buat peralatan, parameter, lalu masuk Tab & Kolom Input.',
  'Pada pengaturan tab, tambah tab baru atau ubah nama tab lama, atur urutan dengan tombol naik/turun. Kode tab tetap tidak berubah.',
  'Pilih tab di sebelah kiri. Pada tabel kolom, gunakan pilihan Tab Tujuan untuk memindahkan parameter, ikon Tampilkan/Sembunyikan untuk mengatur visibilitas, dan tombol naik/turun untuk mengatur urutan.',
  'Klik Simpan Perubahan dan muat ulang Input Beban Harian. Tombol Batal membuang pengaturan draft yang belum disimpan.',
  'Parameter Input dapat diisi operator, Computed tetap read-only, dan Imported mengikuti sumber yang tersedia. Menyembunyikan kolom tidak menghapus data histori atau pengukuran.',
  'Tab yang nonaktif tidak ditampilkan pada formulir operator, tetapi konfigurasi dan data lama tetap tersimpan. Sembunyikan parameter bila perlu, bukan menghapus kode lama.',
  'Perubahan tab tidak mengubah pemetaan kolom workbook Excel. File Excel dengan layout berbeda memerlukan penyesuaian importer tersendiri.',
  'V1.4.2 belum menerapkan kewajiban pengisian per parameter (required) karena aturan finalisasi historis belum ditetapkan. Semua pemeriksaan kualitas lama tetap berlaku.']},
 {name:'6B. Master Satuan (V1.4.2.1)',summary:'Admin menambah satuan dan memeriksa faktor konversi',items:[
  'Pengaturan → Master Satuan. Satuan standar sudah tersedia. Satuan custom dibuat melalui tombol Tambah Satuan.',
  'Pilih simbol, nama, jenis besaran, serta faktor terhadap satuan dasar. Faktor dan dimensi satuan bersifat permanen setelah disimpan.',
  'Contoh: MW dan kW sama-sama daya aktif, dengan faktor MW=1000 dan kW=1. Daya aktif kW tidak dapat langsung dikonversi menjadi daya semu kVA.',
  'Parameter Input, Computed, Perhitungan Historis, dan Engineering Rules sekarang memilih satuan dari daftar yang sama.',
  'Nilai pengukuran lama tidak pernah ditulis ulang akibat perubahan tampilan atau konversi grafik.']},
 {name:'7. Formula Engine V1.1',summary:'Perhitungan tanpa Python',items:[
  'Saat membuat parameter Computed, pilih parameter sumber dan susun ekspresi dengan operasi +, −, ×, ÷, SUM, AVG, MIN, MAX, IF sesuai dukungan editor.',
  'Gunakan Uji/Simulasi sebelum Simpan. Nilai kosong, pembagian nol, dan satuan yang tidak sesuai harus diperiksa.',
  'Computed dapat bergantung pada computed lain selama tidak membuat referensi melingkar.',
  'Formula existing tidak diubah diam-diam; periksa konsekuensi perubahan sebelum mengaktifkan definisi baru.']},
 {name:'8. Analisis & Perhitungan Historis',summary:'Rumus lintas jam/hari/bulan/tahun',items:[
  'Buka Analisis Beban → Perhitungan Historis. Pilih contoh atau buat rumus, metode AVG/MAX/MIN/SUM, periode, dan jam tertentu.',
  'Contoh: rata-rata cadangan, puncak beban malam, jumlah jam melebihi daya mampu, moving average, dan YoY.',
  'Perhitungan yang berubah dibuat sebagai revisi baru. Daftar hanya menampilkan Aktif secara default; gunakan filter Arsip/ Semua untuk menemukan dan memulihkan formula lama.',
  'Saat memeriksa hasil selalu lihat jumlah jam valid dan coverage. Data parsial tidak boleh disimpulkan sebagai periode lengkap.']},
 {name:'9. Engineering Rules V1.3',summary:'Status teknis berdasarkan rule yang disahkan',items:[
  'Buka Analisis Beban → Engineering Rules. Admin membuat draft: nama, formula, arah ambang, batas waspada/kritis, satuan, dasar ketentuan, dan tanggal berlaku.',
  'Lakukan simulasi, lalu aktifkan secara eksplisit. Tidak ada batas teknis PLN yang ditetapkan otomatis oleh sistem.',
  'Revisi aturan membuat draft baru, sedangkan versi lama tetap dapat diaudit. Daftar menampilkan Aktif secara default; pilih Draft, Arsip atau Semua untuk jenis lain.',
  'Output Normal/Waspada/Kritis hanya interpretasi data tercatat; bukan alarm SCADA atau perintah pengoperasian jaringan.']},
 {name:'10. Dashboard Builder V1.4',summary:'Tambah panel, tata layout, default sistem/pribadi',items:[
  'Buka Dashboard Builder dan klik Dashboard Baru. Pilih Pribadi (semua peran) atau Sistem (admin).',
  'Klik Edit Layout → Tambah Panel. Pilih sumber Parameter, Perhitungan Historis, atau Engineering Rules lalu tipe Grafik/KPI/Gauge/Tabel/Status.',
  'Pada mode edit, geser panel untuk mengubah urutan; gunakan kontrol lebar atau tombol panah jika memakai HP/keyboard. Simpan Perubahan untuk mengirim perubahan ke server; Batal atau Reset ke Tersimpan untuk membuang draft tanpa mengubah database.',
  'Gunakan Duplikat untuk menyalin dashboard sistem menjadi pribadi. Klik Jadikan Default untuk menentukan dashboard yang ditampilkan pada menu Dashboard utama. Default pribadi lebih diutamakan daripada default sistem.',
  'Pilihan periode Harian/Bulanan/Tahunan/Kustom berlaku untuk semua panel. Grafik H/J berpasangan dan hanya menggunakan agregasi AVG.',
  'Mengarsipkan dashboard atau menghapus sebuah panel tidak menghapus parameter, formula, ataupun data historis.']},
 {name:'10A. Advanced Visualization (V1.4.3)',summary:'Warna, konversi, legenda dan jenis grafik',items:[
  'Dashboard Builder → Edit Layout → ikon pensil panel. Tersedia jenis garis, area, batang, tangga, batang bertumpuk, KPI, gauge dan tabel.',
  'Pada bagian Pengaturan Grafik & Tampilan, pilih warna setiap seri, posisi legenda, angka desimal, serta apakah titik pengukuran akan ditampilkan.',
  'Satuan tampilan bisa dipilih dari dimensi yang kompatibel. Contoh 48.000 kW terlihat sebagai 48 MW; database tetap menyimpan 48.000 kW.',
  'Agregasi AVG, MAX/Puncak, MIN memiliki arti berbeda. Menjumlahkan nilai kW tidak menghasilkan kWh tanpa definisi integrasi energi.',
  'Grafik H/J tetap berpasangan dan tidak boleh dibuat menjadi stacked bar. Tooltip menunjukkan waktu/periode WITA.',
  'Terapkan ke Dashboard lalu Simpan Perubahan. Gunakan Batal untuk membatalkan perubahan yang belum disimpan.']},
 {name:'10B. Dashboard Management V1.4.4',summary:'Template dashboard, share, versi dan konfigurasi JSON',items:[
  'Buka Dashboard Builder → Buka Pengaturan pada Kelola Dashboard. Pilih template Operasi/Pembangkit/Feeder lalu buat sebagai dashboard pribadi.',
  'Klik Unduh Konfigurasi JSON untuk menyimpan susunan panel. Impor JSON membuat dashboard pribadi baru, tidak memindahkan data listrik maupun akun.',
  'Pada Riwayat Layout, pilih versi terdahulu lalu Pulihkan. Versi baru dibuat; perubahan lama tetap tercatat.',
  'Pemilik dashboard pribadi dapat membagikan ke username lain dengan hak baca-saja dan mencabut aksesnya kembali.',
  'Dashboard sistem tetap terlihat oleh pengguna yang berwenang; hanya admin yang dapat mengubahnya. Jangan bagikan JSON berisi nama panel sensitif ke pihak luar.']},
 {name:'11A. Export Data Custom V1.4.4',summary:'CSV/Excel dengan kolom dan template sendiri',items:[
  'Buka Laporan → Export Data Excel / CSV. Pilih tanggal awal dan akhir serta resolusi jam, hari, bulan, atau tahun.',
  'Pilih parameter dari daftar. Gunakan tombol naik/turun untuk menentukan urutan kolom, dan ubah judul bila diperlukan. Kolom Tanggal wajib ada.',
  'Untuk resolusi harian/bulanan/tahunan pilih AVG, MAX, atau MIN. Perhitungan dilakukan per parameter berdasarkan pembacaan yang tersedia; jangan menyamakan rata-rata data parsial dengan periode lengkap.',
  'Satuan dapat dikonversi pada tampilan ekspor jika satu dimensi (contoh kW → MW). Satuan asal pada database tidak berubah.',
  'Klik Preview 10 Baris lalu Unduh XLSX atau CSV. CSV menggunakan UTF-8 BOM dan pemisah titik koma. Sel kosong tetap kosong, tidak menjadi nol.',
  'Untuk format yang dipakai berulang, isi nama template lalu simpan sebagai Pribadi atau Bersama (admin). Template yang dipilih dapat diperbarui atau diarsipkan.',
  'Batas permintaan saat ini 10 tahun dan maksimal 45 kolom. Data parameter yang belum pernah dicatat mungkin kosong; kalkulasi lintas waktu tersendiri tidak otomatis menjadi kolom ekspor.']},
 {name:'11. Laporan & Perbandingan',summary:'Grafik YoY, export Excel dan PDF',items:[
  'Buka Laporan & Perbandingan untuk memilih rentang tanggal serta mengekspor laporan sesuai fitur yang disediakan.',
  'Perbandingan antar-tahun harus memakai periode setara; tahun berjalan dan data parsial wajib diberi penanda.',
  'Untuk output resmi, pastikan hari dan rumus yang digunakan sudah diverifikasi dan sumber data dapat ditelusuri.']},
 {name:'11B. Laporan Kustom V1.4.6',summary:'Membuat laporan dari komponen pilihan',items:[
  'Buka Laporan & Perbandingan → Laporan Kustom. Klik Baru, beri nama, lalu tambah bagian Judul, Paragraf, KPI, Grafik, atau Tabel.',
  'Untuk KPI/Grafik/Tabel pilih parameter dari master dan metode AVG, MIN atau MAX; pilih resolusi Jam/Hari/Bulan untuk tabel/grafik.',
  'Gunakan tombol panah untuk mengatur urutan bagian. Klik Pratinjau untuk melihat nilai dalam rentang tanggal, lalu Simpan.',
  'Setelah disimpan pilih PDF atau Excel. Laporan klasik tetap ada; CSV fleksibel tersedia di menu Export Data Excel / CSV.',
  'Perbandingan dua parameter memakai jam pengukuran yang sama; jika salah satu tidak tersedia, celah tetap kosong.',
  'Template Sistem hanya dapat dibuat/diubah admin. Template Pribadi hanya boleh diubah pemilik. Duplikat dan Arsip tidak menghapus data sumber.']},
 {name:'10D. Gaya Panel Dashboard V1.4.6',summary:'Warna, ukuran font, latar dan preset',items:[
  'Buka Dashboard Builder → Edit Layout → ikon pensil panel → Gaya Panel & Tipografi.',
  'Pilih preset Klasik, Gelap atau Lembut, ukuran judul (11–24 px), ukuran angka KPI (18–54 px), jenis font, serta warna teks/latar/bingkai.',
  'Gunakan tombol Otomatis jika ingin warna mengikuti preset. Terapkan ke Dashboard lalu Simpan Perubahan untuk menyimpan.',
  'Perubahan gaya tidak mengubah parameter, formula, pengukuran atau laporan historis.']},
 {name:'13. Topologi Single Line — Mode Edit V1.5.0 Tahap 3',summary:'Admin membuat diagram dan memindahkan kotak parameter',items:[
  'Buka Monitoring → Topologi. Admin memilih Diagram Baru untuk membuat diagram kosong, lalu klik Edit Diagram.',
  'Di kiri, pilih peralatan dan parameter aktif, kemudian Tambah Kotak. Kotak baru tidak membuat sambungan listrik dan hanya menyimpan referensi parameter.',
  'Klik kotak untuk membuka Properti Kotak. Ubah judul, peralatan, centang 1–6 parameter, atur urutan dengan tombol naik/turun, lebar, X/Y, desimal, satuan, rule aktif, jangkar, dan kunci posisi.',
  'Geser kotak dengan mouse atau sentuhan pada kanvas; posisi mengikuti grid 10 px. Tersedia Urungkan, Ulangi, Reset ke Tersimpan, Batal, dan Simpan Perubahan.',
  'Buat draf dari daftar peralatan hanya menempatkan simbol tanpa menggambar sambungan. Penataan garis dan palet simbol penuh disiapkan untuk Tahap 4.',
  'Riwayat Revisi bisa dipulihkan sebagai versi baru. Jika muncul konflik versi, muat ulang agar perubahan pengguna lain tidak tertimpa.',
  'Kotak parameter yang baru belum menampilkan pembacaan sebelum disimpan dan dimuat ulang. Operator/manajemen tetap menggunakan Mode Lihat tanpa tombol edit.',
  'Peringatan meninggalkan halaman berlaku saat draf belum disimpan. Nilai kosong tetap “—”, nol tetap 0, dan status PMT tidak pernah diasumsikan.' ]},
 {name:'12. Keamanan & Perawatan',summary:'Backup, user, gangguan dan audit',items:[
  'Admin membuat akun pengguna, memilih role, dan menonaktifkan akses bila diperlukan. Jangan membagikan akun admin atau mengirim password di log/chat.',
  'Sebelum upgrade, jalankan ./deploy/backup.sh di direktori proyek aktif; pastikan hasil backup database dan arsip Excel tersedia.',
  'Gunakan docker compose ps, docker compose logs --tail=100 backend/web, dan ./deploy/smoke-test.sh saat masalah muncul.',
  'Jangan jalankan docker compose down -v atau menghapus volume pgdata; tindakan tersebut dapat menghilangkan database.',
  'Perubahan source harus dibackup, diuji, dan dipasang dalam tahap kecil. Aplikasi digunakan melalui jaringan internal/VPN.']},
];

export default function HelpPage({version}:{version:string}){
 const {branding}=useBranding();
  const [query,setQuery]=useState('');
  const filtered=TOPICS.filter(t=>`${t.name} ${t.summary} ${t.items.join(' ')}`.toLowerCase().includes(query.toLowerCase()));
  return <div className="page-space help-page"><div className="page-top"><div>
    <div className="eyebrow">PANDUAN PENGGUNA</div><h2>Petunjuk {branding.app_name} V{version}</h2>
    <p>Alur penggunaan lengkap untuk operator, pengawas, admin, dan manajemen.</p></div>
    <button className="btn secondary" onClick={()=>window.print()}><Printer size={16}/> Cetak / Simpan sebagai PDF</button></div>
    <div className="panel help-search"><Search size={19}/><input aria-label="Cari topik panduan" placeholder="Cari topik: import, parameter, formula, dashboard..." value={query} onChange={e=>setQuery(e.target.value)}/>
      <span>{filtered.length} topik</span></div>
    <div className="help-grid"><nav className="panel help-index"><strong><BookOpen size={16}/> Daftar Isi</strong>
      {filtered.map((t,i)=><a key={t.name} href={`#help-${TOPICS.indexOf(t)+1}`}>{t.name}</a>)}</nav>
      <article className="help-content">{filtered.map(t=><section id={`help-${TOPICS.indexOf(t)+1}`} className="panel help-section" key={t.name}>
        <h3>{t.name}</h3><p>{t.summary}</p><ol>{t.items.map((x,i)=><li key={i}>{x.replaceAll('BerauLoad',branding.app_name)}</li>)}</ol>
      </section>)}{!filtered.length&&<div className="panel">Tidak ditemukan topik yang sesuai.</div>}</article></div>
    <div className="panel help-footer"><strong>Catatan keselamatan data</strong><p>{branding.app_name} adalah aplikasi pencatatan dan analisis data operasional. Hasil rule tidak boleh dijadikan satu-satunya dasar keputusan manuver atau kendali real-time.</p></div>
  </div>;
}
