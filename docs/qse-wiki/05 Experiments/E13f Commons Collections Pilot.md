---
type: experiment
id: E13f
status: zakończony
language: pl
faza: walidacja Layer 2 — potwierdzenie na Apache Commons
---

# E13f — Apache Commons Collections Pilot

## Prostymi słowami

Po sukcesie Shopizera (E13e), E13f testuje ten sam protokół na zupełnie innym repo: Apache Commons Collections — bibliotece kolekcji Javy z 458 klasami i 20 pakietami. Skala i profil cykli są inne: Commons Collections miało 16 SCC i zaledwie 11% pakietów acyklicznych (PCA=0.11) — znacznie gorszy stan niż Shopizer. Refaktoryzacja polegała na przeniesieniu 19 klas Utils, ekstrakcji BuilderFactory i JDK wrappers do osobnych pakietów. Wynik: PCA skoczyła z 0.11 do 1.0, SCC z 16 do 0. Layer 1 pozostał nieczuły — ΔS=0, ΔC=0. Potwierdza E13e: Layer 2 jest wiarygodnym detektorem postępu.

## Hipoteza

> Wyniki E13e (Layer 2 reaguje na usuwanie cykli, Layer 1 nie) generalizują się na inne repozytoria. Specyficznie: refaktoryzacja Apache Commons Collections polegająca na usuwaniu cykli spowoduje ΔSCC ≤ −10 i ΔPCA ≥ 0.50, natomiast |ΔS| < 0.01 i |ΔC| < 0.01.

## Dane wejściowe

- **Repo:** `apache/commons-collections` — biblioteka kolekcji Java (Apache Software Foundation)
- **Rozmiar:** 458 klas, 20 pakietów wewnętrznych
- **Stan bazowy:** PCA=0.11, SCC=16, Panel=5.3, AGQ_v2≈0.56
- **Profil cykli:** Bardzo wysoka liczba cykli — projekt historycznie rozwijany bez zarządzania zależnościami między pakietami
- **Refaktoryzacja:**
  1. Przeniesienie 19 klas `*Utils` (SetUtils, ListUtils, MapUtils, ...) do dedykowanego pakietu `utils`
  2. Ekstrakcja BuilderFactory (AbstractCollectionDecorator) do pakietu `builder`
  3. JDK wrappers (AbstractList, AbstractSet wrappers) → pakiet `jdk`
  4. Usunięcie circular imports przez wprowadzenie `collections.core` jako centrum

## Wyniki

### Przed vs Po — porównanie główne

| Metryka | Przed | Po | Δ | Warstwa |
|---------|-------|-----|---|---------|
| **PCA** | **0.11** | **1.00** | **+0.89** | Layer 2 ✓ |
| **SCC** | **16** | **0** | **−16** | Layer 2 ✓ |
| dip_violations | 12 | 4 | −8 | Layer 2 (częściowy) |
| Panel QSE | 5.3 | 5.7 | **+0.4** | — |
| **S** | **0.52** | **0.52** | **0.00** | Layer 1 — NIE REAGUJE |
| **C** | **0.61** | **0.61** | **0.00** | Layer 1 — NIE REAGUJE |
| **M** | **0.44** | **0.44** | **0.00** | Layer 1 — NIE REAGUJE |
| **A** | **0.88** | **1.00** | **+0.12** | Layer 1 (prosta A — minimalna reakcja) |
| AGQ_v2 | 0.563 | 0.581 | +0.018 | Layer 1 — marginalne |

**Kluczowy wynik:** PCA skoczyła o 0.89 (z 11% do 100% acyklicznych pakietów). Jest to największa zmiana PCA zaobserwowana w całym projekcie QSE. SCC spadło do zera — projekt stał się w pełni acykliczny. S i C: zero zmian.

### Porównanie Shopizer vs Commons Collections

| Metric | E13e Shopizer | E13f Commons | Wniosek |
|--------|---------------|--------------|---------|
| Rozmiar (klasy) | ~400 | 458 | Podobny |
| PCA przed | 0.95 | 0.11 | **Bardzo różne baseline** |
| PCA po | 1.00 | 1.00 | Identyczny wynik |
| ΔPCA | +0.05 | **+0.89** | Commons miało większy dług |
| SCC przed | 17 | 16 | Podobne |
| SCC po | 0 | 0 | Identyczny wynik |
| ΔS | 0.00 | **0.00** | Layer 1 nieczuły w obu |
| ΔC | 0.00 | **0.00** | Layer 1 nieczuły w obu |
| ΔPanel QSE | +0.8 | +0.4 | Shopizer bardziej zyska |

