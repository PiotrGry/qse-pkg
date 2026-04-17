---
type: canon
language: pl
---

# Niezmienniki projektu QSE

## Prostymi słowami

Niezmienniki to reguły, których nie można złamać bez fundamentalnego naruszenia założeń projektu. To nie są „sugestie" ani „dobre praktyki" — to granice metodologiczne, które gwarantują że wyniki badań są porównywalne, nie sfabrykowane i możliwe do falsyfikacji.

---

## Szczegółowy opis

### Lista niezmienników

#### N1: AGQ v1 jest nienaruszalny

Wersja AGQ v1 (`0.35·M + 0.25·A + 0.20·S + 0.20·C`) nigdy nie jest modyfikowana. Służy jako historyczna referencja — pozwala sprawdzić jak wyglądały wyniki przed każdą zmianą formuły.

**Dlaczego:** Bez stabilnej referencji nie można mierzyć postępu. Zmiana v1 retro-aktywnie zmienia sens porównań historycznych.

#### N2: Formuły per-język nie mogą być stosowane między językami

AGQ v3c Python (z flat_score, waga 0.35) nie może być używany do oceny repozytoriów Java. AGQ v3c Java (równe wagi 0.20) nie może być używany do oceny repozytoriów Python.

**Dlaczego:** Language bias jest empirycznie udowodniony. Go ma strukturalnie cohesion=1.0 z przyczyn językowych, Java ma strukturalnie niższe cohesion. Stosowanie formuły cross-language daje wyniki bez sensu fizycznego. AGQ-z (z-score per język) jest właściwym narzędziem do porównań cross-language.

#### N3: Ground Truth pochodzi od panelu ekspertów, nie od metryki BLT

BLT (Bug-churn-based Label) to automatyczna etykieta oparta na historii bugów i churnu kodu — może być używana jako proxy, ale **nie zastępuje Ground Truth**. GT musi pochodzić od oceny eksperckiej (panel 4 recenzentów, skala 1–10, σ≤2.0).

**Dlaczego:** BLT jest metryka procesowa, nie architektoniczna. Projekt może mieć wiele bugów z innych powodów (słaba dokumentacja, zła specyfikacja). Używanie BLT jako GT oznaczałoby, że weryfikujemy AGQ przez korelację z inną niedoskonałą proxy — to nie jest walidacja.

#### N4: Zmiany do formuły muszą przetrwać test falsyfikacji

Każda propozycja zmiany formuły AGQ musi być testowana pod kątem:
- czy nie tautologicznie zakłada własny wynik?
- czy działa na nowych danych, nie tylko na zbiorze kalibracyjnym?
- czy nie overfittuje (LOO-CV jako standard)?

**Dlaczego:** Bez tego warunku można by zaprojektować formułę która „działa" tylko dlatego, że została skalibrowana na tym samym zbiorze na którym jest testowana. To by było badanie bez wartości naukowej.

#### N5: Brak modeli nieliniowych w AGQ Core

AGQ Core jest liniową kombinacją czterech (lub pięciu) składowych. Nie używamy sieci neuronowych, random forests ani innych modeli nieliniowych do obliczania AGQ.

**Dlaczego (trzy powody):**
1. **Interpretowalność:** Każda składowa AGQ ma jednoznaczne znaczenie architektoniczne. Model nieliniowy traci tę właściwość.
2. **Deterministyczność:** Ten sam kod musi zawsze dawać ten sam wynik — modele stochastyczne (np. z dropout) tego nie gwarantują.
3. **Porównywalność:** Liniowość gwarantuje że poprawa jednej składowej zawsze poprawia AGQ (przy innych równych). W modelu nieliniowym interakcje między zmiennymi mogą dawać kontraintuicyjne wyniki.

#### N6: Brak brute-force optymalizacji wag

Wagi AGQ są kalibrowane przez ograniczoną optymalizację (L-BFGS-B z ograniczeniami na sumę wag = 1, każda waga ≥ 0) z cross-validacją LOO-CV. **Nie** są szukane przez grid search, random search ani ewolucję.

**Dlaczego:** Brute-force na małej próbie (n=74) miałby wysokie ryzyko overfittingu. L-BFGS-B z ograniczeniami i LOO-CV jest metodą statystycznie uzasadnioną i powtarzalną.

#### N7: Maksymalnie 5 iteracji eksperymentu per sesja

Protokół eksperymentalny (Java-S experiment) wymaga zatrzymania po maksymalnie 5 iteracjach lub 2 kolejnych iteracjach bez poprawy — cokolwiek wystąpi pierwsze.

**Dlaczego:** Nieograniczone iterowanie jest formą brute-force. Ograniczenie chroni przed adaptowaniem formuły do konkretnych wyników bez uzasadnienia teoretycznego.

---

## Definicja formalna — protokół eksperymentalny Java-S

```
PROTOKÓŁ JAVA-S (z sesji badawczych)

Warunki STOP:
  1. Po maksymalnie 5 iteracjach
  2. Po 2 kolejnych iteracjach bez poprawy AUC lub p-value
  3. Natychmiast jeśli wykryto:
     - overfit (poprawa na GT, pogorszenie na Jolak)
     - tautologię (metryk używana do budowania GT i testowania AGQ)
     - niestabilność (zmiana wag nie daje spójnych wyników)

Ograniczenia formalne:
  - Brak modeli nieliniowych (N5)
  - Brak brute-force (N6)
  - Brak nowych metryk bez jawnego uzasadnienia architektonicznego
  - Każda zmiana musi być testowana na Jolak (niezależny zbiór)
```

---

## Reguły implementacyjne (nie-metodologiczne)

Oprócz metodologicznych niezmienników, projekt ma reguły implementacyjne:

| Reguła | Uzasadnienie |
|---|---|
| AGQ obliczane tylko z wewnętrznych węzłów | Zewnętrzne biblioteki nie są problemem architektonicznym projektu |
| Acyclicity używa **największego** SCC, nie średniej | Jeden „boski cykl" 100-węzłowy jest katastrofą — nie powinien rozcieńczać się w dużym projekcie |
| Normalizacja Modularity przez 0.75 | Empiryczny sufit dla projektów OSS — nie przez 1.0 (nieosiągalne) |
| flat_score tylko dla Pythona | Hierarchia namespace nie ma sensu dla Javy (granulacja pakietów) |

---

## Zobacz też
[[QSE Canon]] · [[Ground Truth]] · [[Architecture]] · [[Current Priorities]] · [[AGQ Formulas]]
