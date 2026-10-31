# Jadwal otomatis (cron)

Contoh menjalankan agent setiap pagi 06:00 dan sore 17:00 (Linux/macOS, `crontab -e`).
Ganti `<perintah-agent>` dengan cara menjalankan agent Anda secara non-interaktif (mis. mode "print"/headless yang menerima prompt).

```cron
# m  h  *  *  *  perintah
0    6  *  *  *  cd ~/koran-pribadi && <perintah-agent> "Buatkan Koran Pagi hari ini, ikuti prompts/SOP-koran.md" >> out/cron.log 2>&1
0   17  *  *  *  cd ~/koran-pribadi && <perintah-agent> "Buatkan Koran Sore hari ini, ikuti prompts/SOP-koran.md" >> out/cron.log 2>&1
```

Pastikan zona waktu server sesuai (`timedatectl` di Linux), atau sesuaikan jamnya.

Mau cetak otomatis? Setelah PDF jadi, kirim ke printer dengan `lp out/koran-pagi-$(date +%F).pdf` (CUPS).
