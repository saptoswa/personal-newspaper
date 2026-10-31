#!/usr/bin/env python3
"""Koran Pribadi: koran harian (pagi/sore) bergaya surat kabar, disusun agent AI, jadi HTML + PDF A4.

  python3 koran.py edisi/contoh.json            -> out/koran-pagi.html + out/koran-pagi-<tanggal>.pdf
  python3 koran.py edisi/contoh.json --no-pdf   -> HTML saja (tanpa WeasyPrint)

Isi redaksi (sapaan, jadwal, berita) ditulis agent ke file JSON edisi (lihat edisi/contoh.json).
Data live diambil otomatis tanpa kunci API: cuaca (Open-Meteo) dan kurs (Frankfurter / ECB).
Pengaturan (nama, kota cuaca, kurs, rubrik, susunan kolom) ada di config.json.
"""
import argparse, html, json, os, shlex, subprocess, sys, urllib.request
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
E = lambda s: html.escape(str(s))
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
BULAN = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
WMO = {0: "Cerah", 1: "Cerah berawan", 2: "Berawan sebagian", 3: "Mendung", 45: "Berkabut", 48: "Berkabut",
       51: "Gerimis ringan", 53: "Gerimis", 55: "Gerimis lebat", 61: "Hujan ringan", 63: "Hujan sedang", 65: "Hujan lebat",
       80: "Hujan lokal ringan", 81: "Hujan lokal", 82: "Hujan lokal lebat", 95: "Badai petir", 96: "Badai petir", 99: "Badai petir"}


# ---------- data live ----------
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "koran-pribadi/1.0"}), timeout=25) as r:
        return json.load(r)


def cuaca(cfg, tgl):
    out = []
    tz = cfg.get("zona_waktu", "Asia/Jakarta").replace("/", "%2F")
    for k in cfg["kota"]:
        try:
            d = get(f"https://api.open-meteo.com/v1/forecast?latitude={k['lat']}&longitude={k['lon']}"
                    f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
                    f"&hourly=precipitation_probability&timezone={tz}&start_date={tgl}&end_date={tgl}")
        except Exception as e:
            print(f"cuaca {k['nama']} gagal: {e}", file=sys.stderr)
            continue
        jam = [(t[-5:], p or 0) for t, p in zip(d["hourly"]["time"], d["hourly"]["precipitation_probability"]) if "06:00" <= t[-5:] <= "21:00"]
        dd = d["daily"]
        out.append({"kota": k["nama"], "kondisi": WMO.get(dd["weather_code"][0], "-"), "min": round(dd["temperature_2m_min"][0]),
                    "max": round(dd["temperature_2m_max"][0]), "hujan": dd["precipitation_probability_max"][0] or 0, "jam": jam})
    return out


def kurs(cfg, tgl):
    """Seri 10 hari: {kode: [(tanggal, nilai dalam mata uang tujuan)]}. Sumber: ECB via Frankfurter."""
    k = cfg.get("kurs") or {}
    dari, ke = k.get("dari", []), k.get("ke", "IDR")
    if not dari:
        return {}
    start = (date.fromisoformat(tgl) - timedelta(days=10)).isoformat()
    try:
        d = get(f"https://api.frankfurter.app/{start}..?from=EUR&to={','.join(sorted(set(dari + [ke]) - {'EUR'}))}")
    except Exception as e:
        print(f"kurs gagal: {e}", file=sys.stderr)
        return {}
    rows = sorted(d["rates"].items())
    return {c: [(t, r[ke] / (r[c] if c != "EUR" else 1)) for t, r in rows if ke in r and (c == "EUR" or c in r)] for c in dari}


def tasks(cfg, d):
    """Daftar task: dari JSON edisi ("task": [...]) atau dari perintah di config (satu task per baris)."""
    if d.get("task") is not None:
        return list(d["task"])
    cmd = cfg.get("task_command")
    if not cmd:
        return None
    try:
        args = shlex.split(os.path.expanduser(cmd))
        if args and args[0] in ("python", "python3"):
            args[0] = sys.executable
        r = subprocess.run(args, capture_output=True, text=True, timeout=30, cwd=HERE)
        return [l.strip() for l in r.stdout.splitlines() if l.strip()] if r.returncode == 0 else ["Task tidak terbaca (cek task_command)"]
    except Exception:
        return ["Task tidak terbaca (cek task_command)"]


# ---------- komponen ----------
def rp(x):
    return f"{x:,.0f}".replace(",", ".")


