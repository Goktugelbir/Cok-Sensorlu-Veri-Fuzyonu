"""Yerel web arayüzü: senaryoları tarayıcıda etkileşimli olarak izlemek için.

Kullanım:
    python web.py               (http://localhost:8000 adresini açar)
    python web.py --port 8080

Sadece Python standart kütüphanesi (http.server) kullanılır. Sayfa web/index.html
dosyasıdır; veriler /api/kos?senaryo=sis&seed=42 adresinden JSON olarak gelir.
"""

import argparse
import json
import sys
import threading
import webbrowser
from concurrent.futures import ProcessPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np

from main import KONFIGLER
from src.degerlendirme import degerlendir
from src.fuzyon import fuzyon_calistir
from src.gorsel import KONFIG_ETIKET
from src.saha import SAHA_BOYUTU, SURE, hedefleri_olustur
from src.sensorler import SENARYOLAR, SENSORLER, olcumleri_uret, sensor_durumu

WEB_DIZINI = Path(__file__).parent / "web"
_onbellek = {}
_kilit = threading.Lock()
_havuz = None


def _konfig_kos(senaryo, seed, ad):
    """Tek bir konfigürasyonu koşturur (ayrı süreçte çalışır)."""
    hedefler = hedefleri_olustur()
    olcumler = olcumleri_uret(hedefler, senaryo, np.random.default_rng(seed))
    sensorler, guven = KONFIGLER[ad]
    gecmis, _ = fuzyon_calistir(olcumler, sensorler, guven_agirliklandirma=guven)
    metrik = degerlendir(gecmis, hedefler)
    kareler = []
    for t, resim, guvenler in gecmis:
        kareler.append({
            "t": t,
            "guven": {s: round(g, 3) for s, g in guvenler.items()},
            # [id, x, y, vx, vy, skor, sensörler, dost]
            "izler": [[iz["id"], round(float(iz["konum"][0]), 1), round(float(iz["konum"][1]), 1),
                       round(float(iz["hiz"][0]), 2), round(float(iz["hiz"][1]), 2),
                       round(iz["skor"], 3), iz["sensorler"], iz["dost"]] for iz in resim],
        })
    return ad, {"etiket": KONFIG_ETIKET[ad], "metrik": metrik, "kareler": kareler}


def kos(senaryo, seed):
    """Senaryoyu tüm konfigürasyonlarla koşturup arayüz için JSON verisi hazırlar."""
    anahtar = (senaryo, seed)
    with _kilit:
        if anahtar in _onbellek:
            return _onbellek[anahtar]

    hedefler = hedefleri_olustur()
    olcumler = olcumleri_uret(hedefler, senaryo, np.random.default_rng(seed))
    isler = [_havuz.submit(_konfig_kos, senaryo, seed, ad) for ad in KONFIGLER]
    konfigler = dict(f.result() for f in isler)

    adimlar = np.arange(0, SURE + 1, 1.0)
    veri = {
        "senaryo": senaryo,
        "seed": seed,
        "sure": SURE,
        "saha": SAHA_BOYUTU,
        "sensorler": {ad: {"konum": None if np.isnan(s.konum).any() else s.konum.tolist(),
                           "menzil": None if np.isinf(s.menzil) else s.menzil}
                      for ad, s in SENSORLER.items()},
        "hedefler": [{"id": h.hid, "ad": h.ad, "dost": h.dost,
                      "rota": [[round(float(x), 1), round(float(y), 1)]
                               for x, y in (h.konum_at(t) for t in adimlar)]}
                     for h in hedefler],
        "olcumler": {ad: [[round(o.t_olcum, 2), round(float(o.z[0]), 1), round(float(o.z[1]), 1)]
                          for o in liste] for ad, liste in olcumler.items()},
        "durum": [{ad: _durum_ozeti(senaryo, ad, t) for ad in SENSORLER} for t in adimlar],
        "konfigler": konfigler,
        "konfig_sirasi": list(KONFIGLER),
    }
    with _kilit:
        _onbellek[anahtar] = veri
    return veri


def _durum_ozeti(senaryo, ad, t):
    d = sensor_durumu(senaryo, ad, t)
    if not d["aktif"]:
        etiket = "KAPALI"
    elif d["karistirma"]:
        etiket = "KARIŞTIRMA"
    elif d["gurultu_carpani"] > 1:
        etiket = "SİS"
    else:
        etiket = "açık"
    menzil = None if np.isinf(d["menzil"]) else d["menzil"]
    return {"aktif": d["aktif"], "etiket": etiket, "menzil": menzil}


class Isleyici(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIZINI), **kwargs)

    def log_message(self, format, *args):
        pass  # terminali sade tut

    def _json(self, veri, kod=200):
        govde = json.dumps(veri, ensure_ascii=False).encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(govde)))
        self.end_headers()
        self.wfile.write(govde)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/api/bilgi":
            return self._json({"senaryolar": list(SENARYOLAR),
                               "konfigler": {ad: KONFIG_ETIKET[ad] for ad in KONFIGLER}})
        if url.path == "/api/kos":
            q = parse_qs(url.query)
            senaryo = q.get("senaryo", ["normal"])[0]
            try:
                seed = int(q.get("seed", ["42"])[0])
            except ValueError:
                return self._json({"hata": "seed bir tamsayı olmalı"}, 400)
            if senaryo not in SENARYOLAR or not 0 <= seed <= 1_000_000:
                return self._json({"hata": "geçersiz senaryo veya seed"}, 400)
            try:
                return self._json(kos(senaryo, seed))
            except Exception as e:  # hata tarayıcıda görünsün
                return self._json({"hata": f"{type(e).__name__}: {e}"}, 500)
        return super().do_GET()


def main():
    global _havuz
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Çok sensörlü veri füzyonu web arayüzü")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--tarayici-acma", action="store_true", help="tarayıcıyı otomatik açma")
    args = parser.parse_args()

    _havuz = ProcessPoolExecutor(max_workers=len(KONFIGLER))
    sunucu = ThreadingHTTPServer(("127.0.0.1", args.port), Isleyici)
    adres = f"http://localhost:{args.port}"
    print(f"Web arayüzü çalışıyor: {adres}  (durdurmak için Ctrl+C)")
    if not args.tarayici_acma:
        threading.Timer(0.8, lambda: webbrowser.open(adres)).start()
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        print("\nKapatılıyor...")
    finally:
        sunucu.server_close()
        _havuz.shutdown(cancel_futures=True)


if __name__ == "__main__":
    main()
