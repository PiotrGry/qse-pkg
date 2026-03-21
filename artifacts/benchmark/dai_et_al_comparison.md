# Porównanie QSE AGQ z Dai et al. (2026) — published baseline

**Data:** 2026-03-21
**Dane:** `artifacts/benchmark/dai_et_al_comparison.json`
**Skrypt:** `scripts/dai_et_al_comparison.py`
**Paper:** Dai et al. "An integrated graph neural network model for joint software defect prediction and code quality assessment", Scientific Reports 16:1677 (doi:10.1038/s41598-025-31209-5)

---

## 1. Cel

Porównanie wyników QSE AGQ z published results Dai et al. na **tych samych repozytoriach Java**. Cel: sprawdzić czy AGQ daje wyniki spójne z niezależnym narzędziem badawczym (GNN model) na tych samych danych.

---

## 2. Metodologia

| | Dai et al. | QSE AGQ |
|---|---|---|
| Metoda | Supervised GNN (AST+CFG+DFG) | Deterministyczne metryki grafowe |
| Granularność | Per-file | Per-repo |
| Training | 6.8h na RTX 3090 | 0 (zero-shot) |
| Output | 5-class quality + defect prediction | Score 0-1 + fingerprint |
| Wymiar "architectural integrity" | Trained classifier (accuracy 0.800-0.815) | stability + acyclicity + modularity |

### Repozytoria (3/4 z paperu)

| Projekt | Files | Defects | LOC | Dai complexity |
|---|---|---|---|---|
| Apache Ant | 1,248 | 345 | 158K | Low |
| Apache Camel | 3,874 | 789 | 453K | High |
| Apache Hadoop | 2,893 | 678 | 567K | Medium |

Eclipse JDT (2,156 files) pominięty — Rust scanner crash na 9,267 plikach Java.

---

## 3. Wyniki

### 3.1 Porównanie metryk

```
Project             AGQ   Mod   Acy  Stab   Coh  Def/file  Dai F1  Dai Arch
Apache Ant        0.549  0.50  0.97  0.47  0.26    0.276   0.811    0.800
Apache Camel      0.570  0.79  1.00  0.15  0.34    0.204   0.811    0.801
Apache Hadoop     0.626  0.66  0.99  0.59  0.26    0.234   0.809    0.815
```

### 3.2 Zgodność rankingów

| Ranking | 1st (best) | 2nd | 3rd (worst) |
|---|---|---|---|
| **QSE AGQ** | **Hadoop (0.626)** | **Camel (0.570)** | **Ant (0.549)** |
| **Dai arch. integrity** | **Hadoop (0.815)** | **Camel (0.801)** | **Ant (0.800)** |
| Defect density (best=lowest) | Camel (0.204) | Hadoop (0.234) | Ant (0.276) |

**AGQ ranking jest identyczny z Dai et al. architectural integrity ranking (Spearman rho=1.0).**

AGQ vs defect density: rho=0.5 (częściowa zgodność — Hadoop i Ant zgadzają się, Camel nie).

### 3.3 Co AGQ diagnozuje

| Projekt | AGQ diagnoza | Spójne z Dai et al.? |
|---|---|---|
| **Apache Ant** | Niska kohezja (0.26) — god classes | Tak — najniższy Dai arch. integrity |
| **Apache Camel** | Bardzo niska stability (0.15) — flat architecture | Tak — "High complexity" w Dai Table 8, +11.2% improvement (biggest gain = worst baseline) |
| **Apache Hadoop** | Najlepszy AGQ, ale niska kohezja (0.26) | Tak — najwyższy Dai arch. integrity |

---

## 4. Interpretacja

### Co potwierdza ten benchmark

1. **Ranking AGQ = ranking Dai et al. architectural integrity** (rho=1.0, n=3). Pomimo fundamentalnie różnych metod (deterministyczny graf vs trained GNN), oba narzędzia rankują te same projekty w tej samej kolejności.

2. **AGQ daje actionable diagnostykę**: dla Ant wskazuje god classes (LCOM4), dla Camel wskazuje flat architecture (brak zróżnicowania warstw). Dai et al. dają tylko accuracy score per dimension — nie mówią *co* jest źle.

3. **Complementary approaches**: Dai et al. potrzebują labeled data + GPU. AGQ działa zero-shot w <1s. Oba dają spójne wyniki.

### Ograniczenia

- **n=3** — za mało na statystykę. Ranking rho=1.0 przy n=3 ma tylko 6 możliwych permutacji — nie jest istotny statystycznie (p=0.17 dla exact test). To obserwacja jakościowa, nie dowód.
- Eclipse JDT pominięty (scanner crash) — zmniejsza próbkę.
- Wersje repo mogą się różnić (Dai et al. nie podają commitów).
- Porównanie ranking vs ranking, nie score vs score (różne skale).

---

## 5. Wniosek dla grantu

> "Comparison with published GNN results (Dai et al. 2026, Scientific Reports) on the same 3 Apache Java projects shows perfect rank concordance between AGQ and their trained architectural integrity classifier (Spearman rho=1.0, n=3). While this sample is too small for statistical significance, the qualitative alignment between a zero-shot deterministic metric (AGQ) and a supervised deep learning model provides evidence that AGQ captures meaningful architectural properties. Notably, AGQ additionally identifies specific architectural issues (low cohesion in Ant/Hadoop, flat architecture in Camel) that the GNN model does not expose."

---

## 6. Reprodukcja

```bash
# Clone repos
git clone --depth 1 https://github.com/apache/ant.git /tmp/dai-repos/ant
git clone --depth 1 https://github.com/apache/camel.git /tmp/dai-repos/camel
git clone --depth 1 https://github.com/apache/hadoop.git /tmp/dai-repos/hadoop

# Run QSE (requires Rust scanner)
qse agq /tmp/dai-repos/ant --threshold 0
qse agq /tmp/dai-repos/camel --threshold 0
qse agq /tmp/dai-repos/hadoop --threshold 0

# Full comparison
python3 scripts/dai_et_al_comparison.py
```