def num(x):
    return rp(x) if x >= 100 else f"{x:.2f}".replace(".", ",")


def mini_bars(jam, w=95, h=22):
    if not jam:
        return ""
    bw = w / len(jam)
    r = "".join(f'<rect x="{i*bw+0.6:.1f}" y="{h-max(1,p/100*h):.1f}" width="{bw-1.2:.1f}" height="{max(1,p/100*h):.1f}" fill="{"#1F4E8C" if p>=60 else "#A9BCD6"}"/>'
                for i, (_, p) in enumerate(jam))
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Peluang hujan per jam">{r}</svg>'


def spark(series, w=170, h=26):
    v = [x for _, x in series]
    if len(v) < 2:
        return ""
    lo, hi = min(v), max(v); g = (hi - lo) or 1
    pts = " ".join(f"{2+i*(w-4)/(len(v)-1):.1f},{h-2-(x-lo)/g*(h-4):.1f}" for i, x in enumerate(v))
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}"><polyline points="{pts}" fill="none" stroke="#B3261E" stroke-width="1.4"/></svg>'


def sumber(b):
    return ", ".join(f'<a href="{E(u)}">{E(n)}</a>' if u else E(n) for n, u in b.get("sumber", []))


def artikel(b, kicker, lbl):
    rel = f'<p class="buat"><b>{E(lbl)}:</b> {E(b["relevansi"])}</p>' if b.get("relevansi") else ""
    return (f'<div class="art"><div class="kick">{E(kicker)}</div><h3>{E(b["judul"])}</h3>'
            f'<p><b class="dl">{E(b.get("tanggal",""))} –</b> {E(b["isi"])}</p>{rel}<p class="src">Sumber: {sumber(b)}</p></div>')


def tabel_peluang(items, label, catatan):
    rows = "".join(f'<tr><td><b>{E(x["judul"])}</b>'
                   + (f'<br><span class="sm"><b>Nilai:</b> {E(x["nilai"])}</span>' if x.get("nilai") else "")
                   + (f'<br><span class="sm">{E(x["status"])}</span>' if x.get("status") else "")
                   + (f'<br><span class="sm">Sumber: {sumber(x)}</span>' if x.get("sumber") else "") + "</td></tr>" for x in items)
    if not rows:
        rows = '<tr><td><i>Belum ada item yang terverifikasi.</i></td></tr>'
    return (f'<div class="art"><div class="kick">{E(label)}</div><h3>{E(label)}</h3><table class="tbl">{rows}</table>'
            + (f'<p class="src">{E(catatan)}</p>' if catatan else "") + "</div>")


