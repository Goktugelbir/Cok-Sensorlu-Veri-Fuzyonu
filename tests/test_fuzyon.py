"""Füzyon hattının uçtan uca regresyon testleri (seed=42)."""

import numpy as np
import pytest

from src.degerlendirme import degerlendir
from src.fuzyon import fuzyon_calistir
from src.saha import hedefleri_olustur
from src.sensorler import SENSORLER, olcumleri_uret

TUM = ["radar", "kamera", "konum"]


@pytest.fixture(scope="module")
def hedefler():
    return hedefleri_olustur()


def _olcumler(hedefler, senaryo):
    return olcumleri_uret(hedefler, senaryo, np.random.default_rng(42))


def test_bias_kestirimi_gercege_yakin(hedefler):
    _, merkez = fuzyon_calistir(_olcumler(hedefler, "normal"), TUM)
    hata = np.linalg.norm(merkez.bias["konum"] - np.array(SENSORLER["konum"].bias))
    assert hata < 10.0


def test_fuzyon_en_iyi_tek_sensorden_iyi(hedefler):
    olcumler = _olcumler(hedefler, "normal")
    fuzyon = degerlendir(fuzyon_calistir(olcumler, TUM)[0], hedefler)
    radar = degerlendir(fuzyon_calistir(olcumler, ["radar"])[0], hedefler)
    assert fuzyon["gospa"] < radar["gospa"]
    assert fuzyon["kacirma"] < radar["kacirma"]
    # Dost/diğer etiketini sadece füzyon doğru verir (radar izleri hep "diğer")
    assert fuzyon["etiket"] > 0.99
    assert radar["etiket"] < 0.8


def test_karistirmada_radar_guveni_duser_ve_sahte_iz_olusmaz(hedefler):
    olcumler = _olcumler(hedefler, "karistirma")
    gecmis, _ = fuzyon_calistir(olcumler, TUM)
    karistirma_guveni = [g["radar"] for t, _, g in gecmis if 120 <= t < 220]
    assert np.mean(karistirma_guveni) < 0.5
    assert degerlendir(gecmis, hedefler)["yanlis_iz"] == 0
    # Ablasyon: güven ağırlıklandırma kapatılınca sahte iz oluşur
    gecmis_guvensiz, _ = fuzyon_calistir(olcumler, TUM, guven_agirliklandirma=False)
    assert degerlendir(gecmis_guvensiz, hedefler)["yanlis_iz"] > 0


def test_normal_senaryoda_sensor_guvenleri_yuksek_kalir(hedefler):
    gecmis, _ = fuzyon_calistir(_olcumler(hedefler, "normal"), TUM)
    son = gecmis[-1][2]
    assert all(g > 0.9 for g in son.values())


def test_imm_sert_donuste_cvden_iyi(hedefler):
    """İHA-1'in sert sağa kırılması (210-222 s) sabit hız modelini zorlar; IMM daha iyi izler."""
    olcumler = _olcumler(hedefler, "normal")
    imm = degerlendir(fuzyon_calistir(olcumler, TUM, hareket_modeli="imm")[0], hedefler)
    cv = degerlendir(fuzyon_calistir(olcumler, TUM, hareket_modeli="cv")[0], hedefler)
    assert imm["gospa"] < cv["gospa"]
    assert imm["rmse"] < cv["rmse"]


def test_imm_model_olasiliklari_duz_ve_donuste_ayrisir(hedefler):
    gecmis, _ = fuzyon_calistir(_olcumler(hedefler, "normal"), TUM)
    iha = hedefler[1]
    duz, donus = [], []
    for t, resim, _ in gecmis:
        gercek = iha.konum_at(t)
        yakin = [iz for iz in resim if np.linalg.norm(iz["konum"] - gercek) < 100.0]
        if yakin:
            (donus if 212 <= t < 224 else duz).append(yakin[0]["model_olasiliklari"][1])
    assert np.mean(duz) < 0.3
    assert np.mean(donus) > 0.5
