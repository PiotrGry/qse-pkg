---
type: meta
language: pl
---

# Jak czytać eksperymenty

## Prostymi słowami

Wyobraź sobie, że próbujesz sprawdzić, czy termometr naprawdę mierzy gorączkę. Mierzysz temperaturę u zdrowych i chorych osób — jeśli wyniki nie różnią się, termometr jest bezużyteczny. Dokładnie tak QSE testuje swoje metryki: porównuje wyniki dla projektów znanych jako „dobre" (POS) i „złe" (NEG), używając niezależnych ocen ekspertów.

## Szczegółowy opis

### Protokół badawczy QSE

Każdy eksperyment w QSE musi spełniać następujące zasady:

**1. Ograniczenie iteracji**
Maksymalnie 5 iteracji per eksperyment. Stop po 2 kolejnych iteracjach bez poprawy mierzonej przez partial Spearman r lub Mann-Whitney p-value. Zasada chroni przed overfittingiem na małej próbie.

**2. Zakaz modeli nieliniowych**
Żadnych modeli nieliniowych (drzewa, sieci neuronowe, SVM). Wszystkie formuły AGQ są liniowymi kombinacjami metryk. Powód: przy n=14 jakikolwiek model nieliniowy może dopasować się do szumu.

**3. Zakaz brute-force**
Przestrzeń wag nie jest przeszukiwana siłowo. Grid search był stosowany tylko z BLT jako GT — i dał błędne wyniki (patrz [[W1 BLT Correlation]]). Wagi kalibruje się przez PCA lub racjonalne uzasadnienie.

**4. Każda zmiana musi przeżyć falsyfikację**
Nowa metryka lub waga musi pokazać poprawę na partial Spearman (kontrola rozmiaru) i Mann-Whitney (separacja kategorii). Poprawa tylko na jednym teście jest niewystarczająca.

**5. Ustalona hierarchia GT**
Wyłączny GT: panel ekspertów z progiem σ<2.0. BLT (Bug Lead Time) jest oficjalnie obalony jako GT — nie wolno go ponownie używać do kalibracji (zob. [[W1 BLT Correlation]]).

### Jak interpretować wyniki

```
partial r > 0.60, p < 0.05   →  silny sygnał, potwierdzony
partial r 0.40–0.60, p < 0.05 →  umiarkowany sygnał
partial r < 0.40 lub p > 0.05  →  sygnał słaby / brak sygnału (ns)
```

**Kontrola rozmiaru (partial Spearman):** Surowa korelacja AGQ z panelem (r=+0.661*) jest częściowo artefaktem size confoundu — duże repo mają inne statystyki niż małe. Partial Spearman usuwa ten efekt, kontrolując zmienną `nodes`. Tylko wyniki po partial Spearman są miarodajne.

**Mann-Whitney U:** Test nieparametryczny sprawdzający czy rozkłady POS i NEG są statystycznie różne. Używamy go gdy n jest małe i nie zakładamy normalności rozkładu.

### Typowe pułapki w eksperymentach QSE

| Pułapka | Opis | Jak uniknąć |
|---|---|---|
| Mała próba | n<10 — statystyki losowe | Min. n=13 pewnych ocen panelowych |
| Size confound | Duże repo mają inny ratio niż małe | Zawsze partial Spearman z kontrolą nodes |
| Multi-module repos | QSE scala submoduły w jeden graf | Flaga `issues=multi_module`, wykluczenie |
| BLT jako GT | r(AGQ→BLT)=−0.125 ns — zepsuty | Używaj wyłącznie panelu ekspertów |
| DDD bias | 4/4 POS to DDD — test niesprawiedliwy | Dodaj non-DDD POS (hexagonal, CQRS, layered) |
| Size outliers | OsmAnd 6831 vs library 256 — 25× różnicy | Wykluczaj gdy nodes > 3× mediana |

### Struktura każdego dokumentu eksperymentu

Każda strona eksperymentu ma:
1. **Prostymi słowami** — intuicja w 2–3 zdaniach
2. **Hipoteza** — co dokładnie sprawdzano
3. **Dane wejściowe** — dataset, n, GT
4. **Wyniki** — konkretne liczby (r, p, Δ pos–neg)
5. **Interpretacja** — co wynik oznacza i dlaczego
6. **Następny krok** — co wynika z eksperymentu
7. **Powiązane hipotezy** — [[wikilinki]]

## Definicja formalna

### Testy statystyczne stosowane w QSE

**Spearman ρ (korelacja rangowa):**
Mierzy monotoniczny związek między metryką a oceną panelu. Stosujemy zamiast Pearsona bo dane nie są normalne.

**Partial Spearman:**
Korelacja Spearmana po usunięciu wspólnego efektu zmiennej kontrolnej (nodes). Formalnie: ρ(X, Y | Z) obliczane przez regresję reszt.

**Mann-Whitney U:**
Test nieparametryczny H₀: rozkłady POS i NEG są identyczne. p < 0.05 oznacza istotną separację kategorii.

**Progi istotności stosowane w QSE:**
- p < 0.001: `***`
- p < 0.01: `**`
- p < 0.05: `*`
- p ≥ 0.05: `ns` (nieistotne statystycznie)

## Zobacz też

- [[Experiments Index]] — lista wszystkich eksperymentów
- [[W1 BLT Correlation]] — dlaczego BLT jest złym GT
- [[Ground Truth]] — jak działa panel ekspertów
- [[AGQv2]] — formuła po E2
