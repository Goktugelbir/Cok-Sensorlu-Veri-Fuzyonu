| Senaryo | Konfigürasyon | RMSE (m) | GOSPA (m) | Kaçırma (%) | Yanlış iz | ID switch | Etiket doğruluğu (%) |
|---|---|---:|---:|---:|---:|---:|---:|
| normal | Sadece radar | 13.4 ± 0.5 | 33.8 ± 1.1 | 1.4 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.2 | 60.0 ± 0.0 |
| normal | Sadece kamera | 5.3 ± 0.2 | 171.9 ± 0.2 | 30.9 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 71.9 ± 0.0 |
| normal | Sadece konum bildirimi | 40.4 ± 0.2 | 313.3 ± 0.3 | 60.9 ± 0.2 | 0.0 ± 0.0 | 0.0 ± 0.2 | 100.0 ± 0.0 |
| normal | Füzyon (güven ağırlıklandırma kapalı) | 7.9 ± 0.5 | 18.8 ± 0.8 | 1.1 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.0 | 100.0 ± 0.0 |
| normal | Füzyon (IMM kapalı, sadece CV) | 12.6 ± 0.9 | 23.5 ± 1.0 | 1.2 ± 0.1 | 0.0 ± 0.0 | 1.0 ± 0.2 | 100.0 ± 0.0 |
| normal | **Füzyon** | 7.9 ± 0.5 | 18.8 ± 0.8 | 1.1 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.0 | 100.0 ± 0.0 |
| sis | Sadece radar | 13.4 ± 0.5 | 33.8 ± 1.1 | 1.4 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.2 | 60.0 ± 0.0 |
| sis | Sadece kamera | 15.0 ± 2.4 | 317.4 ± 1.9 | 65.0 ± 0.2 | 0.2 ± 0.4 | 1.4 ± 0.7 | 83.2 ± 0.3 |
| sis | Sadece konum bildirimi | 40.4 ± 0.2 | 313.3 ± 0.4 | 60.9 ± 0.2 | 0.0 ± 0.0 | 0.1 ± 0.3 | 100.0 ± 0.0 |
| sis | Füzyon (güven ağırlıklandırma kapalı) | 12.6 ± 0.8 | 36.6 ± 6.3 | 1.1 ± 0.1 | 1.7 ± 1.5 | 0.6 ± 1.2 | 100.0 ± 0.0 |
| sis | Füzyon (IMM kapalı, sadece CV) | 14.9 ± 1.0 | 34.1 ± 1.8 | 1.5 ± 0.1 | 0.0 ± 0.2 | 1.0 ± 0.2 | 100.0 ± 0.0 |
| sis | **Füzyon** | 11.0 ± 0.5 | 27.1 ± 1.1 | 1.1 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.2 | 100.0 ± 0.0 |
| karistirma | Sadece radar | 41.2 ± 3.4 | 104.7 ± 19.2 | 7.6 ± 5.5 | 0.0 ± 0.0 | 2.4 ± 1.4 | 59.8 ± 2.3 |
| karistirma | Sadece kamera | 5.4 ± 0.2 | 171.9 ± 0.2 | 30.9 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 71.9 ± 0.0 |
| karistirma | Sadece konum bildirimi | 40.4 ± 0.2 | 313.3 ± 0.4 | 60.9 ± 0.2 | 0.0 ± 0.0 | 0.1 ± 0.3 | 100.0 ± 0.0 |
| karistirma | Füzyon (güven ağırlıklandırma kapalı) | 9.2 ± 1.1 | 49.8 ± 10.4 | 1.3 ± 0.2 | 7.8 ± 2.4 | 0.6 ± 0.8 | 100.0 ± 0.0 |
| karistirma | Füzyon (IMM kapalı, sadece CV) | 13.5 ± 0.7 | 25.1 ± 1.2 | 1.2 ± 0.1 | 0.0 ± 0.0 | 1.0 ± 0.2 | 100.0 ± 0.0 |
| karistirma | **Füzyon** | 8.5 ± 1.0 | 20.0 ± 1.5 | 1.2 ± 0.1 | 0.0 ± 0.0 | 0.1 ± 0.3 | 100.0 ± 0.0 |
| sensor_kaybi | Sadece radar | 14.1 ± 0.8 | 116.8 ± 1.5 | 23.8 ± 0.2 | 0.0 ± 0.0 | 5.1 ± 0.3 | 60.0 ± 0.1 |
| sensor_kaybi | Sadece kamera | 5.6 ± 0.3 | 249.0 ± 0.1 | 53.5 ± 0.0 | 0.0 ± 0.0 | 4.0 ± 0.0 | 74.9 ± 0.0 |
| sensor_kaybi | Sadece konum bildirimi | 40.4 ± 0.2 | 330.1 ± 0.5 | 68.9 ± 0.2 | 0.0 ± 0.0 | 2.0 ± 0.0 | 100.0 ± 0.0 |
| sensor_kaybi | Füzyon (güven ağırlıklandırma kapalı) | 10.1 ± 0.8 | 40.0 ± 1.1 | 4.6 ± 0.1 | 0.0 ± 0.0 | 3.1 ± 0.3 | 100.0 ± 0.0 |
| sensor_kaybi | Füzyon (IMM kapalı, sadece CV) | 13.2 ± 0.8 | 44.8 ± 1.1 | 4.9 ± 0.1 | 0.0 ± 0.0 | 4.0 ± 0.0 | 100.0 ± 0.0 |
| sensor_kaybi | **Füzyon** | 10.1 ± 0.8 | 40.1 ± 1.1 | 4.6 ± 0.1 | 0.0 ± 0.0 | 3.1 ± 0.3 | 100.0 ± 0.0 |

