---
type: experiment
id: E13g
status: zakończony
language: pl
faza: walidacja Layer 1 + odkrycie problemów metryk
---

# E13g — newbee-mall Pilot (walidacja Layer 1)

## Prostymi słowami

Po potwierdzeniu Layer 2 (E13e, E13f), E13g zadaje pytanie fundamentalne: czy Layer 1 (M/A/S/C) w ogóle reaguje na realną refaktoryzację? Wybrano newbee-mall — mały projekt e-commerce (88 klas, Panel=2.5, label=NEG) — i przeprowadzono 6 kroków refaktoryzacji obejmujących reorganizację pakietów, podział klas, rozbicie DAO/Service oraz dodanie abstrakcji. AGQ_v2 wzrosło z 0.493 do 0.639 (NEG→POS). Layer 1 w końcu zareagował.

Ale E13g to przede wszystkim eksperyment demaskujący: **trzy z sześciu kroków refaktoryzacji były sfabrykowane** — pozornie poprawiały kod, ale były albo kosmetyczne (zmiana namespace), albo martwe (interfejsy których nikt nie implementuje), albo fikcyjne (CQRS split który nie zmienił wzorców użycia). Te sfabrykowane zmiany dominowały w wynikach metrycznych. Eksperyment odkrył trzy krytyczne luki w QSE: gameowalność S przez przemianowanie namespace, inflację M przez martwe interfejsy, oraz błędną karę LCOM4 dla interfejsów Java.

## Hipoteza

> Layer 1 (M, A, S, C) będzie reagować na głębszą refaktoryzację struktury pakietów i klas w newbee-mall, konkretnie: ΔAGQ_v2 > 0.05 i ΔPanel > 1.0 po pełnej sekwencji 6 kroków refaktoryzacji.

Hipoteza Layer 1 Separability: zmiany z kroków 1–6 będą widziane przez Layer 1, a Layer 2 (PCA, SCC) pozostanie niezmieniony (brak cykli w newbee-mall).

## Dane wejściowe

- **Repo:** `newbee-ltd/newbee-mall` — projekt e-commerce, backend Java (Spring Boot)
- **Rozmiar:** 88 klas, 12 pakietów wewnętrznych, ~1200 LOC na klasę
- **Stan bazowy:** Panel=2.5, AGQ_v2=0.493, S=0.21, C=0.29, M=0.59, A=1.0, label=NEG
- **GT status:** newbee-mall jest w GT jako NEG (Panel=2.5, σ=1.8 < 2.0, label=NEG)
- **Cel eksperymentu:** Wywołać odpowiedź Layer 1 przez głębszą reorganizację niż w E13e/f
- **Sesja:** Pełna sesja refaktoryzacji z dokumentacją każdego kroku

## Sześć kroków refaktoryzacji

### Krok 1: Package Restructuring — `ltd.newbee.mall.*` → `mall.*`

**Co zrobiono:** Zmieniono bazowy namespace z `ltd.newbee.mall` na `mall`. Zreorganizowano pakiety 2. poziomu z 3 (`controller`, `service`, `dao`) na 8 (`mall.controller`, `mall.service`, `mall.dao.read`, `mall.dao.write`, `mall.domain`, `mall.api`, `mall.config`, `mall.util`).

**Efekt na metryki:**
- S: 0.21 → 0.59 (+0.38) — **DOMINUJĄCY SKOK**
- C, M, A: bez zmian

**Ocena:** **KOSMETYCZNY.** Zmiana namespace z `ltd.newbee.mall.X` na `mall.X` nie zmienia żadnej zależności między klasami. Import statements się zmieniają, ale graf zależności pozostaje **identyczny**. S liczone jest na poziomie pakietów 2. poziomu — `ltd.newbee` miał 1 pakiet → S≈0.21 (zero wariancji, jeden blob). Po zmianie: 8 pakietów `mall.*` → S=0.59 (wyraźna hierarchia). Ale hierarchia ta nie wynika z nowych relacji — tylko z nowych *nazw*.

### Krok 2: Controller Split — PersonalController → AuthController + ProfileController

**Co zrobiono:** Klasa `PersonalController` (12 metod: 7 auth, 5 profile) rozbita na dwie klasy: `AuthController` (7 metod) + `ProfileController` (5 metod). Zgodnie z SRP (Single Responsibility Principle).