# ---------- halaman ----------
CSS = """
@page { size: A4; margin: 11mm 11mm 12mm;
  @bottom-left { content: "__FOOT__"; font: 600 6.5pt "Plus Jakarta Sans", sans-serif; color: #6B6B6B; letter-spacing: .06em }
  @bottom-right { content: "Halaman " counter(page) " dari " counter(pages); font: 600 6.5pt "Plus Jakarta Sans", sans-serif; color: #6B6B6B } }
* { box-sizing: border-box }
body { margin: 0; font: 400 8.6pt/1.38 "Source Serif 4", Georgia, serif; color: #141414 }
a { color: inherit }
.sm { font-size: 6.8pt; color: #555 }
.kick { font: 800 6.6pt/1 "Plus Jakarta Sans", sans-serif; letter-spacing: .12em; text-transform: uppercase; color: #0B3D7A; margin-bottom: 3px; break-after: avoid }
.kick.red { color: #B3261E }
.mast { text-align: center; padding: 2px 0 0 }
.mast h1 { font: 900 42pt/1 "Playfair Display", serif; margin: 0; letter-spacing: -.01em; color: #0B3D7A; white-space: nowrap }
.mast .tag { font: 600 7pt "Plus Jakarta Sans", sans-serif; letter-spacing: .18em; text-transform: uppercase; color: #444 }
.wx { width: 100%; border-collapse: collapse } .wx-c { vertical-align: top; padding: 0 2px }
.big { font: 900 15pt/1 "Playfair Display", serif }
.fx { width: 100%; border-collapse: collapse } .fx td { padding: 1px 0 } .fx .v { font: 900 12pt/1 "Playfair Display", serif; text-align: right }
.dateline { border-top: 2.2pt solid #141414; border-bottom: 0.6pt solid #141414; margin: 6px 0 8px; padding: 3px 0;
  font: 600 7pt "Plus Jakarta Sans", sans-serif; letter-spacing: .05em; text-transform: uppercase; overflow: hidden }
.dateline .l { float: left } .dateline .r { float: right }
.top { width: 100%; border-collapse: collapse } .top > tbody > tr > td { vertical-align: top }
.main { width: 66%; padding-right: 10px; border-right: 0.6pt solid #999 }
.side { width: 34%; padding-left: 10px }
.head { font: 900 21pt/1.08 "Playfair Display", serif; margin: 2px 0 5px }
.deck { font: italic 400 10pt/1.35 "Source Serif 4", serif; margin: 0 0 6px; color: #333 }
.body1 { column-count: 2; column-gap: 12px; margin: 0 0 5px }
.box { border-top: 2pt solid #0B3D7A; padding-top: 4px; margin-bottom: 8px }
.box ul { margin: 2px 0 0; padding-left: 0; list-style: none }
.box li { padding: 1.5px 0 1.5px 12px; border-bottom: 0.4pt dotted #999; position: relative }
.box li:before { content: "☐"; position: absolute; left: 0; font-size: 7.5pt }
.tbl { width: 100%; border-collapse: collapse; font-size: 7.8pt }
.tbl td { padding: 2px 0; border-bottom: 0.4pt dotted #999; vertical-align: top }
.t { text-align: left; white-space: nowrap; padding: 2px 6px 2px 0; font-weight: 700 }
hr.sec { border: 0; border-top: 1.4pt solid #141414; margin: 5px 0 }
.grid { width: 100%; border-collapse: collapse; table-layout: fixed }
.gc { width: 33.33%; vertical-align: top; padding: 0 7px; border-left: 0.5pt solid #BBB }
.gc:first-child { padding-left: 0; border-left: 0 } .gc:last-child { padding-right: 0 }
.art { margin-bottom: 9px }
.art h3 { font: 700 11.5pt/1.15 "Playfair Display", serif; margin: 0 0 3px; break-after: avoid }
.art p { margin: 0 0 3px }
.dl { font-family: "Plus Jakarta Sans", sans-serif; font-size: 6.8pt; text-transform: uppercase; letter-spacing: .04em }
.buat { background: #EEF2F8; padding: 3px 4px; font-size: 7.8pt }
.src { font-size: 6.6pt; color: #666; font-style: italic }
.greet { margin: 2px 0 0; font-style: italic; font-size: 8.2pt }
.colofon { font-size: 6.5pt; color: #666; border-top: 0.6pt solid #999; padding-top: 3px; margin-top: 8px }
"""

WEB_CSS = """<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root { --desk: #E9E6DF; --paper: #FFFFFF }
@media (prefers-color-scheme: dark) { :root { --desk: #1C1C1C } }
html { background: var(--desk) }
body { background: var(--paper); max-width: 210mm; margin: 16px auto; padding: 11mm; box-shadow: 0 1px 6px rgba(0,0,0,.18) }
@media (max-width: 760px) {
  body { margin: 0; padding: 14px 16px; box-shadow: none; font-size: 16px; line-height: 1.55 }
  .art { margin-bottom: 18px; padding-bottom: 14px; border-bottom: 1px solid #DDD }
  .box { margin-bottom: 16px } .greet { font-size: 16px } .box li { padding: 5px 0 5px 18px; font-size: 15px }
  .fx .v { font-size: 20px } .big { font-size: 24px } .tbl td { padding: 6px 0 }
  .mast h1 { font-size: 40px; white-space: normal }
  .dateline .l, .dateline .r { float: none; display: block }
  .top, .top > tbody, .top > tbody > tr, .top > tbody > tr > td { display: block; width: 100% !important; padding: 0 !important; border: 0 !important }
  .grid, .grid > tbody, .grid > tbody > tr { display: block; width: 100% }
  .gc { display: block; width: 100% !important; padding: 0 !important; border: 0 !important }
  .main { margin-bottom: 12px } .head { font-size: 26px } .body1 { column-count: 1 }
  .sm, .src, .dl, .colofon { font-size: 12px } .kick { font-size: 11px } .buat, .tbl { font-size: 13px } .art h3 { font-size: 19px }
  svg { max-width: 100% }
}
</style>"""


