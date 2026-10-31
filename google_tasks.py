#!/usr/bin/env python3
"""Ambil task Google Tasks untuk kotak "Task belum selesai" di koran (hanya BACA, tanpa library tambahan).

Setup sekali (panduan lengkap: docs/google-tasks.md):
  python3 google_tasks.py setup kunci.json       # file OAuth client (Desktop app) dari Google Cloud
  python3 google_tasks.py login                  # buka link, izinkan, selesai
Pemakaian:
  python3 google_tasks.py lists                  # daftar task list
  python3 google_tasks.py list [--list NAMA]     # task belum selesai, satu per baris (dipakai koran.py)

Di config.json:  "task_command": "python3 google_tasks.py list"
Kunci & token disimpan di ~/.config/koran-pribadi/ (izin 600). Jangan ikut di-commit.
"""
import argparse, http.server, json, os, sys, threading, time, urllib.error, urllib.parse, urllib.request

DIR = os.path.expanduser("~/.config/koran-pribadi")
CLIENT = os.path.join(DIR, "google-client.json")
TOKEN = os.path.join(DIR, "google-tasks-token.json")
SCOPE = "https://www.googleapis.com/auth/tasks.readonly"
PORT = 8765
REDIRECT = f"http://localhost:{PORT}"
API = "https://tasks.googleapis.com/tasks/v1"


def simpan(path, data):
    os.makedirs(DIR, mode=0o700, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)


def post_form(url, data):
    req = urllib.request.Request(url, urllib.parse.urlencode(data).encode())
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR {e.code}: {e.read().decode()[:300]}")


def klien():
    if not os.path.exists(CLIENT):
        sys.exit("Belum setup. Jalankan: python3 google_tasks.py setup <file-kunci.json>  (lihat docs/google-tasks.md)")
    return json.load(open(CLIENT))


def tukar_kode(code):
    c = klien()
    r = post_form("https://oauth2.googleapis.com/token", {"code": code, "client_id": c["client_id"], "client_secret": c["client_secret"],
                                                         "redirect_uri": REDIRECT, "grant_type": "authorization_code"})
    if "refresh_token" not in r:
        sys.exit("Google tidak memberi refresh_token. Ulangi: python3 google_tasks.py login")
    simpan(TOKEN, {"refresh_token": r["refresh_token"], "access_token": r["access_token"], "expires_at": time.time() + r.get("expires_in", 3600)})
    print("OK, login berhasil. Coba: python3 google_tasks.py list")


def token():
    if not os.path.exists(TOKEN):
        sys.exit("Belum login. Jalankan: python3 google_tasks.py login")
    t, c = json.load(open(TOKEN)), klien()
    if t.get("expires_at", 0) - 60 > time.time():
        return t["access_token"]
    r = post_form("https://oauth2.googleapis.com/token", {"client_id": c["client_id"], "client_secret": c["client_secret"],
                                                         "refresh_token": t["refresh_token"], "grant_type": "refresh_token"})
    t.update(access_token=r["access_token"], expires_at=time.time() + r.get("expires_in", 3600))
    simpan(TOKEN, t)
    return t["access_token"]


def get(path, params=None):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token()})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR {e.code}: {e.read().decode()[:300]}")


def login():
    c = klien()
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": c["client_id"], "redirect_uri": REDIRECT, "response_type": "code",
        "scope": SCOPE, "access_type": "offline", "prompt": "consent"})
    hasil = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            hasil["code"] = (q.get("code") or [None])[0]
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
            self.wfile.write("<h2>Login berhasil. Tutup tab ini dan kembali ke terminal.</h2>".encode())

        def log_message(self, *a):
            pass

    print("\n1) Buka link ini di browser, pilih akun Google Anda, lalu klik Izinkan:\n\n" + url + "\n")
    print("2) Kalau browser ada di komputer yang sama, login selesai otomatis.")
    print("   Kalau ini server/VPS: setelah klik Izinkan, browser membuka alamat 'localhost:8765/?code=...'")
    print("   yang gagal dimuat. Itu normal. Copy seluruh alamat itu, lalu jalankan:")
    print("   python3 google_tasks.py code '<alamat yang di-copy>'\n")
    try:
        srv = http.server.HTTPServer(("127.0.0.1", PORT), H)
    except OSError:
        return
    srv.timeout = 1
    t0 = time.time()
    while not hasil and time.time() - t0 < 300:
        srv.handle_request()
    srv.server_close()
    if hasil.get("code"):
        tukar_kode(hasil["code"])
    else:
        print("Belum ada login dalam 5 menit. Pakai cara 'code' di atas, atau ulangi login.")


def main():
    ap = argparse.ArgumentParser(description="Google Tasks (baca saja) untuk koran pribadi")
    ap.add_argument("cmd", choices=["setup", "login", "code", "lists", "list"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--list", help="nama atau ID task list (default: list utama)")
    a = ap.parse_args()
    if a.cmd == "setup":
        if not a.arg or not os.path.exists(a.arg):
            sys.exit("Pakai: python3 google_tasks.py setup <file-kunci.json yang didownload dari Google Cloud>")
        j = json.load(open(a.arg))
        j = j.get("installed") or j.get("web") or j
        simpan(CLIENT, {"client_id": j["client_id"], "client_secret": j["client_secret"]})
        print(f"OK, kunci tersimpan di {CLIENT}. Sekarang: python3 google_tasks.py login")
    elif a.cmd == "login":
        login()
    elif a.cmd == "code":
        code = (a.arg or "").strip()
        if "code=" in code:
            code = urllib.parse.parse_qs(urllib.parse.urlparse(code).query)["code"][0]
        tukar_kode(code)
    elif a.cmd == "lists":
        for l in get("/users/@me/lists").get("items", []):
            print(f'{l["title"]}  (id {l["id"]})')
    elif a.cmd == "list":
        lid = "@default"
        if a.list:
            ls = get("/users/@me/lists").get("items", [])
            hit = [l for l in ls if a.list in (l["id"], l["title"])]
            if not hit:
                sys.exit("Task list tidak ditemukan: " + a.list)
            lid = hit[0]["id"]
        for t in get(f"/lists/{lid}/tasks", {"showCompleted": "false", "maxResults": 100}).get("items", []):
            if t.get("title", "").strip():
                due = f' (batas {t["due"][8:10]}/{t["due"][5:7]})' if t.get("due") else ""
                print(t["title"].strip() + due)


if __name__ == "__main__":
    main()
