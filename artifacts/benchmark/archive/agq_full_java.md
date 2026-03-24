# AGQ Multi-Language Benchmark

- generated: `2026-03-08T02:07:44.325182+00:00`
- languages: Java
- repos_ok: `10/10`
- agq_mean: `0.6404`  spread: `0.3253`

## Correlations

- spearman_agq_vs_hotspot_ratio: r_s=-0.1273 p=0.7261 n=10
- spearman_agq_vs_churn_gini: r_s=-0.6000 p=0.0667 n=10

## Results

| Repo | Lang | AGQ | Nodes | Mod | Acy | Stab | Coh | Hotspot | ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| spring-boot | Java | 0.8032 | 9239 | 0.7483 | 0.9995 | 0.9432 | 0.5217 | 0.0634 | 211ms |
| resilience4j | Java | 0.7822 | 1240 | 0.7752 | 0.9944 | 0.9913 | 0.3680 | 0.1034 | 50ms |
| log4j | Java | 0.7329 | 2321 | 0.6871 | 0.9677 | 0.9615 | 0.3152 | 0.0577 | 65ms |
| junit5 | Java | 0.7118 | 1680 | 0.6038 | 0.9976 | 0.9132 | 0.3324 | 0.0847 | 119ms |
| guava | Java | 0.6422 | 1831 | 0.6665 | 1.0000 | 0.7028 | 0.1995 | 0.1052 | 85ms |
| netty | Java | 0.6254 | 3961 | 0.6793 | 0.9987 | 0.5477 | 0.2761 | 0.0584 | 110ms |
| mockito | Java | 0.5561 | 901 | 0.6326 | 0.8679 | 0.2494 | 0.4744 | 0.0533 | 42ms |
| hibernate-orm | Java | 0.5469 | 10450 | 0.8342 | 0.8402 | 0.2114 | 0.3018 | 0.0941 | 603ms |
| grpc-java | Java | 0.5257 | 2553 | 0.6551 | 1.0000 | 0.1777 | 0.2698 | 0.0918 | 48ms |
| jackson-databind | Java | 0.4779 | 869 | 0.6374 | 0.8504 | 0.2630 | 0.1607 | 0.0952 | 23ms |

