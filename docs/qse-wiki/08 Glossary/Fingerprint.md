---
type: glossary
language: pl
---

# Fingerprint

## Prostymi słowami

Fingerprint to etykieta opisująca „wzorzec architektoniczny" projektu — jedna z siedmiu kategorii. Zamiast jednej liczby AGQ, Fingerprint mówi *jaki typ* architektury ma projekt: czy jest czysty jak podręcznik (CLEAN), warstwowy (LAYERED), płaski bez struktury (FLAT), czy poplątany z cyklami (TANGLED). To jak grupa krwi dla architektury — mówi więcej niż sama liczba ciśnienia.

## Szczegółowy opis

Fingerprint jest jedną z pięciu metryk [[AGQ Enhanced]] (Warstwa 5). Obliczany na podstawie surowych składowych AGQ (M, A, S, C, CD) — bez dodatkowego skanowania. Algorytm jest deterministyczny (rule-based, nie ML).

### Siedem wzorców architektonicznych

| Wzorzec | Warunek (uproszczony) | Charakterystyka | Typowe projekty |
|---|---|---|---|
| **CLEAN** | A≈1.0, C>0.5, S>0.3, M>0.6 | Brak cykli, wysoka spójność, wyraźne warstwy | Małe biblioteki Go, DDD samples |
| **LAYERED** | A>0.9, S>0.2, C>0.3 | Hierarchia warstw, drobne cykle | Django, Flask, Spring Boot |
| **LOW_COHESION** | C<0.30 | Klasy robią za dużo — „god classes" | Duże monolity Java, enterprise CRUDs |
| **MODERATE** | Żaden ekstremalny wzorzec | Brak wyraźnych patologii ani cnót | Projekty mid-range |
| **FLAT** | S<0.10 | Brak hierarchii — wszystko na jednym poziomie | youtube-dl, flat Python scripts |
| **TANGLED** | A<0.85 i C<0.30 | Cykle + niska spójność — najgorszy wzorzec | Legacy monolity z circular imports |
| **CYCLIC** | A<0.85, C≥0.30 | Cykle bez innych problemów — do naprawy | Projekty z circular package deps |

### Rozkład w Benchmarku 558

```
LAYERED       ████████████████████  68 (28%)
CLEAN         ███████████████       51 (21%)
LOW_COHESION  █████████████         44 (18%)
MODERATE      ████████████          40 (16%)
FLAT          ███████               23 (10%)
TANGLED       ███                    9  (4%)
CYCLIC        ██                     5  (2%)
(reszta: nodes=0)                   ~58 (brak danych)
```

**Obserwacja per język:**
- **Go:** zdominowane przez CLEAN (47/51) — Go wymusza brak cykli i prostą strukturę pakietów
- **Python:** zdominowane przez LAYERED (57/68) — Python ma naturalne warstwy (django, flask)
- **Java:** dominują LOW_COHESION (40/44) i TANGLED (9/9) — klasy Java są historycznie "grube"
- **TypeScript:** za mało danych (n=8, 73% nodes=0 — problem parsera)

### Szczegółowy algorytm klasyfikacji

Fingerprint jest obliczany kaskadowo — sprawdzane są warunki od najpoważniejszych patologii:

```python
def classify_fingerprint(M, A, S, C, CD):
    # 1. Cykle = najpoważniejszy problem
    if A < 0.85:
        if C < 0.30:
            return "TANGLED"  # cykle + niska spójność
        return "CYCLIC"       # cykle ale spójne klasy
    
    # 2. Niska spójność (god classes)
    if C < 0.30:
        return "LOW_COHESION"
    
    # 3. Flat architecture (brak hierarchii)
    if S < 0.10:
        return "FLAT"
    
    # 4. Clean (wszystko powyżej mediany)
    if A >= 0.98 and C >= 0.50 and S >= 0.30 and M >= 0.60:
        return "CLEAN"
    
    # 5. Layered (dobra hierarchia, drobne problemy)
    if A >= 0.90 and S >= 0.20 and C >= 0.30:
        return "LAYERED"
    
    # 6. Reszta
    return "MODERATE"
```

### Przykłady z GT i pilotów

| Repo | Panel | AGQ | Fingerprint | Dlaczego ten wzorzec |
|---|---|---|---|---|
| ddd-by-examples/library | 8.50 | 0.681 | CLEAN | A=1.0, C=0.72, S=0.42, M=0.71 |
| spring-boot | 7.25 | 0.574 | LAYERED | A=0.982, S=0.31, C=0.38 |
| mall (newbee-mall) | 2.50 | 0.493 | LOW_COHESION | C=0.29 — klasy CRUD z wieloma metodami |
| youtube-dl | 2.25 | 0.831 | FLAT | S=0.02, 895/895 modułów w depth≤2 |
| shopizer (before E13e) | 4.00 | 0.551 | CYCLIC | A=0.95, SCC=17, ale C=0.41 OK |
| shopizer (after E13e) | 4.80 | 0.553 | LAYERED | A=1.0, SCC=0 — naprawione cykle |

**Przypadek youtube-dl jest szczególnie instruktywny:** AGQ=0.831 (wysoki!) ale Fingerprint=FLAT. Surowe AGQ wprowadza w błąd — youtube-dl to płaski spaghetti z 895 modułami na jednym poziomie. Fingerprint natychmiast to ujawnia.

### Ograniczenia

1. **Progi są arbitralne** — oparte na analizie rozkładów benchmarku, nie na Ground Truth. Próg C<0.30 dla LOW_COHESION mógłby być 0.25 lub 0.35 — nie mamy kalibracji na GT.
2. **Kaskadowość ukrywa problemy wtórne** — projekt z A<0.85 i C<0.30 dostaje TANGLED, ale nie widać że ma też S<0.10 (FLAT). Fingerprint jest jednoetykietowy.
3. **Nie ma ARCHIPELAGO** — efekt archipelagu (odkryty w Pilot-2) nie jest wykrywalny przez Fingerprint. Potrzebny jest osobny detektor ([[Pilot Multi-Repo Scan|Pilot-2]]).

## Definicja formalna

\[\text{Fingerprint}(r) \in \{\text{CLEAN}, \text{LAYERED}, \text{LOW\_COHESION}, \text{MODERATE}, \text{FLAT}, \text{TANGLED}, \text{CYCLIC}\}\]

Funkcja klasyfikująca jest deterministyczna i zależy wyłącznie od wartości M, A, S, C, CD repozytorium \(r\). Kolejność sprawdzania warunków jest ustalona (priorytet: cykle > spójność > płaskość > czystość > warstwowość).

## Zobacz też

- [[AGQ Enhanced]] — zestaw metryk rozszerzonych (Warstwa 5)
- [[CycleSeverity]] — bardziej granularna klasyfikacja cykli
- [[Architecture]] — architektura systemu QSE
- [[Benchmark 558]] — dane benchmarkowe i rozkłady
- [[Repository Types]] — typologia repozytoriów (CRUD, DDD, library, framework)
- [[Pilot Multi-Repo Scan]] — odkrycie efektu archipelagu (brak w Fingerprint)
- [[E13g newbee-mall Pilot]] — przykład przejścia LOW_COHESION → LAYERED
