"""Çok sensörlü veri füzyonu demosu.

Kullanım:
    python main.py --senaryo sis
    python main.py --hepsi
    python main.py --hepsi --tekrar 10   (daha az koşu, daha hızlı)
    python main.py --hepsi --gif-yok     (animasyonları atla)

Her senaryo önce seed=42 ile bir kez koşturulur (animasyon ve özet figür için),
ardından seed=42, 43, ... ile --tekrar kez koşturulup ölçütlerin ortalaması ve
standart sapması raporlanır.
"""

import argparse
import json
import os
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from src.degerlendirme import degerlendir
from src.fuzyon import fuzyon_calistir
from src.gorsel import KONFIG_ETIKET, gif_olustur, karsilastirma_grafigi, ozet_figur
from src.saha import hedefleri_olustur
from src.sensorler import SENARYOLAR, SENSORLER, olcumleri_uret

TOHUM = 42
SONUC_DIZINI = Path(__file__).parent / "results"
TUM_SENSORLER = ["radar", "kamera", "konum"]
# konfigürasyon -> (kullanılan sensörler, güven ağırlıklandırma açık mı)
KONFIGLER = {
    "radar": (["radar"], True),
    "kamera": (["kamera"], True),
    "konum": (["konum"], True),
    "fuzyon_guvensiz": (TUM_SENSORLER, False),   # ablasyon
    "fuzyon": (TUM_SENSORLER, True),
}
TEK_SENSORLER = ("radar", "kamera", "konum")
OLCUTLER = ("rmse", "gospa", "kacirma", "yanlis_iz", "id_switch")


def senaryo_kos(senaryo, hedefler, tohum=TOHUM):
    """Bir senaryoyu tüm konfigürasyonlarla bir kez koşturur ve değerlendirir."""
    rng = np.random.default_rng(tohum)
    olcumler = olcumleri_uret(hedefler, senaryo, rng)
    gecmisler, metrikler = {}, {}
    for ad, (sensorler, guven) in KONFIGLER.items():
        gecmis, merkez = fuzyon_calistir(olcumler, sensorler, guven_agirliklandirma=guven)
        gecmisler[ad] = gecmis
        metrikler[ad] = degerlendir(gecmis, hedefler)
        if ad == "fuzyon":
            metrikler[ad]["bias_kestirimi"] = merkez.bias["konum"].round(1).tolist()
    return olcumler, gecmisler, metrikler


def _mc_isci(is_):
    """Paralel çalışan tek koşu: (senaryo, tohum) -> ölçütler."""
    senaryo, tohum = is_
    _, _, metrikler = senaryo_kos(senaryo, hedefleri_olustur(), tohum)
    return (senaryo, tohum, {k: {o: m[o] for o in OLCUTLER} for k, m in metrikler.items()},
            metrikler["fuzyon"]["bias_kestirimi"])


def bias_ozeti(kestirimler):
    """Konum bildirimi bias kestirimlerinin (her koşudan bir tane) özeti."""
    K = np.array(kestirimler, float)
    gercek = np.array(SENSORLER["konum"].bias)
    hata = np.linalg.norm(K - gercek, axis=1)
    std = lambda d: float(d.std(ddof=1)) if len(d) > 1 else 0.0
    return {"gercek": gercek.tolist(),
            "ortalama": K.mean(axis=0).tolist(), "std": [std(K[:, 0]), std(K[:, 1])],
            "hata_ort": float(hata.mean()), "hata_std": std(hata)}


def mc_ozetle(kosular):
    """kosular[konfig] = [ölçüt sözlüğü, ...] -> ozet[konfig][ölçüt] = (ortalama, std)."""
    ozet = {}
    for k, liste in kosular.items():
        ozet[k] = {}
        for o in OLCUTLER:
            d = np.array([m[o] for m in liste], float)
            ozet[k][o] = (float(d.mean()), float(d.std(ddof=1)) if len(d) > 1 else 0.0)
    return ozet


def kazanma_sayisi(kosular, olcut="rmse"):
    """Füzyonun ölçütünün, aynı koşudaki en iyi tek sensörden düşük olduğu koşu sayısı."""
    return sum(f[olcut] < min(kosular[t][i][olcut] for t in TEK_SENSORLER)
               for i, f in enumerate(kosular["fuzyon"]))


