| Senaryo | Konfigürasyon | RMSE (m) | GOSPA (m) | Kaçırma (%) | Yanlış iz | ID switch |
|---|---|---:|---:|---:|---:|---:|
| normal | Sadece radar | 14.9 ± 0.7 | 36.7 ± 1.4 | 1.4 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.2 |
| normal | Sadece kamera | 6.3 ± 0.2 | 197.2 ± 0.2 | 33.9 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| normal | Sadece konum bildirimi | 40.3 ± 0.2 | 313.4 ± 0.6 | 60.9 ± 0.2 | 0.0 ± 0.0 | 0.2 ± 0.4 |
| normal | Füzyon (güven ağırlıklandırma kapalı) | 8.4 ± 0.5 | 20.5 ± 0.8 | 1.1 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| normal | **Füzyon** | 8.4 ± 0.5 | 20.5 ± 0.8 | 1.1 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| sis | Sadece radar | 14.9 ± 0.7 | 36.7 ± 1.4 | 1.4 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.2 |
| sis | Sadece kamera | 15.7 ± 2.1 | 317.4 ± 1.9 | 65.0 ± 0.2 | 0.2 ± 0.4 | 1.4 ± 0.7 |
| sis | Sadece konum bildirimi | 40.3 ± 0.2 | 313.6 ± 0.7 | 61.0 ± 0.3 | 0.0 ± 0.0 | 0.3 ± 0.5 |
| sis | Füzyon (güven ağırlıklandırma kapalı) | 14.7 ± 1.4 | 42.4 ± 6.9 | 1.2 ± 0.1 | 2.0 ± 1.3 | 1.3 ± 1.7 |
| sis | **Füzyon** | 12.4 ± 0.8 | 30.2 ± 1.5 | 1.1 ± 0.1 | 0.0 ± 0.2 | 0.0 ± 0.2 |
| karistirma | Sadece radar | 41.0 ± 3.7 | 110.3 ± 19.0 | 8.9 ± 4.4 | 0.0 ± 0.0 | 2.7 ± 1.5 |
| karistirma | Sadece kamera | 6.3 ± 0.2 | 197.3 ± 0.2 | 33.9 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| karistirma | Sadece konum bildirimi | 40.3 ± 0.2 | 313.3 ± 0.4 | 60.9 ± 0.2 | 0.0 ± 0.0 | 0.1 ± 0.3 |
| karistirma | Füzyon (güven ağırlıklandırma kapalı) | 9.7 ± 1.5 | 51.5 ± 9.5 | 1.3 ± 0.2 | 7.9 ± 2.4 | 0.8 ± 0.9 |
| karistirma | **Füzyon** | 8.8 ± 0.6 | 21.5 ± 1.1 | 1.1 ± 0.1 | 0.0 ± 0.0 | 0.0 ± 0.2 |
| sensor_kaybi | Sadece radar | 14.5 ± 0.6 | 117.4 ± 1.4 | 23.8 ± 0.2 | 0.0 ± 0.0 | 5.0 ± 0.0 |
| sensor_kaybi | Sadece kamera | 7.4 ± 0.4 | 274.5 ± 0.1 | 56.5 ± 0.0 | 0.0 ± 0.0 | 4.0 ± 0.0 |
| sensor_kaybi | Sadece konum bildirimi | 40.3 ± 0.2 | 330.0 ± 0.5 | 68.9 ± 0.2 | 0.0 ± 0.0 | 2.1 ± 0.3 |
| sensor_kaybi | Füzyon (güven ağırlıklandırma kapalı) | 10.0 ± 0.5 | 41.3 ± 1.0 | 4.6 ± 0.1 | 0.0 ± 0.0 | 3.0 ± 0.0 |
| sensor_kaybi | **Füzyon** | 10.0 ± 0.5 | 41.3 ± 1.0 | 4.6 ± 0.1 | 0.0 ± 0.0 | 3.0 ± 0.0 |

| Senaryo | Füzyonun en iyi tek sensörden düşük olduğu koşu: RMSE | GOSPA |
|---|---:|---:|
| normal | 0/30 | 30/30 |
| sis | 29/30 | 30/30 |
| karistirma | 0/30 | 30/30 |
| sensor_kaybi | 0/30 | 30/30 |

| Senaryo | Bias kestirimi x (m) | Bias kestirimi y (m) | Kestirim hatası (m) |
|---|---:|---:|---:|
| normal | 35.2 ± 2.3 | -19.8 ± 2.5 | 3.0 ± 1.6 |
| sis | 35.3 ± 2.2 | -19.8 ± 2.6 | 3.0 ± 1.6 |
| karistirma | 35.4 ± 2.4 | -19.7 ± 2.6 | 3.1 ± 1.7 |
| sensor_kaybi | 35.3 ± 2.2 | -19.7 ± 2.6 | 3.0 ± 1.6 |