def render(cfg, d, cu, ku, tk, dibuat):
    sore = d.get("jenis") == "sore"
    nama = d.get("nama_koran") or ("Koran Sore" if sore else "Koran Pagi")
    t = date.fromisoformat(d["tanggal"])
    tgl_str = f"{HARI[t.weekday()]}, {t.day} {BULAN[t.month]} {t.year}"
    lbl = cfg.get("label_relevansi", "Buat Anda")
    RUB = cfg.get("rubrik", {})
    berita = {k: list(v) for k, v in d.get("berita", {}).items() if isinstance(v, list)}

    # Berita utama: d["utama"] = [rubrik, index]; default berita pertama rubrik pertama yang berisi
    utama = ""
    rub, idx = d.get("utama") or next(([k, 0] for k, v in berita.items() if v and k != "peluang"), [None, 0])
    if rub and berita.get(rub):
        hb = berita[rub].pop(idx)
        utama = (f'<div class="kick red">Berita Utama · {E(RUB.get(rub, rub))}</div><h1 class="head">{E(hb["judul"])}</h1>'
                 f'<p class="deck">{E(hb.get("deck") or hb.get("relevansi", ""))}</p>'
                 f'<p class="body1"><b class="dl">{E(hb.get("tanggal",""))} –</b> {E(hb.get("isi_panjang") or hb["isi"])}</p>'
                 + (f'<p class="buat"><b>{E(lbl)}:</b> {E(hb["relevansi"])}</p>' if hb.get("relevansi") else "")
                 + f'<p class="src">Sumber: {sumber(hb)}</p>')

    def brk(x):
        if not x.get("berangkat"):
            return ""
        return (f'<br><span class="sm">Berangkat <b>{E(x["berangkat"])}</b>'
                + (f' dari {E(x["dari"])}' if x.get("dari") else "") + (f' ({E(x["estimasi"])})' if x.get("estimasi") else "") + "</span>")
    jadwal = "".join(f'<tr><td class="t">{E(x.get("jam",""))}</td><td><b>{E(x["judul"])}</b>'
                     + (f'<br><span class="sm">{E(x["lokasi"])}</span>' if x.get("lokasi") else "") + brk(x)
                     + (f'<br><span class="sm">{E(x["catatan"])}</span>' if x.get("catatan") else "") + "</td></tr>"
                     for x in d.get("agenda", [])) or f'<tr><td><i>Tidak ada jadwal {"besok" if sore else "hari ini"}.</i></td></tr>'

    def blok(key):
        if key == "_task":
            if tk is None:
                return ""
            li = "".join(f"<li>{E(x)}</li>" for x in tk) or "<li><i>Semua task selesai.</i></li>"
            return f'<div class="box"><div class="kick">Task belum selesai · {len(tk)}</div><ul>{li}</ul></div>'
        if key == "_kurs":
            if not ku:
                return ""
            ke = cfg["kurs"].get("ke", "IDR")
            rows = ""
            for c, s in ku.items():
                if not s:
                    continue
                dl = s[-1][1] - s[0][1]
                rows += (f'<tr><td>{E(c)}</td><td class="v">{"Rp " if ke == "IDR" else ""}{num(s[-1][1])}</td></tr>'
                         f'<tr><td colspan="2">{spark(s)}</td></tr>'
                         f'<tr><td colspan="2" class="sm">{"naik" if dl > 0 else "turun"} {num(abs(dl))} dalam 10 hari</td></tr>')
            return (f'<div class="box"><div class="kick">Kurs referensi → {E(ke)}</div><table class="fx">{rows}</table>'
                    f'<p class="sm">Kurs tengah ECB, bukan kurs jual bank.</p></div>')
        items = berita.get(key, [])
        if key == "peluang":
            return tabel_peluang(items, RUB.get(key, key), d.get("berita", {}).get("peluang_catatan", ""))
        return "".join(artikel(b, RUB.get(key, key), lbl) for b in items)

    kolom = cfg.get("kolom") or [list(RUB)[:2], list(RUB)[2:], ["_task", "_kurs"]]
    cols = "".join(f'<td class="gc">{"".join(blok(k) for k in ks)}</td>' for ks in kolom)
    cw = "".join(f'<td class="wx-c"><b>{E(c["kota"])}</b><br><span class="big">{c["max"]}°</span> <span class="sm">/{c["min"]}°</span><br>'
                 f'<span class="sm">{E(c["kondisi"])} · hujan {c["hujan"]}%</span><br>{mini_bars(c["jam"])}</td>' for c in cu)
    clabel = d.get("cuaca_label", "Cuaca besok" if sore else "Cuaca hari ini")
    jlabel = d.get("jadwal_label", "Jadwal besok" if sore else "Jadwal hari ini")
    web = cfg.get("web_url") or d.get("web_url")
    colofon = ("Cuaca: Open-Meteo · Kurs: Frankfurter (ECB)" + (f" · Versi web: {E(web)}" if web else "")
               + " · Dibuat dengan koran-pribadi")
    css = CSS.replace("__FOOT__", f"{nama.upper()} · {tgl_str}".replace('"', ""))
    return f'''<!doctype html><html lang="id"><head><meta charset="utf-8"><title>{E(nama)} · {E(tgl_str)}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;0,8..60,700;1,8..60,400&family=Plus+Jakarta+Sans:wght@600;800&display=swap">
<style>{css}</style></head><body>
<div class="mast"><div class="tag">{E(cfg.get("tagline", ""))}</div><h1>{E(nama)}</h1></div>
<div class="dateline"><span class="l">{E(tgl_str)}</span><span class="r">Edisi #{E(d.get("edisi", 1))} · Disusun {E(cfg.get("penyusun", "Asisten AI"))}, {E(dibuat)} {E(cfg.get("label_zona", "WIB"))}</span></div>
<table class="top"><tr>
 <td class="main">{utama}</td>
 <td class="side">
  {f'<div class="box"><div class="kick">{E(clabel)}</div><table class="wx"><tr>{cw}</tr></table></div>' if cu else ""}
  <div class="box"><div class="kick">{"Sore ini" if sore else "Pagi ini"}</div><p class="greet">{E(d.get("sapaan", ""))}</p></div>
  <div class="box"><div class="kick">{E(jlabel)}</div><table class="tbl">{jadwal}</table></div>
 </td></tr></table>
<hr class="sec">
<table class="grid"><tr>{cols}</tr></table>
<div class="colofon">{colofon}</div>
</body></html>'''


