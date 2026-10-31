#!/usr/bin/env bash
# Installer Koran Pribadi: download, pasang kebutuhan, tanya-jawab pengaturan, lalu buat contoh koran.
#   curl -fsSL https://raw.githubusercontent.com/saptoswa/personal-newspaper/main/install.sh | bash
# atau dari dalam folder repo:  bash install.sh
set -euo pipefail

REPO="${KORAN_REPO:-https://github.com/saptoswa/personal-newspaper.git}"
DIR="${KORAN_DIR:-$HOME/koran-pribadi}"

hijau() { printf '\033[32m%s\033[0m\n' "$*"; }
kuning() { printf '\033[33m%s\033[0m\n' "$*"; }
gagal() { printf '\033[31m%s\033[0m\n' "$*" >&2; exit 1; }

hijau "== Koran Pribadi: instalasi =="

# 1. Cek kebutuhan dasar
command -v python3 >/dev/null || gagal "Python 3 belum terpasang. Ubuntu/Debian: sudo apt install python3 python3-venv · macOS: brew install python"
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || gagal "Butuh Python 3.10 atau lebih baru (sekarang: $(python3 -V))."

# 2. Ambil kode (lewati bila installer dijalankan dari dalam folder repo)
if [ -f "./koran.py" ] && [ -f "./setup_wizard.py" ]; then
  DIR="$(pwd)"
elif [ -d "$DIR/.git" ]; then
  hijau "Folder $DIR sudah ada, memperbarui..."
  git -C "$DIR" pull --ff-only || kuning "Gagal update (ada perubahan lokal?). Lanjut dengan versi yang ada."
else
  command -v git >/dev/null || gagal "git belum terpasang. Ubuntu/Debian: sudo apt install git · macOS: xcode-select --install"
  git clone --depth 1 "$REPO" "$DIR"
fi
cd "$DIR"
hijau "Folder: $DIR"

# 3. Lingkungan Python terpisah (.venv) + WeasyPrint untuk PDF
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv 2>/dev/null || gagal "Gagal membuat venv. Ubuntu/Debian: sudo apt install python3-venv, lalu jalankan installer lagi."
fi
.venv/bin/python -m pip install -q --upgrade pip >/dev/null
.venv/bin/python -m pip install -q -r requirements.txt
PDF=1
if ! .venv/bin/python -c "import weasyprint" 2>/dev/null; then
  PDF=0
  kuning "WeasyPrint terpasang tapi library sistemnya (Pango) belum ada, jadi PDF belum bisa dibuat."
  kuning "  Ubuntu/Debian: sudo apt install libpango-1.0-0 libpangoft2-1.0-0   ·   macOS: brew install pango"
  kuning "  Versi web (HTML) tetap jalan. Setelah dipasang, PDF otomatis ikut dibuat."
fi

# 4. Tanya-jawab pengaturan (dibaca dari terminal walau installer dijalankan lewat curl | bash)
if (exec </dev/tty) 2>/dev/null; then
  .venv/bin/python setup_wizard.py < /dev/tty
else
  kuning "Terminal tidak interaktif: lewati tanya-jawab. Jalankan nanti: .venv/bin/python setup_wizard.py"
fi

# 5. Perintah singkat ./koran
cat > koran <<'EOF'
#!/usr/bin/env bash
# Pakai: ./koran edisi/<tanggal>.json   (atau ./koran setup untuk mengubah pengaturan)
cd "$(dirname "$0")"
if [ "${1:-}" = "setup" ]; then exec .venv/bin/python setup_wizard.py; fi
exec .venv/bin/python koran.py "$@"
EOF
chmod +x koran

# 6. Coba buat koran contoh
hijau "Membuat koran contoh..."
if [ "$PDF" = 1 ]; then ./koran edisi/contoh.json >/dev/null; else ./koran edisi/contoh.json --no-pdf >/dev/null; fi

hijau "
Selesai! Koran contoh ada di:
  $DIR/out/koran-pagi.html$( [ "$PDF" = 1 ] && printf '\n  %s' "$DIR/out/koran-pagi-2026-11-02.pdf" )

Langkah berikutnya:
  1. Buka folder ini dengan agent AI Anda, lalu bilang:
     \"Buatkan Koran Pagi hari ini, ikuti prompts/SOP-koran.md\"
  2. Ubah pengaturan kapan saja:  ./koran setup
  3. Task dari Google Tasks:      lihat docs/google-tasks.md
  4. Jadwal otomatis pagi/sore:   lihat docs/jadwal.md"
