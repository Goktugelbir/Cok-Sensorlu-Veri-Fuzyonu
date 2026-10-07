| Senaryo | Konfigürasyon | RMSE (m) | GOSPA (m) | Kaçırma (%) | Yanlış iz | ID switch | Etiket doğruluğu (%) |
|---|---|---:|---:|---:|---:|---:|---:|
| normal | Sadece radar | 13.4 ± 0.7 | 34.2 ± 1.5 | 1.5 ± 0.1 | 0.0 ± 0.0 | 0.1 ± 0.3 | 60.0 ± 0.1 |
| normal | Sadece kamera | 5.3 ± 0.2 | 171.8 ± 0.2 | 30.9 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 71.9 ± 0.0 |
| normal | Sadece konum bildirimi | 40.4 ± 0.2 | 313.2 ± 0.3 | 60.8 ± 0.1 | 0.0 ± 0.0 | 0.1 ± 0.3 | 100.0 ± 0.0 |
| normal | Füzyon (güven ağırlıklandırma kapalı) | 7.9 ± 0.5 | 19.0 ± 0.8 | 1.1 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.0 | 100.0 ± 0.0 |
| normal | Füzyon (IMM kapalı, sadece CV) | 12.5 ± 1.0 | 23.6 ± 1.0 | 1.2 ± 0.1 | 0.0 ± 0.0 | 1.0 ± 0.2 | 100.0 ± 0.0 |
| normal | **Füzyon** | 7.9 ± 0.5 | 19.0 ± 0.8 | 1.1 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.0 | 100.0 ± 0.0 |
| sis | Sadece radar | 13.4 ± 0.7 | 34.2 ± 1.5 | 1.5 ± 0.1 | 0.0 ± 0.0 | 0.1 ± 0.3 | 60.0 ± 0.1 |
| sis | Sadece kamera | 15.1 ± 2.2 | 317.1 ± 1.1 | 65.0 ± 0.2 | 0.3 ± 0.4 | 1.4 ± 0.8 | 83.2 ± 0.2 |
| sis | Sadece konum bildirimi | 40.4 ± 0.2 | 313.3 ± 0.3 | 60.8 ± 0.2 | 0.0 ± 0.0 | 0.0 ± 0.0 | 100.0 ± 0.0 |
| sis | Füzyon (güven ağırlıklandırma kapalı) | 12.8 ± 1.0 | 39.1 ± 6.8 | 1.2 ± 0.1 | 2.1 ± 1.6 | 1.2 ± 1.7 | 100.0 ± 0.0 |
| sis | Füzyon (IMM kapalı, sadece CV) | 14.9 ± 1.1 | 34.4 ± 1.9 | 1.5 ± 0.2 | 0.0 ± 0.0 | 1.0 ± 0.0 | 100.0 ± 0.0 |
| sis | **Füzyon** | 11.1 ± 0.8 | 27.4 ± 1.4 | 1.2 ± 0.1 | 0.0 ± 0.0 | 0.1 ± 0.3 | 100.0 ± 0.0 |
| karistirma | Sadece radar | 40.4 ± 3.5 | 102.9 ± 17.2 | 7.4 ± 4.0 | 0.0 ± 0.0 | 2.5 ± 1.5 | 60.4 ± 2.4 |
| karistirma | Sadece kamera | 5.3 ± 0.2 | 171.8 ± 0.2 | 30.9 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 71.9 ± 0.0 |
| karistirma | Sadece konum bildirimi | 40.5 ± 0.2 | 313.2 ± 0.2 | 60.8 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.2 | 100.0 ± 0.0 |
| karistirma | Füzyon (güven ağırlıklandırma kapalı) | 10.4 ± 2.1 | 51.1 ± 9.0 | 1.3 ± 0.3 | 7.5 ± 2.2 | 0.9 ± 1.2 | 100.0 ± 0.0 |
| karistirma | Füzyon (IMM kapalı, sadece CV) | 13.9 ± 1.0 | 25.3 ± 1.4 | 1.1 ± 0.1 | 0.0 ± 0.0 | 1.0 ± 0.0 | 100.0 ± 0.0 |
| karistirma | **Füzyon** | 8.5 ± 0.7 | 20.0 ± 1.1 | 1.1 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.0 | 100.0 ± 0.0 |
| sensor_kaybi | Sadece radar | 13.8 ± 0.4 | 116.8 ± 1.1 | 23.8 ± 0.2 | 0.0 ± 0.0 | 5.0 ± 0.0 | 60.0 ± 0.1 |
| sensor_kaybi | Sadece kamera | 5.7 ± 0.3 | 249.0 ± 0.1 | 53.5 ± 0.0 | 0.0 ± 0.0 | 4.0 ± 0.0 | 74.9 ± 0.0 |
| sensor_kaybi | Sadece konum bildirimi | 40.4 ± 0.2 | 329.9 ± 0.2 | 68.8 ± 0.1 | 0.0 ± 0.0 | 2.0 ± 0.0 | 100.0 ± 0.0 |
| sensor_kaybi | Füzyon (güven ağırlıklandırma kapalı) | 9.8 ± 0.5 | 39.8 ± 0.9 | 4.6 ± 0.1 | 0.0 ± 0.0 | 3.0 ± 0.0 | 100.0 ± 0.0 |
| sensor_kaybi | Füzyon (IMM kapalı, sadece CV) | 13.1 ± 0.8 | 44.7 ± 0.9 | 4.8 ± 0.1 | 0.0 ± 0.0 | 4.0 ± 0.0 | 100.0 ± 0.0 |
| sensor_kaybi | **Füzyon** | 9.8 ± 0.5 | 39.8 ± 0.9 | 4.6 ± 0.1 | 0.0 ± 0.0 | 3.0 ± 0.0 | 100.0 ± 0.0 |

| Senaryo | Füzyonun en iyi tek sensörden düşük olduğu koşu: RMSE | GOSPA |
|---|---:|---:|
| normal | 0/30 | 30/30 |
| sis | 30/30 | 30/30 |
| karistirma | 0/30 | 30/30 |
| sensor_kaybi | 0/30 | 30/30 |

| Senaryo | Bias kestirimi x (m) | Bias kestirimi y (m) | Kestirim hatası (m) |
|---|---:|---:|---:|
| normal | 35.9 ± 2.5 | -19.8 ± 2.3 | 3.0 ± 1.7 |
| sis | 36.0 ± 2.5 | -19.8 ± 2.3 | 3.1 ± 1.7 |
| karistirma | 36.1 ± 2.5 | -19.9 ± 2.2 | 3.0 ± 1.8 |
| sensor_kaybi | 36.0 ± 2.3 | -20.0 ± 2.3 | 2.9 ± 1.7 |

Filtre tutarlılığı: konum NEES'i. Tutarlı bir filtrede ANEES ≈ 2 olur ve noktaların ~%95'i %95 kabul bandında kalır.

| Senaryo | Füzyon (IMM) ANEES | IMM bantta (%) | Sadece CV ANEES | CV bantta (%) | İHA-1 ANEES (IMM / CV) |
|---|---:|---:|---:|---:|---:|
| normal | 1.81 | 74 | 4.49 | 67 | 1.9 / 14.5 |
| sis | 2.30 | 62 | 3.62 | 60 | 2.6 / 8.4 |
| karistirma | 1.87 | 73 | 4.72 | 65 | 1.9 / 15.4 |
| sensor_kaybi | 1.83 | 72 | 2.98 | 65 | 2.0 / 7.1 |
