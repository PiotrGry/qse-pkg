---
type: glossary
language: pl
---

# GT — Ground Truth (Zbiór walidacyjny)

## Prostymi słowami

Ground Truth to zestaw projektów, dla których wiemy z góry, czy mają dobrą, czy złą architekturę — sądząc po eksperckich ocenach. Jak „klucz odpowiedzi" w teście: mamy poprawne odpowiedzi, i sprawdzamy, czy nasza metryka zgadza się z tymi odpowiedziami. Jeżeli metryka mówi „ta architektura jest zła" i ekspert też tak ocenia — to dobry znak.

## Szczegółowy opis

**Ground Truth (GT)** to zbiór repozytoriów z przypisanymi etykietami jakości, uzyskanymi niezależnie od AGQ przez symulowany **panel ekspertów**. Służy jako benchmark do walidacji metryki: czy AGQ poprawnie klasyfikuje projekty?

### Dwa dostępne GT w QSE

| Zbiór | n | POS | NEG | Status |
|---|---:|---:|---:|---|
| **Java GT (n=59)** | 59 | 31 | 28 | ✅ Aktualny (kwiecień 2026) |
| **Python GT (n=30)** | 30 | 13 | 17 | ⚠️ Problem kierunku |

### Metodologia tworzenia GT

**Krok 1 — Selekcja kandydatów**
Repozytoria dobierane są z publicznych GitHuba według kryteriów:
- Minimalny rozmiar (co najmniej kilkadziesiąt plików)
- Popularność lub jawna klasyfikacja (DDD sample, known-bad repo)
- Zbalansowanie POS/NEG

**Krok 2 — Ocena panelowa**
Każde repozytorium ocenia panel 4 symulowanych ekspertów:
1. Puryst architektoniczny
2. Pragmatyk
3. Metrykolog
4. Praktyk przemysłowy

Każdy wystawia ocenę 1–10. Panel Score = mean(4 ocen).

**Krok 3 — Przypisanie etykiety**
- Panel Score ≥ 6.0 → **POS** (pozytywna architektura)
- Panel Score < 6.0 → **NEG** (negatywna architektura)
- σ (niezgodność) > 2.0 → repo wykluczane lub powtarzane

**Krok 4 — Walidacja statystyczna**
AGQ obliczane dla wszystkich repo. Sprawdzane:
- Mann-Whitney U test (POS vs NEG)
- Spearman ρ (AGQ vs Panel Score)
- Partial Spearman (kontrola confounders)
- AUC-ROC

### Wyniki walidacji Java GT (n=59)

| Statystyka | Wartość |
|---|---|
| POS mean AGQ | 0.571 |
| NEG mean AGQ | 0.486 |
| Gap | 0.085 |
| Mann-Whitney p | **0.000221** |
| Spearman ρ | **0.380** (p=0.003) |
| Partial r | **0.447** (p=0.0004) |
| AUC-ROC | **0.767** |

AUC=0.767 oznacza, że losowo wybrany POS ma 76.7% szans na wyższy AGQ niż losowo wybrany NEG — zdecydowanie powyżej przypadku (0.5).

### Ewolucja GT

```
Oryginalne GT Java:  n=29 (15 POS, 14 NEG) — gt_java_final_fixed.json
Ekspansja (2026-04): +30 repo (16 POS, 14 NEG) — commit b336496
Rozszerzone GT:      n=59 (31 POS, 28 NEG) — gt_java_expanded.json
```

Gap zmniejszył się z 0.115 do 0.085 przy rozszerzeniu (oczekiwane — większa różnorodność). Wszystkie testy istotności pozostają p<0.01.

### Ograniczenia GT

- Panel ekspertów jest **symulowany** — nie są to prawdziwi zewnętrzni eksperci
- GT Java jest większy i lepiej skalibrowany niż GT Python
- Brak walidacji na projektach przemysłowych (closed-source)
- Selektywność: GT bazuje na popularnych OSS (GitHub stars bias)

## Definicja formalna

Niech R = {r₁, ..., rₙ} będzie zbiorem repozytoriów. GT definiuje funkcję etykietowania:

$$L: R \to \{POS, NEG\}, \quad L(r) = \begin{cases} POS & \text{jeśli Panel}(r) \geq 6.0 \\ NEG & \text{jeśli Panel}(r) < 6.0 \end{cases}$$

Metryka AGQ jest walidowana przez test, czy:
$$\text{AGQ}(r | L(r)=POS) > \text{AGQ}(r | L(r)=NEG)$$

ze statystycznie istotną różnicą (Mann-Whitney U, p < 0.05).

## Zobacz też

- [[07 Benchmarks/Java GT Dataset|Java GT Dataset]] — pełne dane Java GT
- [[07 Benchmarks/Python GT Dataset|Python GT Dataset]] — pełne dane Python GT
- [[Panel Score|Panel Score]] — jak obliczana jest ocena panelowa
- [[Mann-Whitney|Mann-Whitney]] — test używany do walidacji
- [[Partial Spearman|Partial Spearman]] — korelacja z kontrolą confounders
