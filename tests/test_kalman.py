import numpy as np

from src.kalman import IMM, KalmanCT, KalmanCV, ct_matrisleri, cv_matrisleri, tpm_dt


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


# --- CT modeli testleri ---

def test_ct_omega_sifir_cv_gibi():
    """omega=0 olduğunda CT modeli CV modeli gibi davranmalı."""
    x_state = np.array([0.0, 0.0, 5.0, 3.0, 0.0])
    _, F_ct, _ = ct_matrisleri(1.0, 1.0, 0.3, x_state)
    F_cv, _ = cv_matrisleri(1.0, 1.0)
    # CT'nin 4x4 bloğu CV ile aynı olmalı
    assert np.allclose(F_ct[:4, :4], F_cv, atol=1e-10)


def test_ct_donus_izler():
    """CT modeli dönen bir hedefi izleyebilmeli."""
    rng = np.random.default_rng(42)
    kf = KalmanCT([0, 0], np.eye(2) * 25.0)
    omega = 0.05  # rad/s
    v = 20.0
    dt = 1.0
    x, y, yon = 0.0, 0.0, 0.0
    for k in range(1, 80):
        yon += omega * dt
        x += v * np.cos(yon) * dt
        y += v * np.sin(yon) * dt
        kf.tahmin(dt)
        kf.guncelle(np.array([x, y]) + rng.normal(0, 5.0, 2), np.eye(2) * 25.0)
    # omega kestirimi gerçeğe yakın olmalı
    assert abs(kf.x[4] - omega) < 0.02
    assert np.linalg.norm(kf.konum - [x, y]) < 20.0


# --- IMM testleri ---

def test_imm_sabit_hiz_cv_baskin():
    """Sabit hızda IMM'de CV modeli baskın olmalı."""
    rng = np.random.default_rng(42)
    imm = IMM([0, 0], np.eye(2) * 25.0)
    hiz = np.array([10.0, 5.0])
    for k in range(1, 60):
        imm.tahmin(1.0)
        imm.guncelle(hiz * k + rng.normal(0, 5.0, 2), np.eye(2) * 25.0)
    # CV modeli (indeks 0) baskın olmalı
    assert imm.model_olasiliklari[0] > 0.7
    # Konum doğru olmalı
    assert np.linalg.norm(imm.konum - hiz * 59) < 15.0


def test_imm_manevrali_hedef():
    """Manevrada IMM'de CT modeli aktifleşmeli."""
    rng = np.random.default_rng(42)
    imm = IMM([0, 0], np.eye(2) * 25.0)
    v = 15.0
    omega = 0.0
    dt = 0.2
    x, y, yon = 0.0, 0.0, 0.0
    ct_baskin_anlar = 0
    toplam = 0
    for k in range(1, 500):
        t = k * dt
        # 30-70 s arası manevra
        omega = 0.05 if 30 <= t < 70 else 0.0
        yon += omega * dt
        x += v * np.cos(yon) * dt
        y += v * np.sin(yon) * dt
        imm.tahmin(dt)
        imm.guncelle(np.array([x, y]) + rng.normal(0, 3.0, 2), np.eye(2) * 9.0)
        if 40 <= t < 65:
            toplam += 1
            if imm.model_olasiliklari[1] > 0.3:
                ct_baskin_anlar += 1
    # Manevra sırasında CT modeli sık sık aktifleşmeli
    assert ct_baskin_anlar / toplam > 0.5, (
        f"CT modeli manevra sırasında yeterince aktifleşmedi: {ct_baskin_anlar}/{toplam}")
    # Konum doğru olmalı
    assert np.linalg.norm(imm.konum - [x, y]) < 15.0


def test_imm_cv_uyumlu_arayuz():
    """IMM, KalmanCV ile aynı arayüzü sunmalı: x, P, konum, inovasyon."""
    imm = IMM([100, 200], np.eye(2) * 25.0)
    assert imm.x.shape == (4,)
    assert imm.P.shape == (4, 4)
    assert imm.konum.shape == (2,)
    y, S = imm.inovasyon(np.array([105.0, 205.0]), np.eye(2) * 10.0)
    assert y.shape == (2,)
    assert S.shape == (2, 2)


def test_imm_tahmin_sonrasi_konum_degisir():
    """Tahmin sonrası konum ileri taşınmalı."""
    imm = IMM([0, 0], np.eye(2) * 25.0)
    # Bir ölçümle hız kestirimi oluştur
    imm.tahmin(1.0)
    imm.guncelle(np.array([10.0, 0.0]), np.eye(2) * 10.0)
    konum1 = imm.konum.copy()
    imm.tahmin(1.0)
    konum2 = imm.konum.copy()
    # vx > 0 olduğu için x artmış olmalı
    assert konum2[0] > konum1[0]


# --- Geçiş matrisinin zamana ölçeklenmesi ---

def test_tpm_dt_bir_saniyede_ayni_kisa_surede_birime_yakin():
    tpm = np.array([[0.99, 0.01], [0.10, 0.90]])
    assert np.allclose(tpm_dt(tpm, 1.0), tpm)
    T = tpm_dt(tpm, 0.01)
    assert np.allclose(T.sum(axis=1), 1.0)
    assert np.allclose(T, np.eye(2), atol=2e-3)


def test_imm_olasiliklari_cok_sayida_kisa_tahminde_dagilmaz():
    """Tahmin çağrı sıklığı model olasılıklarını değiştirmemeli.

    Füzyon merkezi tahmini saniyede 10'dan fazla çağırır. Geçişler dt'ye
    ölçeklenmezse olasılıklar her çağrıda %50/%50'ye çekilir.
    """
    tek = IMM([0, 0], np.eye(2) * 25.0)
    cok = IMM([0, 0], np.eye(2) * 25.0)
    tek.tahmin(1.0)
    for _ in range(20):
        cok.tahmin(0.05)
    beklenen = tek.tpm.T @ np.array([0.9, 0.1])
    assert np.allclose(tek.model_olasiliklari, beklenen)
    assert np.allclose(cok.model_olasiliklari, beklenen, atol=0.01)