def tablo_yazdir(senaryo, ozet, kosular):
    n = len(kosular["fuzyon"])
    print(f"\n=== Senaryo: {senaryo}  ({n} koşu, ortalama ± std) ===")
    print(f"{'Konfigürasyon':<40}{'RMSE (m)':>14}{'GOSPA (m)':>15}{'Kaçırma (%)':>15}"
          f"{'Yanlış iz':>14}{'ID switch':>14}")
    print("-" * 112)
    for ad in KONFIGLER:
        m = ozet[ad]
        print(f"{KONFIG_ETIKET[ad]:<40}"
              f"{m['rmse'][0]:>8.1f} ± {m['rmse'][1]:<4.1f}"
              f"{m['gospa'][0]:>9.1f} ± {m['gospa'][1]:<4.1f}"
              f"{100 * m['kacirma'][0]:>8.1f} ± {100 * m['kacirma'][1]:<5.1f}"
              f"{m['yanlis_iz'][0]:>8.1f} ± {m['yanlis_iz'][1]:<4.1f}"
              f"{m['id_switch'][0]:>8.1f} ± {m['id_switch'][1]:<4.1f}")
    print(f"Füzyonun en iyi tek sensörden düşük olduğu koşu sayısı: RMSE {kazanma_sayisi(kosular)}/{n}, "
          f"GOSPA {kazanma_sayisi(kosular, 'gospa')}/{n}")


def markdown_tablo(ozet_tum, kosular_tum, bias_tum):
    satirlar = ["| Senaryo | Konfigürasyon | RMSE (m) | GOSPA (m) | Kaçırma (%) | Yanlış iz | ID switch |",
                "|---|---|---:|---:|---:|---:|---:|"]
    for senaryo, ozet in ozet_tum.items():
        for ad in KONFIGLER:
            m = ozet[ad]
            ad_metin = f"**{KONFIG_ETIKET[ad]}**" if ad == "fuzyon" else KONFIG_ETIKET[ad]
            satirlar.append(
                f"| {senaryo} | {ad_metin} | {m['rmse'][0]:.1f} ± {m['rmse'][1]:.1f} "
                f"| {m['gospa'][0]:.1f} ± {m['gospa'][1]:.1f} "
                f"| {100 * m['kacirma'][0]:.1f} ± {100 * m['kacirma'][1]:.1f} "
                f"| {m['yanlis_iz'][0]:.1f} ± {m['yanlis_iz'][1]:.1f} "
                f"| {m['id_switch'][0]:.1f} ± {m['id_switch'][1]:.1f} |")
    satirlar.append("")
    satirlar.append("| Senaryo | Füzyonun en iyi tek sensörden düşük olduğu koşu: RMSE | GOSPA |")
    satirlar.append("|---|---:|---:|")
    for senaryo, kosular in kosular_tum.items():
        n = len(kosular["fuzyon"])
        satirlar.append(f"| {senaryo} | {kazanma_sayisi(kosular)}/{n} | {kazanma_sayisi(kosular, 'gospa')}/{n} |")
    satirlar.append("")
    satirlar.append("| Senaryo | Bias kestirimi x (m) | Bias kestirimi y (m) | Kestirim hatası (m) |")
    satirlar.append("|---|---:|---:|---:|")
    for senaryo, b in bias_tum.items():
        satirlar.append(f"| {senaryo} | {b['ortalama'][0]:.1f} ± {b['std'][0]:.1f} "
                        f"| {b['ortalama'][1]:.1f} ± {b['std'][1]:.1f} | {b['hata_ort']:.1f} ± {b['hata_std']:.1f} |")
    return "\n".join(satirlar)


