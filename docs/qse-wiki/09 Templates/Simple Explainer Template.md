---
type: template
language: pl
---

# Szablon prostego wyjaśnienia (Glossary / Concept)

> Skopiuj ten plik dla nowych haseł glossary lub stron konceptualnych. Zachowaj trójpoziomową strukturę — każda strona wiki QSE ma te same 3 poziomy głębokości.

---

# [Nazwa pojęcia / termin]

## Prostymi słowami

(2-3 zdania. Analogia z życia codziennego. Zrozumiałe dla studenta 1 roku lub osoby bez wiedzy technicznej. Styl: „wyobraź sobie…", „jak w…", „to jak…")

> Przykład dobrego: „Acyclicity to brak pętli w instrukcji budowania. Jeśli żeby zbudować silnik potrzebujesz kół, ale żeby zbudować koła potrzebujesz silnika — nie zbudujesz nic."
> Przykład złego: „Acyclicity = 1 - (SCC_nodes / total_nodes)." (To jest poziom 3, nie 1.)

## Szczegółowy opis

(Pełne wyjaśnienie techniczne. Używaj:)

### Jak to działa
(Mechanizm, krok po kroku, przykład kodu jeśli pomocny)

### Jak to mierzy QSE
(Jak konkretnie obliczana jest ta metryka / realizowane pojęcie w QSE)

```mermaid
(Opcjonalny diagram — graf zależności, sekwencja, quadrant chart)
```

### Wyniki empiryczne
| Zbiór | Wartość | Istotność |
|---|---|---|
| Java GT (n=59) | — | — |
| Python GT (n=30) | — | — |
| Benchmark 558 | — | — |

### Przykłady
(Konkretne repozytoria z benchmarku — co mają wysokie, co niskie wartości i dlaczego)

### Znane ograniczenia
(Co ta metryka/pojęcie pomija? Kiedy zawodzi?)

## Definicja formalna

(Wzór matematyczny, definicja algorytmiczna, cytaty z literatury naukowej)

$$\text{[wzór LaTeX]}$$

(Cytaty: Autor et al. (rok) — „cytat z paperu")

**Walidacja empiryczna:**
- Statystyki: MW p=??, Spearman ρ=??, AUC=??
- Odniesienie: [[Benchmark Index|Benchmark]]

## Zobacz też

- [[Glossary|Słownik]] — powiązane pojęcia
- [[Powiązana metryka]] — wikilink
- [[Powiązany benchmark]] — dane empiryczne
- [[Powiązana hipoteza]] — jak to pojęcie jest badane
