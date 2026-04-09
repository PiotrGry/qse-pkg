# Porównanie QSE AGQ z Dai et al. (2026) - published baseline

**Data:** 2026-03-21
**Dane:** `artifacts/benchmark/dai_et_al_comparison.json`
**Skrypt:** `scripts/dai_et_al_comparison.py`
**Paper:** Dai et al. "An integrated graph neural network model for joint software defect prediction and code quality assessment", Scientific Reports 16:1677 (doi:10.1038/s41598-025-31209-5)

---

## 1. Cel

Porównanie wyników QSE AGQ z published results Dai et al. na **tych samych 4 repozytoriach Java**.

---

## 2. Metodologia

| | Dai et al. | QSE AGQ |
|---|---|---|
| Metoda | Supervised GNN (AST+CFG+DFG), 32GB GPU | Deterministyczne metryki grafowe, zero-shot |
| Training | 6.8h na RTX 3090 | 0 (brak) |
| Output | 5-class quality + defect prediction | Score 0-1 + fingerprint + diagnostyka |
| Scanner | QSE Rust qse-core (tree-sitter-java) | - |

---

## 3. Wyniki

### 3.1 Porównanie metryk

```
Project             AGQ   Mod   Acy  Stab   Coh  Def/file  Dai F1  Dai Arch
Apache Ant        0.549  0.50  0.97  0.47  0.26    0.276   0.811    0.800
Apache Camel      0.570  0.79  1.00  0.15  0.34    0.204   0.811    0.801
Apache Hadoop     0.626  0.66  0.99  0.59  0.26    0.234   0.809    0.815
Eclipse JDT       0.632  0.77  0.96  0.48  0.31    0.251   0.808    0.823
```

### 3.2 Zgodność rankingów (n=4)

| Ranking | 1st (best) | 2nd | 3rd | 4th (worst) |
|---|---|---|---|---|
| **QSE AGQ** | **JDT (0.632)** | **Hadoop (0.626)** | **Camel (0.570)** | **Ant (0.549)** |
| **Dai arch. integrity** | **JDT (0.823)** | **Hadoop (0.815)** | **Camel (0.801)** | **Ant (0.800)** |
| Defect density (lower=better) | Camel (0.204) | Hadoop (0.234) | JDT (0.251) | Ant (0.276) |

**AGQ ranking = Dai et al. architectural integrity ranking (Spearman rho=1.0, n=4).**

AGQ vs defect density: rho=0.2 (słaba - defect density bardziej koreluje z wielkością projektu i dojrzałością).

### 3.3 Diagnostyka AGQ

| Projekt | AGQ diagnoza | Kontekst Dai et al. |
|---|---|---|
| **Apache Ant** | Niska kohezja (0.26) - god classes | Najniższy arch. integrity (0.800), "Low complexity" ale najwyższy defect density |
| **Apache Camel** | Bardzo niska stability (0.15) - flat architecture | "High complexity" w Dai, +11.2% improvement (biggest gain = worst baseline) |
| **Apache Hadoop** | Niska kohezja (0.26) - god classes | Medium we wszystkim |
| **Eclipse JDT** | Najlepszy AGQ, cycles=MEDIUM | Najwyższy Dai arch. integrity (0.823) |

---

## 4. Interpretacja

### Perfektna zgodność rankingu (rho=1.0)

Pomimo fundamentalnie różnych metod:
- Dai et al.: supervised GNN trenowany na labeled data (6.8h, 32GB VRAM)
- QSE AGQ: deterministyczny graf zależności, zero training

Oba narzędzia rankują te 4 projekty **identycznie**. To silny argument za face validity AGQ.

### AGQ daje więcej niż ranking

Dai et al. daje accuracy per quality dimension - ale nie mówi *co* jest źle. AGQ identyfikuje:
- **Ant/Hadoop**: god classes (LCOM4 wskazuje klasy bez kohezji)
- **Camel**: flat architecture (stability=0.15 - brak zróżnicowania ról pakietów)
- **JDT**: cycles detected (acyclicity=0.96 - 4% węzłów w cyklu)

### Fix scannera: enterprise-ready

Przy okazji naprawiono Rust scanner:
- Pomijanie katalogów `workspace`, `*.tests.*`, `*.test.*` (Eclipse-style test fixtures)
- Skip plików >1MB (wygenerowane/fixture data)
- Skip plików non-UTF-8

Te poprawki są konieczne do skanowania enterprise repo (Eclipse, IntelliJ, duże mono-repo).

---

## 5. Ograniczenia

- **n=4** - za mało na statystykę. rho=1.0 przy n=4 ma p=0.083 (exact permutation test) - nie osiąga p<0.05.
- Wersje repo mogą się różnić od Dai et al. (nie podają commitów).
- Porównanie ranking vs ranking, nie score vs score (różne skale).
- Dai et al. mierzą per-file, QSE per-repo - różna granularność.

---

## 6. Wniosek dla grantu

> "Comparison with Dai et al. (2026, Scientific Reports) on all 4 Apache Java projects shows perfect rank concordance between AGQ and their trained architectural integrity classifier (Spearman rho=1.0, n=4, p=0.083). While not statistically significant due to small sample, the qualitative alignment between a zero-shot deterministic metric and a supervised deep learning model trained on labeled data provides convergent validity evidence. AGQ additionally provides actionable architectural diagnostics (god classes, flat architecture, cycle detection) that the GNN model does not expose."

---

## 7. Reprodukcja

```bash
# Requires Rust scanner
make build

# Clone and scan
git clone --depth 1 https://github.com/apache/ant.git /tmp/dai-repos/ant
git clone --depth 1 https://github.com/eclipse-jdt/eclipse.jdt.core.git /tmp/dai-repos/eclipse-jdt-core
git clone --depth 1 https://github.com/apache/camel.git /tmp/dai-repos/camel
git clone --depth 1 https://github.com/apache/hadoop.git /tmp/dai-repos/hadoop

python3 scripts/dai_et_al_comparison.py
```