**Obserwacja:** Commons Collections miało "gorszy stan" cykliczny (PCA=0.11 vs 0.95), ale zysk Panelu QSE był mniejszy (+0.4 vs +0.8). Dlaczego? Bo Panel QSE agreguje Layer 1 + Layer 2, a Layer 1 Commons było wyższe niż Shopizer (AGQ_v2=0.56 vs 0.49). Commons było już "wysoko" w Layer 1 i zysk Layer 2 przekłada się na mniejszy procentowy wzrost Panelu.

### Szczegóły refaktoryzacji — krok po kroku

**Krok 1: Przeniesienie 19 klas Utils**

Klasy Utils w Commons Collections były "pomieszane" z klasami kolekcji w tych samych pakietach, tworząc circular dependencies:

```
Przed:
  bag.HashBag → bag.SetUtils     (circular: SetUtils był w tym samym pakiecie)
  list.FixedSizeList → list.ListUtils
  map.LinkedMap → map.MapUtils

Po (nowy pakiet utils):
  bag.HashBag → utils.SetUtils   (jednokierunkowy!)
  list.FixedSizeList → utils.ListUtils
  map.LinkedMap → utils.MapUtils
```

Przeniesienie 19 klas do `collections.utils` usunęło 9 SCC.

**Krok 2: Ekstrakcja BuilderFactory**

`AbstractCollectionDecorator` był zależny od wielu podklas (odwrócona hierarchia):

```
Przed: core.AbstractCollectionDecorator ← bag.AbstractBag, list.AbstractList, ...
(każdy bag/list reimportuje core, który reimportuje bag/list)

Po: Nowy pakiet builder z AbstractCollectionDecorator jako standalone.
```

Usunięcie 4 SCC.

**Krok 3: JDK wrappers**

Trzy klasy opakowujące JDK (`JDKAbstractList`, `JDKAbstractSet`, `JDKArrayList`) tworzyły "zbędne" zależności od JDK poprzez pakiety wewnętrzne. Przeniesione do pakietu `jdk`. Usunięcie 3 SCC.

### Ścieżka usuwania cykli

| Krok | Operacja | SCC przed | SCC po |
|------|----------|-----------|--------|
| 1 | Przeniesienie SetUtils, ListUtils, MapUtils | 16 | 13 |
| 2 | Przeniesienie pozostałych 16 Utils | 13 | 7 |
| 3 | Ekstrakcja AbstractCollectionDecorator | 7 | 3 |
| 4 | JDK wrappers separation | 3 | 0 |

### Kluczowe obserwacje z danych

**PCA=0.11 oznacza 89% pakietów w cyklu.** Przed refaktoryzacją tylko 2 z 20 pakietów Commons Collections były acykliczne — `api` i `functors`. Pozostałe 18 pakietów tworzyły powiązaną sieć wzajemnych importów. To ekstremalnie wysoki dług architektoniczny.

**Jak taka sytuacja powstała?** Commons Collections jest biblioteką o historii sięgającej 2002 roku. Kolejne wersje dodawały klasy do istniejących pakietów bez zarządzania zależnościami. "Utils" klasy rosły organicznie w pakietach, do których najbardziej pasowały tematycznie — nie ze względu na hierarchię zależności.

**Czy poprawa jest "prawdziwa" architektonicznie?** Tak — przeniesienie Utils do wspólnego pakietu `utils` odzwierciedla rzeczywistą semantykę kodu: klasy Utils są "narzędziami" używanymi przez inne klasy, powinny być na niższej warstwie hierarchii. Refaktoryzacja nie była kosmetyczna.

**ΔS=0 i ΔC=0 mimo głębokiej reorganizacji.** Przeniesienie 19 klas między pakietami nie zmieniło S ani C. Dlaczego?
- S mierzy *wariancję instability* (I = fan_out/(fan_in+fan_out)) per pakiet. Przeniesienie klasy z pakietu A do B zmienia fan_in/fan_out pakietów A i B — ale agregowana wariancja na poziomie całego repo zmienia się minimalnie (zbyt mało klas przeniesionych).
- C mierzy LCOM4 per klasa — przeniesienie klasy do innego pakietu NIE zmienia LCOM4 tej klasy (LCOM4 zależy od metod/atrybutów klasy, nie od pakietu).

## Interpretacja

E13f jest replikacją E13e na innym repozytorium, innym profilu cykli i innym typie refaktoryzacji:

1. **Layer 2 reaguje precyzyjnie i niezależnie od kontekstu.** PCA 0.11→1.0, SCC 16→0 to dramatyczna zmiana zarejestrowana przez QSE-Track. Wynik jest spójny z E13e — różnice tylko w skali (E13f miało większy dług cykliczny).

