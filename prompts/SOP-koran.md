# SOP Koran Pribadi (untuk agent AI)

Untuk agent AI yang bekerja di folder repo ini. Tambahkan ke instruksi agent (mis. file instruksi proyek):
"Saat diminta membuat Koran Pagi/Sore, baca dan ikuti `prompts/SOP-koran.md`."

## Profil pembaca & rubrik
Semua ada di `config.json` (diisi lewat `./koran setup`). **Baca file itu dulu setiap membuat edisi.**
- `nama_pembaca`, `profil.panggilan`: cara menyapa pembaca di `sapaan` (mis. "Selamat pagi, Bu Sari").
- `profil.pekerjaan`: dasar menulis kolom `relevansi` ("Buat Bu: ...").
- `rubrik`: kunci rubrik → judul. Isi `berita` di JSON edisi **hanya dengan kunci yang ada di sini**.
  - `industri`: berita industri pembaca (`profil.industri`, kata kunci `profil.kata_kunci`).
  - `topik2` (bila ada): topik kedua (`profil.topik2`).
  - `peluang` (bila ada): tender / pengadaan / lead proyek sesuai `profil.peluang_kata_kunci`. Tampil sebagai tabel; isi `peluang_catatan`.
  - `ekonomi` (bila ada): ekonomi & bisnis yang berdampak ke pekerjaan pembaca.
- `profil.wilayah`: utamakan berita dari wilayah ini; berita luar boleh bila tidak ada yang segar, beri label "(global)".

Jumlah: 1–2 berita per rubrik, peluang maks. 5. Total 6–8 berita supaya PDF muat 1 halaman A4 (maksimal 2).

## Aturan redaksi
1. **Berita harus baru.** Idealnya terbit ≤3 hari terakhir, maksimal 7 hari. Cek tanggal di isi artikel, bukan hanya di hasil pencarian.
2. **Jangan mengarang.** Setiap berita wajib punya sumber (nama media + tanggal + URL). Kalau rubrik kosong, tulis apa adanya.
3. **Angka di judul dicocokkan ke artikel.** Baca kalimat lengkapnya sebelum menulis judul.
4. **Tulis ulang dengan bahasa sendiri.** Ringkas 2–3 kalimat; jangan menyalin paragraf artikel.
5. **Kolom `relevansi`** = kenapa berita ini penting buat pembaca dan apa yang bisa dilakukan (1–2 kalimat).
6. **Peluang/tender:** wajib verifikasi tahun anggaran dan jadwal di halaman detail. Agregator sering memberi label tahun yang salah. Lead dari berita (gedung baru, proyek pemda) boleh, tandai "Lead, bukan tender terbuka".
7. Jangan menembus situs yang memblokir akses otomatis atau butuh login.
8. Pilih satu berita paling penting sebagai `utama`, isi juga `deck` (1 kalimat) dan `isi_panjang` (4–6 kalimat).

## Langkah Koran Pagi
1. Ambil jadwal hari ini dari kalender (bila agent punya akses kalender). Untuk acara di luar, tulis jam berangkat yang disarankan.
2. Riset berita per rubrik (24–72 jam terakhir) sesuai aturan di atas.
3. Tulis `edisi/<YYYY-MM-DD>.json` mengikuti format `edisi/contoh.json`. Nomor `edisi` = edisi sebelumnya + 1.
   `sapaan` = 3–5 kalimat: ringkasan hari ini, hal yang perlu disiapkan, satu kalimat soal berita terpenting.
4. Jalankan `./koran edisi/<YYYY-MM-DD>.json` (atau `python3 koran.py ...`). Jangan isi `task` di JSON bila `task_command` di config sudah terisi (task diambil otomatis). Cek jumlah halaman PDF (`pdfinfo`); kalau lebih dari 2, pangkas berita.
5. Kirim ke pembaca (Telegram/WhatsApp/email): jadwal, 3 berita terpenting, file PDF atau link versi web.

## Langkah Koran Sore
Sama dengan pagi, bedanya:
- Di JSON: `"jenis": "sore"`, `"cuaca_label": "Cuaca besok"`, `"jadwal_label": "Jadwal besok"`. Cuaca otomatis untuk besok.
- `agenda` = jadwal besok.
- Berita: yang terbit hari ini, terutama sejak edisi pagi. Jangan ulang headline pagi kecuali ada perkembangan baru.
- `sapaan` dimulai "Selamat sore": ringkasan hari ini + persiapan besok.

## Privasi
- Jangan memasukkan password, nomor rekening, data klien, atau data anak ke koran yang akan dibagikan.
- File `edisi/*.json` dan `out/` berisi data pribadi; sudah di-ignore oleh `.gitignore`.
