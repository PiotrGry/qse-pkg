---
type: experiment
id: E4
status: zakończony
language: pl
tested_hypothesis: W4
sesja_turn: ~
---

# E4 — Rozszerzenie GT do n≥30

## Prostymi słowami

Żeby wiedzieć, że metryka działa, potrzeba odpowiednio dużej próby. Przy n=14 repozytoriach wszelkie statystyki są przypadkowe — jedno „dziwne\" repozytorium potrafi odwrócić wyniki. E4 to prace infrastrukturalne: zebranie kolejnych repozytoriów, ocena przez panel ekspertów i scalenie w jeden powiększony GT. Dopiero po tym kroku liczby stały się wiarygodne.

## Cel

Rozbudowa panelu Ground Truth Java do minimalnej próby statystycznej (n≥30), umożliwiająca wyciąganie wniosków z testów statystycznych. Przy n<30 moc testów (Mann-Whitney, partial Spearman) jest zbyt niska, żeby odróżnić prawdziwy sygnał od szumu.

## Dane wejściowe

- **Punkt startowy:** GT Java n=14 (7 POS, 7 NEG) — wyjście z E2
- **Metoda rozszerzenia:** Kolejne repozytoria oceniane przez panel 4 ekspertów (protokół identyczny jak w GT bazowym)
- **Kryterium akceptacji:** σ < 2.0 (zgodność panelu)

## Wyniki

### Rozbudowa w etapach

```
GT v1 (wyjście E2)       GT v2 (po E4, etap 1)     GT v3 (po E4, etap 2)
  n=14                     n=29                        n=59
  7 POS, 7 NEG             15 POS, 14 NEG              31 POS + 28 NEG
                           ↑ commit c1ee146            → post-exclusion:
                                                         27 POS + 28 NEG + 4 EXCL
```

**Commity:** `c1ee146` (n=14→n=29), `cfa15c8` (n=29→n=59 batch merge), `c3a633e` (finalizacja GT v3)

### Kluczowy wynik — pierwsza liczba oparta na solidnych danych

| Wersja | n | AGQ partial r | p | Status |
|---|---|---|---|---|
| AGQ v1 | 14 | ~0.564 | ns (p > 0.05) | Nieistotny |
| **AGQ v2** | **29 (etap 1)** | **+0.675** | **0.008 ✓** | **Pierwszy istotny wynik** |
| AGQ v2 | 59 | 0.447 | 0.0004 ✓ | Potwierdzony na pełnym GT |

Partial r = **+0.675 (p = 0.008)** przy n=29 to **pierwsza liczba oparta na solidnych danych** w projekcie QSE — pierwszy raz AGQ v2 przeżył kontrolę rozmiaru (partial Spearman) na próbie o wystarczającej mocy statystycznej.

### Python GT — pierwsze kroki

W ramach E4 uruchomiono również prace nad Python GT:
- Przeskanowano pierwsze **20 repozytoriów Python**
- Potwierdzono, że AGQ v2 (bez flat_score) **działa na Pythonie** — podstawowa infrastruktura skanowania
- Odkryto problem odwróconego kierunku korelacji dla metryk standardowych w Pythonie (→ motywacja dla E6)

## Interpretacja

### Dlaczego n=14 było za małe?

Przy n=14 test Mann-Whitney ma moc ~0.40–0.50 na efekcie r=0.5 — rzucamy monetą, czy wykryjemy efekt, który istnieje. Dopiero przy n≥30 moc rośnie do ~0.70–0.80. Wyniki E2 na n=14 były zachęcające, ale methodologicznie niewystarczające do wyciągania wniosków o AGQ jako narzędziu.

### Jakość ocen panelowych

Każde nowe repozytorium w rozszerzeniu przeszło przez pełny protokół:
- 4 recenzentów, skala 1–10
- Odrzucenie jeśli σ ≥ 2.0
- Efekt: kilka repozytoriów z „szarą strefą" (panel ~5.5–6.5) zostało oznaczonych, ale nie wykluczonych w tym etapie (późniejsze filtrowanie → Strict GT)

### Odkrycie 4 EXCL (efekt archipelagu)

Po scaleniu do n=59 odkryto, że 4 repozytoria POS to kolekcje niezależnych projektów (java-design-patterns, camunda-bpm-examples, javaee7-samples, quarkus-quickstarts). Panel słusznie oceniał je jako POS (jakość kodu próbek), ale metryki grafowe QSE mierzą inną właściwość — architekturę na poziomie repozytorium. Te 4 zostały oznaczone jako EXCL (zob. [[Ground Truth]] — sekcja „Wykluczone repozytoria\").

## Powiązane pliki

| Plik | Opis |
|---|---|
| `artifacts/gt_java_final_fixed.json` | GT bazowy (n=29) |
| `artifacts/gt_java_candidates.json` | Batch rozszerzenia (n=30) |
| `artifacts/gt_java_expanded.json` | Scalony GT (n=59, aktywne=55) |

## Zobacz też

- [[Ground Truth]] — pełna dokumentacja GT Java i Python
- [[Expert Panel]] — metodologia panelu ekspertów
- [[W4 AGQv2 Beats AGQv1 on Java GT]] — hipoteza potwierdzona dzięki E4
- [[E2 Coupling Density]] — poprzedni eksperyment (GT n=14)
- [[How to Read Experiments]] — protokół eksperymentów QSE
