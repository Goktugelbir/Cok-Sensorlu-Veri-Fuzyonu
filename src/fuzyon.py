"""Çok sensörlü füzyon merkezi.

Adımlar:
1. Zaman senkronizasyonu: Ölçümler farklı gecikmelerle gelir. Füzyon merkezi,
   en büyük gecikmeden uzun sabit bir pencere (FUZYON_GECIKMESI) kadar geriden
   çalışır. Böylece bir zaman aralığına ait bütün ölçümler gelmiş olur; bunlar
   alınış zamanına göre sıralanır ve her taramadan önce izler tam o ana
   tahmin edilir. Sonunda tüm izler ortak zaman adımına hizalanır.
2. Bias düzeltme: Konum bildirimindeki sabit sapma, referans sensörlerle
   (radar/kamera) desteklenen izlere göre hesaplanan artıkların ortalamasıyla
   kestirilir ve ölçümlerden çıkarılır.
3. İlişkilendirme: Mahalanobis kapılama + Macar algoritması.
4. Kalman güncellemesi: sensör güvenine göre ölçeklenmiş R ile.
5. İz yönetimi: yeni iz başlatma, onaylama, silme ve çift izleri birleştirme.
"""

from collections import defaultdict

import numpy as np

from .iliskilendirme import iliskilendir, maliyet_matrisi
from .kalman import KalmanCV
from .saha import SURE
from .sensorler import FUZYON_GECIKMESI

ADIM = 0.2                  # füzyon zaman adımı (s)
ONAY_VURUS = 3              # aday izin onaylanması için gereken güncelleme sayısı
ADAY_OMUR = 2.5             # aday iz bu süre güncellenmezse silinir (s)
ONAYLI_OMUR = 6.0           # onaylı iz bu süre güncellenmezse silinir (s)
BIAS_ORNEK = 60             # bias kestirimi için gereken örnek sayısı
OLGUN_IZ_VURUS = 10         # bias örneği alınacak izin en az vuruş sayısı
KALIBRASYON_SIGMA = 60.0    # bias öğrenilene kadar konum bildirimi için kapı belirsizliği (m)
BIAS_KALAN_SIGMA = 3.0      # bias kestirimindeki kalan belirsizlik (m)
NIS_TOLERANS = 4.0          # sensör güveni bu NIS ortalamasının üstünde düşmeye başlar
GENIS_KAPI = 100.0         # yeni iz bastırma ve güven ölçümü için geniş Mahalanobis eşiği
# Güven skorunda her sensörün temel katkısı
SENSOR_KATKI = {"radar": 0.6, "kamera": 0.7, "konum": 0.8}
REFERANS_SENSORLER = ("radar", "kamera")


class Iz:
    def __init__(self, iz_id, z, R, t, sensor):
        self.id = iz_id
        self.kf = KalmanCV(z, R)
        self.onayli = False
        self.vurus = 1
        self.son_guncelleme = t
        self.sensor_son = {sensor: t}  # sensör -> son katkı zamanı
        self.dost_etiket = None