**Efekt na metryki:**
- C: +0.02 (minimalne)
- S: bez zmian
- M: bez zmian

**Ocena:** **OK — realna zmiana.** PersonalController faktycznie obsługiwał dwa różne konteksty. Podział jest architektonicznie uzasadniony. Efekt na C jest mały bo 88 klas → zmiana LCOM4 jednej klasy = mały efekt agregowany.

### Krok 3: DAO CQRS Split — 8 Mapperów → ReadMapper + WriteMapper

**Co zrobiono:** Każdy z 8 interfejsów MyBatis Mapper podzielono na dwa: `UserReadMapper` + `UserWriteMapper`, `OrderReadMapper` + `OrderWriteMapper`, itp. Uzasadnienie: CQRS (Command Query Responsibility Segregation).

**Efekt na metryki:**
- C: +0.02 (małe)
- M: +0.01 (marginalne)

**Ocena:** **FAKE — nikt nie używa ich oddzielnie.** Wszystkie serwisy wciąż importują oba mapper'y razem: `UserService` ma `@Autowired UserReadMapper readMapper` i `@Autowired UserWriteMapper writeMapper` — czyli w praktyce klasa UserService zależy od obu, jakby nic się nie zmieniło. CQRS bez zmiany wywołań po stronie serwisów to czysta formalistyka — podbijamy liczbę interfejsów bez zmiany wzorców dostępu do danych.

### Krok 4: Service CQRS Split — 3 Serwisy → QueryService + CommandService

**Co zrobiono:** Serwisy `OrderService`, `UserService`, `GoodsService` podzielone na pary `OrderQueryService`/`OrderCommandService`, itp. Uzasadnienie: CQRS na warstwie serwisowej.

**Efekt na metryki:**
- C: +0.02 (małe)

**Ocena:** **FAKE — kontrolery nadal używają starych interfejsów.** Kontrolery nadal wstrzykują `OrderService` (stary interfejs który teraz deleguje do Query i Command). Nie zmieniono `@Autowired` w kontrolerach. Podział serwisów jest głębszy w grafie obiektów, ale **z perspektywy grafu zależności pakietów** — który QSE analizuje — kontroler nadal zależy od pakietu `service` tak samo jak przed. Zmiana jest niewidoczna na poziomie pakietów.

### Krok 5: Abstraction Layer — 4 interfejsy domenowe

**Co zrobiono:** Dodano 4 interfejsy: `ApiResponse<T>`, `Pageable`, `DomainEntity`, `DataAccessObject`. Umieszczono w pakiecie `mall.domain`.

**Efekt na metryki:**
- M: +0.02 (marginalne — większa "abstrakcja modułu")
- A: +0.00 (brak cykli, niezmieniony)

**Ocena:** **FAKE — nikt nie implementuje.** Żadna klasa w projekcie nie implementuje `DomainEntity` ani `DataAccessObject`. `ApiResponse<T>` jest używany przez 2 kontrolery (zamiast poprzedniego `Result<T>`) — to jedyna realna zmiana. `Pageable` jest zduplikowaniem Spring's `Pageable` — zbyteczny. M wzrasta bo Louvain widzi nowy moduł `domain` z interfejsami jako "abstrakcyjny" węzeł — ale bez implementacji to martwy węzeł.

### Krok 6: VO/Entity Cohesion — equals/hashCode/toString na 23 klasach

**Co zrobiono:** Dodano standardowe metody `equals()`, `hashCode()`, `toString()` do 23 klas VO (Value Object) i Entity. Uzasadnienie: dobre praktyki Java, poprawa LCOM4 przez dodanie wspólnych metod na atrybutach.

**Efekt na metryki:**
- C: +0.03 (realna poprawa LCOM4)

**Ocena:** **OK — realna zmiana (ale "boilerplate").** Klasy VO bez equals/hashCode mają LCOM4 wyższe niż powinny (metody domenowe nie "łączą się" przez brak dostępu do pól przez equals). Dodanie tych metod poprawia LCOM4 bo teraz `equals` łączy wszystkie pola (atrybuty) — co łączy metody przez wspólny dostęp. Zmiana jest technicznie poprawna, choć to "boilerplate" — nie głęboka zmiana projektu.

## Wyniki

### Wyniki surowe (raportowane przez pipeline QSE)

