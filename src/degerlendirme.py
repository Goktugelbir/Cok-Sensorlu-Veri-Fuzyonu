"""Başarım ölçütleri: RMSE, kaçırma oranı, yanlış iz sayısı, ID switch."""

import numpy as np
from scipy.optimize import linear_sum_assignment

ESLESME_ESIGI = 250.0  # iz ile gerçek hedef bu mesafeden uzaksa eşleşmiş sayılmaz (m)


def degerlendir(gecmis, hedefler):
    """Füzyon geçmişini gerçek rotalarla karşılaştırır.

    Her kayıt anında onaylı izler gerçek hedeflere Macar algoritmasıyla
    (Öklid mesafesi, eşikli) eşlenir.
    - RMSE: eşleşen çiftlerin konum hatasının karesel ortalamasının kökü (m)
    - Kaçırma oranı: hiçbir ize eşlenmeyen (hedef, an) çiftlerinin oranı
    - Yanlış iz: ömrünün yarısından fazlasında hiçbir hedefe eşlenmeyen iz sayısı
    - ID switch: bir hedefi izleyen iz kimliğinin değiştiği durum sayısı
    """
    hatalar_kare = []
    kacan, toplam = 0, 0
    iz_eslesme = {}           # iz_id -> [eşleşen an sayısı, toplam an sayısı]
    son_id = {h.hid: None for h in hedefler}
    id_switch = 0

    for t, resim, _ in gecmis:
        gercek = np.array([h.konum_at(t) for h in hedefler])
        tahmin = np.array([iz["konum"] for iz in resim]).reshape(-1, 2)
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
    return dict(rmse=rmse, kacirma=kacan / toplam, yanlis_iz=yanlis_iz, id_switch=id_switch)
