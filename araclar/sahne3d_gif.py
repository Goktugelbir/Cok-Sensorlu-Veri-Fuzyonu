"""3D sahneden README için animasyonlu GIF üretir.

Kullanım (proje kök dizininden):
    python araclar/sahne3d_gif.py                       (results/sahne3d.gif)
    python araclar/sahne3d_gif.py --bas 196 --son 226 --adim 0.25 --fps 10

Gereksinimler: Microsoft Edge ya da Google Chrome/Chromium ve Node.js 22+ (yerleşik
WebSocket için). Araç web arayüzünü geçici bir portta başlatır, tarayıcıyı görünmez
modda açar, 3D sahneyi sabit bir kamera açısıyla kare kare çeker (araclar/cdp_kareler.mjs)
ve kareleri ortak paletli bir GIF'e çevirir. Sahnedeki animasyonlar kayıt modunda sanal
bir saatle ilerlediği için çıktı her çalıştırmada aynıdır.
"""

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from PIL import Image

KOK = Path(__file__).resolve().parent.parent
TARAYICI_ADAYLARI = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]

# Karıştırma senaryosunda 196-226 s: radar karıştırılırken İHA-1 sert sağa kırılır (210-222 s),
# karıştırma 220. saniyede biter. Kamera radar, karıştırıcı ve İHA-1'i aynı karede tutar.
VARSAYILAN_KAMERA = {"konum": [-500, 3100, 5600], "hedef": [650, 0, 650]}
SENARYO_ADI = {"normal": "normal", "sis": "sis", "karistirma": "karıştırma", "sensor_kaybi": "sensör kaybı"}
VARSAYILAN_OLAYLAR = [
    [0, "radar karıştırılıyor, füzyonun ona güveni düşük"],
    [210, "<b>İHA-1 sert sağa kırılıyor: IMM dönüş modeline geçer (sarı halka)</b>"],
    [222, "İHA-1 düz uçuşa döndü"],
]


def tarayici_bul():
    for yol in TARAYICI_ADAYLARI:
        if Path(yol).exists():
            return yol
    for ad in ("msedge", "google-chrome", "chromium", "chromium-browser", "chrome"):
        if shutil.which(ad):
            return shutil.which(ad)
    sys.exit("Edge ya da Chrome bulunamadı.")


def bos_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def bekle_url(url, sure=120):
    son = time.time() + sure
    while time.time() < son:
        try:
            with urllib.request.urlopen(url, timeout=600) as r:
                return r.read()
        except OSError:
            time.sleep(0.5)
    sys.exit(f"Yanıt alınamadı: {url}")


def gif_yaz(kareler, yol, fps):
    """Kareleri ortak bir paletle GIF'e çevirir (titremesiz, değişmeyen bölgeler tekrar yazılmaz)."""
    goruntuler = [Image.open(k).convert("RGB") for k in kareler]
    ornek = goruntuler[:: max(1, len(goruntuler) // 8)]
    kolaj = Image.new("RGB", (ornek[0].width, ornek[0].height * len(ornek)))
    for i, g in enumerate(ornek):
        kolaj.paste(g, (0, i * g.height))
    palet = kolaj.quantize(colors=160, method=Image.Quantize.MEDIANCUT)
    paletli = [g.quantize(palette=palet, dither=Image.Dither.NONE) for g in goruntuler]
    paletli[0].save(yol, save_all=True, append_images=paletli[1:], duration=round(1000 / fps),
                    loop=0, optimize=True)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="3D sahneden animasyonlu GIF üretir")
    p.add_argument("--senaryo", default="karistirma")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--bas", type=float, default=196.0, help="başlangıç zamanı (s)")
    p.add_argument("--son", type=float, default=226.0, help="bitiş zamanı (s)")
    p.add_argument("--adim", type=float, default=0.25, help="kareler arası simülasyon süresi (s)")
    p.add_argument("--fps", type=float, default=10.0)
    p.add_argument("--genislik", type=int, default=880)
    p.add_argument("--yukseklik", type=int, default=540)
    p.add_argument("--cikti", default=str(KOK / "results" / "sahne3d.gif"))
    args = p.parse_args()

    if not shutil.which("node"):
        sys.exit("Node.js bulunamadı (22 ya da üstü gerekli).")
    web_port, cdp_port = bos_port(), bos_port()
    gecici = Path(tempfile.mkdtemp(prefix="sahne3d_gif_"))
    sunucu = tarayici = None
    try:
        sunucu = subprocess.Popen([sys.executable, str(KOK / "web.py"), "--port", str(web_port), "--tarayici-acma"],
                                  cwd=KOK, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        bekle_url(f"http://127.0.0.1:{web_port}/api/bilgi")
        print(f"{args.senaryo}, seed={args.seed} hesaplanıyor...")
        bekle_url(f"http://127.0.0.1:{web_port}/api/kos?senaryo={args.senaryo}&seed={args.seed}")

        tarayici = subprocess.Popen([
            tarayici_bul(), "--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
            "--hide-scrollbars", f"--remote-debugging-port={cdp_port}", f"--user-data-dir={gecici / 'profil'}",
            f"--window-size={args.genislik},{args.yukseklik}", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        bekle_url(f"http://127.0.0.1:{cdp_port}/json/version")

        (gecici / "kareler").mkdir()
        ayar = {"port": cdp_port, "dizin": str(gecici / "kareler"),
                "url": f"http://127.0.0.1:{web_port}/#senaryo={args.senaryo}&seed={args.seed}"
                       f"&t={args.bas}&gorunum=3d",
                "t0": args.bas, "t1": args.son, "adim": args.adim,
                "genislik": args.genislik, "yukseklik": args.yukseklik, "kamera": VARSAYILAN_KAMERA,
                "baslik": f"Çok sensörlü füzyon · 3D sahne · {SENARYO_ADI.get(args.senaryo, args.senaryo)} senaryosu",
                "olaylar": VARSAYILAN_OLAYLAR}
        (gecici / "ayar.json").write_text(json.dumps(ayar, ensure_ascii=False), encoding="utf-8")
        print("Kareler çekiliyor...")
        subprocess.run(["node", str(KOK / "araclar" / "cdp_kareler.mjs"), str(gecici / "ayar.json")], check=True)

        kareler = sorted((gecici / "kareler").glob("kare_*.png"))
        gif_yaz(kareler, args.cikti, args.fps)
        boyut = os.path.getsize(args.cikti) / 1e6
        print(f"-> {args.cikti} kaydedildi ({len(kareler)} kare, {boyut:.1f} MB)")
    finally:
        for surec in (tarayici, sunucu):
            if surec:
                surec.terminate()
                try:
                    surec.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    surec.kill()
        shutil.rmtree(gecici, ignore_errors=True)


if __name__ == "__main__":
    main()