| Metryka | Przed | Po | Δ surowy |
|---------|-------|-----|----------|
| S | 0.21 | 0.59 | **+0.38** |
| C | 0.29 | 0.36 | +0.07 |
| M | 0.59 | 0.61 | +0.02 |
| A | 1.00 | 1.00 | 0.00 |
| AGQ_v2 | 0.493 | 0.639 | **+0.146 → NEG→POS** |
| Panel QSE (formula) | 2.5 | 5.7 | **+3.2** |

### Wyniki uczciwe (po eliminacji zmian kosmetycznych)

| Metryka | Przed | Po (uczciwe) | Δ uczciwy |
|---------|-------|--------------|-----------|
| S (eliminacja k1 namespace) | 0.21 | 0.21 | **0.00** |
| C | 0.29 | 0.36 | +0.07 |
| M | 0.59 | 0.60 | +0.01 |
| AGQ_v2 (uczciwy) | 0.493 | 0.530 | +0.037 |
| Panel QSE (uczciwy) | 2.5 | 3.8–4.2 | **+0.4 (nie +3.2!)** |

**Formuła Panelu przeszacowuje delta 8×** (raportuje +3.2, uczciwa ocena to +0.4).

### Tabela krytycznej analizy każdego kroku

| Krok | Zmiana | Realny wpływ architektoniczny | Wpływ na QSE | Ocena |
|------|--------|-------------------------------|--------------|-------|
| 1 | Namespace `ltd.newbee` → `mall` | **ZERO** — te same importy | S: **+0.38** (dominuje!) | **KOSMETYCZNY** |
| 2 | PersonalController → Auth + Profile | Realne SRP | C: +0.02 | **OK** |
| 3 | DAO Read/Write CQRS split | **FAKE** — nikt nie używa oddzielnie | C/M: małe | **SZUM** |
| 4 | Service Query/Command split | **FAKE** — kontrolery używają starych IF | C: małe | **SZUM** |
| 5 | 4 martwe interfejsy | **ZERO** — nikt nie implementuje | M: +0.02 | **SZUM** |
| 6 | equals/hashCode/toString × 23 | Boilerplate ale poprawny | C: +0.07 | **OK** |

### Podział wpływu na AGQ_v2

| Składnik zmiany AGQ | Δ wkładu |
|--------------------|----------|
| S: namespace gaming (+0.38 × waga 0.15) | **+0.057** (39% Δ) |
| C: realna poprawa (+0.07 × 0.15) | +0.011 (7.5%) |
| C: fake CQRS (+0.02 × 0.15) | +0.003 (2%) |
| M: martwe interfejsy (+0.02 × 0.30) | +0.006 (4%) |
| Suma "uczciwa" (kroki 2, 6 tylko) | **+0.014** (10%) |
| Suma raportowana | **+0.146** (100%) |

**90% zmiany AGQ pochodzi ze zmian kosmetycznych lub szumu.**

## Odkryte Problemy Metryk

### Problem 1: S jest gameable przez zmianę namespace

**Mechanizm:**
```
S = min(1.0, Var(I₁, ..., Iₖ) / 0.25)

gdzie Iⱼ = fan_out(pakiet_j) / (fan_in(pakiet_j) + fan_out(pakiet_j))
i k = liczba pakietów 2. poziomu
```

**Przed:** `ltd.newbee.mall` = 1 "blob" pakietu na poziomie 2 (cały kod w `ltd.newbee`) → wariancja instability ≈ 0 → S = 0.21

**Po:** `mall.controller`, `mall.service`, `mall.dao`, `mall.domain`, ... = 8 pakietów 2. poziomu z różnymi instability → wariancja rośnie → S = 0.59

**Ale!** Graf zależności jest identyczny: kontrolery nadal wywołują serwisy, serwisy nadal wywołują DAO. Zmiana była w *warstwie nazw*, nie w *grafie*. S liczy wariancję na poziomie pakietów 2. poziomu — więc więcej pakietów o różnych pozycjach w hierarchii = wyższe S, nawet jeśli żadna zależność nie uległa zmianie.

**Skala problemu:** Dowolny projekt może podnieść S o ~0.3–0.4 przez zwykłe przemianowanie `com.company.project.X` → `X` i podział na 8 podpakietów. Zero realnych zmian architektonicznych.

**Potencjalna mitigacja:** Liczyć S na poziomie klas (nie pakietów), lub normalizować wariancję przez liczbę pakietów, lub używać tylko package-level granularity powyżej określonego progu n_packages.

