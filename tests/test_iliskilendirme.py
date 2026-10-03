import numpy as np

from src.iliskilendirme import iliskilendir, maliyet_matrisi
from src.kalman import KalmanCV


def test_macar_algoritmasi_en_iyi_eslesmeyi_bulur():
    M = np.array([[1.0, 5.0],
                  [2.0, 1.5]])
    eslesmeler, bos_iz, bos_olc = iliskilendir(M)
    assert sorted(eslesmeler) == [(0, 0), (1, 1)]
    assert bos_iz == [] and bos_olc == []


def test_kapi_disindaki_olcum_atanmaz():
    R = np.eye(2) * 25.0
    izler = [KalmanCV([0, 0], R), KalmanCV([1000, 0], R)]
    olcumler = [np.array([1.0, 2.0]), np.array([5000.0, 5000.0])]
    M = maliyet_matrisi(izler, olcumler, [R, R])
    eslesmeler, bos_iz, bos_olc = iliskilendir(M)
    assert eslesmeler == [(0, 0)]
    assert bos_iz == [1]
    assert bos_olc == [1]


def test_capraz_olcumler_dogru_ize_gider():
    R = np.eye(2) * 25.0
    izler = [KalmanCV([0, 0], R), KalmanCV([100, 100], R)]
    olcumler = [np.array([98.0, 103.0]), np.array([-2.0, 1.0])]
    M = maliyet_matrisi(izler, olcumler, [R, R])
    eslesmeler, _, _ = iliskilendir(M)
    assert sorted(eslesmeler) == [(0, 1), (1, 0)]


def test_bos_girdi():
    eslesmeler, bos_iz, bos_olc = iliskilendir(np.zeros((0, 3)))
    assert eslesmeler == [] and bos_iz == [] and bos_olc == [0, 1, 2]
