import numpy as np

from src.degerlendirme import gospa

C = 250.0


def test_gospa_mukemmel_eslesmede_sifir():
    X = np.array([[0.0, 0.0], [1000.0, 0.0]])
    assert gospa(X, X.copy(), C) == 0.0


def test_gospa_konum_hatasi():
    X = np.array([[0.0, 0.0]])
    Y = np.array([[3.0, 4.0]])
    assert np.isclose(gospa(X, Y, C), 5.0)


def test_gospa_kacirilan_ve_sahte_hedef_cezasi():
    X = np.array([[0.0, 0.0], [5000.0, 5000.0]])
    Y = np.array([[0.0, 0.0], [9000.0, 0.0]])
    # bir eşleşme (hata 0), bir kaçırılan + bir sahte: sqrt(c²/2 * 2) = c
    assert np.isclose(gospa(X, Y, C), C)


def test_gospa_bos_iz_listesi():
    X = np.array([[0.0, 0.0], [10.0, 0.0]])
    assert np.isclose(gospa(X, np.zeros((0, 2)), C), np.sqrt(C ** 2 / 2 * 2))
