"""Çok sensörlü veri füzyonu demosu.

Kullanım:
    python main.py --senaryo sis
    python main.py --hepsi
    python main.py --hepsi --tekrar 10   (daha az koşu, daha hızlı)
    python main.py --hepsi --gif-yok     (animasyonları atla)
    python main.py --hepsi --ilk-seed 100 --gif-yok   (bağımsız doğrulama, seed 100-129)

Her senaryo önce seed=42 ile bir kez koşturulur (animasyon ve özet figür için),
ardından seed=42, 43, ... ile --tekrar kez koşturulup ölçütlerin ortalaması ve
standart sapması raporlanır.
"""

import argparse
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from scipy.stats import mannwhitneyu

from src.degerlendirme import degerlendir
from src.fuzyon import fuzyon_calistir
from src.gorsel import KONFIG_ETIKET, gif_olustur, karsilastirma_grafigi, nees_grafigi, ozet_figur
from src.saha import SURE, hedefleri_olustur
from src.sensorler import SENARYOLAR, SENSORLER, olcumleri_uret
from src.tutarlilik import BOYUT, nees_dizisi
from src.tutarlilik import ozetle as nees_ozetle

TOHUM = 42
SONUC_DIZINI = Path(__file__).parent / "results"
TUM_SENSORLER = ["radar", "kamera", "konum"]
# konfigürasyon -> (kullanılan sensörler, güven ağırlıklandırma açık mı, hareket modeli)
KONFIGLER = {
    "radar": (["radar"], True, "imm"),
    "kamera": (["kamera"], True, "imm"),
    "konum": (["konum"], True, "imm"),
    "fuzyon_guvensiz": (TUM_SENSORLER, False, "imm"),   # ablasyon: NIS tabanlı sensör güveni kapalı
    "fuzyon_cv": (TUM_SENSORLER, True, "cv"),           # ablasyon: IMM yerine sadece sabit hız
    "fuzyon": (TUM_SENSORLER, True, "imm"),
}
TEK_SENSORLER = ("radar", "kamera", "konum")
OLCUTLER = ("rmse", "gospa", "kacirma", "yanlis_iz", "id_switch", "etiket")
NEES_KONFIGLER = ("fuzyon", "fuzyon_cv")   # filtre tutarlılığı IMM ile sadece CV arasında karşılaştırılır
# NEES grafiğinde gölgelenen İHA-1 manevraları (src/saha.py ile aynı zaman aralıkları)
IHA1_MANEVRALARI = [(60, 150, "yumuşak sola dönüş"), (210, 222, "sert sağa kırılma")]


def senaryo_kos(senaryo, hedefler, tohum=TOHUM, sureler=None):
    """Bir senaryoyu tüm konfigürasyonlarla bir kez koşturur ve değerlendirir.

    sureler sözlüğü verilirse her konfigürasyonun füzyon süresi (s) buna yazılır.
    """
    rng = np.random.default_rng(tohum)
    olcumler = olcumleri_uret(hedefler, senaryo, rng)
    gecmisler, metrikler = {}, {}
    for ad, (sensorler, guven, model) in KONFIGLER.items():
        t0 = time.perf_counter()
        gecmis, merkez = fuzyon_calistir(olcumler, sensorler, guven_agirliklandirma=guven,
                                         hareket_modeli=model)
        if sureler is not None:
            sureler[ad] = time.perf_counter() - t0
        gecmisler[ad] = gecmis
        metrikler[ad] = degerlendir(gecmis, hedefler)
        if ad == "fuzyon":
            metrikler[ad]["bias_kestirimi"] = merkez.bias["konum"].round(1).tolist()
    return olcumler, gecmisler, metrikler


def _mc_isci(is_):
    """Paralel çalışan tek koşu: (senaryo, tohum) -> ölçütler, bias kestirimi ve NEES dizileri."""
    senaryo, tohum = is_
    hedefler = hedefleri_olustur()
    _, gecmisler, metrikler = senaryo_kos(senaryo, hedefler, tohum)
    nees = {k: nees_dizisi(gecmisler[k], hedefler) for k in NEES_KONFIGLER}
    return (senaryo, tohum, {k: {o: m[o] for o in OLCUTLER} for k, m in metrikler.items()},
            metrikler["fuzyon"]["bias_kestirimi"],
            {k: (z, n.astype(np.float32)) for k, (z, n) in nees.items()})


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
          f"{'Yanlış iz':>14}{'ID switch':>14}{'Etiket (%)':>16}")
    print("-" * 128)
    for ad in KONFIGLER:
        m = ozet[ad]
        print(f"{KONFIG_ETIKET[ad]:<40}"
              f"{m['rmse'][0]:>8.1f} ± {m['rmse'][1]:<4.1f}"
              f"{m['gospa'][0]:>9.1f} ± {m['gospa'][1]:<4.1f}"
              f"{100 * m['kacirma'][0]:>8.1f} ± {100 * m['kacirma'][1]:<5.1f}"
              f"{m['yanlis_iz'][0]:>8.1f} ± {m['yanlis_iz'][1]:<4.1f}"
              f"{m['id_switch'][0]:>8.1f} ± {m['id_switch'][1]:<4.1f}"
              f"{100 * m['etiket'][0]:>9.1f} ± {100 * m['etiket'][1]:<5.1f}")
    print(f"Füzyonun en iyi tek sensörden düşük olduğu koşu sayısı: RMSE {kazanma_sayisi(kosular)}/{n}, "
          f"GOSPA {kazanma_sayisi(kosular, 'gospa')}/{n}")