class FuzyonMerkezi:
    def __init__(self, sensorler, guven_agirliklandirma=True):
        self.sensorler = list(sensorler)
        # Kapalıysa tüm sensörlerin güveni 1'de sabit kalır (ablasyon deneyi için)
        self.guven_agirliklandirma = guven_agirliklandirma
        self.zaman = 0.0
        self.izler = []
        self.sonraki_id = 1
        self.tampon = []
        self.nis_ema = {s: 2.0 for s in self.sensorler}
        self.guven = {s: 1.0 for s in self.sensorler}
        self.bias_artiklar = defaultdict(list)
        self.bias = {s: np.zeros(2) for s in self.sensorler}
        self.referans_var = any(s in self.sensorler for s in REFERANS_SENSORLER)

    # ------------------------------------------------------------------ zaman
    def olcum_al(self, olcumler):
        self.tampon.extend(o for o in olcumler if o.sensor in self.sensorler)

    def ilerle(self, t_simdi):
        """Füzyon zamanını t_simdi - FUZYON_GECIKMESI anına getirir."""
        hedef_zaman = t_simdi - FUZYON_GECIKMESI
        hazir = [o for o in self.tampon if o.t_olcum <= hedef_zaman]
        self.tampon = [o for o in self.tampon if o.t_olcum > hedef_zaman]

        # Aynı sensörün aynı andaki ölçümleri bir "tarama" oluşturur
        taramalar = defaultdict(list)
        for o in hazir:
            taramalar[(o.t_olcum, o.sensor)].append(o)
        for (t, sensor) in sorted(taramalar):
            if t < self.zaman:
                continue  # pencereyi aşacak kadar geç gelen ölçüm: atılır
            self._tahmin(t)
            self._tarama_isle(sensor, t, taramalar[(t, sensor)])

        self._tahmin(hedef_zaman)
        self._iz_yonetimi()

    def _tahmin(self, t):
        dt = t - self.zaman
        for iz in self.izler:
            iz.kf.tahmin(dt)
        self.zaman = max(self.zaman, t)

    # ------------------------------------------------------------- ölçüm işle
    def _bias_hazir(self, sensor):
        return len(self.bias_artiklar[sensor]) >= BIAS_ORNEK

    def _temel_R(self, o):
        """Bias düzeltmesi sonrası, güven ölçeklemesinden önceki R."""
        if o.sensor != "konum" or not self.referans_var:
            return o.R
        if not self._bias_hazir("konum"):
            return np.eye(2) * KALIBRASYON_SIGMA ** 2
        return o.R + np.eye(2) * BIAS_KALAN_SIGMA ** 2

    def _tarama_isle(self, sensor, t, olcumler):
        Z = [o.z - self.bias[sensor] for o in olcumler]
        R_temel = [self._temel_R(o) for o in olcumler]
        R_etkin = [R / self.guven[sensor] for R in R_temel]

        self._guven_guncelle(sensor, Z, R_temel)

        kf_listesi = [iz.kf for iz in self.izler]
        M = maliyet_matrisi(kf_listesi, Z, R_etkin)
        # Konum bildirimi kimlik taşır: başka dost birliğe bağlanmış ize atanamaz
        for j, o in enumerate(olcumler):
            if o.etiket is None:
                continue
            for i, iz in enumerate(self.izler):
                if iz.dost_etiket is not None and iz.dost_etiket != o.etiket:
                    M[i, j] = 1e9
        eslesmeler, _, bos_olcumler = iliskilendir(M)

        kalibrasyonda = sensor == "konum" and self.referans_var and not self._bias_hazir(sensor)
        for i, j in eslesmeler:
            iz, o = self.izler[i], olcumler[j]
            if o.etiket is not None:
                iz.dost_etiket = o.etiket
            if kalibrasyonda:
                # Bias öğrenilene kadar ölçüm izi güncellemez; sadece bias kestirimine
                # ve kimlik etiketine katkı verir (izi sapmalı konuma çekmemek için)
                self._bias_ogren(iz, o, t)
                if iz.onayli:
                    continue
            iz.kf.guncelle(Z[j], R_etkin[j])
            # Vuruş, sensör güveniyle ağırlıklandırılır: güveni düşük sensörün
            # (ör. karıştırılan radar) tek başına yeni iz onaylatması zorlaşır
            iz.vurus += self.guven[sensor]
            iz.son_guncelleme = t
            iz.sensor_son[sensor] = t
            if iz.vurus >= ONAY_VURUS:
                iz.onayli = True

        # Atanmamış ölçümler: mevcut onaylı bir izin çok yakınında değilse yeni iz
        for j in bos_olcumler:
            if self._onayli_ize_yakin(Z[j], R_etkin[j]):
                continue
            yeni = Iz(self.sonraki_id, Z[j], R_etkin[j], t, sensor)
            yeni.dost_etiket = olcumler[j].etiket
            self.izler.append(yeni)
            self.sonraki_id += 1

    def _onayli_ize_yakin(self, z, R):
        for iz in self.izler:
            if iz.onayli:
                y, S = iz.kf.inovasyon(z, R)
                if y @ np.linalg.solve(S, y) < GENIS_KAPI:
                    return True
        return False

    def _guven_guncelle(self, sensor, Z, R_listesi):
        """Sensör güveni: onaylı izlere göre normalize inovasyon karesi (NIS) tutarlılığı.

        Tutarlı bir sensörde NIS ortalaması ~2'dir (2 boyut). Ortalama belirgin
        biçimde yükselirse sensör beyan ettiğinden daha gürültülüdür; güveni
        düşürülür ve ölçümlerinin ağırlığı azalır. Çelişkili sensörler bu şekilde
        dengelenir. NIS_TOLERANS'a kadar olan sapmalar (ör. hedef manevrasından
        kaynaklanan model uyumsuzluğu) sensöre fatura edilmez.
        """
        onayli = [iz for iz in self.izler if iz.onayli]
        if not onayli or not self.guven_agirliklandirma:
            return
        for z, R in zip(Z, R_listesi):
            nis_min = np.inf
            for iz in onayli:
                y, S = iz.kf.inovasyon(z, R)
                nis_min = min(nis_min, float(y @ np.linalg.solve(S, y)))
            if nis_min < GENIS_KAPI:
                self.nis_ema[sensor] = 0.95 * self.nis_ema[sensor] + 0.05 * min(nis_min, 50.0)
        self.guven[sensor] = float(np.clip(NIS_TOLERANS / self.nis_ema[sensor], 0.05, 1.0))

    def _bias_ogren(self, iz, o, t):
        """Konum bildirimi artıklarını, referans sensörle desteklenen izlerde biriktirir."""
        destekli = any(t - iz.sensor_son.get(s, -np.inf) < 3.0 for s in REFERANS_SENSORLER)
        # Yeni başlatılan izin hız kestirimi henüz oturmamıştır (hedefin gerisinde kalır);
        # bu yüzden sadece olgun izlerden örnek alınır
        if not (iz.onayli and destekli and iz.vurus >= OLGUN_IZ_VURUS):
            return
        # Artık, iz belirsizliğiyle ters orantılı ağırlıklandırılır: kamera ile
        # desteklenen (hassas) izlerden gelen artıklar daha çok söz sahibi olur
        agirlik = 1.0 / np.trace(iz.kf.P[:2, :2] + o.R)
        self.bias_artiklar["konum"].append((o.z - iz.kf.konum, agirlik))
        if self._bias_hazir("konum"):
            artik = np.array([a for a, _ in self.bias_artiklar["konum"]])
            w = np.array([w for _, w in self.bias_artiklar["konum"]])
            self.bias["konum"] = (artik * w[:, None]).sum(axis=0) / w.sum()

    # ------------------------------------------------------------ iz yönetimi
    def _iz_yonetimi(self):
        t = self.zaman
        self.izler = [iz for iz in self.izler
                      if t - iz.son_guncelleme <= (ONAYLI_OMUR if iz.onayli else ADAY_OMUR)]
        # Aynı hedefe ait çift onaylı izleri birleştir (eski ID korunur)
        silinecek = set()
        onayli = sorted((iz for iz in self.izler if iz.onayli), key=lambda iz: iz.id)
        for a in range(len(onayli)):
            for b in range(a + 1, len(onayli)):
                i1, i2 = onayli[a], onayli[b]
                if i1.id in silinecek or i2.id in silinecek:
                    continue
                d = np.linalg.norm(i1.kf.x[:2] - i2.kf.x[:2])
                dv = np.linalg.norm(i1.kf.x[2:] - i2.kf.x[2:])
                if d < 50.0 and dv < 8.0:
                    silinecek.add(i2.id)
                    for s, ts in i2.sensor_son.items():
                        i1.sensor_son[s] = max(ts, i1.sensor_son.get(s, -np.inf))
                    i1.dost_etiket = i1.dost_etiket or i2.dost_etiket
        self.izler = [iz for iz in self.izler if iz.id not in silinecek]

    def guven_skoru(self, iz):
        """0-1 arası iz güveni: güncel sensör katkılarının birleşimi."""
        kalan = 1.0
        for s, ts in iz.sensor_son.items():
            p = SENSOR_KATKI[s] * self.guven[s] * np.exp(-(self.zaman - ts) / 5.0)
            kalan *= (1.0 - p)
        return 1.0 - kalan

    def durum_resmi(self):
        """Onaylı izlerin anlık durum resmi."""
        resim = []
        for iz in self.izler:
            if not iz.onayli:
                continue
            resim.append(dict(
                id=iz.id, konum=iz.kf.konum, hiz=iz.kf.x[2:].copy(),
                skor=self.guven_skoru(iz),
                sensorler=sorted(s for s, ts in iz.sensor_son.items() if self.zaman - ts < 3.0),
                dost=iz.dost_etiket is not None))
        return resim


