#!/usr/bin/env python3
"""Tanya-jawab singkat untuk mengisi config.json (dipanggil install.sh; bisa dijalankan ulang kapan saja).

  python3 setup_wizard.py          # isi / ubah profil, rubrik, kota cuaca, kurs, Google Tasks
Tekan Enter untuk memakai nilai di [kurung], ketik - untuk mengosongkan.
"""
import json, os, sys, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "config.json")


def tanya(label, default=""):
    try:
        v = input(f"{label}" + (f" [{default}]" if default else "") + ": ").strip()
    except EOFError:
        v = ""
    v = v or default
    return "" if v == "-" else v


def ya(label, default=True):
    v = tanya(label + (" (Y/n)" if default else " (y/N)")).lower()
    return default if not v else v.startswith("y")


def daftar(s):
    return [x.strip() for x in s.split(",") if x.strip()]


def cari_kota(nama):
    u = "https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode({"name": nama, "count": 5, "language": "id"})
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "koran-pribadi/1.0"}), timeout=15) as r:
            return json.load(r).get("results", [])
    except Exception:
        return []


def pilih_kota(no, default):
    while True:
        nama = tanya(f"Kota cuaca {no} (kosongkan bila tidak perlu)", default)
        if not nama:
            return None
        hasil = cari_kota(nama)
        if not hasil:
            print("  Kota tidak ditemukan / tidak ada internet. Coba nama lain.")
            continue
        for i, h in enumerate(hasil, 1):
            print(f"  {i}. {h['name']}, {h.get('admin1', '')}, {h.get('country', '')}")
        n = tanya("  Pilih nomor", "1")
        if n.isdigit() and 1 <= int(n) <= len(hasil):
            h = hasil[int(n) - 1]
            return {"nama": h["name"], "lat": round(h["latitude"], 3), "lon": round(h["longitude"], 3)}


def main():
    src = CFG if os.path.exists(CFG) else os.path.join(HERE, "config.contoh.json")
    c = json.load(open(src, encoding="utf-8")) if os.path.exists(src) else {}
    p = c.get("profil", {})
    print("\n=== Koran Pribadi: pengaturan ===  (Enter = pakai nilai di [kurung], ketik - untuk mengosongkan)\n")

    print("1) Tentang Anda")
    nama = tanya("   Nama Anda", c.get("nama_pembaca", ""))
    pgl = tanya("   Panggilan di koran (Pak/Bu/Kak/Mas/Mbak, kosongkan bila tidak perlu)", p.get("panggilan", ""))
    kerja = tanya("   Pekerjaan / usaha Anda (mis. pemilik toko furnitur, guru SD, kontraktor interior)", p.get("pekerjaan", ""))
    usaha = tanya("   Nama usaha/kantor untuk ditampilkan di koran (boleh kosong)", "")

    print("\n2) Berita yang dipantau")
    ind = tanya("   Industri utama Anda (jadi rubrik pertama)", p.get("industri", "teknologi"))
    kk = tanya("   Kata kunci berita industri, pisahkan koma", ", ".join(p.get("kata_kunci", [])))
    t2 = tanya("   Topik kedua (mis. properti, pendidikan, otomotif; kosongkan bila tidak perlu)", p.get("topik2", ""))
    pel = ya("   Pantau peluang usaha / tender / proyek?", "peluang" in c.get("rubrik", {"peluang": 1}))
    pkk = tanya("   Kata kunci peluang, pisahkan koma", ", ".join(p.get("peluang_kata_kunci", []))) if pel else ""
    eko = ya("   Tambah rubrik Ekonomi & Bisnis?", True)
    wil = tanya("   Wilayah berita yang diutamakan", p.get("wilayah", "Indonesia"))

    print("\n3) Cuaca & kurs")
    lama = c.get("kota", [])
    kota = [k for k in (pilih_kota(1, lama[0]["nama"] if lama else "Jakarta"),
                        pilih_kota(2, lama[1]["nama"] if len(lama) > 1 else "")) if k]
    ks = tanya("   Kurs yang dipantau, kode mata uang dipisah koma (kosongkan bila tidak perlu)",
               ", ".join((c.get("kurs") or {}).get("dari", ["USD", "CNY"])))
    ke = tanya("   Dalam mata uang", (c.get("kurs") or {}).get("ke", "IDR")).upper()

    print("\n4) Task (Google Tasks)")
    gt = ya("   Tampilkan task dari Google Tasks? (butuh setup sekali, lihat docs/google-tasks.md)", bool(c.get("task_command")))

    sapa = f"{pgl} {nama}".strip()
    rub = {"industri": ind[:1].upper() + ind[1:]}
    if t2:
        rub["topik2"] = t2[:1].upper() + t2[1:]
    if pel:
        rub["peluang"] = "Peluang Usaha"
    if eko:
        rub["ekonomi"] = "Ekonomi & Bisnis"
    tengah = [k for k in ("peluang", "ekonomi") if k in rub]
    kiri = [k for k in ("industri", "topik2") if k in rub]
    if not tengah and len(kiri) > 1:
        tengah = [kiri.pop()]
    c.update({
        "nama_pembaca": nama,
        "tagline": " · ".join(x for x in (f"Untuk {sapa}" if sapa else "", usaha) if x),
        "penyusun": c.get("penyusun", "Asisten AI"),
        "profil": {"panggilan": pgl, "pekerjaan": kerja, "industri": ind, "kata_kunci": daftar(kk), "topik2": t2,
                   "peluang_kata_kunci": daftar(pkk), "wilayah": wil},
        "label_relevansi": f"Buat {pgl}" if pgl else "Buat Anda",
        "zona_waktu": c.get("zona_waktu", "Asia/Jakarta"), "label_zona": c.get("label_zona", "WIB"),
        "kota": kota,
        "kurs": {"dari": [x.upper() for x in daftar(ks)], "ke": ke} if ks else None,
        "rubrik": rub,
        "kolom": [kiri, tengah, ["_task", "_kurs"]],
        "task_command": "python3 google_tasks.py list" if gt else None,
        "web_url": c.get("web_url", ""),
    })
    json.dump(c, open(CFG, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nOK, tersimpan di {CFG}. Ubah lagi kapan saja: python3 setup_wizard.py (atau edit file-nya langsung).")
    if gt:
        print("Google Tasks: ikuti docs/google-tasks.md, lalu jalankan: python3 google_tasks.py login")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nDibatalkan, config.json tidak diubah.")
