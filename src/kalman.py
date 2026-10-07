"""Kalman filtreleri: sabit hız (CV), koordineli dönüş (CT) ve IMM.

CV durum vektörü: [x, y, vx, vy].
CT durum vektörü: [x, y, vx, vy, omega] (omega: dönüş hızı, rad/s).
Ölçüm sadece konumdur: [x, y].

IMM (Interacting Multiple Model), CV ve CT modellerini etkileşimli olarak
çalıştırarak hem düz hem manevralı hedefleri izleyebilir. Her adımda
modellerin olasılıkları güncellenir; manevrada CT modeli baskınlaşır,
düz rotada CV modeli baskınlaşır.
"""

import numpy as np

H_CV = np.array([[1.0, 0.0, 0.0, 0.0],
                 [0.0, 1.0, 0.0, 0.0]])

H_CT = np.array([[1.0, 0.0, 0.0, 0.0, 0.0],
                 [0.0, 1.0, 0.0, 0.0, 0.0]])


# ---------------------------------------------------------------------------
# Sabit hız (CV) modeli
# ---------------------------------------------------------------------------

def cv_matrisleri(dt, ivme_sigma):
    """dt süresi için geçiş matrisi F ve süreç gürültüsü Q (beyaz ivme modeli)."""
    F = np.eye(4)
    F[0, 2] = F[1, 3] = dt
    q = ivme_sigma ** 2
    dt2, dt3, dt4 = dt ** 2, dt ** 3, dt ** 4
    Q = q * np.array([[dt4 / 4, 0, dt3 / 2, 0],
                      [0, dt4 / 4, 0, dt3 / 2],
                      [dt3 / 2, 0, dt2, 0],
                      [0, dt3 / 2, 0, dt2]])
    return F, Q


class KalmanCV:
    def __init__(self, konum, R, hiz_sigma=30.0, ivme_sigma=1.0):
        self.x = np.array([konum[0], konum[1], 0.0, 0.0])
        self.P = np.zeros((4, 4))
        self.P[:2, :2] = R
        self.P[2:, 2:] = np.eye(2) * hiz_sigma ** 2
        self.ivme_sigma = ivme_sigma

    def tahmin(self, dt):
        """Durumu dt kadar ileri taşır."""
        if dt <= 0:
            return
        F, Q = cv_matrisleri(dt, self.ivme_sigma)
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q

    def inovasyon(self, z, R):
        """Ölçüm artığı (y) ve kovaryansı (S)."""
        y = z - H_CV @ self.x
        S = H_CV @ self.P @ H_CV.T + R
        return y, S

    def guncelle(self, z, R):
        """Ölçümle günceller; normalize inovasyon karesini (NIS) döndürür."""
        y, S = self.inovasyon(z, R)
        S_inv = np.linalg.inv(S)
        K = self.P @ H_CV.T @ S_inv
        self.x = self.x + K @ y
        # Joseph formu: sayısal olarak daha kararlı
        I_KH = np.eye(4) - K @ H_CV
        self.P = I_KH @ self.P @ I_KH.T + K @ R @ K.T
        return float(y @ S_inv @ y)

    @property
    def konum(self):
        return self.x[:2].copy()


# ---------------------------------------------------------------------------
# Koordineli dönüş (CT) modeli — EKF (Extended Kalman Filter)
# ---------------------------------------------------------------------------

