"""İz-ölçüm ilişkilendirme: Mahalanobis kapılama + optimal atama.

Atama problemi (Macar algoritmasının çözdüğü problem) scipy.optimize.linear_sum_assignment
ile çözülür; bu fonksiyon Crouse'un (2016) en kısa artırma yolu yöntemini uygular.
"""

import numpy as np
from scipy.optimize import linear_sum_assignment

# 2 serbestlik dereceli ki-kare dağılımının %99.9 eşiği
KAPI_ESIGI = 13.8
ATANAMAZ = 1e9  # kapı dışı ya da yasak (iz, ölçüm) çiftinin maliyeti


def maliyet_matrisi(izler, olcumler, R_listesi):
    """Her (iz, ölçüm) çifti için Mahalanobis uzaklığının karesi.

    Kapı dışında kalan çiftler çok büyük maliyet alır.
    izler: konum ve P (kovaryans) özelliği olan filtre nesneleri (KalmanCV, IMM)
    """
    M = np.full((len(izler), len(olcumler)), ATANAMAZ)
    if not izler or not olcumler:
        return M
    # Bütün (iz, ölçüm) çiftleri tek seferde: y = z - Hx, S = HPHᵀ + R
    konum = np.array([iz.konum for iz in izler])                # (n, 2)
    P_konum = np.array([iz.P[:2, :2] for iz in izler])          # (n, 2, 2)
    y = np.asarray(olcumler)[None, :, :] - konum[:, None, :]    # (n, m, 2)
    S = P_konum[:, None, :, :] + np.asarray(R_listesi)[None]    # (n, m, 2, 2)
    # 2x2 simetrik S için kapalı form: d² = yᵀ S⁻¹ y
    a, b, d = S[..., 0, 0], S[..., 0, 1], S[..., 1, 1]
    det = a * d - b * b
    d2 = (d * y[..., 0] ** 2 - 2 * b * y[..., 0] * y[..., 1] + a * y[..., 1] ** 2) / det
    kapida = d2 <= KAPI_ESIGI
    # log|S| terimi: belirsizliği çok büyük izlerin her şeyi "kapmasını" önler
    M[kapida] = d2[kapida] + np.log(det[kapida])
    return M


def iliskilendir(M):
    """Maliyet matrisinden en iyi eşleşmeyi bulur.

    Dönüş: (eşleşmeler [(iz_idx, olcum_idx)], atanmamış izler, atanmamış ölçümler)
    """
    n_iz, n_olc = M.shape
    if n_iz == 0 or n_olc == 0:
        return [], list(range(n_iz)), list(range(n_olc))
    satir, sutun = linear_sum_assignment(M)
    eslesmeler = [(i, j) for i, j in zip(satir, sutun) if M[i, j] < ATANAMAZ]
    atanan_iz = {i for i, _ in eslesmeler}
    atanan_olc = {j for _, j in eslesmeler}
    bos_izler = [i for i in range(n_iz) if i not in atanan_iz]
    bos_olcumler = [j for j in range(n_olc) if j not in atanan_olc]
    return eslesmeler, bos_izler, bos_olcumler
