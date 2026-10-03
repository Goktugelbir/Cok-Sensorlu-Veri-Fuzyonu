| Senaryo | Konfigürasyon | RMSE (m) | GOSPA (m) | Kaçırma (%) | Yanlış iz | ID switch |
|---|---|---:|---:|---:|---:|---:|
| normal | Sadece radar | 14.8 ± 0.6 | 36.9 ± 1.4 | 1.5 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| normal | Sadece kamera | 6.4 ± 0.2 | 197.3 ± 0.2 | 33.8 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| normal | Sadece konum bildirimi | 40.2 ± 0.1 | 313.4 ± 0.6 | 61.0 ± 0.3 | 0.0 ± 0.0 | 0.2 ± 0.4 |
| normal | Füzyon (güven ağırlıklandırma kapalı) | 8.4 ± 0.5 | 20.8 ± 0.9 | 1.1 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| normal | **Füzyon** | 8.4 ± 0.5 | 20.8 ± 0.9 | 1.1 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| sis | Sadece radar | 14.8 ± 0.6 | 36.9 ± 1.4 | 1.5 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| sis | Sadece kamera | 16.0 ± 2.4 | 317.4 ± 2.2 | 65.0 ± 0.2 | 0.2 ± 0.5 | 1.3 ± 0.8 |
| sis | Sadece konum bildirimi | 40.2 ± 0.2 | 313.5 ± 0.6 | 61.0 ± 0.3 | 0.0 ± 0.0 | 0.3 ± 0.5 |
| sis | Füzyon (güven ağırlıklandırma kapalı) | 14.8 ± 1.6 | 45.1 ± 7.5 | 1.2 ± 0.1 | 2.4 ± 1.8 | 2.5 ± 2.4 |
| sis | **Füzyon** | 12.4 ± 0.7 | 30.3 ± 1.4 | 1.1 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| karistirma | Sadece radar | 41.3 ± 4.6 | 109.4 ± 19.6 | 8.7 ± 4.8 | 0.0 ± 0.0 | 2.9 ± 1.7 |
| karistirma | Sadece kamera | 6.4 ± 0.3 | 197.3 ± 0.2 | 33.9 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| karistirma | Sadece konum bildirimi | 40.3 ± 0.2 | 313.5 ± 0.5 | 61.0 ± 0.2 | 0.0 ± 0.0 | 0.4 ± 0.5 |
| karistirma | Füzyon (güven ağırlıklandırma kapalı) | 10.3 ± 1.8 | 52.5 ± 9.6 | 1.3 ± 0.3 | 7.7 ± 2.4 | 1.0 ± 1.2 |
| karistirma | **Füzyon** | 8.8 ± 0.7 | 21.7 ± 1.0 | 1.1 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| sensor_kaybi | Sadece radar | 14.4 ± 0.5 | 117.6 ± 1.2 | 23.8 ± 0.2 | 0.0 ± 0.0 | 5.0 ± 0.0 |
| sensor_kaybi | Sadece kamera | 7.5 ± 0.4 | 274.5 ± 0.1 | 56.5 ± 0.0 | 0.0 ± 0.0 | 4.0 ± 0.0 |
| sensor_kaybi | Sadece konum bildirimi | 40.2 ± 0.3 | 330.1 ± 0.5 | 68.9 ± 0.2 | 0.0 ± 0.0 | 2.2 ± 0.4 |
| sensor_kaybi | Füzyon (güven ağırlıklandırma kapalı) | 10.0 ± 0.5 | 41.2 ± 0.9 | 4.6 ± 0.1 | 0.0 ± 0.0 | 3.0 ± 0.0 |
| sensor_kaybi | **Füzyon** | 10.0 ± 0.5 | 41.2 ± 0.9 | 4.6 ± 0.1 | 0.0 ± 0.0 | 3.0 ± 0.0 |

| Senaryo | Füzyonun en iyi tek sensörden düşük olduğu koşu: RMSE | GOSPA |
|---|---:|---:|
| normal | 0/30 | 30/30 |
| sis | 30/30 | 30/30 |
| karistirma | 0/30 | 30/30 |
| sensor_kaybi | 0/30 | 30/30 |

| Senaryo | Bias kestirimi x (m) | Bias kestirimi y (m) | Kestirim hatası (m) |
|---|---:|---:|---:|
| normal | 36.1 ± 2.5 | -19.9 ± 2.3 | 3.2 ± 1.6 |
| sis | 36.0 ± 2.4 | -19.7 ± 2.4 | 3.1 ± 1.7 |
| karistirma | 36.0 ± 2.5 | -19.9 ± 2.5 | 3.2 ± 1.7 |
| sensor_kaybi | 36.0 ± 2.4 | -19.9 ± 2.5 | 3.1 ± 1.7 |
