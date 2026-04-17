---
type: hypothesis
id: O5
status: otwarta
language: pl
topic: CD, Python, odwrócony kierunek
sesja_turn: 34-35
---

# O5 — Dlaczego CD odwraca kierunek dla Pythona

## Prostymi słowami

Dla Javy: mało krawędzi (edges/nodes) = dobra architektura. Dla Pythona: mało krawędzi = też może znaczyć flat spaghetti. youtube-dl: ratio=1.35 (najniższe w datasecie!), bo 1000 extractorów nie importuje się nawzajem. Czy to jedyna przyczyna? Czy istnieje typ złej architektury Pythona z WYSOKIM ratio? I czy da się zbudować metrykę która rozróżnia „dobry niski ratio" od „zły niski ratio"?

## Co badano

> **H₁:** Odwrócony kierunek CD w Pythonie wynika wyłącznie z flat spaghetti (niski ratio przez brak struktury, nie przez luźne sprzężenia).

> **H₂:** Istnieje typ złej architektury Pythona z wysokim ratio (tangled imports), który flat_score nie wykrywa.

## Status

**OTWARTA** — mechanizm zidentyfikowany jakościowo (flat spaghetti), ale nie zwalidowany ilościowo.

## Dane i mechanizm (Turn 34-35)

### Java vs Python — odwrócony kierunek 5/6 metryk

| Metryka | Java Δ (pos-neg) | Python Δ (pos-neg) | Zgodność |
|---|---|---|---|
| AGQ v2 | +0.107 ** | −0.087 ns | ODWROTNY ✗ |
| ratio (edges/nodes) | −0.961 ** | +1.472 ns | ODWROTNY ✗ |
| Stability (S) | +0.158 ns | −0.114 ns | ODWROTNY ✗ |
| Acyclicity (A) | +0.029 ns | −0.027 ns | ODWROTNY ✗ |
| Cohesion (C) | +0.107 ns | +0.022 ns | zgodny ✓ |
| NSdepth | +0.085 * | +0.065 ns | zgodny ✓ |

Pięć na sześć metryk ma odwrócony kierunek. To nie jest przypadek — to strukturalny problem.

### Mechanizm flat spaghetti

```
Java: zła architektura = za dużo krawędzi
  (tangled imports, god classes, circular dependencies)
  → wysoki ratio → wysoka edges/nodes → niski CD → niski AGQ

Python: zła architektura = brak struktury hierarchicznej
  (youtube-dl: 1000 extractorów w jednym namespace)
  → brak importów między extractorami = brak krawędzi!
  → niski ratio → high CD → wysoki AGQ (błędnie)
```

### Pytanie: czy istnieje zła architektura Python z WYSOKIM ratio?

Możliwy scenariusz: projekt Python z „bogate importy bez struktury" — wiele importów między modułami, ale wszystkie na tym samym poziomie namespace. Czy taki wzorzec istnieje w realnych projektach?

Kandydaci z GT Python:
- taiga-back: ratio=3.45, Panel=4.25 NEG — możliwy kandydat
- sentry: ratio=8.32, Panel=6.00 POS — kontrprzykład (wysoki ratio, dobry Panel)

## Otwarte pytania

1. **Czy flat spaghetti to jedyna przyczyna odwróconego CD?**
   Test: czy wszystkie NEG Python mają niski ratio (flat spaghetti) czy są NEG z wysokim ratio?

2. **Czy flat_score (E6) naprawia CD odwrócenie w praktyce?**
   AGQ v3c Python ma zgodny kierunek (+0.460*) — ale nie wiemy czy przez flat_score czy przez inne składowe.

3. **Czy Python potrzebuje innej definicji CD?**
   Np. CD_python = penalizacja za koncentrację klas w top-level namespace, zamiast penalizacji za gęstość krawędzi.

4. **Czy to zjawisko dotyczy też TypeScript?**
   TypeScript ma podobną do Pythona możliwość flat namespace (np. duże monorepo z wszystkim w `src/`). QSE benchmark ma TypeScript dane — warto sprawdzić.

## Warunki zamknięcia

**Zamknięcie O5 (jako wyjaśniona):**
1. Zebrane ≥10 NEG Python, sklasyfikowane jako: (a) flat spaghetti (niski ratio), (b) tangled (wysoki ratio)
2. Sprawdzono czy flat_score wykrywa typ (a) ale nie (b)
3. Zaproponowana metryka specyficzna dla typu (b) i walidacja

**Zamknięcie O5 (jako nieistotna):**
- Wszystkie NEG Python to flat spaghetti → CD odwrócenie w pełni wyjaśnione przez E6
- flat_score wystarczy → O5 zamknięta jako H₁ potwierdzona

## Powiązania

- [[E6 flatscore]] — obecne częściowe rozwiązanie
- [[E5 Namespace Metrics]] — dodatkowe metryki namespace
- [[E2 Coupling Density]] — oryginalne odkrycie CD
- [[W9 AGQv3c Python Discriminates Quality]] — hipoteza o całej formule
- [[O4 Namespace Metrics for Python]] — pokrewne otwarte pytanie
- [[Hypotheses Register]] — pełna lista hipotez
