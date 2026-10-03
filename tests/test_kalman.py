import numpy as np

from src.kalman import KalmanCV, cv_matrisleri


def test_gecis_matrisi_sabit_hiz():
    F, Q = cv_matrisleri(2.0, 1.0)
    x = np.array([0.0, 0.0, 3.0, -1.0])
    assert np.allclose(F @ x, [6.0, -2.0, 3.0, -1.0])
    assert np.allclose(Q, Q.T)


def test_tahmin_belirsizligi_artirir():
    kf = KalmanCV([0, 0], np.eye(2) * 25.0)
    iz_once = np.trace(kf.P)
    kf.tahmin(1.0)
    assert np.trace(kf.P) > iz_once


def test_guncelleme_belirsizligi_azaltir_ve_olcume_yaklasir():
    kf = KalmanCV([0, 0], np.eye(2) * 100.0)
    kf.tahmin(1.0)
    P_once = np.trace(kf.P[:2, :2])
    kf.guncelle(np.array([10.0, 0.0]), np.eye(2) * 100.0)
    assert np.trace(kf.P[:2, :2]) < P_once
    assert 0.0 < kf.x[0] < 10.0


def test_sabit_hizli_hedefi_izler():
    rng = np.random.default_rng(42)
    kf = KalmanCV([0, 0], np.eye(2) * 25.0)
    hiz = np.array([10.0, 5.0])
    for k in range(1, 60):
        kf.tahmin(1.0)
        kf.guncelle(hiz * k + rng.normal(0, 5.0, 2), np.eye(2) * 25.0)
    assert np.linalg.norm(kf.x[2:] - hiz) < 1.0
    assert np.linalg.norm(kf.konum - hiz * 59) < 10.0
