"""Çok sensörlü veri füzyonu demosu.

Kullanım:
    python main.py --senaryo sis
    python main.py --hepsi
    python main.py --hepsi --gif-yok     (animasyonları atla, daha hızlı)
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from src.degerlendirme import degerlendir
from src.fuzyon import fuzyon_calistir
from src.gorsel import KONFIG_ETIKET, gif_olustur, karsilastirma_grafigi, ozet_figur
from src.saha import hedefleri_olustur
from src.sensorler import SENARYOLAR, olcumleri_uret

TOHUM = 42
SONUC_DIZINI = Path(__file__).parent / "results"
KONFIGLER = {
    "radar": ["radar"],
    "kamera": ["kamera"],
    "konum": ["konum"],
    "fuzyon": ["radar", "kamera", "konum"],
}


def senaryo_kos(senaryo, hedefler, gif=True):
    """Bir senaryoyu tüm sensör konfigürasyonlarıyla koşturur ve değerlendirir."""
    rng = np.random.default_rng(TOHUM)
    olcumler = olcumleri_uret(hedefler, senaryo, rng)
    gecmisler, metrikler = {}, {}
    for ad, sensorler in KONFIGLER.items():
        gecmis, merkez = fuzyon_calistir(olcumler, sensorler)
        gecmisler[ad] = gecmis
        metrikler[ad] = degerlendir(gecmis, hedefler)
        if ad == "fuzyon":
            metrikler[ad]["bias_kestirimi"] = merkez.bias["konum"].round(1).tolist()
    if gif:
        yol = SONUC_DIZINI / f"{senaryo}.gif"
        gif_olustur(senaryo, hedefler, olcumler, gecmisler["fuzyon"], yol)
        print(f"  -> {yol.relative_to(Path(__file__).parent)} kaydedildi")
    return olcumler, gecmisler, metrikler


def tablo_yazdir(senaryo, metrikler):
    print(f"\n=== Senaryo: {senaryo} ===")
    print(f"{'Konfigürasyon':<24}{'RMSE (m)':>10}{'Kaçırma':>10}{'Yanlış iz':>11}{'ID switch':>11}")
    print("-" * 66)
    for ad in KONFIGLER:
        m = metrikler[ad]
        print(f"{KONFIG_ETIKET[ad]:<24}{m['rmse']:>10.1f}{100 * m['kacirma']:>9.1f}%"
              f"{m['yanlis_iz']:>11d}{m['id_switch']:>11d}")
    tek = min(metrikler[a]["rmse"] for a in ("radar", "kamera", "konum"))
    durum = "DAHA DÜŞÜK" if metrikler["fuzyon"]["rmse"] < tek else "daha düşük değil"
    print(f"Füzyon RMSE'si en iyi tek sensöre göre {durum} "
          f"({metrikler['fuzyon']['rmse']:.1f} m / {tek:.1f} m)")


def markdown_tablo(sonuclar):
    satirlar = ["| Senaryo | Konfigürasyon | RMSE (m) | Kaçırma oranı | Yanlış iz | ID switch |",
                "|---|---|---:|---:|---:|---:|"]
    for senaryo, metrikler in sonuclar.items():
        for ad in KONFIGLER:
            m = metrikler[ad]
            ad_metin = f"**{KONFIG_ETIKET[ad]}**" if ad == "fuzyon" else KONFIG_ETIKET[ad]
            satirlar.append(f"| {senaryo} | {ad_metin} | {m['rmse']:.1f} | %{100 * m['kacirma']:.1f} "
                            f"| {m['yanlis_iz']} | {m['id_switch']} |")
    return "\n".join(satirlar)


def main():
    # Windows konsolunda Türkçe karakterlerin düzgün görünmesi için
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Çok sensörlü veri füzyonu demosu")
    grup = parser.add_mutually_exclusive_group(required=True)
    grup.add_argument("--senaryo", choices=list(SENARYOLAR), help="tek bir senaryo çalıştır")
    grup.add_argument("--hepsi", action="store_true", help="tüm senaryoları çalıştır")
    parser.add_argument("--gif-yok", action="store_true", help="GIF animasyonlarını üretme")
    args = parser.parse_args()

    SONUC_DIZINI.mkdir(exist_ok=True)
    hedefler = hedefleri_olustur()
    senaryolar = list(SENARYOLAR) if args.hepsi else [args.senaryo]

    sonuclar, kayitlar = {}, {}
    for senaryo in senaryolar:
        print(f"[{senaryo}] çalıştırılıyor...")
        olcumler, gecmisler, metrikler = senaryo_kos(senaryo, hedefler, gif=not args.gif_yok)
        sonuclar[senaryo] = metrikler
        kayitlar[senaryo] = (olcumler, gecmisler)
        tablo_yazdir(senaryo, metrikler)

    karsilastirma_grafigi(sonuclar, SONUC_DIZINI / "karsilastirma.png")
    (SONUC_DIZINI / "sonuclar.json").write_text(json.dumps(sonuclar, indent=2, ensure_ascii=False),
                                                encoding="utf-8")
    (SONUC_DIZINI / "sonuclar.md").write_text(markdown_tablo(sonuclar) + "\n", encoding="utf-8")
    print("\n-> results/karsilastirma.png, results/sonuclar.json, results/sonuclar.md kaydedildi")

    # Özet figür: bir başarılı (sis) ve bir zorlu (sensör kaybı) örnek yan yana
    if "sis" in kayitlar and "sensor_kaybi" in kayitlar:
        veriler = [
            ("sis", *kayitlar["sis"], sonuclar["sis"],
             "Başarılı örnek — sis: kamera bozulur, füzyon radar ve konum bildirimiyle telafi eder"),
            ("sensor_kaybi", *kayitlar["sensor_kaybi"], sonuclar["sensor_kaybi"],
             "Zorlu örnek — sensör kaybı: radar ve kamera sırayla düşer, izler kopar ve ID değişir"),
        ]
        ozet_figur(hedefler, veriler, SONUC_DIZINI / "ozet.png")
        print("-> results/ozet.png kaydedildi")


if __name__ == "__main__":
    main()
