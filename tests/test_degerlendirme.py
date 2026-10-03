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


def _sabit_hedef(hid, konum, dost=False):
    from src.saha import Hedef
    return Hedef(hid, f"H{hid}", dost, np.array([0.0, 1000.0]), np.array([konum, konum], float))


def _iz(iz_id, konum, dost=False):
    return {"id": iz_id, "konum": np.array(konum, float), "dost": dost}


def test_degerlendir_id_switch_yanlis_iz_ve_etiket():
    from src.degerlendirme import degerlendir
    hedefler = [_sabit_hedef(1, (0, 0)), _sabit_hedef(2, (5000, 5000), dost=True)]
    gecmis = [
        (0.0, [_iz(1, (10, 0)), _iz(2, (5000, 5000), dost=True)], {}),
        (1.0, [_iz(1, (10, 0)), _iz(2, (5000, 5000), dost=False)], {}),
        # Hedef 1'in izi değişir (ID switch); uzakta sahte bir iz belirir
        (2.0, [_iz(3, (0, 10)), _iz(2, (5000, 5000), dost=True), _iz(9, (9000, 0))], {}),
        # Hedef 2 kaçırılır
        (3.0, [_iz(3, (0, 10)), _iz(9, (9000, 0))], {}),
    ]
    m = degerlendir(gecmis, hedefler)
    assert m["id_switch"] == 1
    assert m["yanlis_iz"] == 1                 # iz 9 hiç eşleşmedi
    assert np.isclose(m["kacirma"], 1 / 8)     # 8 (hedef, an) çiftinden 1'i
    assert np.isclose(m["rmse"], np.sqrt(4 * 10.0 ** 2 / 7))  # 7 eşleşme; 4'ünde hata 10 m
    assert np.isclose(m["etiket"], 6 / 7)      # 7 eşleşmeden birinde dost etiketi yanlış