def seed_kumesi_testi(ana, kosular_tum):
    """Ana seed kümesi ile doğrulama kümesindeki füzyon sonuçlarını Mann-Whitney U testiyle karşılaştırır."""
    satirlar = [f"Mann-Whitney U testi, füzyon: seed {ana['tohumlar'][0]}-{ana['tohumlar'][-1]} ile bu küme "
                "(iki yönlü; p > 0.05 ise anlamlı fark yok)", "",
                "| Senaryo | GOSPA p | RMSE p |", "|---|---:|---:|"]
    for senaryo, kosular in kosular_tum.items():
        if senaryo not in ana["kosular"]:
            continue
        p = [mannwhitneyu([m[o] for m in ana["kosular"][senaryo]["fuzyon"]],
                          [m[o] for m in kosular["fuzyon"]]).pvalue for o in ("gospa", "rmse")]
        print(f"[{senaryo}] seed kümeleri arası Mann-Whitney U: GOSPA p={p[0]:.2f}, RMSE p={p[1]:.2f}")
        satirlar.append(f"| {senaryo} | {p[0]:.2f} | {p[1]:.2f} |")
    return "\n".join(satirlar)


def markdown_tablo(ozet_tum, kosular_tum, bias_tum):
    satirlar = ["| Senaryo | Konfigürasyon | RMSE (m) | GOSPA (m) | Kaçırma (%) | Yanlış iz | ID switch "
                "| Etiket doğruluğu (%) |",
                "|---|---|---:|---:|---:|---:|---:|---:|"]
    for senaryo, ozet in ozet_tum.items():
        for ad in KONFIGLER:
            m = ozet[ad]
            ad_metin = f"**{KONFIG_ETIKET[ad]}**" if ad == "fuzyon" else KONFIG_ETIKET[ad]
            satirlar.append(
                f"| {senaryo} | {ad_metin} | {m['rmse'][0]:.1f} ± {m['rmse'][1]:.1f} "
                f"| {m['gospa'][0]:.1f} ± {m['gospa'][1]:.1f} "
                f"| {100 * m['kacirma'][0]:.1f} ± {100 * m['kacirma'][1]:.1f} "
                f"| {m['yanlis_iz'][0]:.1f} ± {m['yanlis_iz'][1]:.1f} "
                f"| {m['id_switch'][0]:.1f} ± {m['id_switch'][1]:.1f} "
                f"| {100 * m['etiket'][0]:.1f} ± {100 * m['etiket'][1]:.1f} |")
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


def argumanlari_oku():
    parser = argparse.ArgumentParser(description="Çok sensörlü veri füzyonu demosu")
    grup = parser.add_mutually_exclusive_group(required=True)
    grup.add_argument("--senaryo", choices=list(SENARYOLAR), help="tek bir senaryo çalıştır")
    grup.add_argument("--hepsi", action="store_true", help="tüm senaryoları çalıştır")
    parser.add_argument("--tekrar", type=int, default=30,
                        help="istatistik için farklı seed'li koşu sayısı (varsayılan 30)")
    parser.add_argument("--gif-yok", action="store_true", help="GIF animasyonlarını üretme")
    parser.add_argument("--ilk-seed", type=int, default=TOHUM,
                        help="istatistik koşularının ilk seed'i (bağımsız doğrulama için ör. 100)")
    return parser.parse_args()


