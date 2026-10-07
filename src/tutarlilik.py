"""Filtre tutarlılığı: normalize kestirim hatası karesi (NEES) [1].

Tutarlı bir filtrede konum hatası e = x̂ - x, filtrenin kendi bildirdiği konum
kovaryansı P ile uyumludur: NEES = eᵀ P⁻¹ e, 2 serbestlik dereceli ki-kare dağılır
(ortalaması 2). N Monte Carlo koşusunun ortalaması ANEES için N · ANEES ~ χ²(2N)
olduğundan her an için %95'lik bir kabul bandı hesaplanır. ANEES bandın
üstündeyse filtre kendine fazla güveniyor (hata, bildirdiği belirsizlikten büyük),
altındaysa fazla temkinli.

İzler gerçek hedeflere RMSE ile aynı eşleştirmeyle (degerlendirme.eslestir)
bağlanır; eşleşmeyen (hedef, an) çiftleri hesaba girmez.
"""

import warnings

import numpy as np
from scipy.stats import chi2

from .degerlendirme import eslestir

BOYUT = 2  # konum NEES'inin serbestlik derecesi (x, y)


def nees_dizisi(gecmis, hedefler):
    """Tek koşu: her (hedef, an) için eşleşen izin konum NEES'i, eşleşme yoksa NaN.

    Dönüş: (zamanlar (n_an,), NEES (n_hedef, n_an))
    """
    zaman = np.array([t for t, _, _ in gecmis])
    nees = np.full((len(hedefler), len(gecmis)), np.nan)
    for k, (t, resim, _) in enumerate(gecmis):
        gercek = np.array([h.konum_at(t) for h in hedefler])
        tahmin = np.array([iz["konum"] for iz in resim]).reshape(-1, 2)
        for i, (j, _) in eslestir(gercek, tahmin).items():
            e = tahmin[j] - gercek[i]
            nees[i, k] = float(e @ np.linalg.solve(resim[j]["P_konum"], e))
    return zaman, nees


def anees(nees_kosular):
    """(n_koşu, n_hedef, n_an) -> koşu ortalaması ANEES ve her noktadaki koşu sayısı."""
    A = np.asarray(nees_kosular, float)
    n = np.sum(~np.isnan(A), axis=0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # hiç eşleşme olmayan anlar NaN kalır
        return np.nanmean(A, axis=0), n


def kabul_bandi(n, olasilik=0.95):
    """n koşunun ANEES'i için iki yönlü kabul bandı (alt, üst); n = 0 olan yerlerde NaN."""
    n = np.asarray(n, float)
    a = (1 - olasilik) / 2
    with np.errstate(divide="ignore", invalid="ignore"):
        alt = np.where(n > 0, chi2.ppf(a, BOYUT * n) / n, np.nan)
        ust = np.where(n > 0, chi2.ppf(1 - a, BOYUT * n) / n, np.nan)
    return alt, ust


def ozetle(nees_kosular, en_az_kosu):
    """Tutarlılık özeti.

    - anees: bütün eşleşen (koşu, hedef, an) örneklerinin NEES ortalaması (beklenen 2)
    - bant_ici: ANEES'in %95 kabul bandında kaldığı (hedef, an) oranı; sadece en az
      en_az_kosu koşuda eşleşmesi olan noktalar sayılır
    - hedef: aynı iki değer hedef bazında
    """
    A = np.asarray(nees_kosular, float)
    ort, n = anees(A)
    alt, ust = kabul_bandi(n)
    yeterli = n >= en_az_kosu
    icinde = (ort >= alt) & (ort <= ust) & yeterli

    def oran(maske_ici, maske):
        return float(maske_ici.sum() / maske.sum()) if maske.sum() else float("nan")

    return {"anees": float(np.nanmean(A)), "bant_ici": oran(icinde, yeterli),
            "hedef": [{"anees": float(np.nanmean(A[:, i])) if np.any(~np.isnan(A[:, i])) else float("nan"),
                       "bant_ici": oran(icinde[i], yeterli[i])} for i in range(A.shape[1])]}