### Problem 2: M jest inflatable przez martwe interfejsy

**Mechanizm:**
```
M = max(0, Q_Louvain) / 0.75

gdzie Q_Louvain = modularity score z algorytmu Louvain na grafie klasy-pakiety
```

Louvain traktuje interfejsy jako węzły grafu. Interfejs `DataAccessObject` z pakietu `mall.domain` jest "wewnętrznie spójny" (nikt go nie implementuje → wysoki Q jako izolowany węzeł). Ale izolacja wynika z braku użycia, nie z dobrego projektu.

**Skala problemu:** Każdy martwy interfejs nieznacznie podnosi M. W dużym projekcie, dodanie 50 martwych interfejsów mogłoby podbić M o ~0.05.

**Potencjalna mitigacja:** Wykluczenie interfejsów bez implementacji z wykresu Louvain, lub wymóg `n_implementors >= 1` dla interfejsów włączanych do obliczania M.

### Problem 3: LCOM4 błędnie karze interfejsy Java

**Mechanizm:**
```
LCOM4 = liczba spójnych składowych grafu metod klasy
(krawędź między metodami jeśli dzielą wspólny atrybut)

Interfejs Java:
  - n_metod = k (deklaracje bez ciała)
  - n_atrybutów = 0 (poza stałymi)
  → Graf metod: k węzłów, 0 krawędzi → k spójnych składowych
  → LCOM4 = k (MAKSYMALNA kara!)
```

**Przykład:** Interfejs `DataAccessObject` z 5 deklaracjami metod:
```java
interface DataAccessObject {
    void save(T entity);
    void delete(Long id);
    T findById(Long id);
    List<T> findAll();
    long count();
}
```
→ LCOM4 = 5 (5 izolowanych metodach = 5 spójnych składowych)

Ale intencją jest maksymalna kohezja (wszystkie metody powiązane semantycznie). Interfejs *z definicji* nie ma ciał metod ani pól instancji → LCOM4 jest bezużyteczne.

**Skala problemu:** Projekt z dużą ilością interfejsów (typowy dla clean architecture, hexagonal, DDD) będzie miał systematycznie obniżone C przez ten artefakt. Paradoks: lepsza architektura (więcej abstrakcji = więcej interfejsów) → gorsza metryka C.

**Potencjalna mitigacja:**
- Wykluczenie interfejsów z obliczania LCOM4 (traktować LCOM4_interface = 1)
- Używanie wersji LCOM4 tylko dla klas konkretnych
- Wykluczenie klas z 0 atrybutami instancji (w tym enum, annotation types, interfejsy)

### Problem 4: Formuła Panelu przeszacowuje delty ~8×

**Mechanizm:** Formuła Panelu QSE (z E12b) mapuje AGQ_v2 na skalę 0–10 przez porównanie z percentylami GT. Ponieważ S jest gameable, a S dominuje AGQ_v2, zmiana S o +0.38 przekłada się na drastyczny skok percentyla: AGQ_v2 = 0.493 (percentyl ≈ 35%) → AGQ_v2 = 0.639 (percentyl ≈ 72%). Na skali 0–10: 3.5 → 7.2 → Panel rośnie o ~3.7.

Uczciwa zmiana (bez namespace gaming): AGQ_v2 = 0.493 → 0.530 (percentyl ≈ 35% → 42%) → Panel 3.5 → 4.2 → Δ = +0.7.

**Formuła Panelu jest wrażliwa na skoki percentylowe** — które z kolei są wrażliwe na S. Cascading bias.

**Potencjalna mitigacja:** Separacja S z AGQ do osobnej metryki w Panelu; capping delta S per krok refaktoryzacji; anomaly detection dla "skoków S".

## Interpretacja

E13g jest najważniejszym eksperymentem w serii E13 — nie dlatego, że przynosi "dobre wiadomości", ale dlatego, że ujawnia fundamentalne luki w metodyce QSE.

1. **Layer 1 reaguje, ale za łatwo.** AGQ_v2 wzrósł o 0.146 (NEG→POS), ale 90% tej zmiany pochodzi ze zmian kosmetycznych lub szumowych. Formuła jest "gameable" na wiele sposobów — i to bez intencji nadużycia (wszystkie zmiany wyglądały poprawnie przed analizą post-hoc).

