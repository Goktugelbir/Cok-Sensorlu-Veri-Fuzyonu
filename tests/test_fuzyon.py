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
