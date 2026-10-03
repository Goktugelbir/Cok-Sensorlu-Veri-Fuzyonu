"""Simüle edilmiş sensör ölçümleri.

Her sensör, hedeflerin gerçek konumuna gürültü ekleyerek konum ölçümü üretir.
Ölçümler sensörün kendi zaman çizelgesinde alınır ve kendi gecikmesiyle
füzyon merkezine ulaşır. Her ölçüm, sensörün beyan ettiği nominal gürültü
kovaryansını (R) taşır; sis veya karıştırma gibi bozulmalar bu beyana
yansımaz, füzyon merkezi bunu kendisi fark etmek zorundadır.
"""

from dataclasses import dataclass

import numpy as np

from .saha import SAHA_BOYUTU, SURE

# Senaryolar: olayların geçerli olduğu zaman pencereleri (s)
SENARYOLAR = {
    "normal": {},
    "sis": {"sis": (60.0, SURE)},
    "karistirma": {"karistirma": (80.0, 220.0)},
    "sensor_kaybi": {"kayip": {"radar": (100.0, 170.0),
                               "kamera": (150.0, 230.0),
                               "konum": (200.0, 260.0)}},
}

KARISTIRICI_KONUM = np.array([7000.0, 6500.0])  # karıştırma kaynağının yeri


@dataclass
class SensorTanimi:
    ad: str
    konum: np.ndarray      # sensörün sahadaki yeri (konum bildirimi için anlamsız)
    menzil: float          # m
    frekans: float         # Hz
    faz: float             # ilk ölçüm anı (s); sensörler aynı anda ölçmez
    gecikme: float         # ortalama iletim gecikmesi (s)
    titreme: float         # gecikmedeki rastgele oynama (s)
    sigma_sabit: float     # gürültü: sigma = sigma_sabit + sigma_oran * mesafe
    sigma_oran: float
    tespit_olasiligi: float
    yanlis_alarm: float    # tarama başına ortalama yanlış alarm sayısı
    sadece_dost: bool = False
    bias: tuple = (0.0, 0.0)


SENSORLER = {
    "radar": SensorTanimi("radar", np.array([4000.0, 4000.0]), 8_000.0, 1.0, 0.37,
                          0.6, 0.1, 12.0, 0.002, 0.9, 0.5),
    "kamera": SensorTanimi("kamera", np.array([5500.0, 5000.0]), 3_500.0, 5.0, 0.05,
                           0.3, 0.05, 3.0, 0.004, 0.95, 0.0),
    "konum": SensorTanimi("konum", np.array([np.nan, np.nan]), np.inf, 0.5, 0.8,
                          1.5, 0.2, 3.0, 0.0, 0.98, 0.0, sadece_dost=True,
                          bias=(35.0, -20.0)),
}

FUZYON_GECIKMESI = 2.0  # füzyonun beklediği sabit gecikme penceresi (s); en büyük gecikmeden büyük


@dataclass
class Olcum:
    sensor: str
    t_olcum: float         # ölçümün alındığı an
    t_varis: float         # füzyon merkezine ulaştığı an
    z: np.ndarray          # ölçülen konum (2,)
    R: np.ndarray          # sensörün beyan ettiği gürültü kovaryansı (2x2)
    etiket: int = None     # konum bildiriminde dost birliğin kimliği
    kaynak: int = None     # sadece hata ayıklama için: ölçümü üreten gerçek hedef


def _icinde(t, pencere):
    return pencere is not None and pencere[0] <= t < pencere[1]


def sensor_durumu(senaryo, ad, t):
    """Senaryoya göre sensörün t anındaki etkin parametrelerini döndürür."""
    s = SENSORLER[ad]
    olay = SENARYOLAR[senaryo]
    durum = dict(aktif=True, menzil=s.menzil, gurultu_carpani=1.0,
                 pd=s.tespit_olasiligi, yanlis_alarm=s.yanlis_alarm, karistirma=False)
    if _icinde(t, olay.get("kayip", {}).get(ad)):
        durum["aktif"] = False
    if ad == "kamera" and _icinde(t, olay.get("sis")):
        # Sis: görüş mesafesi kısalır, gürültü artar, hedefler kaçırılır
        durum.update(menzil=s.menzil * 0.65, gurultu_carpani=3.0, pd=0.5)
    if ad == "radar" and _icinde(t, olay.get("karistirma")):
        # Karıştırma: gürültü artar, tespit düşer, yoğun yanlış alarm oluşur
        durum.update(gurultu_carpani=4.0, pd=0.7, yanlis_alarm=8.0, karistirma=True)
    return durum


def _sigma(s, mesafe):
    return s.sigma_sabit + s.sigma_oran * mesafe


def olcumleri_uret(hedefler, senaryo, rng):
    """Tüm sensörlerin senaryo boyunca ürettiği ölçümleri döndürür (sözlük: sensör -> liste)."""
    sonuc = {}
    for ad, s in SENSORLER.items():
        liste = []
        for t in np.arange(s.faz, SURE, 1.0 / s.frekans):
            d = sensor_durumu(senaryo, ad, t)
            if not d["aktif"]:
                continue
            gecikme = s.gecikme + rng.uniform(0, s.titreme)

            # Gerçek hedeflerden gelen tespitler
            for h in hedefler:
                if s.sadece_dost and not h.dost:
                    continue
                p = h.konum_at(t)
                mesafe = 0.0 if s.sadece_dost else np.linalg.norm(p - s.konum)
                if mesafe > d["menzil"] or rng.random() > d["pd"]:
                    continue
                sigma_nom = _sigma(s, mesafe)
                z = p + np.array(s.bias) + rng.normal(0, sigma_nom * d["gurultu_carpani"], 2)
                liste.append(Olcum(ad, t, t + gecikme, z, np.eye(2) * sigma_nom ** 2,
                                   etiket=h.hid if s.sadece_dost else None, kaynak=h.hid))

            # Yanlış alarmlar
            for _ in range(rng.poisson(d["yanlis_alarm"])):
                if d["karistirma"] and rng.random() < 0.7:
                    z = KARISTIRICI_KONUM + rng.normal(0, 1200.0, 2)
                else:
                    z = rng.uniform(0, SAHA_BOYUTU, 2)
                mesafe = np.linalg.norm(z - s.konum)
                if mesafe > d["menzil"]:
                    continue
                liste.append(Olcum(ad, t, t + gecikme, z, np.eye(2) * _sigma(s, mesafe) ** 2))
        sonuc[ad] = liste
    return sonuc
