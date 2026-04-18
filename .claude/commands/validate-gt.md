# /validate-gt

Uruchamia pełną walidację statystyczną AGQ na zbiorach Ground Truth (Java n=59, Python n=30).
Porównuje wyniki z bazą QSEv3c i raportuje PASS/FAIL per hipoteza.

---

## Protokół wykonania

### Krok 1 — Wczytaj kontekst

1. Wczytaj `ROLE_RESEARCH.md` — rola analityka badawczego
2. Wczytaj `docs/qse-wiki/07 Benchmarks/Java GT Dataset.md` — opis GT
3. Wczytaj `docs/qse-wiki/07 Benchmarks/Python GT Dataset.md`
4. Sprawdź aktualny status hipotez: `docs/qse-wiki/06 Hypotheses/Hypotheses Register.md`

---

### Krok 2 — Uruchom GT scan Java

```bash
cd /home/user/qse-pkg
python3 scripts/e10_gt_scan.py 2>&1 | tee /tmp/gt_validation_$(date +%Y%m%d).log
```

Jeśli skrypt nie istnieje lub wymaga aktualizacji, uruchom alternatywnie:
```bash
python3 -c "
import json, sys
sys.path.insert(0, '.')
from qse.graph_metrics import compute_agq_from_path
# Wczytaj GT z artifacts/gt_java_v4.json
with open('artifacts/gt_java_v4.json') as f:
    gt = json.load(f)
# Skanuj każde repo i oblicz metryki
"
```

---

### Krok 3 — Oblicz statystyki

Dla każdego komponentu (M, A, S, C, CD) oraz AGQv3c oblicz:

**a) Partial Spearman r (kontrolując log(nodes)):**
```python
from scipy.stats import spearmanr
from scipy.stats import pearsonr
import numpy as np

# partial_r(metric, panel | log_nodes)
# Rezydua: metric_resid = metric - fit(log_nodes)
#           panel_resid = panel - fit(log_nodes)
# partial_r = spearmanr(metric_resid, panel_resid)
```

**b) Mann-Whitney U (POS vs NEG):**
```python
from scipy.stats import mannwhitneyu
stat, p = mannwhitneyu(pos_scores, neg_scores, alternative='greater')
auc = stat / (len(pos_scores) * len(neg_scores))
```

**c) AUC-ROC:**
```python
from sklearn.metrics import roc_auc_score
auc = roc_auc_score(labels_binary, metric_scores)
```

---

### Krok 4 — Porównaj z bazą QSEv3c

| Metryka | Baseline partial r | Baseline MW p | AUC |
|---------|-------------------|---------------|-----|
| C (Cohesion) | 0.479 | 0.0002 | — |
| CD (Coupling) | 0.342 | 0.004 | — |
| S (Stability) | 0.593 (n=29) | 0.016 | — |
| A (Acyclicity) | marginal | 0.030 | — |
| M (Modularity) | ns | 0.226 | — |
| **AGQv3c** | **0.447** | **0.000221** | **0.733** |

**Kryterium PASS:**
- AGQv3c partial r ≥ 0.447 AND AUC ≥ 0.733 → **PASS**
- AGQv3c partial r < 0.350 OR AUC < 0.680 → **FAIL — regresja**
- Pomiędzy → **NEUTRAL — bez poprawy**

---

### Krok 5 — Weryfikacja Jolak (opcjonalna)

Jeśli dostępne dane Jolak (`artifacts/jolak_scan_results.json`):
```bash
python3 -c "
import json
with open('artifacts/jolak_scan_results.json') as f:
    jolak = json.load(f)
# Sprawdź: MyPerf4J najwyższy, Sentinel najniższe S, seata tangled
# 4/5 wniosków Jolak powinno być zgodnych
"
```

Raport: ile z 5 wniosków Jolak jest potwierdzonych.

---

### Krok 6 — Zapisz wyniki

```bash
python3 -c "
import json, datetime
results = {
    'date': datetime.date.today().isoformat(),
    'java_gt_n': 59,
    'agq_v3c_partial_r': <wartość>,
    'agq_v3c_auc': <wartość>,
    'components': {
        'C': {'partial_r': ..., 'mw_p': ...},
        'S': {'partial_r': ..., 'mw_p': ...},
        # ...
    },
    'verdict': 'PASS|FAIL|NEUTRAL',
    'notes': ''
}
with open('artifacts/validation_$(date +%Y%m%d).json', 'w') as f:
    json.dump(results, f, indent=2)
"
```

---

### Krok 7 — Raport końcowy

Wypisz tabelę porównawczą (before/after) i jeden z werdyktów:

- ✅ **PASS** — metryka poprawiona, baseline nie cofnięty
- ❌ **FAIL** — regresja, NIE commituj zmian kodu
- ⚠️ **NEUTRAL** — brak poprawy, rozważ inną strategię