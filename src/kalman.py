"""Sabit hız (constant velocity) modelli Kalman filtresi.

Durum vektörü: [x, y, vx, vy]. Ölçüm sadece konumdur: [x, y].
"""

import numpy as np

H = np.array([[1.0, 0.0, 0.0, 0.0],
              [0.0, 1.0, 0.0, 0.0]])


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
        y = z - H @ self.x
        S = H @ self.P @ H.T + R
        return y, S

    def guncelle(self, z, R):
        """Ölçümle günceller; normalize inovasyon karesini (NIS) döndürür."""
        y, S = self.inovasyon(z, R)
        S_inv = np.linalg.inv(S)
        K = self.P @ H.T @ S_inv
        self.x = self.x + K @ y
        # Joseph formu: sayısal olarak daha kararlı
        I_KH = np.eye(4) - K @ H
        self.P = I_KH @ self.P @ I_KH.T + K @ R @ K.T
        return float(y @ S_inv @ y)

    @property
    def konum(self):
        return self.x[:2].copy()