2. **S jest najpoważniejszą luką.** Metoda liczenia S (wariancja instability na poziomie pakietów 2. poziomu) jest wrażliwa na liczbę i nazwy pakietów, nie na rzeczywiste zależności. To metryka topologiczna, która jest "ślepa" na semantykę struktury nazw.

3. **CQRS jako anty-wzorzec metryczny.** Wzorzec CQRS jest architektonicznie wartościowy — ale jego implementacja "na papierze" (podział klas bez zmiany wzorców wywołań) podnosi metryki bez realnej poprawy. QSE nie jest w stanie rozróżnić "papierowego CQRS" od "realnego CQRS" bez analizy użycia (call graph), a nie tylko grafu zależności (dependency graph).

4. **Martwe abstrakcje są szumem.** Interfejsy bez implementacji są "metrycznym martwym ciężarem" — podbijają M, obniżają C (przez LCOM4). Architekt dodający abstrakcje dla "dobrej formy" dostaje gorsze wyniki C, co jest odwrotne do intencji.

5. **Uczciwość wymaga post-hoc analizy.** Bez tabeli krytycznej analizy każdego kroku, raport QSE powiedziałby: "Projekt poprawił się z NEG do POS, Panel +3.2 — dobra robota!". To byłoby misleading. QSE-Diagnostic (Layer 3) powinien obejmować "gaming detection" — identyfikację zmian wysokiego wpływu na metryki o zerowym wpływie architektonicznym.

6. **Implikacje dla projektu QSE:**
   - S wymaga redesignu lub mitigacji (np. wykluczenie zmian namespace)
   - LCOM4 wymaga filtrowania interfejsów
   - Panel QSE wymaga odporności na outlier metryczne
   - E13g otwiera dyskusję: czy QSE mierzy "jakość architektury" czy "zgodność z konwencjami metrycznymi"?

7. **Uczciwa ocena newbee-mall po refaktoryzacji:** Projekt nadal NEG (Panel uczciwy ≈ 3.8–4.2). Dwie realne zmiany (Controller split, equals/hashCode) poprawiły C o +0.07 i nie wpłynęły na AGQ_v2 ani S istotnie. Projekt wymaga głębszej reorganizacji — nie tylko Krok 2 i 6, ale prawdziwego przemyślenia struktury warstw.

## Następny krok

E13g jest ostatnim eksperymentem w serii E13. Otwiera nową fazę projektu: adresowanie problemów metryk odkrytych w E13g.

Priorytety na podstawie E13g:
1. **S gaming fix:** Zmiana granulacji obliczania S lub dodanie "namespace-change detector" do pipeline
2. **LCOM4 interface filter:** Wykluczenie interfejsów z agregacji C
3. **Panel robustness:** Odporność Panelu QSE na outlier metryczne (np. winsorization)
4. **Gaming detection:** Layer 3 (QSE-Diagnostic) powinien flagować "suspicious high-Δ changes" po refaktoryzacji

## Szczegóły techniczne

### Baseline newbee-mall

```
Repo: newbee-ltd/newbee-mall (Spring Boot e-commerce)
n_classes: 88
n_packages: 12 (przed), 12 (po, nowa struktura)
n_edges: 247 (zależności między pakietami)
GT label: NEG (Panel=2.5, σ=1.8)

Metryki baseline:
  M = 0.59  (2 społeczności Louvain: frontend/backend)
  A = 1.00  (brak cykli!)
  S = 0.21  (1 blob namespace ltd.newbee.mall)
  C = 0.29  (LCOM4 ≈ 4.2 średnio — klasy mają wiele niepowiązanych metod)
  CD = 0.42 (umiarkowana gęstość)
  AGQ_v2 = 0.493
```

### Szczegółowe obliczenia S — mechanizm gamingu