def ornek_kosular(senaryolar, hedefler, gif):
    """seed=42 ile her senaryodan bir örnek koşu: süre ölçümü, animasyon ve özet figür verisi."""
    kayitlar, ornek_metrikler = {}, {}
    for senaryo in senaryolar:
        print(f"[{senaryo}] örnek koşu (seed={TOHUM})...")
        sureler = {}
        olcumler, gecmisler, metrikler = senaryo_kos(senaryo, hedefler, sureler=sureler)
        print(f"  füzyon süresi: IMM {sureler['fuzyon']:.2f} s, CV {sureler['fuzyon_cv']:.2f} s "
              f"({SURE:.0f} s'lik senaryo; IMM gerçek zamanın ~{SURE / sureler['fuzyon']:.0f} katı hızlı)")
        kayitlar[senaryo] = (olcumler, gecmisler)
        ornek_metrikler[senaryo] = metrikler
        if gif:
            yol = SONUC_DIZINI / f"{senaryo}.gif"
            gif_olustur(senaryo, hedefler, olcumler, gecmisler["fuzyon"], yol)
            print(f"  -> results/{yol.name} kaydedildi")
    return kayitlar, ornek_metrikler


def coklu_kosular(senaryolar, tohumlar):
    """Her senaryoyu her seed ile paralel koşturur, özetleri hesaplar ve tabloları yazdırır."""
    print(f"\n{len(senaryolar)} senaryo x {len(tohumlar)} seed koşturuluyor "
          f"(seed {tohumlar[0]}-{tohumlar[-1]})...")
    isler = [(s, t) for s in senaryolar for t in tohumlar]
    with Pool(min(len(isler), os.cpu_count() or 1)) as havuz:
        sonuc_listesi = havuz.map(_mc_isci, isler)
    kosular_tum = {s: {k: [] for k in KONFIGLER} for s in senaryolar}
    bias_kestirimleri = {s: [] for s in senaryolar}
    nees_kosular = {s: {k: [] for k in NEES_KONFIGLER} for s in senaryolar}
    nees_zaman = None
    for senaryo, _, metrikler, bias, nees in sorted(sonuc_listesi, key=lambda r: (r[0], r[1])):
        for k in KONFIGLER:
            kosular_tum[senaryo][k].append(metrikler[k])
        bias_kestirimleri[senaryo].append(bias)
        for k, (zaman, dizi) in nees.items():
            nees_zaman = zaman
            nees_kosular[senaryo][k].append(dizi)
    ozet_tum = {s: mc_ozetle(kosular_tum[s]) for s in senaryolar}
    bias_tum = {s: bias_ozeti(bias_kestirimleri[s]) for s in senaryolar}
    # NEES özeti için bir (hedef, an) noktasının en az koşuların yarısında eşleşmiş olması gerekir
    tutarlilik_tum = {s: {k: nees_ozetle(nees_kosular[s][k], max(1, len(tohumlar) // 2)) for k in NEES_KONFIGLER}
                      for s in senaryolar}
    for senaryo in senaryolar:
        tablo_yazdir(senaryo, ozet_tum[senaryo], kosular_tum[senaryo])
        b = bias_tum[senaryo]
        print(f"Konum bildirimi bias kestirimi: ({b['ortalama'][0]:.1f} ± {b['std'][0]:.1f}, "
              f"{b['ortalama'][1]:.1f} ± {b['std'][1]:.1f}) m, gerçek ({b['gercek'][0]:.0f}, "
              f"{b['gercek'][1]:.0f}) m, hata {b['hata_ort']:.1f} ± {b['hata_std']:.1f} m")
        f, c = tutarlilik_tum[senaryo]["fuzyon"], tutarlilik_tum[senaryo]["fuzyon_cv"]
        print(f"Filtre tutarlılığı (ANEES, beklenen {BOYUT}): IMM {f['anees']:.2f} (%{100 * f['bant_ici']:.0f} "
              f"bantta), sadece CV {c['anees']:.2f} (%{100 * c['bant_ici']:.0f} bantta)")
    nees_tum = {"zaman": nees_zaman, "kosular": nees_kosular, "ozet": tutarlilik_tum}
    return kosular_tum, ozet_tum, bias_tum, nees_tum


def tutarlilik_tablosu(tutarlilik_tum, hedefler):
    """Filtre tutarlılığı (NEES) özet tablosu, Markdown."""
    i_iha = [h.ad for h in hedefler].index("İHA-1")
    satirlar = [f"Filtre tutarlılığı: konum NEES'i. Tutarlı bir filtrede ANEES ≈ {BOYUT} olur ve noktaların "
                "~%95'i %95 kabul bandında kalır.", "",
                "| Senaryo | Füzyon (IMM) ANEES | IMM bantta (%) | Sadece CV ANEES | CV bantta (%) "
                "| İHA-1 ANEES (IMM / CV) |",
                "|---|---:|---:|---:|---:|---:|"]
    for senaryo, d in tutarlilik_tum.items():
        f, c = d["fuzyon"], d["fuzyon_cv"]
        satirlar.append(f"| {senaryo} | {f['anees']:.2f} | {100 * f['bant_ici']:.0f} | {c['anees']:.2f} "
                        f"| {100 * c['bant_ici']:.0f} | {f['hedef'][i_iha]['anees']:.1f} / "
                        f"{c['hedef'][i_iha]['anees']:.1f} |")
    return "\n".join(satirlar)


def sonuclari_yaz(args, tohumlar, kosular_tum, ozet_tum, bias_tum, nees_tum, ornek_metrikler, hedefler):
    """Karşılaştırma grafiği, JSON ve Markdown tabloları.

    Tek senaryo koşusu, tüm senaryoların ortak tablosunu ezmesin diye senaryo
    adını taşıyan ayrı dosyalara yazılır (ör. karsilastirma_sis.png). Bağımsız
    doğrulama koşusu da (--ilk-seed) ana sonuçları ezmez.
    """
    ek = "" if args.hepsi else f"_{args.senaryo}"
    dosyalar = [f"karsilastirma{ek}.png", f"sonuclar{ek}.json", f"sonuclar{ek}.md"]
    if args.ilk_seed != TOHUM:
        dosyalar = [f"dogrulama_seed{args.ilk_seed}{ek}.{u}" for u in ("png", "json", "md")]
    karsilastirma_grafigi(ozet_tum, SONUC_DIZINI / dosyalar[0], len(tohumlar))
    json_veri = {"tekrar": len(tohumlar), "tohumlar": tohumlar, "ozet": ozet_tum,
                 "kosular": kosular_tum, "bias_kestirimi": bias_tum, "tutarlilik": nees_tum["ozet"],
                 "ornek_kosu_seed42": ornek_metrikler}
    (SONUC_DIZINI / dosyalar[1]).write_text(json.dumps(json_veri, indent=1, ensure_ascii=False),
                                            encoding="utf-8")
    md = markdown_tablo(ozet_tum, kosular_tum, bias_tum)
    md += "\n\n" + tutarlilik_tablosu(nees_tum["ozet"], hedefler)
    ana_json = SONUC_DIZINI / "sonuclar.json"
    if args.ilk_seed != TOHUM and ana_json.exists():
        md += "\n\n" + seed_kumesi_testi(json.loads(ana_json.read_text(encoding="utf-8")), kosular_tum)
    (SONUC_DIZINI / dosyalar[2]).write_text(md + "\n", encoding="utf-8")
    print("\n-> " + ", ".join(f"results/{d}" for d in dosyalar) + " kaydedildi")

    # NEES grafiği: İHA-1'in manevraları normal senaryoda (sadece ana seed kümesi için)
    if "normal" in nees_tum["kosular"] and args.ilk_seed == TOHUM:
        yol = SONUC_DIZINI / f"nees{ek}.png"
        nees_grafigi(nees_tum["zaman"], nees_tum["kosular"]["normal"], hedefler, yol, len(tohumlar),
                     manevralar=IHA1_MANEVRALARI)
        print(f"-> results/{yol.name} kaydedildi")


def ozet_figuru_yaz(hedefler, kayitlar, ornek_metrikler):
    """Özet figür: bir başarılı (sis) ve bir zorlu (sensör kaybı) örnek yan yana."""
    if "sis" not in kayitlar or "sensor_kaybi" not in kayitlar:
        return
    veriler = [
        ("sis", *kayitlar["sis"], ornek_metrikler["sis"],
         "Başarılı örnek — sis: kamera bozulur, füzyon radar ve konum bildirimiyle telafi eder"),
        ("sensor_kaybi", *kayitlar["sensor_kaybi"], ornek_metrikler["sensor_kaybi"],
         "Zorlu örnek — sensör kaybı: radar ve kamera sırayla düşer, izler kopar ve ID değişir"),
    ]
    ozet_figur(hedefler, veriler, SONUC_DIZINI / "ozet.png")
    print("-> results/ozet.png kaydedildi")


def main():
    # Windows konsolunda Türkçe karakterlerin düzgün görünmesi için
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = argumanlari_oku()

    SONUC_DIZINI.mkdir(exist_ok=True)
    hedefler = hedefleri_olustur()
    senaryolar = list(SENARYOLAR) if args.hepsi else [args.senaryo]
    tohumlar = list(range(args.ilk_seed, args.ilk_seed + max(1, args.tekrar)))

    kayitlar, ornek_metrikler = ornek_kosular(senaryolar, hedefler, gif=not args.gif_yok)
    kosular_tum, ozet_tum, bias_tum, nees_tum = coklu_kosular(senaryolar, tohumlar)
    sonuclari_yaz(args, tohumlar, kosular_tum, ozet_tum, bias_tum, nees_tum, ornek_metrikler, hedefler)
    ozet_figuru_yaz(hedefler, kayitlar, ornek_metrikler)


if __name__ == "__main__":
    main()