def fuzyon_calistir(olcumler, sensorler, kayit_araligi=1.0, guven_agirliklandirma=True):
    """Verilen sensörlerle tüm senaryoyu koşturur.

    Dönüş: [(füzyon_zamanı, durum_resmi, sensör_güvenleri), ...] (kayit_araligi saniyede bir)
    """
    merkez = FuzyonMerkezi(sensorler, guven_agirliklandirma)
    tum = sorted((o for s in sensorler for o in olcumler[s]), key=lambda o: o.t_varis)
    gecmis = []
    k_idx = 0
    n_adim = int(round((SURE + FUZYON_GECIKMESI) / ADIM))
    kayit_her = int(round(kayit_araligi / ADIM))
    for k in range(1, n_adim + 1):
        t_simdi = k * ADIM
        # Bu adıma kadar füzyon merkezine ulaşmış ölçümler
        gelen = []
        while k_idx < len(tum) and tum[k_idx].t_varis <= t_simdi:
            gelen.append(tum[k_idx])
            k_idx += 1
        merkez.olcum_al(gelen)
        merkez.ilerle(t_simdi)
        if k % kayit_her == 0 and merkez.zaman >= 0:
            gecmis.append((round(merkez.zaman, 3), merkez.durum_resmi(), dict(merkez.guven)))
    return gecmis, merkez
