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