def main():
    # Windows konsolunda Türkçe karakterlerin düzgün görünmesi için
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Çok sensörlü veri füzyonu demosu")
    grup = parser.add_mutually_exclusive_group(required=True)
    grup.add_argument("--senaryo", choices=list(SENARYOLAR), help="tek bir senaryo çalıştır")
    grup.add_argument("--hepsi", action="store_true", help="tüm senaryoları çalıştır")
    parser.add_argument("--tekrar", type=int, default=30,
                        help="istatistik için farklı seed'li koşu sayısı (varsayılan 30)")
    parser.add_argument("--gif-yok", action="store_true", help="GIF animasyonlarını üretme")
    args = parser.parse_args()

    SONUC_DIZINI.mkdir(exist_ok=True)
    hedefler = hedefleri_olustur()
    senaryolar = list(SENARYOLAR) if args.hepsi else [args.senaryo]
    tekrar = max(1, args.tekrar)
    tohumlar = list(range(TOHUM, TOHUM + tekrar))

    # 1) seed=42 ile örnek koşu: animasyon ve özet figür
    kayitlar, ornek_metrikler = {}, {}
    for senaryo in senaryolar:
        print(f"[{senaryo}] örnek koşu (seed={TOHUM})...")
        olcumler, gecmisler, metrikler = senaryo_kos(senaryo, hedefler)
        kayitlar[senaryo] = (olcumler, gecmisler)
        ornek_metrikler[senaryo] = metrikler
        if not args.gif_yok:
            yol = SONUC_DIZINI / f"{senaryo}.gif"
            gif_olustur(senaryo, hedefler, olcumler, gecmisler["fuzyon"], yol)
            print(f"  -> results/{yol.name} kaydedildi")

    # 2) Çok seed'li koşular (paralel)
    print(f"\n{len(senaryolar)} senaryo x {tekrar} seed koşturuluyor (seed {tohumlar[0]}-{tohumlar[-1]})...")
    isler = [(s, t) for s in senaryolar for t in tohumlar]
    with Pool(min(len(isler), os.cpu_count() or 1)) as havuz:
        sonuc_listesi = havuz.map(_mc_isci, isler)
    kosular_tum = {s: {k: [] for k in KONFIGLER} for s in senaryolar}
    bias_kestirimleri = {s: [] for s in senaryolar}
    for senaryo, _, metrikler, bias in sorted(sonuc_listesi, key=lambda r: (r[0], r[1])):
        for k in KONFIGLER:
            kosular_tum[senaryo][k].append(metrikler[k])
        bias_kestirimleri[senaryo].append(bias)
    ozet_tum = {s: mc_ozetle(kosular_tum[s]) for s in senaryolar}
    bias_tum = {s: bias_ozeti(bias_kestirimleri[s]) for s in senaryolar}
    for senaryo in senaryolar:
        tablo_yazdir(senaryo, ozet_tum[senaryo], kosular_tum[senaryo])
        b = bias_tum[senaryo]
        print(f"Konum bildirimi bias kestirimi: ({b['ortalama'][0]:.1f} ± {b['std'][0]:.1f}, "
              f"{b['ortalama'][1]:.1f} ± {b['std'][1]:.1f}) m, gerçek ({b['gercek'][0]:.0f}, "
              f"{b['gercek'][1]:.0f}) m, hata {b['hata_ort']:.1f} ± {b['hata_std']:.1f} m")

    # 3) Çıktılar. Tek senaryo koşusu, tüm senaryoların ortak tablosunu ezmesin diye
    # senaryo adını taşıyan ayrı dosyalara yazılır (ör. karsilastirma_sis.png).
    ek = "" if args.hepsi else f"_{args.senaryo}"
    dosyalar = [f"karsilastirma{ek}.png", f"sonuclar{ek}.json", f"sonuclar{ek}.md"]
    karsilastirma_grafigi(ozet_tum, SONUC_DIZINI / dosyalar[0], tekrar)
    json_veri = {"tekrar": tekrar, "tohumlar": tohumlar, "ozet": ozet_tum,
                 "kosular": kosular_tum, "bias_kestirimi": bias_tum,
                 "ornek_kosu_seed42": ornek_metrikler}
    (SONUC_DIZINI / dosyalar[1]).write_text(json.dumps(json_veri, indent=1, ensure_ascii=False),
                                            encoding="utf-8")
    (SONUC_DIZINI / dosyalar[2]).write_text(markdown_tablo(ozet_tum, kosular_tum, bias_tum) +"\n",
                                            encoding="utf-8")
    print("\n-> " + ", ".join(f"results/{d}" for d in dosyalar) + " kaydedildi")

    # Özet figür: bir başarılı (sis) ve bir zorlu (sensör kaybı) örnek yan yana
    if "sis" in kayitlar and "sensor_kaybi" in kayitlar:
        veriler = [
            ("sis", *kayitlar["sis"], ornek_metrikler["sis"],
             "Başarılı örnek — sis: kamera bozulur, füzyon radar ve konum bildirimiyle telafi eder"),
            ("sensor_kaybi", *kayitlar["sensor_kaybi"], ornek_metrikler["sensor_kaybi"],
             "Zorlu örnek — sensör kaybı: radar ve kamera sırayla düşer, izler kopar ve ID değişir"),
        ]
        ozet_figur(hedefler, veriler, SONUC_DIZINI / "ozet.png")
        print("-> results/ozet.png kaydedildi")


if __name__ == "__main__":
    main()
