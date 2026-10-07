import numpy as np
from scipy.stats import chi2

from src.fuzyon import fuzyon_calistir
from src.saha import Hedef, hedefleri_olustur
from src.sensorler import olcumleri_uret
from src.tutarlilik import kabul_bandi, nees_dizisi, ozetle


def _sabit_hedef(konum):
    return Hedef(1, "H", False, np.array([0.0, 1000.0]), np.array([konum, konum], float))


def test_nees_elle_hesaplanan_deger():
    hedefler = [_sabit_hedef((0.0, 0.0))]
    P = np.diag([100.0, 25.0])  # σx = 10 m, σy = 5 m
    gecmis = [(0.0, [{"konum": np.array([10.0, 5.0]), "P_konum": P}], {}),
              (1.0, [], {})]                                     # eşleşme yok -> NaN
    zaman, nees = nees_dizisi(gecmis, hedefler)
    assert np.allclose(zaman, [0.0, 1.0])
    assert np.isclose(nees[0, 0], 10 ** 2 / 100 + 5 ** 2 / 25)  # = 2
    assert np.isnan(nees[0, 1])


def test_kabul_bandi_tek_kosuda_ki_kare_yuzdelikleri():
    alt, ust = kabul_bandi(np.array([1, 30]))
    assert np.isclose(alt[0], chi2.ppf(0.025, 2)) and np.isclose(ust[0], chi2.ppf(0.975, 2))
    assert alt[1] < 2 < ust[1] and ust[1] - alt[1] < ust[0] - alt[0]  # koşu arttıkça bant daralır


def test_tutarli_kestirici_beklenen_degerleri_verir():
    """Hatası gerçekten bildirdiği kovaryansla dağılan bir kestirici: ANEES ≈ 2, ~%95 bantta."""
    rng = np.random.default_rng(0)
    P = np.array([[400.0, 120.0], [120.0, 225.0]])
    L = np.linalg.cholesky(P)
    e = rng.standard_normal((30, 3, 200, 2)) @ L.T                  # (koşu, hedef, an, 2)
    nees = np.einsum("...i,ij,...j->...", e, np.linalg.inv(P), e)
    ozet = ozetle(nees, en_az_kosu=15)
    assert abs(ozet["anees"] - 2) < 0.05
    assert 0.92 < ozet["bant_ici"] < 0.98


def test_imm_tutarli_cv_sert_donuste_tutarsiz():
    hedefler = hedefleri_olustur()
    olcumler = olcumleri_uret(hedefler, "normal", np.random.default_rng(42))
    i_iha = [h.ad for h in hedefler].index("İHA-1")
    sonuc = {}
    for model in ("imm", "cv"):
        gecmis, _ = fuzyon_calistir(olcumler, ["radar", "kamera", "konum"], hareket_modeli=model)
        sonuc[model] = nees_dizisi(gecmis, hedefler)[1]
    assert 1.0 < np.nanmean(sonuc["imm"]) < 3.5
    assert np.nanmean(sonuc["cv"][i_iha]) > 3 * np.nanmean(sonuc["imm"][i_iha])
