---
type: metric
language: pl
---

# DMS Instability (Distance from Main Sequence)

## Prostymi słowami

DMS (Distance from Main Sequence) to metryka Roberta Martina (2003) mierząca, czy każdy pakiet "zachowuje się właściwie" dla swojej roli. Teoria mówi: stabilne pakiety (od których dużo zależy) powinny być abstrakcyjne (interfejsy, klasy abstrakcyjne). Niestabilne (zależące od wielu) mogą być konkretne. "Main Sequence" to linia idealna. DMS = odległość od tej linii.

## Szczegółowy opis

### Instability (I) — podstawowa metryka

\[I(p) = \frac{C_e}{C_a + C_e}\]

- \(C_a\) (afferent): liczba pakietów importujących \(p\) — fan-in
- \(C_e\) (efferent): liczba pakietów importowanych przez \(p\) — fan-out

\(I = 0\): całkowita stabilność — wiele zależy od \(p\), \(p\) nie zależy od niczego.
\(I = 1\): całkowita niestabilność — \(p\) zależy od wielu, nikt nie zależy od \(p\).

### Abstractness (A)

\[A(p) = \frac{n_{\text{abstract}}}{n_{\text{total}}}\]

Gdzie \(n_{\text{abstract}}\) = liczba klas abstrakcyjnych/interfejsów w pakiecie.

### Distance from Main Sequence (D)

\[D(p) = |A(p) + I(p) - 1|\]

"Main Sequence" to linia \(A + I = 1\). Punkt na tej linii: stabilny pakiet jest abstrakcyjny (\(A=1, I=0\)), niestabilny jest konkretny (\(A=0, I=1\)).

Dobra architektura: \(D \approx 0\) dla każdego pakietu.

### Wersja QSE: bez A (wariancja I)

**Problem z oryginalnym DMS:** Abstractness \(A\) jest niedostępna w Pythonie (duck typing — prawie wszystkie klasy mają A=0). Nawet w Javie wiele projektów ma A=0 dla klas domenowych.

**Rozwiązanie QSE:** zamiast \(D = |A + I - 1|\), używa **wariancji** samego \(I\):

\[\text{Stability}_{\text{QSE}} = \min\!\left(1,\ \frac{\text{Var}(I(p_1), \ldots, I(p_k))}{0.25}\right)\]

Uzasadnienie: wysoka wariancja \(I\) oznacza że pakiety mają różne role architektoniczne (jądro vs obrzeże). To jest operacyjna definicja "wyraźnej hierarchii".

### Python: wymaga detekcji abstrakcyjności

Dla Javy QSE używa detekcji:
- `abstract class`
- `interface`

Dla Pythona:
- `ABC` (Abstract Base Class)
- `Protocol`
- `@abstractmethod`

Bez tej detekcji Stability w Pythonie jest niemonotoniczna — klasy abstrakcyjne są penalizowane jako "stabilny konkret".

### Przykłady Instability per pakiet (dddsample Java)

| Pakiet | I | Rola |
|---|---|---|
| domain/cargo | 0.42 | Rdzeń domenowy — bogaty model |
| domain/location | 0.38 | Rdzeń domenowy |
| application/booking | 0.71 | Warstwa aplikacyjna |
| interfaces | 0.89 | Obrzeże — API zewnętrzne |

Wariancja I ≈ 0.04 → wysoki Stability.

### Paradoks DDD (kluczowy wniosek E1)

DDD dobre repo (dddsample, Panel=8.25): `domain_instability = 0.464` — *wyższe* niż w złym repo:

| Repo | Panel | Domain I |
|---|---|---|
| dddsample (DDD) | 8.25 | 0.464 |
| mall (CRUD anemic) | 2.00 | 0.024 |

Rich domain w DDD ma wiele wewnętrznych interakcji (fan-out do klas domenowych) → wyższe I. CRUD POJO to "sink" → I≈0. Metryka Martina z założoną hierarchią (domain I < app I) nie działa dla DDD.

## Definicja formalna

**Instability:**
\[I(p) = \frac{C_e(p)}{C_a(p) + C_e(p)}, \quad I \in [0, 1]\]

Gdzie \(C_a, C_e\) są liczone per pary pakietów (zależności między pakietami, nie pliki).

**Stability QSE** (bez A):
\[S = \min\!\left(1,\ \frac{\text{Var}(I(p_1), \ldots, I(p_k))}{0.25}\right)\]

**Oryginalne DMS Martina** (dla porównania):
\[D(p) = |A(p) + I(p) - 1|, \quad D \in [0, 1]\]

**Stability (oryginalna):**
\[\bar{D} = \frac{1}{k} \sum_{p} D(p)\]

QSE odchodzi od \(\bar{D}\) na rzecz \(\text{Var}(I)\), co empirycznie lepiej koreluje z panelem (brak potrzeby A).

## Zobacz też

- [[Stability]] — metryka obliczana na DMS Instability
- [[Package]] — jednostka dla której obliczane jest I
- [[Hierarchy]] — hierarchia jako wynik zróżnicowania I
- [[E1 Stability Hierarchy]] — eksperyment obalający założenia o I
