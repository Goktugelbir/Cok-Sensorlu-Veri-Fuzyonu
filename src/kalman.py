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

# Geriye dönük uyumluluk: eski koddan import edilen H
H = H_CV


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

def ct_matrisleri(dt, ivme_sigma, omega_sigma, x_state):
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
    Q[4, 4] = omega_sigma ** 2 * dt
    return x_tahmin, F, Q


class KalmanCT:
    """Koordineli dönüş modeli — genişletilmiş Kalman filtresi (EKF).

    Durum: [x, y, vx, vy, omega]. Durum tahmini doğrusal olmayan fonksiyonla,
    kovaryans propagasyonu Jacobian ile yapılır. Bu sayede omega, konum
    ölçümlerinden dolaylı olarak kestirilir.
    """

    def __init__(self, konum, R, hiz_sigma=30.0, ivme_sigma=1.0, omega_sigma=0.3):
        self.x = np.array([konum[0], konum[1], 0.0, 0.0, 0.0])
        self.P = np.zeros((5, 5))
        self.P[:2, :2] = R
        self.P[2:4, 2:4] = np.eye(2) * hiz_sigma ** 2
        self.P[4, 4] = omega_sigma ** 2
        self.ivme_sigma = ivme_sigma
        self.omega_sigma = omega_sigma

    def tahmin(self, dt):
        """Durumu dt kadar ileri taşır (EKF: doğrusal olmayan tahmin + Jacobian)."""
        if dt <= 0:
            return
        x_tahmin, F, Q = ct_matrisleri(dt, self.ivme_sigma, self.omega_sigma, self.x)
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

# Varsayılan Markov geçiş matrisi: modeller arası geçiş olasılıkları
# TPM[i, j] = P(model j'ye geçiş | şu an model i)
# Manevralara zamanında tepki vermek için geçiş olasılığı dengelendi
VARSAYILAN_TPM = np.array([
    [0.90, 0.10],   # CV -> CT geçiş olasılığı (manevra tespiti için yeterli duyarlılık)
    [0.10, 0.90],   # CT -> CV geçiş olasılığı
])

# Başlangıç model olasılıkları (CV'ye öncelik)
VARSAYILAN_MODEL_OLASILIK = np.array([0.9, 0.1])


def _cv_durum_ct(x_cv):
    """CV durumunu CT durumuna genişletir: omega=0 eklenir."""
    return np.array([x_cv[0], x_cv[1], x_cv[2], x_cv[3], 0.0])


def _ct_durum_cv(x_ct):
    """CT durumundan CV durumuna daraltır: omega atılır."""
    return x_ct[:4].copy()


def _cv_P_ct(P_cv):
    """CV kovaryansını CT boyutuna genişletir."""
    P = np.zeros((5, 5))
    P[:4, :4] = P_cv
    P[4, 4] = 0.3 ** 2  # omega için varsayılan belirsizlik
    return P


def _ct_P_cv(P_ct):
    """CT kovaryansından CV boyutuna daraltır."""
    return P_ct[:4, :4].copy()


