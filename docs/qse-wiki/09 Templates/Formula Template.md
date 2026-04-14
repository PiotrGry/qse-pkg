---
type: template
language: pl
---

# Szablon formuły AGQ

> Skopiuj ten plik dla każdej nowej wersji lub wariantu formuły AGQ. Wypełnij wszystkie sekcje.

---

# AGQ [wersja] — [nazwa/opis]

## Prostymi słowami

(Analogia: czym różni się ta formuła od poprzedniej? Co poprawia, co wprowadza nowego? Zrozumiałe dla osoby bez wiedzy o PCA i optymalizacji.)

## Szczegółowy opis

### Wzór
```
AGQ_[wersja] = [waga1]·M + [waga2]·A + [waga3]·S + [waga4]·C + [waga5]·CD [+ inne]
```

Uzasadnienie wag:
| Komponent | Waga | Dlaczego ta waga |
|---|---:|---|
| Modularity (M) | 0.?? | — |
| Acyclicity (A) | 0.?? | — |
| Stability (S) | 0.?? | — |
| Cohesion (C) | 0.?? | — |
| Coupling Density (CD) | 0.?? | — |

### Metoda kalibracji wag
(PCA / LOO-CV / optymalizacja numeryczna / heurystyka / równe wagi)

### Porównanie z poprzednią wersją
| Parametr | Poprzednia | Ta wersja | Zmiana |
|---|---|---|---|
| Java GT MW p | — | — | — |
| Spearman ρ | — | — | — |
| Partial r | — | — | — |
| Spread | — | — | — |

## Wyniki walidacji

### Java GT (n=??)
| Statystyka | Wartość |
|---|---|
| POS mean AGQ | — |
| NEG mean AGQ | — |
| Gap | — |
| MW p-value | — |
| Spearman ρ | — |
| Partial r | — |
| AUC-ROC | — |

### Python GT (n=??) [jeśli dostępne]
| Statystyka | Wartość |
|---|---|
| MW p-value | — |
| Spearman ρ | — |

## Definicja formalna

$$\text{AGQ}_{[wersja]} = \text{[wzór LaTeX]}$$

(Opis każdego składnika, zakres wartości, normalizacja)

## Zobacz też

- [[AGQ Formula|Indeks formuł AGQ]]
- [[Java GT Dataset]]
- [[Experiments Index|Eksperymenty kalibrujące]]