def ct_matrisleri(dt, ivme_sigma, omega_gurultu, x_state):
    """Koordineli dönüş modeli: doğrusal olmayan durum tahmini ve Jacobian.

    Durum: [x, y, vx, vy, omega]. CT modeli omega'da doğrusal olmadığından,
    kovaryans propagasyonu için tam Jacobian (∂f/∂x) hesaplanır; durum tahmini
    ise doğrudan doğrusal olmayan fonksiyonla yapılır.

    Dönüş: (x_tahmin, F_jacobian, Q)
    """
    vx, vy, w = x_state[2], x_state[3], x_state[4]

    if abs(w) < 1e-6:
        # omega ≈ 0: sabit hız limiti (Taylor açılımı)
        A = dt              # sin(ωdt)/ω → dt
        B = 0.0             # (1-cos(ωdt))/ω → 0
        sw_dt = 0.0         # sin(ωdt) → 0
        cw_dt = 1.0         # cos(ωdt) → 1
        dA_dw = 0.0         # ∂A/∂ω → 0
        dB_dw = dt ** 2 / 2  # ∂B/∂ω → dt²/2
    else:
        sw_dt = np.sin(w * dt)
        cw_dt = np.cos(w * dt)
        A = sw_dt / w
        B = (1 - cw_dt) / w
        dA_dw = (dt * w * cw_dt - sw_dt) / w ** 2
        dB_dw = (dt * w * sw_dt - 1 + cw_dt) / w ** 2

    # Doğrusal olmayan durum tahmini
    x_tahmin = np.array([
        x_state[0] + A * vx - B * vy,
        x_state[1] + B * vx + A * vy,
        cw_dt * vx - sw_dt * vy,
        sw_dt * vx + cw_dt * vy,
        w,
    ])

    # Jacobian (EKF): ∂f/∂x — 5. sütun omega'ya göre türevler içerir
    F = np.array([
        [1, 0, A,     -B,     dA_dw * vx - dB_dw * vy],
        [0, 1, B,      A,     dB_dw * vx + dA_dw * vy],
        [0, 0, cw_dt, -sw_dt, -dt * sw_dt * vx - dt * cw_dt * vy],
        [0, 0, sw_dt,  cw_dt,  dt * cw_dt * vx - dt * sw_dt * vy],
        [0, 0, 0,      0,      1],
    ])

    # Süreç gürültüsü: ivme bileşeni (konum ve hız) + omega bileşeni
    q = ivme_sigma ** 2
    dt2, dt3, dt4 = dt ** 2, dt ** 3, dt ** 4
    Q = np.zeros((5, 5))
    Q[:4, :4] = q * np.array([
        [dt4 / 4, 0, dt3 / 2, 0],
        [0, dt4 / 4, 0, dt3 / 2],
        [dt3 / 2, 0, dt2, 0],
        [0, dt3 / 2, 0, dt2],
    ])
    Q[4, 4] = omega_gurultu ** 2 * dt
    return x_tahmin, F, Q


class KalmanCT:
    """Koordineli dönüş modeli — genişletilmiş Kalman filtresi (EKF).

    Durum: [x, y, vx, vy, omega]. Durum tahmini doğrusal olmayan fonksiyonla,
    kovaryans propagasyonu Jacobian ile yapılır. Bu sayede omega, konum
    ölçümlerinden dolaylı olarak kestirilir.
    """

    def __init__(self, konum, R, hiz_sigma=30.0, ivme_sigma=1.0, omega_sigma=0.3, omega_gurultu=None):
        self.x = np.array([konum[0], konum[1], 0.0, 0.0, 0.0])
        self.P = np.zeros((5, 5))
        self.P[:2, :2] = R
        self.P[2:4, 2:4] = np.eye(2) * hiz_sigma ** 2
        self.P[4, 4] = omega_sigma ** 2  # başlangıç dönüş hızı belirsizliği
        self.ivme_sigma = ivme_sigma
        # Dönüş hızının süreç gürültüsü (rad/s/√s); verilmezse başlangıç belirsizliğiyle aynı alınır
        self.omega_gurultu = omega_sigma if omega_gurultu is None else omega_gurultu

    def tahmin(self, dt):
        """Durumu dt kadar ileri taşır (EKF: doğrusal olmayan tahmin + Jacobian)."""
        if dt <= 0:
            return
        x_tahmin, F, Q = ct_matrisleri(dt, self.ivme_sigma, self.omega_gurultu, self.x)
        self.x = x_tahmin
        self.P = F @ self.P @ F.T + Q

    def inovasyon(self, z, R):
        """Ölçüm artığı (y) ve kovaryansı (S)."""
        y = z - H_CT @ self.x
        S = H_CT @ self.P @ H_CT.T + R
        return y, S

    def guncelle(self, z, R):
        """Ölçümle günceller; normalize inovasyon karesini (NIS) döndürür."""
        y, S = self.inovasyon(z, R)
        S_inv = np.linalg.inv(S)
        K = self.P @ H_CT.T @ S_inv
        self.x = self.x + K @ y
        I_KH = np.eye(5) - K @ H_CT
        self.P = I_KH @ self.P @ I_KH.T + K @ R @ K.T
        return float(y @ S_inv @ y)

    @property
    def konum(self):
        return self.x[:2].copy()


# ---------------------------------------------------------------------------
# IMM (Interacting Multiple Model) filtresi
# ---------------------------------------------------------------------------