def main():
    ap = argparse.ArgumentParser(description="Buat koran pribadi (HTML + PDF) dari file JSON edisi.")
    ap.add_argument("edisi", help="file JSON edisi, mis. edisi/2026-11-01.json")
    cfg_def = os.path.join(HERE, "config.json")
    if not os.path.exists(cfg_def):
        cfg_def = os.path.join(HERE, "config.contoh.json")  # belum menjalankan ./koran setup
    ap.add_argument("--config", default=cfg_def)
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--no-pdf", action="store_true", help="hanya HTML (tanpa WeasyPrint)")
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8"))
    d = json.load(open(a.edisi, encoding="utf-8"))
    os.makedirs(a.out, exist_ok=True)
    tz = ZoneInfo(cfg.get("zona_waktu", "Asia/Jakarta"))
    dibuat = datetime.now(tz).strftime("%d/%m/%Y %H:%M")
    sore = d.get("jenis") == "sore"
    pref = "koran-sore" if sore else "koran-pagi"
    besok = (date.fromisoformat(d["tanggal"]) + timedelta(days=1)).isoformat()
    cu = cuaca(cfg, d.get("cuaca_tanggal") or (besok if sore else d["tanggal"]))
    ku = kurs(cfg, d["tanggal"])
    tk = tasks(cfg, d)
    full = render(cfg, d, cu, ku, tk, dibuat)
    web = os.path.join(a.out, f"{pref}.html")
    open(web, "w", encoding="utf-8").write(full.replace("</head>", WEB_CSS + "</head>", 1))
    pdf = None
    if not a.no_pdf:
        prn = os.path.join(a.out, f"{pref}-print.html")
        open(prn, "w", encoding="utf-8").write(full)
        pdf = os.path.join(a.out, f'{pref}-{d["tanggal"]}.pdf')
        try:
            try:
                import weasyprint  # noqa: F401  (dipasang di venv yang sama oleh install.sh)
                cmd = [sys.executable, "-m", "weasyprint", "-q", prn, pdf]
            except ImportError:
                cmd = ["weasyprint", "-q", prn, pdf]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode:
                print("PDF gagal:", r.stderr[-800:], file=sys.stderr); pdf = None
        except FileNotFoundError:
            print("WeasyPrint belum terpasang (jalankan install.sh). HTML tetap dibuat.", file=sys.stderr); pdf = None
    print(json.dumps({"html": web, "pdf": pdf, "cuaca": [(c["kota"], c["max"], c["hujan"]) for c in cu],
                      "kurs": {c: round(s[-1][1], 2) for c, s in ku.items() if s}, "task": None if tk is None else len(tk)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
