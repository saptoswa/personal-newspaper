# Sinkron Google Tasks (sekali setup, ±10 menit)

Koran akan menampilkan task yang **belum selesai** dari Google Tasks Anda. Aksesnya **hanya baca**: koran tidak bisa menambah, mengubah, atau menghapus task.

Google mewajibkan setiap aplikasi punya "kunci OAuth" sendiri. Kunci ini gratis, dibuat sekali di Google Cloud.

## 1. Buat project & aktifkan Tasks API
1. Buka https://console.cloud.google.com → login dengan akun Google yang punya task-nya.
2. Klik pilihan project di kiri atas → **New Project** → nama bebas, mis. `koran-pribadi` → **Create**.
3. Buka https://console.cloud.google.com/apis/library/tasks.googleapis.com → pastikan project tadi terpilih → **Enable**.

## 2. Atur layar izin (OAuth consent screen)
1. Menu **APIs & Services → OAuth consent screen** (atau "Google Auth Platform").
2. User type: **External** → isi nama aplikasi (mis. `Koran Pribadi`) dan email Anda → simpan.
3. Bagian **Audience / Test users** → **Add users** → masukkan email Google Anda sendiri.
4. **Disarankan:** klik **Publish app** (status jadi "In production"). Kalau dibiarkan "Testing",
   Google mencabut login setiap 7 hari dan task di koran berhenti muncul sampai Anda login ulang.
   Tidak perlu verifikasi Google untuk pemakaian pribadi; Anda hanya akan melihat peringatan "unverified app" saat login.

## 3. Buat kunci OAuth
1. Menu **APIs & Services → Credentials → Create credentials → OAuth client ID**.
2. Application type: **Desktop app** → nama bebas → **Create**.
3. Klik **Download JSON**. Simpan file-nya, mis. ke folder `koran-pribadi` dengan nama `kunci.json`.

## 4. Sambungkan
```bash
cd ~/koran-pribadi
.venv/bin/python google_tasks.py setup kunci.json   # kunci disalin ke ~/.config/koran-pribadi (izin 600)
rm kunci.json                                       # file asli boleh dihapus
.venv/bin/python google_tasks.py login
```
Buka link yang muncul → pilih akun → bila ada peringatan "Google hasn't verified this app", klik **Continue** (ini aplikasi Anda sendiri) → **Allow**.

- **Di laptop/PC sendiri:** login selesai otomatis.
- **Di server/VPS:** setelah Allow, browser membuka `http://localhost:8765/?code=...` yang gagal dimuat. Itu normal. Copy seluruh alamatnya, lalu:
  ```bash
  .venv/bin/python google_tasks.py code 'http://localhost:8765/?code=....'
  ```

## 5. Cek & aktifkan di koran
```bash
.venv/bin/python google_tasks.py lists          # daftar task list Anda
.venv/bin/python google_tasks.py list           # task belum selesai (list utama)
```
Lalu di `config.json`:
```json
"task_command": "python3 google_tasks.py list"
```
Mau list tertentu? `"python3 google_tasks.py list --list \"Kerjaan\""`.
(`./koran setup` juga bisa mengisi ini otomatis bila Anda jawab "y" di pertanyaan Google Tasks.)

## Catatan keamanan
- Kunci dan token tersimpan di `~/.config/koran-pribadi/`, **di luar** folder repo, jadi tidak ikut ter-push ke GitHub.
- Mau mencabut akses: https://myaccount.google.com/permissions → hapus "Koran Pribadi".
- Bila task tiba-tiba tidak muncul (token kedaluwarsa, mis. aplikasi masih "Testing"), jalankan `google_tasks.py login` lagi.