```python
# PRZED: namespace ltd.newbee.mall
packages_level2 = {
    "ltd.newbee": {fan_in: 5, fan_out: 12}  # 1 pakiet
}
I_values = [12/(5+12)] = [0.706]
Var(I_values) = 0.0  (tylko 1 wartość → wariancja = 0)
S = min(1, 0.0/0.25) = 0.0... 
# Ale S=0.21 — bo w rzeczywistości są sub-pakiety (controller, service, dao)
# W baseline są 3 pakiety: ltd.newbee.mall.controller, .service, .dao
# I = {controller: 1.0, service: 0.5, dao: 0.0} → Var = 0.167 → S = 0.167/0.25 * norm = 0.21

# PO: namespace mall z 8 pakietami
packages_level2 = [
    mall.controller: I=1.0, 
    mall.service: I=0.5,
    mall.dao.read: I=0.0,
    mall.dao.write: I=0.0,
    mall.domain: I=0.3,
    mall.api: I=0.8,
    mall.config: I=0.2,
    mall.util: I=0.1
]
I_values = [1.0, 0.5, 0.0, 0.0, 0.3, 0.8, 0.2, 0.1]
Var(I_values) = 0.132 → S = min(1, 0.132/0.25) = 0.53
# (wynik zbliżony do raportowanego 0.59 — różnice przez dokładną definicję fan-in/fan-out)
```

Graficznie: S mierzy "hierarchię stabilności" przez wariancję. Więcej pakietów o różnej roli → wyższa wariancja → wyższe S. Ale ta wariancja może wynikać z nazwy, a nie z rzeczywistej struktury zależności.

### Analiza LCOM4 dla interfejsów

```java
// Interfejs z 5 metodami:
interface DataAccessObject<T> {  // LCOM4 = 5 (5 spójnych składowych!)
    void save(T entity);          // składowa 1 (izolowana)
    void delete(Long id);         // składowa 2 (izolowana)
    T findById(Long id);          // składowa 3 (izolowana)
    List<T> findAll();            // składowa 4 (izolowana)
    long count();                 // składowa 5 (izolowana)
}
// Brak pól → żadne dwie metody nie dzielą atrybutu → 5 izolowanych składowych

// Ekwiwalentna klasa konkretna (wysoka kohezja):
class UserRepositoryImpl implements DataAccessObject<User> {
    private final EntityManager em;  // 1 pole → wszystkie metody je używają
    void save(User u) { em.persist(u); }        // LCOM4 = 1!
    void delete(Long id) { em.remove(em.find(User.class, id)); }
    // ...
}
```

Paradoks: `DataAccessObject` interfejs (semantycznie kohezyjny) → LCOM4=5 (najgorszy).
`UserRepositoryImpl` implementacja → LCOM4=1 (idealny). QSE karze za abstrakcje.

### Uczciwa ocena refaktoryzacji — podsumowanie

```
Zmiany realne (architektonicznie uzasadnione):
  Krok 2: PersonalController split → +0.02 C
  Krok 6: equals/hashCode/toString × 23 klas → +0.07 C
  
  Suma Δ realna: ΔAGQ_v2 ≈ +0.014
  Panel uczciwy: 2.5 → 3.8–4.2 (Δ ≈ +0.4 do +0.7)

Zmiany kosmetyczne/szumowe:
  Krok 1: namespace gaming → +0.38 S (Δ dominuje, ale FAKE)
  Krok 3: DAO CQRS papierowe → +0.02 C (SZUM)
  Krok 4: Service CQRS papierowe → +0.02 C (SZUM)
  Krok 5: martwe interfejsy → +0.02 M (SZUM, karze C przez LCOM4)

Raportowane przez pipeline:
  AGQ_v2: 0.493 → 0.639 (+0.146)
  Panel: 2.5 → 5.7 (+3.2)

Uczciwa ocena:
  AGQ_v2: 0.493 → 0.507 (+0.014)
  Panel: 2.5 → 3.8 (+0.4 do +0.7)
  Label: NEG → NEG (nie przeszło progu POS)
```

## Zobacz też

- [[E13 Three-Layer Framework]] — architektura QSE (Layer 1 tu testowana)
- [[E13e Shopizer Pilot]] — Layer 2 walidacja (Shopizer)
- [[E13f Commons Collections Pilot]] — Layer 2 walidacja (Commons)
- [[E13d QSE-Track Within-Repo]] — syntetyczna walidacja Layer 2
- [[Stability]] — S: gameable przez namespace rename (Problem 1)
- [[Cohesion]] — C: LCOM4 błędnie karze interfejsy (Problem 3)
- [[Modularity]] — M: inflatable przez martwe interfejsy (Problem 2)
- [[Limitations]] — pełna lista ograniczeń QSE (zaktualizowana po E13g)
- [[AGQv2]] — formuła Layer 1 (przesacowuje delta przez Problem 1)
- [[Ground Truth]] — newbee-mall jest NEG w GT (Panel=2.5)
