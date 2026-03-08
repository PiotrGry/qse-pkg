# AGQ Multi-Language Benchmark

- generated: `2026-03-08T02:07:43.824654+00:00`
- languages: Python
- repos_ok: `10/10`
- agq_mean: `0.7366`  spread: `0.1965`

## Correlations

- spearman_agq_vs_hotspot_ratio: r_s=-0.3455 p=0.3282 n=10
- spearman_agq_vs_churn_gini: r_s=0.0909 p=0.8028 n=10

## Results

| Repo | Lang | AGQ | Nodes | Mod | Acy | Stab | Coh | Hotspot | ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| scikit-learn | Python | 0.8001 | 1176 | 0.6910 | 0.9889 | 0.8160 | 0.7042 | 0.1041 | 141ms |
| fastapi | Python | 0.7954 | 145 | 0.5569 | 1.0000 | 0.8368 | 0.7880 | 0.0756 | 20ms |
| django | Python | 0.7936 | 1229 | 0.5217 | 1.0000 | 0.9733 | 0.6794 | 0.1087 | 66ms |
| scrapy | Python | 0.7645 | 417 | 0.4926 | 1.0000 | 0.9740 | 0.5913 | 0.1128 | 11ms |
| pandas | Python | 0.7449 | 1721 | 0.6604 | 1.0000 | 0.9873 | 0.3317 | 0.1096 | 144ms |
| requests | Python | 0.7276 | 67 | 0.8120 | 1.0000 | 0.6485 | 0.4500 | 0.1905 | 4ms |
| celery | Python | 0.7188 | 420 | 0.4614 | 1.0000 | 0.9331 | 0.4809 | 0.1388 | 25ms |
| flask | Python | 0.7095 | 79 | 0.5227 | 1.0000 | 0.7373 | 0.5778 | 0.1379 | 5ms |
| airflow | Python | 0.7078 | 8017 | 0.7624 | 1.0000 | 0.4635 | 0.6053 | 0.1099 | 450ms |
| ansible | Python | 0.6035 | 2155 | 0.5005 | 1.0000 | 0.2229 | 0.6908 | 0.0903 | 76ms |

