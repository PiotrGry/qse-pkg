---
type: glossary
language: pl
---

# Typ 1 — Flat Spaghetti

## Prostymi słowami

Flat Spaghetti to projekt, który wygląda jak miska makaronu: wszystko w jednym miejscu, wszystko połączone ze wszystkim, zero hierarchii. Wyobraź sobie sałatkę bez misek: kapusta, makaron, sos i ryba wymieszane razem w jednej kupie. Nie wiadomo, gdzie co szukać, co od czego zależy, ani jak cokolwiek zmienić bez dotykania wszystkiego innego.

## Szczegółowy opis

**Typ 1 — Flat Spaghetti** to anty-wzorzec architektoniczny charakteryzujący się:

1. **Płaską strukturą** — mało lub brak hierarchii modułów/pakietów
2. **Gęstymi zależnościami** — duży coupling density
3. **Niską spójnością** — klasy robią wiele niezwiązanych rzeczy
4. **Brakiem warstw** — kod UI, logika biznesowa i baza danych wymieszane

### Profil metryk AGQ

| Metryka | Wartość typowa | Kierunek |
|---|---|---|
| Modularity (M) | Niska (0.2–0.4) | ↓ |
| Acyclicity (A) | Może być wysoka (1.0) | Zróżnicowana |
| Stability (S) | Niska (0.0–0.2) | ↓↓ |
| Cohesion (C) | Niska (0.1–0.3) | ↓↓ |
| Coupling Density (CD) | Niska (gęste) | ↓ |
| **AGQ** | **< 0.55** | **↓** |
| Fingerprint | **FLAT** lub **LOW_COHESION** | |

### Przykłady z benchmarku

Z badania spaghetti vs mainstream:

| Repozytorium | Węzły | AGQ | Smells/KLOC | Uwagi |
|---|---:|---:|---:|---|
| python_bad_project | 46 | 0.731 | 23.67 | Mylący wysoki AGQ — mała struktura |
| python_code_disasters | 33 | 0.707 | 10.93 | Brak separacji modułów |
| nickineering_spaghetti | 41 | 0.671 | 19.54 | Gęste zależności |
| oddup_investors_spaghetti | 7 | 0.682 | 95.89 | Ekstremalnie wysoki smells |

**Uwaga:** Małe projekty spaghetti mogą mieć zaskakująco wysoki AGQ — bo mała struktura = brak grafowych problemów (mało węzłów = mało cykli = wysoka Acyclicity). Dlatego potrzebne są miary jak smells/KLOC do pełnej oceny.

### Różnica od Typ 2 Legacy Monolith

| Właściwość | Typ 1 Flat Spaghetti | [[Type 2 Legacy Monolith\|Typ 2 Legacy Monolith]] |
|---|---|---|
| Rozmiar | Mały-średni | Duży (historyczny) |
| Cykle | Mogą być, mogą nie być | Często obecne |
| Wiek projektu | Nowy lub młody | Stary, legacy |
| Przyczyna | Brak planowania | Erozja architektoniczna w czasie |
| Acyclicity | Różna | Niższa |
| Główny problem | Brak struktury od początku | Narosła kompleksowość |

### Jak QSE wykrywa Flat Spaghetti

Fingerprint FLAT lub LOW_COHESION przypisywany gdy:
- S (Stability) < 0.15 — brak hierarchii warstw
- C (Cohesion) < 0.25 — klasy wielofunkcyjne
- M (Modularity) < 0.40 — brak wyraźnych grup modułów

Diagnoza w wynikach QSE:
```
AGQ = 0.421  [FLAT]  z=-2.3 (2%ile Python)
  Modularity=0.22  Acyclicity=1.00  Stability=0.08  Cohesion=0.18
  → Projekt w dolnych 2% repozytoriów Python
  → Wzorzec FLAT: brak hierarchii warstw, niespójne klasy
  → Zalecenie: refaktoryzacja struktury pakietów
```

### Rekomendacje dla Flat Spaghetti

1. **Wprowadź warstwy** — wydziel przynajmniej 3 warstwy (prezentacja, logika, dane)
2. **Wydziel moduły** — pogrupuj klasy według domeny, nie według technikaliów
3. **Rozbij duże klasy** — każda klasa z LCOM4 > 1 jest kandydatem do podziału
4. **Zacznij od forbidden edges** — zadeklaruj, czego nie może importować warstwa prezentacji

## Definicja formalna

Repozytorium r klasyfikowane jako Flat Spaghetti gdy:

$$F(r) \in \{\text{FLAT}, \text{LOW\_COHESION}\} \text{ i } \text{AGQ}(r) < 0.55$$

Zgodnie z Fingerprint classification z [[Repository Types|Typy repozytoriów]].

## Zobacz też

- [[AGQ|AGQ]] — metryka główna
- [[Repository Types|Typy repozytoriów]] — klasyfikacja Fingerprint
- [[Type 2 Legacy Monolith|Typ 2 Legacy Monolith]] — pokrewny anty-wzorzec
- [[Layer|Warstwa]] — co brakuje w Flat Spaghetti
- [[LCOM4|LCOM4]] — miara niskiej spójności
- [[DDD|DDD]] — alternatywa — bogata struktura domenowa