class IMM:
    """Interacting Multiple Model filtresi: CV + CT.

    Dışarıdan bakıldığında KalmanCV ile aynı arayüzü sunar (tahmin,
    inovasyon, guncelle, konum). Füzyon merkezi bu sınıfı KalmanCV yerine
    doğrudan kullanabilir.
    """

    def __init__(self, konum, R, hiz_sigma=30.0, ivme_sigma=1.0, omega_sigma=0.3,
                 tpm=None, baslangic_olasilik=None):
        self.filtreler = [
            KalmanCV(konum, R, hiz_sigma, ivme_sigma),
            KalmanCT(konum, R, hiz_sigma, ivme_sigma, omega_sigma),
        ]
        self.tpm = tpm if tpm is not None else VARSAYILAN_TPM.copy()
        self.mu = (baslangic_olasilik if baslangic_olasilik is not None
                   else VARSAYILAN_MODEL_OLASILIK.copy())
        self.ivme_sigma = ivme_sigma
        self._n_model = 2
        self._c_bar = self.tpm.T @ self.mu
        self._birlestir()  # _x_comb ve _P_comb'u başlat

    # ---------- model durum/kovaryansi okuma/yazma yardımcıları ----------

    def _durum_al(self, j):
        """Model j'nin durumunu ortak (5 boyutlu) formatta döndürür."""
        if j == 0:
            return _cv_durum_ct(self.filtreler[0].x)
        return self.filtreler[1].x.copy()

    def _durum_koy(self, j, x):
        """Ortak formattaki durumu model j'ye yazar."""
        if j == 0:
            self.filtreler[0].x = _ct_durum_cv(x)
        else:
            self.filtreler[1].x = x.copy()

    def _P_al(self, j):
        """Model j'nin kovaryansını ortak (5x5) formatta döndürür."""
        if j == 0:
            return _cv_P_ct(self.filtreler[0].P)
        return self.filtreler[1].P.copy()

    def _P_koy(self, j, P):
        """Ortak formattaki kovaryansı model j'ye yazar."""
        if j == 0:
            self.filtreler[0].P = _ct_P_cv(P)
        else:
            self.filtreler[1].P = P.copy()

    # ---------- IMM adımları ----------

    def _etkilesim(self):
        """Etkileşim adımı: karışım olasılıkları ve karıştırılmış durumlar.

        Her model j için, modellerin ağırlıklı karışımından yeni bir başlangıç
        durumu ve kovaryansı hesaplanır.
        """
        n = self._n_model
        c_bar = self.tpm.T @ self.mu  # her model j için normalleştirme
        c_bar = np.maximum(c_bar, 1e-30)

        # Karışım ağırlıkları: mu_{i|j} = TPM[i,j] * mu[i] / c_bar[j]
        mu_ij = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                mu_ij[i, j] = self.tpm[i, j] * self.mu[i] / c_bar[j]

        # Her model j için karıştırılmış durum ve kovaryans
        durumlar = [self._durum_al(i) for i in range(n)]
        kovaryanlar = [self._P_al(i) for i in range(n)]
        dim = 5  # ortak boyut

        for j in range(n):
            x_mix = np.zeros(dim)
            for i in range(n):
                x_mix += mu_ij[i, j] * durumlar[i]

            P_mix = np.zeros((dim, dim))
            for i in range(n):
                d = durumlar[i] - x_mix
                P_mix += mu_ij[i, j] * (kovaryanlar[i] + np.outer(d, d))

            self._durum_koy(j, x_mix)
            self._P_koy(j, P_mix)

        self._c_bar = c_bar

    def _model_olasilik_guncelle(self, z, R):
        """Ölçüm olabilirliklerinden model olasılıklarını günceller."""
        n = self._n_model
        L = np.zeros(n)
        for j in range(n):
            y, S = self.filtreler[j].inovasyon(z, R)
            # Gauss olabilirlik (log → exp güvenli)
            sign, logdet = np.linalg.slogdet(S)
            if sign <= 0:
                L[j] = 1e-30
                continue
            S_inv = np.linalg.inv(S)
            mahal = float(y @ S_inv @ y)
            L[j] = np.exp(-0.5 * (mahal + logdet + 2 * np.log(2 * np.pi)))
            L[j] = max(L[j], 1e-30)

        mu_yeni = self._c_bar * L
        toplam = mu_yeni.sum()
        if toplam > 0:
            mu_yeni /= toplam
        else:
            mu_yeni = np.ones(n) / n
        self.mu = mu_yeni

    def _birlestir(self):
        """Birleştirme adımı: model çıkışlarının ağırlıklı ortalaması."""
        n = self._n_model
        dim = 5

        durumlar = [self._durum_al(j) for j in range(n)]
        kovaryanlar = [self._P_al(j) for j in range(n)]

        x_comb = np.zeros(dim)
        for j in range(n):
            x_comb += self.mu[j] * durumlar[j]

        P_comb = np.zeros((dim, dim))
        for j in range(n):
            d = durumlar[j] - x_comb
            P_comb += self.mu[j] * (kovaryanlar[j] + np.outer(d, d))

        # Birleşik sonucu sakla (dışarıya sunmak için)
        self._x_comb = x_comb
        self._P_comb = P_comb

    # ---------- Dışa açık arayüz (KalmanCV uyumlu) ----------

    def tahmin(self, dt):
        """Durumu dt kadar ileri taşır (etkileşim + model tahminleri)."""
        if dt <= 0:
            return
        self._etkilesim()
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

        Normalize inovasyon karesini (NIS) döndürür (birleşik durumdan).
        """
        # Birleşik inovasyon (NIS hesabı için)
        y, S = self.inovasyon(z, R)
        S_inv = np.linalg.inv(S)
        nis = float(y @ S_inv @ y)

        # Model olasılıklarını güncelle (ölçüm olabilirliklerine göre)
        self._model_olasilik_guncelle(z, R)

        # Her modeli kendi filtresiyle güncelle
        for f in self.filtreler:
            f.guncelle(z, R)

        # Birleştir
        self._birlestir()

        return nis

    @property
    def konum(self):
        return self._x_comb[:2].copy()

    @property
    def x(self):
        """KalmanCV uyumlu durum vektörü [x, y, vx, vy] (4 boyutlu)."""
        return self._x_comb[:4].copy()

    @x.setter
    def x(self, deger):
        """Dışarıdan durum ataması (uyumluluk için)."""
        # Güncelle: hem birleşik hem bireysel filtrelere yansıt
        x5 = np.zeros(5)
        x5[:4] = deger
        if hasattr(self, '_x_comb'):
            x5[4] = self._x_comb[4]
        self._x_comb = x5
        self._durum_koy(0, x5)
        self._durum_koy(1, x5)

    @property
    def P(self):
        """KalmanCV uyumlu kovaryans matrisi (4x4)."""
        return self._P_comb[:4, :4].copy()

    @P.setter
    def P(self, deger):
        """Dışarıdan kovaryans ataması (uyumluluk için)."""
        P5 = np.zeros((5, 5))
        P5[:4, :4] = deger
        if hasattr(self, '_P_comb'):
            P5[4, 4] = self._P_comb[4, 4]
        else:
            P5[4, 4] = 0.3 ** 2
        self._P_comb = P5
        self._P_koy(0, P5)
        self._P_koy(1, P5)

    @property
    def model_olasiliklari(self):
        """Modellerin mevcut olasılıkları: [P(CV), P(CT)]."""
        return self.mu.copy()