| Senaryo | Füzyonun en iyi tek sensörden düşük olduğu koşu: RMSE | GOSPA |
|---|---:|---:|
| normal | 0/30 | 30/30 |
| sis | 30/30 | 30/30 |
| karistirma | 0/30 | 30/30 |
| sensor_kaybi | 0/30 | 30/30 |

| Senaryo | Bias kestirimi x (m) | Bias kestirimi y (m) | Kestirim hatası (m) |
|---|---:|---:|---:|
| normal | 35.3 ± 2.2 | -19.8 ± 2.4 | 2.8 ± 1.7 |
| sis | 35.3 ± 2.2 | -19.8 ± 2.5 | 2.9 ± 1.6 |
| karistirma | 35.3 ± 2.4 | -19.6 ± 2.4 | 2.9 ± 1.7 |
| sensor_kaybi | 35.3 ± 2.2 | -19.8 ± 2.4 | 2.8 ± 1.6 |

Filtre tutarlılığı: konum NEES'i. Tutarlı bir filtrede ANEES ≈ 2 olur ve noktaların ~%95'i %95 kabul bandında kalır.

| Senaryo | Füzyon (IMM) ANEES | IMM bantta (%) | Sadece CV ANEES | CV bantta (%) | İHA-1 ANEES (IMM / CV) |
|---|---:|---:|---:|---:|---:|
| normal | 1.75 | 69 | 4.43 | 63 | 1.9 / 14.6 |
| sis | 2.21 | 59 | 3.53 | 58 | 2.6 / 8.4 |
| karistirma | 1.83 | 71 | 4.56 | 63 | 1.9 / 14.8 |
| sensor_kaybi | 1.82 | 67 | 2.92 | 62 | 2.2 / 7.1 |

Mann-Whitney U testi, füzyon: seed 42-71 ile bu küme (iki yönlü; p > 0.05 ise anlamlı fark yok)

| Senaryo | GOSPA p | RMSE p |
|---|---:|---:|
| normal | 0.51 | 0.62 |
| sis | 0.57 | 0.88 |
| karistirma | 0.70 | 0.88 |
| sensor_kaybi | 0.28 | 0.06 |
