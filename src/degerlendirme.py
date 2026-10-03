"""Başarım ölçütleri: RMSE, GOSPA, kaçırma oranı, yanlış iz sayısı, ID switch, etiket doğruluğu."""

import numpy as np
from scipy.optimize import linear_sum_assignment

ESLESME_ESIGI = 250.0  # iz ile gerçek hedef bu mesafeden uzaksa eşleşmiş sayılmaz (m)
GOSPA_C = ESLESME_ESIGI  # GOSPA kesme mesafesi c (m); p = 2, alfa = 2


def gospa(gercek, tahmin, c=GOSPA_C):
    """Tek an için GOSPA uzaklığı (p=2, alfa=2).

    Eşleşen çiftlerin konum hatası ile kaçırılan ve sahte hedeflerin her biri
    için c²/2 cezası tek bir sayıda toplanır. Hiç iz yoksa her hedef kaçırılmış,
    hiç hedef yoksa her iz sahte sayılır.
    """
    if len(gercek) == 0 or len(tahmin) == 0:
        return float(np.sqrt(c ** 2 / 2 * (len(gercek) + len(tahmin))))
    D2 = np.minimum(np.sum((gercek[:, None, :] - tahmin[None, :, :]) ** 2, axis=2), c ** 2)
    satir, sutun = linear_sum_assignment(D2)
    konum = sum(D2[i, j] for i, j in zip(satir, sutun) if D2[i, j] < c ** 2)
    eslesen = sum(1 for i, j in zip(satir, sutun) if D2[i, j] < c ** 2)
    eksik_sahte = len(gercek) + len(tahmin) - 2 * eslesen
    return float(np.sqrt(konum + c ** 2 / 2 * eksik_sahte))


def degerlendir(gecmis, hedefler):
    """Füzyon geçmişini gerçek rotalarla karşılaştırır.

    Her kayıt anında onaylı izler gerçek hedeflere optimal atamayla
    (Öklid mesafesi, eşikli) eşlenir.
    - RMSE: eşleşen çiftlerin konum hatasının karesel ortalamasının kökü (m)
    - GOSPA: konum hatası + kaçırılan + sahte hedefleri birlikte cezalandıran
      uzaklığın zaman ortalaması (m); tek sayıda kapsama ve doğruluk
    - Kaçırma oranı: hiçbir ize eşlenmeyen (hedef, an) çiftlerinin oranı
    - Yanlış iz: ömrünün yarısından fazlasında hiçbir hedefe eşlenmeyen iz sayısı
    - ID switch: bir hedefi izleyen iz kimliğinin değiştiği durum sayısı
    - Etiket doğruluğu: eşleşen (hedef, an) çiftlerinde izin dost/diğer etiketinin
      hedefin gerçek türüyle aynı olma oranı. Konum bildirimi desteği olmayan izler
      "diğer" sayılır.
    """
    hatalar_kare = []
    kacan, toplam = 0, 0
    iz_eslesme = {}           # iz_id -> [eşleşen an sayısı, toplam an sayısı]
    son_id = {h.hid: None for h in hedefler}
    id_switch = 0
    etiket_dogru = 0
    gospa_degerleri = []

    for t, resim, _ in gecmis:
        gercek = np.array([h.konum_at(t) for h in hedefler])
        tahmin = np.array([iz["konum"] for iz in resim]).reshape(-1, 2)
        gospa_degerleri.append(gospa(gercek, tahmin))
        eslesen = {}
        if len(tahmin):
            D = np.linalg.norm(gercek[:, None, :] - tahmin[None, :, :], axis=2)
            satir, sutun = linear_sum_assignment(D)
            for i, j in zip(satir, sutun):
                if D[i, j] <= ESLESME_ESIGI:
                    eslesen[i] = j
                    hatalar_kare.append(D[i, j] ** 2)

        for i, h in enumerate(hedefler):
            toplam += 1
            if i not in eslesen:
                kacan += 1
                continue
            iz_id = resim[eslesen[i]]["id"]
            etiket_dogru += resim[eslesen[i]]["dost"] == h.dost
            if son_id[h.hid] is not None and son_id[h.hid] != iz_id:
                id_switch += 1
            son_id[h.hid] = iz_id

        eslesen_izler = set(eslesen.values())
        for j, iz in enumerate(resim):
            kayit = iz_eslesme.setdefault(iz["id"], [0, 0])
            kayit[1] += 1
            if j in eslesen_izler:
                kayit[0] += 1

    yanlis_iz = sum(1 for e, n in iz_eslesme.values() if e < 0.5 * n)
    rmse = float(np.sqrt(np.mean(hatalar_kare))) if hatalar_kare else float("nan")
    eslesen_sayisi = toplam - kacan
    etiket = etiket_dogru / eslesen_sayisi if eslesen_sayisi else float("nan")
    return dict(rmse=rmse, gospa=float(np.mean(gospa_degerleri)), kacirma=kacan / toplam,
                yanlis_iz=yanlis_iz, id_switch=id_switch, etiket=etiket)