# Markov geçiş matrisi, 1 saniyelik aralık için tanımlıdır:
# TPM[i, j] = P(1 s sonra model j | şu an model i)
# Füzyon merkezi tahmini düzensiz aralıklarla çağırır (her sensör taramasında ve
# her 0.2 s'lik adımda, saniyede 10'dan fazla kez). Matris adım başına uygulansaydı
# model olasılıkları her çağrıda durağan dağılıma (%50/%50) çekilirdi; bu yüzden
# geçişler sürekli zamanlı Markov zinciri gibi dt'ye göre ölçeklenir (tpm_dt).
VARSAYILAN_TPM = np.array([
    [0.99, 0.01],   # CV'de kalma / CT'ye geçiş (1 s içinde)
    [0.10, 0.90],   # CV'ye dönüş / CT'de kalma (1 s içinde)
])

# Başlangıç model olasılıkları (CV'ye öncelik)
VARSAYILAN_MODEL_OLASILIK = np.array([0.9, 0.1])

# Değerler seed 42-47 üzerinde CV ile karşılaştırılarak seçildi (README: Ayar parametreleri)
OMEGA_SIGMA = 0.05     # yeni iz ve CV'den gelen karışım için dönüş hızı belirsizliği (rad/s)
OMEGA_GURULTU = 0.01   # CT modelinde dönüş hızının süreç gürültüsü (rad/s/√s)
CV_IVME_SIGMA = 1.0    # IMM içindeki CV modelinin beyaz ivme gürültüsü (m/s²)
CT_IVME_SIGMA = 0.5    # IMM içindeki CT modelinin beyaz ivme gürültüsü (m/s²)


def tpm_dt(tpm_1s, dt):
    """1 saniyelik geçiş matrisini dt süresine ölçekler.

    Her modelde kalma olasılığı p_ii(dt) = p_ii^dt olur; çıkış olasılığı diğer
    modellere 1 saniyelik matristeki oranlarla dağıtılır. dt = 1'de matris
    aynen geri gelir, dt -> 0'da birim matrise yaklaşır.
    """
    if tpm_1s.shape == (2, 2):
        # İki model: çıkış olasılığı doğrudan diğer modele gider (hızlı yol)
        a, b = tpm_1s[0, 0] ** dt, tpm_1s[1, 1] ** dt
        return np.array([[a, 1.0 - a], [1.0 - b, b]])
    kalma = np.diag(tpm_1s)
    kalma_dt = kalma ** dt
    cikis_1s = 1.0 - kalma
    oran = np.divide(1.0 - kalma_dt, cikis_1s, out=np.zeros_like(kalma), where=cikis_1s > 0)
    T = tpm_1s * oran[:, None]
    T[np.diag_indices_from(T)] = kalma_dt
    return T


