---
type: glossary
language: pl
---

# CycleSeverity

## Prostymi słowami

CycleSeverity mówi jak poważne są cykliczne zależności w projekcie — od NONE (brak cykli, ideał) przez LOW (drobne cykle, do naprawy) aż do CRITICAL (duży procent kodu w jednym gigantycznym cyklu, wymagający pilnej interwencji). Każdy program z cyklami ma ryzyko efektu domina — zmiana w module A wymusza zmianę w B, a B z powrotem w A. Im więcej modułów w cyklu, tym trudniejsze utrzymanie.

## Szczegółowy opis

CycleSeverity jest jedną z pięciu metryk [[AGQ Enhanced]] (Warstwa 5). Opiera się na dwóch wartościach z Warstwy 2:
- **A** ([[Acyclicity]]) — odsetek modułów NIE będących w cyklach: `A = 1 − (largest_scc / n_internal)`
- **largest_scc** — rozmiar największego silnie spójnego składnika, wykrywany algorytmem [[Tarjan SCC]]

### Progi klasyfikacji

| Poziom | Warunek A | Warunek largest_scc | Interpretacja | Rekomendacja |
|---|---|---|---|---|
| **NONE** | A = 1.0 | scc ≤ 1 | Brak cykli — graf jest DAG | Utrzymaj (ratchet) |
| **LOW** | A ≥ 0.95 | scc < 5% nodes | Drobne cykle (< 5% modułów) | Napraw przy okazji |
| **MEDIUM** | A ≥ 0.85 | scc = 5–15% nodes | Umiarkowane cykle | Zaplanuj naprawę |
| **HIGH** | A ≥ 0.70 | scc = 15–30% nodes | Poważne cykle, utrudnione utrzymanie | Priorytet naprawy |
| **CRITICAL** | A < 0.70 | scc > 30% nodes | Dominujący cykl — architektura zablokowana | Natychmiastowa interwencja |

### Przykłady z benchmarku i pilotów

| Repo | nodes | largest_scc | A | CycleSeverity | Kontekst |
|---|---|---|---|---|---|
| guava | 1847 | 0 | 1.000 | **NONE** | Google Guava — wzorcowa biblioteka |
| ddd-by-examples/library | 47 | 0 | 1.000 | **NONE** | DDD sample — idealna architektura |
| spring-boot | 684 | 12 | 0.982 | **LOW** | 12 klas w cyklu (< 2% nodes) |
| shopizer (before E13e) | ~400 | 17 | 0.957 | **LOW** | 17 klas w cyklu pakietowym |
| shopizer (after E13e) | ~400 | 0 | 1.000 | **NONE** | Po refaktoryzacji: cykl usunięty ✅ |
| commons-collections (before E13f) | 458 | 16 | 0.965 | **LOW** | 16 Utils w jednym pakiecie |
| commons-collections (after E13f) | 458 | 0 | 1.000 | **NONE** | Po refaktoryzacji: cykl usunięty ✅ |

### Relacja z QSE-Track

QSE-Track (Layer 2 w [[E13 Three-Layer Framework|frameworku trójwarstwowym]]) używa **largest_scc** jako jednej z trzech metryk śledzenia zmian. CycleSeverity jest pochodną tych samych danych, ale w formacie czytelnym dla człowieka.

**Kluczowe odkrycie pilotów E13e/E13f:** QSE-Track (PCA + largest_scc) reaguje natychmiastowo na usunięcie cykli (SCC 17→0, PCA 0.95→1.0), podczas gdy Layer 1 (M/A/S/C) pozostaje niewrażliwy (Δ < 0.01). CycleSeverity odzwierciedla ten sam sygnał co QSE-Track.

### Dlaczego cykle są problemem?

Cykliczne zależności łamią fundamentalną zasadę architektury oprogramowania — **Acyclic Dependencies Principle (ADP)** Martina:

> Zależności między pakietami muszą tworzyć skierowany graf acykliczny (DAG).

Konsekwencje cykli:
1. **Build order** — nie można zbudować modułu A bez B, ani B bez A
2. **Testing** — nie można testować A w izolacji od B
3. **Deployment** — nie można wydać nowej wersji A bez B
4. **Understanding** — zmiana w A wymaga zrozumienia B (i odwrotnie)

Badania [[References|Gnoyke et al. (2024)]] potwierdzają: cykliczne zależności korelują najsilniej z defektami wśród wszystkich architektonicznych smellów. W kalibracji L-BFGS-B na benchmarku Python (n=74), Acyclicity dostała wagę **0.730** — najwyższą z pięciu składowych.

### Rozkład CycleSeverity w benchmarku

Z 558 repozytoriów w Benchmark 558 (iter6):
- **NONE:** ~70% (projekty Go i Python prawie nie mają cykli)
- **LOW:** ~15%
- **MEDIUM:** ~8%
- **HIGH:** ~4%
- **CRITICAL:** ~3% (prawie wyłącznie Java — legacy enterprise)

**Per język:**
- **Go:** 97% NONE (go build wymusza brak circular imports)
- **Python:** 85% NONE (Python import system pozwala cykle, ale konwencja ich unika)
- **Java:** 45% NONE — Java ma najwyższy odsetek projektów z cyklami

## Definicja formalna

\[\text{CycleSeverity}(r) = f(A(r), \text{largest\_scc}(r))\]

gdzie \(f\) jest deterministyczną funkcją progową:

\[\text{CycleSeverity}(r) = \begin{cases}
\text{NONE} & \text{jeśli } A(r) = 1.0 \\
\text{LOW} & \text{jeśli } A(r) \geq 0.95 \\
\text{MEDIUM} & \text{jeśli } A(r) \geq 0.85 \\
\text{HIGH} & \text{jeśli } A(r) \geq 0.70 \\
\text{CRITICAL} & \text{jeśli } A(r) < 0.70
\end{cases}\]

## Ograniczenia

1. **Progi arbitralne** — 0.85, 0.70 etc. nie są kalibrowane na GT. To rozsądne inżynierskie przybliżenia.
2. **Nie rozróżnia typów cykli** — cykl między 3 pakietami (naprawialny przez Extract Interface) vs cykl wewnątrz jednego dużego pakietu (wymaga podziału pakietu) — CycleSeverity traktuje oba identycznie.
3. **Nie widzi „prawie-cykli"** — dwa pakiety z A→B i A→C→B nie tworzą SCC, ale są blisko cykliczności. CycleSeverity daje NONE.

## Zobacz też

- [[AGQ Enhanced]] — zestaw metryk rozszerzonych
- [[Acyclicity]] — składowa AGQ (binarna: DAG vs cykl)
- [[Tarjan SCC]] — algorytm wykrywania cykli (O(V+E))
- [[E13e Shopizer Pilot]] — refaktoryzacja SCC 17→0
- [[E13f Commons Collections Pilot]] — refaktoryzacja SCC 16→0
- [[ChurnRisk]] — ryzyko procesowe (używa A jako wejścia)
- [[Fingerprint]] — pokrewna klasyfikacja (7 wzorców)