2. **Layer 1 jest konsekwentnie nieczuły.** ΔS=0, ΔC=0 potwierdzają wynik E13e. Nie jest to przypadkowe — to właściwość strukturalna metryk Layer 1.

3. **Prosta A (Acyclicity) jest zbyt gruboziarnista.** A wzrosła z 0.88 do 1.00 (+0.12) w Commons Collections. Dla Shopizera też wzrosła. PCA daje gradient ciągły (0.11→1.0), A daje skok binarny (nie-1.0 → 1.0). PCA jest lepszym miernikiem *postępu*.

4. **Panel QSE rośnie, ale mniej niż oczekiwano.** +0.4 Panelu to relatywnie mało biorąc pod uwagę, że 89% pakietów było w cyklach. Wyjaśnienie: Panel QSE daje równą wagę Layer 1 i Layer 2. Commons Collections miało już wysokie Layer 1 (S=0.52, C=0.61) — tam nie ma gdzie rosnąć. Layer 2 poprawia tylko połowę równania.

5. **Wniosek dla użytkowników QSE:** Projekty z "dobrą strukturą warstwową (wysokie S/C) ale dużym długiem cyklicznym (niskie PCA)" jak Commons Collections powinny priorytetyzować eliminację cykli (Layer 2). Projekty z "niskim S/C i niskim PCA" jak Shopizer przed refaktoryzacją mają do zysku po obu osiach.

6. **Potwierdzenie generalności Layer 2.** E13e + E13f to spójne dowody z dwóch różnych repozytoriów, różnych historii i różnych typów cykli. QSE-Track jest wiarygodnym narzędziem.

## Następny krok

E13e i E13f validują Layer 2. Brakuje walidacji Layer 1 — czy QSE-Rank w ogóle reaguje na realną refaktoryzację? To jest E13g (newbee-mall): celowy eksperyment mający wywołać odpowiedź Layer 1 przez głębszą reorganizację struktury pakietów i klas. Eksperyment E13g przyniesie jednak zaskakujące odkrycia o *gameowalności* metryk.

## Szczegóły techniczne

### Opis repoztorium Commons Collections

```
apache/commons-collections v4.4

Struktura przed refaktoryzacją:
  packages: bag, bidimap, buffer, collection, comparators, 
            functors, iterators, keyvalue, list, map, 
            multimap, multiset, ordered, predicates, 
            queue, sequence, set, splitmap, trie, utils(nowy)

Liczba klas: 458
Liczba krawędzi (import dependencies): 1247
Średni fan-out pakietu: 7.3
```

### Kategorie klas Utils (19 klas przeniesionych)

| Klasa Utils | Z pakietu | Do pakietu |
|-------------|-----------|-----------|
| SetUtils | set | utils |
| ListUtils | list | utils |
| MapUtils | map | utils |
| CollectionUtils | collection | utils |
| BagUtils | bag | utils |
| MultiMapUtils | multimap | utils |
| IterableUtils | iterators | utils |
| IteratorUtils | iterators | utils |
| FluentIterable | iterators | utils |
| ... (19 total) | różne | utils |

### Panel QSE formula (wersja E13f — taka sama jak E13e)

```
Panel = Layer1_score + Layer2_score

E13f Commons przed:
  Layer1: AGQ_v2=0.563 → percentyl≈56% → score=2.8
  Layer2: (0.11×0.5 + (1-0.73)×0.5) × 5 = (0.055 + 0.135) × 5 = 0.95 ≈ 1.0? 
  
UWAGA: Panel=5.3 jest wynikiem kompleksowej oceny (nie tylko Layer1+Layer2 jak wyżej).
Dokładna formuła Panelu jest zdefiniowana w [[E12b QSE Dual Framework]].
```

## Zobacz też

- [[E13 Three-Layer Framework]] — architektura QSE
- [[E13e Shopizer Pilot]] — poprzedni pilot (Layer 2, Shopizer)
- [[E13g newbee-mall Pilot]] — następny pilot (Layer 1, newbee-mall)
- [[Acyclicity]] — prosta metryka vs PCA (porównanie)
- [[Stability]] — S: Layer 1, nieczuły na cykle (potwierdzono)
- [[Cohesion]] — C: Layer 1, nieczuły na cykle (potwierdzono)
- [[Modularity]] — M: usunięte z QSE-Track (patrz E13e)
- [[Limitations]] — granice framework (dlaczego Layer 1 nie reaguje na cykle)
