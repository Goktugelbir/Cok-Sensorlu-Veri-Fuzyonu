"""İz-ölçüm ilişkilendirme: Mahalanobis kapılama + Macar algoritması."""

import numpy as np
from scipy.optimize import linear_sum_assignment

# 2 serbestlik dereceli ki-kare dağılımının %99.9 eşiği
KAPI_ESIGI = 13.8
_BUYUK = 1e9


def maliyet_matrisi(izler, olcumler, R_listesi):
    """Her (iz, ölçüm) çifti için Mahalanobis uzaklığının karesi.

    Kapı dışında kalan çiftler çok büyük maliyet alır.
    izler: KalmanCV benzeri nesneler (inovasyon metodu olan)
    """
    M = np.full((len(izler), len(olcumler)), _BUYUK)
    for i, iz in enumerate(izler):
        for j, (z, R) in enumerate(zip(olcumler, R_listesi)):
            y, S = iz.inovasyon(z, R)
            d2 = float(y @ np.linalg.solve(S, y))
            if d2 <= KAPI_ESIGI:
                # log|S| terimi: belirsizliği çok büyük izlerin her şeyi "kapmasını" önler
                M[i, j] = d2 + np.log(np.linalg.det(S))
    return M


def iliskilendir(M):
    """Maliyet matrisinden en iyi eşleşmeyi bulur.

    Dönüş: (eşleşmeler [(iz_idx, olcum_idx)], atanmamış izler, atanmamış ölçümler)
    """
    n_iz, n_olc = M.shape
    if n_iz == 0 or n_olc == 0:
        return [], list(range(n_iz)), list(range(n_olc))
    satir, sutun = linear_sum_assignment(M)
    eslesmeler = [(i, j) for i, j in zip(satir, sutun) if M[i, j] < _BUYUK]
    atanan_iz = {i for i, _ in eslesmeler}
    atanan_olc = {j for _, j in eslesmeler}
    bos_izler = [i for i in range(n_iz) if i not in atanan_iz]
    bos_olcumler = [j for j in range(n_olc) if j not in atanan_olc]
    return eslesmeler, bos_izler, bos_olcumler