class IMM:
    """Interacting Multiple Model filtresi: CV + CT.

    Dışarıdan bakıldığında KalmanCV ile aynı arayüzü sunar (tahmin,
    inovasyon, guncelle, konum). Füzyon merkezi bu sınıfı KalmanCV yerine
    doğrudan kullanabilir.

    Her tahmin adımında: (1) model geçişleri dt'ye ölçeklenmiş TPM ile
    uygulanır ve modeller karıştırılır, (2) her model kendi dinamiğiyle ileri
    taşınır. Her ölçümde model olasılıkları Gauss olabilirlikleriyle güncellenir.
    """

    def __init__(self, konum, R, hiz_sigma=30.0, cv_ivme_sigma=CV_IVME_SIGMA,
                 ct_ivme_sigma=CT_IVME_SIGMA, omega_sigma=OMEGA_SIGMA, omega_gurultu=OMEGA_GURULTU,
                 tpm=None, baslangic_olasilik=None):
        self.filtreler = [
            KalmanCV(konum, R, hiz_sigma, cv_ivme_sigma),
            KalmanCT(konum, R, hiz_sigma, ct_ivme_sigma, omega_sigma, omega_gurultu),
        ]
        self.tpm = tpm if tpm is not None else VARSAYILAN_TPM.copy()
        self.mu = (np.array(baslangic_olasilik, float) if baslangic_olasilik is not None
                   else VARSAYILAN_MODEL_OLASILIK.copy())
        self.omega_sigma = omega_sigma
        self._birlestir()  # _x_comb ve _P_comb'u başlat

    # ---------- model durumları ortak (5 boyutlu) biçimde ----------

    def _durumlar(self):
        """Modellerin durum ve kovaryansları, ortak 5 boyutlu biçimde.

        CV modeli, omega = 0 olan bir CT modeli gibi genişletilir. Omega
        belirsizliği olarak omega_sigma kullanılır; böylece karışım CT modelinin
        dönüş hızı kestirimini sıfıra kilitlemez.
        """
        cv, ct = self.filtreler
        x_cv = np.zeros(5)
        x_cv[:4] = cv.x
        P_cv = np.zeros((5, 5))
        P_cv[:4, :4] = cv.P
        P_cv[4, 4] = self.omega_sigma ** 2
        return x_cv, P_cv, ct.x, ct.P

    @staticmethod
    def _karisim(w0, x0, P0, x1, P1):
        """İki bileşenli Gauss karışımının ortalaması ve kovaryansı (moment eşleme).

        w0 + w1 = 1 olduğundan yayılma terimi tek bir dış çarpıma iner:
        Σ w_i (x_i - x)(x_i - x)ᵀ = w0 · w1 · (x0 - x1)(x0 - x1)ᵀ.
        """
        w1 = 1.0 - w0
        d = x0 - x1
        return w0 * x0 + w1 * x1, w0 * P0 + w1 * P1 + (w0 * w1) * np.outer(d, d)

    # ---------- IMM adımları ----------

    def _etkilesim(self, dt):
        """Etkileşim adımı: model geçişleri ve karıştırılmış başlangıç durumları."""
        T = tpm_dt(self.tpm, dt)
        c_bar = np.maximum(T.T @ self.mu, 1e-30)      # öngörülen model olasılıkları
        mu_ij = T * self.mu[:, None] / c_bar[None, :]  # mu_{i|j}; sütunların toplamı 1
        x_cv, P_cv, x_ct, P_ct = self._durumlar()
        cv, ct = self.filtreler
        x, P = self._karisim(mu_ij[0, 0], x_cv, P_cv, x_ct, P_ct)
        cv.x, cv.P = x[:4], P[:4, :4]
        ct.x, ct.P = self._karisim(mu_ij[0, 1], x_cv, P_cv, x_ct, P_ct)
        self.mu = c_bar / c_bar.sum()

    def _model_olasilik_guncelle(self, z, R):
        """Ölçüm olabilirliklerinden model olasılıklarını günceller (log uzayında)."""
        log_L = np.zeros(len(self.filtreler))
        for j, f in enumerate(self.filtreler):
            y, S = f.inovasyon(z, R)
            _, logdet = np.linalg.slogdet(S)
            log_L[j] = -0.5 * (float(y @ np.linalg.solve(S, y)) + logdet)
        log_mu = np.log(np.maximum(self.mu, 1e-300)) + log_L
        mu = np.exp(log_mu - log_mu.max())
        self.mu = mu / mu.sum()

    def _birlestir(self):
        """Birleştirme adımı: model çıkışlarının olasılık ağırlıklı karışımı."""
        self._x_comb, self._P_comb = self._karisim(self.mu[0], *self._durumlar())

    # ---------- Dışa açık arayüz (KalmanCV uyumlu) ----------

    def tahmin(self, dt):
        """Durumu dt kadar ileri taşır (etkileşim + model tahminleri)."""
        if dt <= 0:
            return
        self._etkilesim(dt)
        for f in self.filtreler:
            f.tahmin(dt)
        self._birlestir()

    def inovasyon(self, z, R):
        """Birleşik durumdan ölçüm artığı ve kovaryansı."""
        y = z - self._x_comb[:2]
        S = self._P_comb[:2, :2] + R
        return y, S

    def guncelle(self, z, R):
        """Her modeli ayrı ayrı günceller, olasılıkları yeniler, birleştirir.

        Normalize inovasyon karesini (NIS) birleşik durumdan döndürür.
        """
        y, S = self.inovasyon(z, R)
        nis = float(y @ np.linalg.solve(S, y))
        self._model_olasilik_guncelle(z, R)
        for f in self.filtreler:
            f.guncelle(z, R)
        self._birlestir()
        return nis

    @property
    def konum(self):
        return self._x_comb[:2].copy()

    @property
    def x(self):
        """KalmanCV uyumlu durum vektörü [x, y, vx, vy] (4 boyutlu)."""
        return self._x_comb[:4].copy()

    @property
    def P(self):
        """KalmanCV uyumlu kovaryans matrisi (4x4)."""
        return self._P_comb[:4, :4].copy()

    @property
    def omega(self):
        """Birleşik dönüş hızı kestirimi (rad/s)."""
        return float(self._x_comb[4])

    @property
    def model_olasiliklari(self):
        """Modellerin mevcut olasılıkları: [P(CV), P(CT)]."""
        return self.mu.copy()
