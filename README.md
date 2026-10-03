# Çok Sensörlü Veri Füzyonu

[![Testler](https://github.com/Goktugelbir/Cok-Sensorlu-Veri-Fuzyonu/actions/workflows/testler.yml/badge.svg)](https://github.com/Goktugelbir/Cok-Sensorlu-Veri-Fuzyonu/actions/workflows/testler.yml)

*Harekât sahasında durumsal farkındalığın artırılması*

Radar, EO/termal kamera ve konum bildirimi sensörlerinden gelen simüle edilmiş
konum ölçümlerini birleştirerek tek bir **ortak durum resmi** oluşturan ve
füzyonun tek sensöre göre kazancını ölçen bir Python projesi [1, 5, 7].

![Özet](results/ozet.png)

*Üst satır (başarılı örnek, sis): Kamera sisten etkilenince tek başına hedeflerin
%65'ini kaçırıyor. Füzyon radar ve konum bildirimiyle bu açığı kapatıyor ve en
düşük RMSE'yi veriyor. Alt satır (zorlu örnek, sensör kaybı): Radar ve kamera
150-170 s arasında aynı anda kapalı kalıyor. Bu sürede sadece dost birlikler
izlenebiliyor; diğer hedeflerin izleri kopuyor ve geri geldiklerinde yeni ID
alıyor. Kırmızı: dost olmayan iz, mavi: dost iz, gri: gerçek rota.
Figür seed=42 örnek koşusundandır; istatistikler için [Sonuçlar](#sonuçlar).*

## Amaç

- 10 km x 10 km'lik bir sahada hareket eden 5 hedefi (2'si dost) farklı
  özelliklere sahip üç sensörle izlemek,
- sensör ölçümlerini zaman, bias ve güven açısından hizalayıp tek bir iz
  listesinde birleştirmek,
- füzyonun tek sensörlere göre kazancını dört senaryoda (normal, sis,
  karıştırma, sensör kaybı) sayısal olarak göstermek.

## Saha ve sensörler

| Hedef | Tür | Rota |
|---|---|---|
| Araç-1 | diğer | düz, sabit 10 m/s |
| İHA-1 | diğer | 22 m/s, uzun sola dönüş ve ardından sağa kırılma |
| İnsan Grubu | diğer | 1.5 m/s, hafif kıvrımlı |
| Dost Araç | **dost** | düz, hız değiştiren (8 → 16 → 5 m/s) |
| Dost İHA | **dost** | 18 m/s, 60° dönüş, ardından yavaşlama |

| Sensör | Konum / menzil | Gürültü (1σ) | Hız | Gecikme | Özel durum |
|---|---|---|---|---|---|
| Radar | (4, 4) km, 8 km | 12 m + 2 m/km | 1 Hz | 0.6-0.7 s | %90 tespit, tarama başına ~0.5 yanlış alarm |
| EO/termal kamera | (5.5, 5) km, 3.5 km | 3 m + 4 m/km | 5 Hz | 0.3-0.35 s | sis: menzil x0.65, gürültü x3, tespit %50 |
| Konum bildirimi | sadece dostlar | 3 m | 0.5 Hz | 1.5-1.7 s | sabit bias (35, -20) m, kimlik taşır |

Sensörler aynı anda ölçmez (her birinin farklı bir faz kayması vardır). Her
ölçüm, sensörün beyan ettiği nominal gürültü kovaryansını taşır. Sis veya
karıştırma bu beyanı değiştirmez; bozulmayı füzyon merkezinin kendisi fark
etmek zorundadır.

## Yöntem

1. **Zaman senkronizasyonu:** Füzyon merkezi, en büyük gecikmeden uzun sabit
   bir pencere (2 s) kadar geriden çalışır. Pencere içindeki ölçümler alınış
   zamanına göre sıralanır, her taramadan önce bütün izler Kalman tahminiyle
   tam o ana taşınır ve sonunda 0.2 s'lik ortak zaman adımına hizalanır. Bu
   sayede gecikmeli ve sırası bozuk gelen ölçümler doğru anda işlenir [1].
2. **Bias düzeltme:** Konum bildirimindeki sabit sapma, radar ve/veya kamerayla
   desteklenen olgun izlere göre hesaplanan artıkların ağırlıklı ortalamasıyla
   kestirilir. Kestirim tamamlanana kadar bu ölçümler izi güncellemez; sadece
   kimlik etiketi ve bias örneği sağlar [1].
3. **İz ilişkilendirme:** Mahalanobis kapılama (χ², %99.9) [1] ve Macar
   algoritması [3] (`scipy.optimize.linear_sum_assignment` [4]) kullanılır. Atanmayan ölçümden
   aday iz başlatılır; güven ağırlıklı 3 vuruşla iz onaylanır. Aday iz 2.5 s,
   onaylı iz 6 s güncellenmezse silinir. Çakışan çift izler birleştirilir [1].
4. **Kalman filtresi** [2]**:** Sabit hız modeli [1] kullanılır; durum `[x, y, vx, vy]`,
   süreç gürültüsü beyaz ivme σ = 1 m/s².
5. **Sensör güveni ve çelişki çözümü:** Her sensör için normalize inovasyon
   karesinin (NIS) [1, 6] hareketli ortalaması tutulur. Ortalama tolerans değerini (4)
   aşarsa sensörün güveni düşer ve ölçüm kovaryansı `R / güven` olarak
   büyütülür. Böylece karıştırılan radar ya da sisteki kamera, çelişkide daha
   az söz sahibi olur. Güveni düşük sensörün vuruşları da onaya daha az katkı
   verir, bu da karıştırmanın ürettiği sahte izleri engeller.
6. **İz güven skoru:** `1 - Π(1 - katkı_s · güven_s · e^{-Δt_s/5})`. Her iz, son
   3 saniyede kendisini destekleyen sensörlerin listesini taşır (animasyonda
   `[R,K,B]` = radar, kamera, konum bildirimi).

**Değerlendirme:** Füzyon zamanında her saniye onaylı izler gerçek hedeflere
Macar algoritmasıyla eşlenir (eşik 250 m). Ölçütler, optimal atamaya dayalı
çok hedefli izleme değerlendirmesiyle [8] aynı mantıktadır.

- **RMSE:** Eşleşen iz-hedef çiftlerinin konum hatası.
- **Kaçırma oranı:** İz atanmamış (hedef, an) çiftlerinin oranı.
- **Yanlış iz:** Ömrünün yarısından fazlasında hiçbir hedefe eşlenmeyen iz.
- **ID switch:** Bir hedefi izleyen iz kimliğinin değişmesi.

Tek sensör sonuçları, aynı füzyon hattının sadece o sensörle çalıştırılmasıyla
elde edilir.

## Kurulum

```bash
git clone https://github.com/Goktugelbir/Cok-Sensorlu-Veri-Fuzyonu.git
cd Cok-Sensorlu-Veri-Fuzyonu
python -m pip install -r requirements.txt
```

Python 3.10+ ve numpy, scipy, matplotlib, pillow (pytest testler için) gerekir.

## Çalıştırma

```bash
python main.py --senaryo sis        # tek senaryo: normal | sis | karistirma | sensor_kaybi
python main.py --hepsi              # tüm senaryolar, 30 seed (~3 dk, çok çekirdekli)
python main.py --hepsi --tekrar 5   # daha az koşu, daha hızlı
python main.py --hepsi --gif-yok    # animasyonsuz
python -m pytest                    # birim testleri
```

Çıktılar `results/` klasörüne yazılır: `<senaryo>.gif`, `karsilastirma.png`,
`ozet.png`, `sonuclar.json`, `sonuclar.md`. Animasyonlar ve özet figür
`seed=42` örnek koşusundan, tablolar `seed=42…71` arasındaki 30 koşudan
üretilir. Tohumlar sabit olduğu için sonuçlar her çalıştırmada aynıdır.

> **Not:** `--senaryo` ile tek senaryo çalıştırıldığında tablo ve grafik,
> dört senaryonun ortak dosyalarını ezmemek için senaryo adını taşıyan ayrı
> dosyalara yazılır: `karsilastirma_<senaryo>.png`, `sonuclar_<senaryo>.json`,
> `sonuclar_<senaryo>.md`. Bu dosyalar git'e eklenmez (`.gitignore`). Ortak
> `karsilastirma.png` ve `sonuclar.*` sadece `--hepsi` ile güncellenir.

## Örnek animasyon

![Sis senaryosu](results/sis.gif)

Gri çizgiler gerçek rotaları, küçük renkli noktalar son 3 saniyenin ham
ölçümlerini, kalın çizgiler füzyon izlerini (ID, güven skoru, destekleyen
sensörler) gösterir. Kesikli daireler sensör menzilleridir; sis altında kamera
dairesi küçülür, kapalı sensör noktalı gri çizilir. Diğer senaryolar:
[normal](results/normal.gif) · [karistirma](results/karistirma.gif) ·
[sensor_kaybi](results/sensor_kaybi.gif)

## Sonuçlar

Her senaryo 30 farklı seed ile (42-71) koşturulmuştur; değerler
**ortalama ± standart sapma** olarak verilmiştir. Hedef rotaları sabit,
sensör gürültüsü, tespitler, yanlış alarmlar ve gecikmeler her seed'de
farklıdır. **Füzyon (güven ağırlıklandırma kapalı)** satırı bir ablasyondur:
aynı füzyon hattı, NIS tabanlı sensör güveni devre dışı bırakılarak (bütün
sensörlerin güveni 1'de sabit) çalıştırılmıştır.

| Senaryo | Konfigürasyon | RMSE (m) | Kaçırma (%) | Yanlış iz | ID switch |
|---|---|---:|---:|---:|---:|
| normal | Sadece radar | 14.8 ± 0.6 | 1.5 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| normal | Sadece kamera | 6.4 ± 0.2 | 33.8 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| normal | Sadece konum bildirimi | 40.2 ± 0.1 | 61.0 ± 0.3 | 0.0 ± 0.0 | 0.2 ± 0.4 |
| normal | Füzyon (güven ağırlıklandırma kapalı) | 8.4 ± 0.5 | 1.1 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| normal | **Füzyon** | 8.4 ± 0.5 | 1.1 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| sis | Sadece radar | 14.8 ± 0.6 | 1.5 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| sis | Sadece kamera | 16.0 ± 2.4 | 65.0 ± 0.2 | 0.2 ± 0.5 | 1.3 ± 0.8 |
| sis | Sadece konum bildirimi | 40.2 ± 0.2 | 61.0 ± 0.3 | 0.0 ± 0.0 | 0.3 ± 0.5 |
| sis | Füzyon (güven ağırlıklandırma kapalı) | 14.8 ± 1.6 | 1.2 ± 0.1 | 2.4 ± 1.8 | 2.5 ± 2.4 |
| sis | **Füzyon** | 12.4 ± 0.7 | 1.1 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| karistirma | Sadece radar | 41.3 ± 4.6 | 8.7 ± 4.8 | 0.0 ± 0.0 | 2.9 ± 1.7 |
| karistirma | Sadece kamera | 6.4 ± 0.3 | 33.9 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| karistirma | Sadece konum bildirimi | 40.3 ± 0.2 | 61.0 ± 0.2 | 0.0 ± 0.0 | 0.4 ± 0.5 |
| karistirma | Füzyon (güven ağırlıklandırma kapalı) | 10.3 ± 1.8 | 1.3 ± 0.3 | 7.7 ± 2.4 | 1.0 ± 1.2 |
| karistirma | **Füzyon** | 8.8 ± 0.7 | 1.1 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| sensor_kaybi | Sadece radar | 14.4 ± 0.5 | 23.8 ± 0.2 | 0.0 ± 0.0 | 5.0 ± 0.0 |
| sensor_kaybi | Sadece kamera | 7.5 ± 0.4 | 56.5 ± 0.0 | 0.0 ± 0.0 | 4.0 ± 0.0 |
| sensor_kaybi | Sadece konum bildirimi | 40.2 ± 0.3 | 68.9 ± 0.2 | 0.0 ± 0.0 | 2.2 ± 0.4 |
| sensor_kaybi | Füzyon (güven ağırlıklandırma kapalı) | 10.0 ± 0.5 | 4.6 ± 0.1 | 0.0 ± 0.0 | 3.0 ± 0.0 |
| sensor_kaybi | **Füzyon** | 10.0 ± 0.5 | 4.6 ± 0.1 | 0.0 ± 0.0 | 3.0 ± 0.0 |

| Senaryo | Füzyonun en iyi tek sensörden düşük RMSE verdiği koşu |
|---|---:|
| normal | 0/30 |
| sis | 30/30 |
| karistirma | 0/30 |
| sensor_kaybi | 0/30 |

![Karşılaştırma](results/karsilastirma.png)

### Yorum

- **Kapsama:** Füzyon her senaryoda en düşük kaçırma oranını veriyor
  (%1.1-4.6). Tek sensörlerde bu oran %1.5-69 arasında.
- **Doğruluk:** Füzyon her senaryoda radar ve konum bildiriminden daha doğru.
  **Sis senaryosunda 30 koşunun 30'unda bütün tek sensörlerden daha düşük
  RMSE veriyor** (12.4 ± 0.7 m; en iyi tek sensör radar 14.8 ± 0.6 m).
- **Kamera ile karşılaştırma:** Normal, karıştırma ve sensör kaybında sadece
  kameranın RMSE'si daha düşük (30 koşunun hiçbirinde füzyon kameranın altına
  inmiyor). Ancak kamera bu sürede hedeflerin %34-57'sini hiç görmüyor;
  RMSE'si sadece menzili içindeki yakın hedeflerden hesaplanıyor. Füzyon ise
  uzak hedefleri de (radarın daha gürültülü ölçümleriyle) izliyor. RMSE'yi
  kaçırma oranıyla birlikte okumak gerekir.
- **Ablasyon, sensör güveninin değeri:** Güven ağırlıklandırma kapatılınca
  karıştırma senaryosunda ortalama **7.7 ± 2.4 sahte iz** oluşuyor, RMSE
  8.8'den 10.3 m'ye çıkıyor ve ID switch'ler beliriyor. Sis senaryosunda da
  2.4 sahte iz, 2.5 ID switch ve 12.4 → 14.8 m RMSE artışı görülüyor. Normal
  ve sensör kaybı senaryolarında iki satır aynı; bu beklenen bir sonuç, çünkü
  bozulmuş bir sensör yokken güven zaten 1'de kalıyor. Bu sonuç hem yanlış iz
  ölçütünün çalıştığını hem de iyileşmenin NIS mekanizmasından geldiğini
  gösteriyor.
- **Bias düzeltme:** Konum bildirimindeki (35, -20) m sapma, seed=42 koşusunda
  her senaryoda ~(39, -19) m olarak kestiriliyor. Kalan hata ~4 m; tek başına
  konum bildiriminin hatası ise ~40 m.
- **Karıştırma:** Radarın güveni karıştırma süresince ~0.1'e düşüyor. Radarın
  tek başına RMSE'si 41.3 ± 4.6 m'ye çıkarken füzyon 8.8 ± 0.7 m'de kalıyor.
- **Sensör kaybı (zayıf nokta):** Radar ve kamera 150-170 s arasında aynı anda
  kapalı. Dost olmayan hedeflerin izleri 6 s sonra siliniyor ve sensörler geri
  gelince yeni ID ile başlıyor (her koşuda 3 ID switch).

## Proje yapısı

```
Cok-Sensorlu-Veri-Fuzyonu/
  main.py                  komut satırı, senaryo koşturma, tablo ve grafik üretimi
  src/saha.py              saha ve hedef rotaları
  src/sensorler.py         sensör modelleri ve senaryo olayları
  src/kalman.py            sabit hız Kalman filtresi
  src/iliskilendirme.py    Mahalanobis kapılama + Macar algoritması
  src/fuzyon.py            füzyon merkezi (senkronizasyon, bias, güven, iz yönetimi)
  src/degerlendirme.py     RMSE, kaçırma, yanlış iz, ID switch
  src/gorsel.py            GIF animasyon, karşılaştırma ve özet figürleri
  tests/                   pytest birim testleri
  .github/workflows/       her push'ta testleri çalıştıran GitHub Actions iş akışı
  results/                 üretilen çıktılar
```

## Varsayımlar ve tasarım kararları

- Sensörler doğrudan kartezyen (x, y) konum ölçer. Gürültü mesafeyle doğrusal
  artar.
- Konum bildirimi mesajı birliğin kimliğini taşır. Füzyon bunu dost/diğer
  etiketi için ve farklı kimlikli ölçümün yanlış ize atanmasını engellemek
  için kullanır.
- Füzyon 2 s geriden çalışır (sabit gecikme penceresi). Durum resmi ve
  değerlendirme bu hizalanmış zamana göredir.
- Sis 60. saniyeden itibaren, karıştırma 80-220 s, sensör kaybı radar
  100-170 s, kamera 150-230 s, konum bildirimi 200-260 s aralığında etkindir.
- Karıştırmada yanlış alarmların %70'i karıştırıcı konumu (7, 6.5) km
  çevresinde yoğunlaşır.

## Gelecek çalışmalar

- Manevralı hedefler için IMM (sabit hız + koordineli dönüş) filtre.
- Kutupsal (menzil-açı) radar ölçüm modeli ve EKF/UKF.
- Gecikmeli ölçümleri pencere beklemeden işlemek için sırası bozuk ölçüm
  (OOSM) güncellemesi ile gerçek zamanlı çıktı.
- Uzun sensör kesintilerinden sonra kimlik korumak için iz yeniden bağlama
  (track re-identification).
- Yoğun yanlış alarm ortamı için JPDA / MHT ilişkilendirme.
- Sensör konumlarındaki ve zaman damgalarındaki hataların da kestirildiği tam
  sensör kaydı (registration).
- Senaryo geometrisinin (rotalar, sensör yerleşimi) de rastgele örneklendiği
  daha geniş bir Monte Carlo çalışması.

## Kaynakça

1. Y. Bar-Shalom, P. K. Willett, X. Tian, *Tracking and Data Fusion: A Handbook
   of Algorithms*, YBS Publishing, 2011.
2. S. Särkkä, L. Svensson, *Bayesian Filtering and Smoothing*, 2. baskı,
   Cambridge University Press, 2023.
3. D. F. Crouse, "On Implementing 2D Rectangular Assignment Algorithms,"
   *IEEE Transactions on Aerospace and Electronic Systems*, 52(4), 1679-1696,
   2016.
4. P. Virtanen ve diğ., "SciPy 1.0: Fundamental Algorithms for Scientific
   Computing in Python," *Nature Methods*, 17, 261-272, 2020.
5. B. Khaleghi, A. Khamis, F. O. Karray, S. N. Razavi, "Multisensor Data
   Fusion: A Review of the State-of-the-Art," *Information Fusion*, 14(1),
   28-44, 2013.
6. Y. Huang, Y. Zhang, Z. Wu, N. Li, J. Chambers, "A Novel Adaptive Kalman
   Filter With Inaccurate Process and Measurement Noise Covariance Matrices,"
   *IEEE Transactions on Automatic Control*, 63(2), 594-601, 2018.
7. R. P. S. Mahler, *Advances in Statistical Multisource-Multitarget Information
   Fusion*, Artech House, 2014.
8. A. S. Rahmathullah, Á. F. García-Fernández, L. Svensson, "Generalized
   Optimal Sub-Pattern Assignment Metric," *20th International Conference on
   Information Fusion (FUSION)*, 2017.
