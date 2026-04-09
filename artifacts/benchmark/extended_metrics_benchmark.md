# Extended Metrics Benchmark (CCD, IC, Fan-out)

**Data:** 2026-03-22
**Dane:** `extended_metrics_benchmark.json` (Python), `extended_metrics_java.json`, `extended_metrics_go.json`, `extended_metrics_normalized.json` (all, size-normalized)
**Skrypt:** `scripts/extended_metrics_benchmark.py`

---

## Metryki

| Metryka | Źródło | Definicja |
|---|---|---|
| **CCD** (Cumulative Component Dependency) | Lakos (1996) | Σ osiągalnych nodes per node, norm. per n·log₂(n) |
| **Indirect Coupling (IC)** | Šora (2013), Chiricota (2003) | ESM = \|shared neighbors\| / \|union neighbors\| per edge |
| **fan_out_std** | Martin (1994) | Std dev fan-out across internal modules |
| **max_fan_out** | Martin (1994) | Max fan-out (identifies god modules) |
| **Per-module breakdown** | fan-in, fan-out, instability, SCC membership per module |

Normalizacja na rozmiar: metric / log(n_modules + 1).

---

## Wyniki cross-language (n=240)

### Po normalizacji na rozmiar

| Metryka | vs churn_gini | vs hotspot_ratio | Size-confound po norm.? |
|---|---|---|---|
| **fan_out_std_norm** | **r=+0.13, p=0.048** | n.s. | **Nie** (r=-0.05 vs nodes) |
| max_fan_out_norm | n.s. | n.s. | Tak (r=+0.38) |
| avg_fan_out_norm | n.s. | n.s. | Tak (r=-0.21) |
| mean_IC | n.s. cross-lang | n.s. | Tak (r=-0.25) |
| ccd_per_node | n.s. | n.s. | Nie (r=+0.08) |

### IC po kontroli rozmiaru (50-500 modules, n=97)

IC vs churn_gini: **r=-0.27, p=0.007** - istotne cross-language po usunięciu confoundu.

### Per-language

| | Python (n=80) | Java (n=79) | Go (n=81) |
|---|---|---|---|
| **Najlepsza metryka** | fan_out_std↔gini r=+0.28 | brak istotnych | IC↔gini r=-0.32 |
| **CCD** | n.s. | n.s. | r=-0.35 (p=0.001) |

---

## Size confound

| Metryka (raw) | r vs nodes |
|---|---|
| max_fan_out | **+0.50** (silny!) |
| fan_out_std | +0.32 |
| mean_IC | -0.25 |
| CCD_norm | +0.16 |

**Po normalizacji per log(n):** fan_out_std_norm i ccd_per_node stają się size-independent.

---

## Wnioski

1. **fan_out_std / log(n)** - jedyna metryka istotna cross-language po normalizacji (r=+0.13)
2. **IC** - istotna po kontroli rozmiaru (r=-0.27), kandydat do Predictor z size-bracket
3. **CCD** - nie daje sygnału, odłożona
4. **Per-module fan-out** - wartość diagnostyczna (identyfikacja god modules), nie predykcyjna
5. Normalizacja na rozmiar jest **konieczna** - raw metryki są zdominowane przez confound
