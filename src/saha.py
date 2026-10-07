"""Harekât sahası ve hedeflerin gerçek rotaları.

Saha 10 km x 10 km'lik iki boyutlu bir alandır. Koordinatlar metre cinsindendir,
(0, 0) sol alt köşedir. Her hedefin rotası; başlangıç noktası, zamana bağlı hız
ve zamana bağlı dönüş hızı ile adım adım üretilir.
"""

from dataclasses import dataclass, field

import numpy as np

SAHA_BOYUTU = 10_000.0  # metre
SURE = 300.0            # toplam senaryo süresi (s)
DT_GERCEK = 0.1         # gerçek rota örnekleme adımı (s)


@dataclass
class Hedef:
    """Sahadaki bir hedef ve gerçek rotası."""
    hid: int
    ad: str
    dost: bool
    zaman: np.ndarray = field(repr=False)     # (N,)
    konum: np.ndarray = field(repr=False)     # (N, 2)
    hava: bool = False  # hava aracı mı; sadece görselleştirmede kullanılır (simülasyon 2 boyutludur)

    def konum_at(self, t):
        """t anındaki gerçek konumu doğrusal ara değerleme ile döndürür."""
        x = np.interp(t, self.zaman, self.konum[:, 0])
        y = np.interp(t, self.zaman, self.konum[:, 1])
        return np.array([x, y])


def _rota_uret(baslangic, yon_derece, hiz_fonk, donus_fonk):
    """Hız (m/s) ve dönüş hızı (derece/s) fonksiyonlarından rota üretir."""
    zaman = np.arange(0.0, SURE + DT_GERCEK, DT_GERCEK)
    konum = np.zeros((len(zaman), 2))
    konum[0] = baslangic
    yon = np.deg2rad(yon_derece)
    for k in range(1, len(zaman)):
        t = zaman[k - 1]
        yon += np.deg2rad(donus_fonk(t)) * DT_GERCEK
        v = hiz_fonk(t)
        konum[k] = konum[k - 1] + v * DT_GERCEK * np.array([np.cos(yon), np.sin(yon)])
    return zaman, konum


def _yumusak_gecis(t, t0, t1, a, b):
    """t0-t1 arasında a değerinden b değerine doğrusal geçiş."""
    if t <= t0:
        return a
    if t >= t1:
        return b
    return a + (b - a) * (t - t0) / (t1 - t0)


def hedefleri_olustur():
    """Senaryodaki beş hedefi (2'si dost) oluşturur."""
    tanimlar = [
        # Düz rota, sabit hız
        dict(hid=1, ad="Araç-1", dost=False, baslangic=(1500, 7000), yon=-20,
             hiz=lambda t: 10.0, donus=lambda t: 0.0),
        # Dönüşlü rota: düz uçuş, uzun bir sola dönüş, ardından sert sağa kırılma
        # (210-222 s: 12 s'de 90°, merkezcil ivme ~2.9 m/s²; sabit hız modelini zorlar)
        dict(hid=2, ad="İHA-1", dost=False, hava=True, baslangic=(8800, 2000), yon=110,
             hiz=lambda t: 22.0,
             donus=lambda t: 1.5 if 60 <= t < 150 else (-7.5 if 210 <= t < 222 else 0.0)),
        # Yavaş hareket eden insan grubu, hafif kıvrımlı
        dict(hid=3, ad="İnsan Grubu", dost=False, baslangic=(4600, 3600), yon=70,
             hiz=lambda t: 1.5, donus=lambda t: 0.3 * np.sin(t / 30.0)),
        # Hız değiştiren dost araç
        dict(hid=4, ad="Dost Araç", dost=True, baslangic=(1000, 1500), yon=35,
             hiz=lambda t: _yumusak_gecis(t, 90, 110, 8.0, 16.0) if t < 190
             else _yumusak_gecis(t, 190, 210, 16.0, 5.0),
             donus=lambda t: 0.0),
        # Dönüşlü ve hız değiştiren dost İHA
        dict(hid=5, ad="Dost İHA", dost=True, hava=True, baslangic=(9200, 8800), yon=200,
             hiz=lambda t: _yumusak_gecis(t, 150, 170, 18.0, 12.0),
             donus=lambda t: 2.0 if 120 <= t < 150 else 0.0),
    ]
    hedefler = []
    for d in tanimlar:
        zaman, konum = _rota_uret(np.array(d["baslangic"], float), d["yon"], d["hiz"], d["donus"])
        hedefler.append(Hedef(d["hid"], d["ad"], d["dost"], zaman, konum, d.get("hava", False)))
    return hedefler
