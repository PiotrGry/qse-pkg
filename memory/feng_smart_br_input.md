# FENG SMART — Wsad merytoryczny B+R
# AGQ: Architecture Graph Quality
# Deterministyczny quality gate dla kodu generowanego przez AI
# Data: 2026-03-06

---

## 1. PROBLEM BADAWCZY

### 1.1 Kontekst technologiczny

Generatywna sztuczna inteligencja fundamentalnie zmienia sposób wytwarzania
oprogramowania. Narzędzia takie jak GitHub Copilot, Cursor, Claude Code czy Devin
umożliwiają generowanie kodu na skalę wcześniej nieosiągalną — według danych
GitHub (2025) ponad 40% kodu w repozytoriach enterprise pochodzi już z modeli AI.
Trend ten przyspiesza: od autouzupełniania (2022-2023) przez asystentów kodowania
(2024) po autonomicznych agentów programistycznych (2025-2026).

Zjawisko określane jako „vibe coding" — generowanie aplikacji przez AI na
podstawie opisów w języku naturalnym — nie jest modą, lecz wczesną fazą
przejścia do aplikacji wytwarzanych w całości przez sztuczną inteligencję.
Na dzień dzisiejszy nie istnieje udokumentowany przypadek systemu klasy
enterprise napisanego w całości przez AI, ale trajektoria rozwoju modeli
(Pass@1 rośnie ~10pp/rok) wskazuje, że jest to kwestia czasu, nie
możliwości technologicznej.

Jednocześnie branża ocenia jakość modeli generujących kod wyłącznie przez pryzmat
poprawności funkcjonalnej — metryki Pass@1 (prawdopodobieństwo, że pierwsza
wygenerowana próbka kodu przechodzi testy jednostkowe). Nie istnieje powszechnie
stosowany benchmark mierzący jakość strukturalną ani architektoniczną generowanego
kodu.

### 1.2 Paradoks Sabra — kluczowy wynik badawczy

Sabra, Schmitt i Tyler (2025, Sonar, preprint 2508.14727) przeprowadzili
najszersze dotąd badanie jakości kodu LLM: 4442 zadania Java × 5 modeli
(Claude Sonnet 4, Claude 3.7, GPT-4o, Llama 3.2 90B, OpenCoder-8B),
analiza ~550 regułami SonarQube.

Główny wynik (RQ4): „No direct correlation between Pass@1 and overall
quality/security of generated code."

Konkretne dane:

| Model | Pass@1 | Issues/passing task |
|---|---|---|
| Claude Sonnet 4 | 77.04% (najlepszy) | 2.11 (najgorszy) |
| Claude 3.7 | 72.46% | 1.78 |
| GPT-4o | 74.40% | 1.71 |
| Llama 3.2 90B | 67.26% | 1.58 |
| OpenCoder-8B | 60.43% (najgorszy) | 1.45 (najlepszy) |

Paradoks w ramach jednego producenta — upgrade Claude 3.7 → Sonnet 4:
- Pass@1: +4.58pp (poprawa)
- BLOCKER bugs: 7.1% → 13.71% (+93%, pogorszenie)
- BLOCKER vulnerabilities: 56.03% → 59.57% (pogorszenie)

Mechanizm paradoksu: lepszy model rozwiązuje trudniejsze zadania, co wymaga
bardziej złożonego kodu. Testy jednostkowe weryfikują poprawność (czy kod działa),
ale nie jakość (jak jest napisany). Defekty strukturalne pozostają ukryte —
kod przechodzi testy, więc trafia na produkcję bez weryfikacji architektury.

Implikacja systemowa: cała branża optymalizuje LLM pod Pass@1. Im lepsze modele
→ im więcej kodu przechodzi testy → im więcej ukrytego długu technicznego
trafia na produkcję. Jest to pozytywne sprzężenie zwrotne prowadzące do
masowej erozji architektonicznej.

### 1.3 Rozkład defektów w kodzie generowanym przez AI

Sabra et al. wykazali następujący rozkład (wszystkie modele, uśrednione):

**Code smells: 90-93% wszystkich defektów**
- Dead/Unused/Redundant code: 14-43%
- Design/Framework best practices violations: 11-22%
- Cognitive complexity: 4-8%

**Bugs: 5-8%**
- Control-flow mistakes: 14-48%
- Exception handling: 11-17%
- Resource management/leaks: 7-15%

**Vulnerabilities: ~2%**
- Path-traversal & injection: 31-34%
- Hard-coded credentials: 14-30%
- Cryptography misconfiguration: 19-25%

Kluczowa obserwacja: dominująca kategoria (90%+) to code smells — defekty
strukturalne wynikające bezpośrednio z problemów architektonicznych: brak
modularyzacji, nadmierne coupling, cykliczne zależności, naruszenie separacji
warstw. Są to defekty, których źródło leży nie w pojedynczym pliku, lecz
w relacjach między modułami — na poziomie grafu zależności.

### 1.4 Quality drift w erze AI — nowy fenomen

Quality drift — systematyczna degradacja jakości strukturalnej kodu w czasie —
istniał przed AI (Perry & Wolf 1992: „architecture erosion"), ale AI radykalnie
zmienia jego dynamikę:

1. **Skala**: AI generuje kod 10-100× szybciej niż człowiek → drift 10-100× szybszy
2. **Brak pamięci architektonicznej**: LLM nie pamięta decyzji z poprzednich
   promptów. Każda generacja jest niezależna od kontekstu architektonicznego projektu.
   Teoretycznie możliwe jest umieszczenie całego repozytorium w oknie kontekstowym
   modelu (context window do 1M tokenów w 2026), ale jest to trade-off: moc
   obliczeniowa modelu zużywana na utrzymanie kontekstu (pamięć) zamiast na
   rozumowanie i generację. Im więcej kontekstu → tym mniej „inteligencji" na
   właściwe zadanie. Ponadto nawet przy pełnym kontekście LLM nie gwarantuje
   spójności architektonicznej — rozumie kod lokalnie, nie widzi grafu zależności
   jako struktury.
3. **Brak ownership**: nikt nie „czuje" kodu generowanego przez AI → nikt nie
   zauważa stopniowej erozji.
4. **Selekcja na Pass@1**: branża wybiera modele po Pass@1 → optymalizacja
   „działa" kosztem „jest dobrze napisane" → systemowy bias w kierunku
   krótkookresowej poprawności kosztem długookresowej utrzymywalności.

### 1.4a Empiryczne dowody że LLM nie rozumieją struktury architektonicznej

Teza o braku rozumienia architektury przez LLM nie jest spekulacją —
potwierdzają ją następujące wyniki empiryczne:

**1. SWE-bench Pro vs SWE-bench Verified (Scale AI, 2026) [16]:**
Najnowszy benchmark wymagający koordynacji zmian średnio w 4.1 plikach
per zadanie. Najlepsze modele na świecie (marzec 2026):
- SWE-bench Verified (single-file): ~80% (Claude Opus 4.1, GPT-5)
- SWE-bench Pro (multi-file): 23.1% (Claude Opus 4.1), 23.3% (GPT-5)
Spadek 3.5× przy przejściu z poziomu pliku na poziom architektury.
Analiza failure modes (Scale AI): 35.9% błędów Opus 4.1 to „semantic
understanding failures" — model nie rozumie jak zmiana w pliku A
wpływa na zachowanie pliku B.

**2. DependEval (ACL Findings, 2025) [17]:**
Dedykowany benchmark mierzący zrozumienie zależności na poziomie
repozytorium. Wynik: nawet modele closed-source (GPT-4, Claude)
mają istotne problemy z operacjami cross-file. Modele rozumieją
kod per plik, ale tracą spójność przy zależnościach między plikami.

**3. „Lost in the Middle" (Liu et al., TACL 2024) [18]:**
Wydajność LLM spada o >30% gdy istotna informacja znajduje się
w środku kontekstu (nie na początku/końcu). Efekt U-shaped performance
curve. Implikacja: umieszczenie całego repozytorium w kontekście
powoduje, że informacje architektoniczne (zależności między modułami,
rozproszone w środku kodu) są systematycznie pomijane. Databricks
(2025) potwierdził degradację po 32K-64K tokenów nawet dla
najnowszych modeli — większe okno kontekstowe ≠ lepsze rozumienie.

**4. Code Graph Model — CGM (Zhang et al., 2025) [19]:**
Autorzy wprost identyfikują lukę: „Real-world repositories often
contain more code than can fit within the model's maximum context
length, and the conversion of repository structure into text format
tends to obscure explicit dependencies that exist in the codebase."
Serializacja grafu zależności do sekwencji tokenów (jedyny format
jaki transformer przetwarza) gubi topologię. Dlatego CGM buduje
oddzielny graph-aware adapter mapujący strukturę grafu na mechanizm
uwagi (attention) — przyznając że sam transformer tego nie widzi.

**5. Retrieval-Augmented Code Generation Survey (2025) [20]:**
„File-system navigation approaches lack a global view of the
repository architecture, resulting in fragmented understanding
of the codebase that impairs long-horizon reasoning and planning."
LLM-y nawigują po repozytorium plik-po-pliku. Nie budują globalnego
obrazu architektury.

**6. Execution failure rate przy generacji repo-level (2025) [20]:**
W praktyce 31.7% generowanego kodu nie wykonuje się poprawnie
z powodu niezrozumianych łańcuchów zależności runtime.

**Synteza:** Problem jest strukturalny, nie incydentalny. Architektura
transformera jest per-token (sekwencyjna), podczas gdy architektura
oprogramowania jest per-graph (relacyjna). Serializacja grafu do tekstu
gubi topologię. Nawet zakładając optymistyczną trajektorię poprawy modeli,
deterministyczny quality gate na poziomie grafu zależności pozostaje
konieczny z trzech powodów:
1. LLM jest probabilistyczny — ten sam prompt daje różne odpowiedzi,
   nie gwarantuje spójności architektonicznej.
2. Poprawa dotyczy przede wszystkim poziomu pliku (80% SWE-bench Verified),
   nie architektury (23% SWE-bench Pro).
3. Quality gate pełni rolę analogiczną do testów jednostkowych — potrzebny
   niezależnie od poziomu umiejętności autora kodu (człowieka czy AI).
   Testy nie znikną gdy programiści staną się lepsi; quality gate nie
   zniknie gdy LLM staną się lepsze.

### 1.4b Rozgraniczenie z podejściami graph-aware w generacji kodu

Istniejące prace nad integracją grafów zależności z LLM — w szczególności
Code Graph Model (CGM, Zhang et al. 2025 [19]) — koncentrują się na fazie
**pre-generation**: graf zależności repozytorium jest kodowany przez Graph
Neural Network (GNN) i podawany jako dodatkowy sygnał do mechanizmu uwagi
(attention) transformera, dzięki czemu model lepiej rozumie strukturę repo
podczas generacji kodu. CGM osiąga 43% na SWE-bench Lite (najlepszy wynik
wśród modeli open-source, +12.33pp vs poprzedni SOTA).

Kluczowe rozróżnienie: CGM i AGQ operują na **różnych etapach pipeline'u**
i pełnią **różne funkcje**:

```
Faza pre-generation (CGM):
  LLM + graph-aware adapter → generuje kod
  Cel: poprawić jakość generacji
  Charakter: probabilistyczny (LLM wciąż decyduje)

Faza post-generation (AGQ):
  Wygenerowany kod → dependency graph → metryki → quality gate
  Cel: deterministycznie zweryfikować wynik
  Charakter: deterministyczny (algorytm, powtarzalny)
```

CGM nie zastępuje AGQ z następujących powodów:
1. **Nie gwarantuje wyniku** — nawet z graph-aware adapterem LLM osiąga
   43% (57% failure). Kod wymaga weryfikacji niezależnie od metody generacji.
2. **Jest w modelu, nie w CI** — CGM to modyfikacja architektury sieci
   neuronowej, nie narzędzie CI/CD. Nie da się go „wrzucić" do pipeline'u
   jako gate.
3. **Jest probabilistyczny** — ten sam prompt → różne wyniki. AGQ daje
   ten sam score za każdym razem.
4. **Nie zna intencji architektonicznej** — CGM widzi istniejący graf, ale
   nie wie jaka architektura jest pożądana. Nie zna constraints użytkownika
   (forbidden edges). AGQ egzekwuje deklaratywne reguły.

Obie klasy rozwiązań są **komplementarne**: CGM poprawia input (lepszy kod
z LLM), AGQ weryfikuje output (deterministyczny pomiar wyniku). Sam fakt
istnienia CGM **potwierdza fundament AGQ** — autorzy zainwestowali w
graph-aware adapter ponieważ sam tekst nie wystarcza do reprezentacji
struktury architektonicznej, co jest tą samą obserwacją która motywuje AGQ.

Ponadto paradoks Sabra ma tu zastosowanie: im lepsze narzędzia generacji
(w tym CGM) → im więcej kodu trafia na produkcję → im większa potrzeba
deterministycznego quality gate.

### 1.5 Luka w istniejących narzędziach

#### Narzędzia operujące na poziomie pliku (mikro):

**SonarQube** (SonarSource, wycena $4.7B, >$98M ARR):
Wiodące narzędzie statycznej analizy. ~550 reguł per język. Mierzy code smells,
bugs, vulnerabilities per plik. Nie widzi relacji między modułami. Nie mierzy
modularności, cyklicznych zależności, stabilności modułów. W lutym 2025 przejął
AutoCodeRover (AI-assisted fix), ale nie rozszerzył analizy na poziom architektury.

**Snyk** (wycena $7.4B, $408M ARR):
Security-first. Analiza zależności (SCA) + SAST (Snyk Code). Potężny w wykrywaniu
vulnerabilities. Nie mierzy jakości architektonicznej. Spowolnienie wzrostu
(12% YoY, 2025) sugeruje nasycenie rynku security-per-file.

**Semgrep** (wycena $0.5-1B, $34M ARR, Series D $100M w 2025):
Custom SAST rules, 30+ języków. Potężny w definiowaniu reguł per plik.
Nie widzi grafu zależności między modułami.

**Qodana** (JetBrains), **DeepSource** ($1.8M ARR): inspekcje IDE / autofix.
Per plik.

#### Narzędzia częściowo adresujące architekturę:

**ArchUnit** (open-source):
Jedyne narzędzie z regułami architektonicznymi. Ale: wyłącznie Java, reguły
pisane w kodzie Java (nie deklaratywne), brak SaaS, brak CI gate z ratchetem.

**CodeScene** (€7.5M funding):
Analiza behawioralna + hotspoty. Częściowo widzi architekturę (change coupling),
ale nie mierzy grafu zależności deterministycznie. Nie ma deklaratywnych constraints.

**Sigrid** (Software Improvement Group):
Benchmark ISO 25010 na próbie tysięcy systemów. Zamknięty model consultingowy,
nie self-service SaaS, nie zintegrowany z CI/CD developera.

**CAST Highlight** (CAST, $180M+ revenue):
Portfolio-level analysis, cloud readiness. Zbyt wysoki poziom abstrakcji
dla CI/CD gate per PR.

#### Podsumowanie luki:

Żadne istniejące narzędzie nie oferuje jednocześnie:
1. Deterministycznego pomiaru jakości na poziomie **grafu zależności**
2. **Deklaratywnych** reguł architektonicznych (forbidden edges jako konfiguracja)
3. Automatycznego **quality gate w CI** blokującego degradację architektoniczną
4. **Ratchet mechanism** (monotoniczny wzrost score, drift fizycznie niemożliwy)
5. Specjalizacji w kodzie generowanym przez **AI**

### 1.6 Sformułowanie problemu badawczego

W erze kodu generowanego przez AI — gdzie wolumen rośnie wykładniczo,
a jakość strukturalna spada (Sabra et al.) — brakuje deterministycznego,
automatycznego quality gate na poziomie grafu zależności, który mógłby
zastąpić architektoniczny aspekt code review.

Dotychczas jedyną warstwą zapewnienia jakości zdolną do oceny architektury
był human code review. Przy wolumenie kodu generowanego przez AI
(10-100× szybciej niż kod pisany ręcznie), code review staje się wąskim
gardłem i nie skaluje się.

**Problem badawczy:** Czy deterministyczne metryki grafowe, wyznaczane
automatycznie z grafu zależności kodu źródłowego, mogą skutecznie zastąpić
architektoniczny aspekt code review i zapobiec degradacji strukturalnej
(quality drift) w procesie ciągłej generacji kodu przez AI?

---

## 2. CEL PROJEKTU

Opracowanie i walidacja nowej klasy narzędzia — AGQ (Architecture Graph Quality)
— realizującego koncepcję „Policy as a Service": deterministyczny, automatyczny
quality gate operujący na grafie zależności kodu źródłowego, zdolny do:

1. Pomiaru jakości architektonicznej projektu za pomocą metryk grafowych
   (Modularity, Acyclicity, Stability, Cohesion)
2. Egzekwowania deklaratywnych reguł architektonicznych (forbidden edges)
   w pipeline CI/CD
3. Blokowania degradacji architektonicznej (ratchet mechanism) przy ciągłej
   generacji kodu przez AI
4. Działania wielojęzykowo (Python, Java, TypeScript, Go, C#, Rust — dowolny
   język z tree-sitter grammar) bez konfiguracji (zero-config auto-detect)
   lub z opcjonalnymi constraints (Level 2)

**Kluczowe założenie projektowe — architecture-agnostic:**
AGQ Level 1 NIE zakłada żadnego konkretnego patternu architektonicznego.
Metryki grafowe mierzą właściwości grafu zależności (modularność, acykliczność,
stabilność, spójność) — nie zgodność z DDD, hexagonal, clean architecture
ani żadnym innym wzorcem. DDD, hexagonal, clean architecture, microservices
to różne topologie tego samego grafu — AGQ mierzy jakość topologii,
nie jej rodzaj.

Konkretne wzorce architektoniczne (DDD, hexagonal, clean) są obsługiwane
wyłącznie jako opcjonalne presety constraints w Level 2 — definiowane
przez użytkownika, nie wbudowane w scoring.

Rezultatem projektu jest innowacja produktowa w skali co najmniej krajowej:
platforma do automatycznego zapewniania jakości architektonicznej kodu,
niezależna od wybranego wzorca architektonicznego, ze szczególnym
uwzględnieniem kodu generowanego przez AI.

**Architektura techniczna produktu:**
- **Core engine w Rust** — high-performance parser (tree-sitter, 50K LOC/s)
  + obliczenia grafowe (petgraph) + LCOM4 (union-find). Kompilowany do
  natywnej biblioteki z Python wrapper (PyO3). Multi-language od dnia 1.
- **ML classifier** (pre-scoring) — detekcja klas abstrakcyjnych w językach
  z duck typing. ONNX Runtime, model zamrożony, deterministyczny output.
- **LLM recommendations** (post-scoring) — generatywne rekomendacje naprawcze.
  Warstwa prezentacyjna, nie wpływa na score.
- **HPC pipeline** (faza badawcza) — masowe przetwarzanie benchmarku 100+ repo,
  kalibracja wag, analiza temporalna. Klaster HPC, embarrassingly parallel.

### 2.1 Obecny poziom gotowości technologicznej: TRL 3

Projekt startuje z TRL 3, **potwierdzonym eksperymentalnie** (4 eksperymenty, 23 testy):

Stan zaimplementowany:
- Metryki grafowe AGQ zaimplementowane w Pythonie: Modularity (Louvain), Acyclicity (Tarjan),
  Stability (Martin DMS z detekcją abstrakcyjności), Cohesion (LCOM4)
- Detekcja klas abstrakcyjnych z AST (ABC, Protocol, @abstractmethod)
- Constraints engine v1 (forbidden edges, glob matching)
- PoC detektory DDD (mutation study, F1: 0.964-1.0) — opcjonalny preset, nie core

Walidacja eksperymentalna TRL 3:
- EXP1 (Smoke test): 5 repo OSS (FastAPI, Black, httpx, Flask, PyJWT) — ranking intuicyjnie
  poprawny, metryki obliczalne, AGQ range 0.513-0.638
- EXP2 (Mutation testing): 4/4 mutacji wykrytych — cykl→A spada 50%, cross-module→Q spada 11%,
  god class→Co spada 25%, spaghetti→Cv spada 47%
- EXP3 (Sensitivity): 10 profili syntetycznych — Modularity std=0.143, Acyclicity std=0.428,
  Stability std=0.113. Metryki rozróżniają jakość.
- EXP4 (Constraints): 4/4 scenariuszy — gate wykrywa violations, score spada proporcjonalnie,
  po naprawie wraca do 1.0

Znane ograniczenia TRL 3:
- Silnik w czystym Pythonie — za wolny na produkcyjne repo (>100K LOC)
- Walidacja na 5 repo — za mało na statystyczną istotność
- Stability niemonotoniczna bez detekcji abstrakcyjności w repo bez ABC/Protocol
- Tylko Python — brak multi-language

TRL 3 jest typowym punktem wejścia dla badań przemysłowych w FENG SMART.
Cel projektu: TRL 3 → TRL 7-8 (prototyp operacyjny z użytkownikami).

---

## 3. STAN WIEDZY I TECHNIKI (State of the Art)

### 3.1 Metryki jakości oprogramowania — poziom mikro

Klasyczne metryki obiektowe Chidamber & Kemerer (1994):
- LCOM (Lack of Cohesion of Methods): spójność wewnętrzna klasy
- CBO (Coupling Between Objects): coupling per klasa
- WMC (Weighted Methods per Class): złożoność per klasa

Martin (2003) — metryki pakietowe:
- Instability I = Ce/(Ca+Ce): stosunek zależności wychodzących do sumy
- Abstractness A: stosunek klas abstrakcyjnych do wszystkich
- Distance from Main Sequence D = |A + I - 1|: odchylenie od optymalnej
  relacji abstrakcja/stabilność

McCabe (1976): Cyclomatic Complexity — liczba niezależnych ścieżek w control flow.

ISO/IEC 25010 (SQuaRE): model jakości — maintainability jako jedna z 8 cech,
rozbita na: modularity, reusability, analysability, modifiability, testability.

**Ograniczenie:** Wszystkie powyższe operują na poziomie klasy lub pliku (mikro).
Nie mierzą jakości relacji między modułami na poziomie całego systemu (makro).
System może mieć czyste pliki (niski CC, dobry LCOM per klasa) ale spaghetti
architecture (cykliczne zależności, brak modularności, leaking abstractions).

### 3.2 Metryki grafowe w analizie oprogramowania

Newman (2006): Modularity Q — miara jakości podziału grafu na społeczności
(communities). Louvain algorithm do efektywnego wyznaczania Q na dużych grafach.
Q ∈ [-0.5, 1]. Stosowany w network science, rzadko w software engineering.

Tarjan (1972): Algorytm wyznaczania Strongly Connected Components (SCC) —
identyfikacja cykli w grafie skierowanym. Stosowany w kompilatorach,
rzadko jako metryka jakości.

Garcia et al. (2013): Architecture recovery — techniki odtwarzania architektury
z kodu źródłowego na podstawie analizy zależności. Potwierdzenie, że graf
importów niesie informację architektoniczną.

**Ograniczenie:** Metryki grafowe opisane w literaturze network science
i software architecture recovery, ale nie zaimplementowane jako narzędzie
CI/CD. Nie zwalidowane na kodzie generowanym przez AI.

### 3.3 Architecture erosion i technical debt

Perry & Wolf (1992): Pojęcie erozji architektonicznej — stopniowa degradacja
zamierzonej architektury w trakcie rozwoju systemu. Proces powolny w rozwoju
ręcznym, potencjalnie gwałtowny przy generacji przez AI.

Kruchten et al. (2012): Technical debt jako metafora finansowa — narastające
„odsetki" od decyzji architektonicznych skracających czas dostarczenia kosztem
jakości długoterminowej. AI amplifikuje ten mechanizm: zerowy koszt krańcowy
generacji kodu eliminuje naturalny hamulec (czas developera).

### 3.4 Fitness functions

Ford, Parsons, Kua (2017): Architectural fitness functions — koncepcja
automatycznych testów weryfikujących zgodność kodu z zamierzoną architekturą.
Fitness function = deterministyczna funkcja zwracająca wartość liczbową
reprezentującą „odległość" systemu od pożądanego stanu architektonicznego.

ArchUnit (Java): Jedyna szeroko stosowana implementacja fitness functions.
Ograniczona do Java. Reguły pisane w kodzie Java (nie deklaratywne — wymagają
umiejętności programistycznych). Brak modelu SaaS.

**Ograniczenie:** Koncepcja fitness functions opisana i zaakceptowana
w literaturze, ale brak wielojęzycznej implementacji z deklaratywnymi
constraints i integracją CI/CD jako usługi.

### 3.5 Benchmarki jakości kodu LLM

Pass@1 / Pass@k (HumanEval, MBPP, SWE-bench, EvoCodeBench):
Dominujące benchmarki. Mierzą wyłącznie poprawność funkcjonalną.
Sukces = kod kompiluje się + przechodzi asserty. Brak kary za code smells,
złą architekturę, coupling, cykliczne zależności.

BLEU / CodeBLEU: Metryki podobieństwa do referencji. 10 poprawnych
rozwiązań tego samego zadania może mieć BLEU=0 między sobą.

Multi-dimensional (ProxyWar 2025, EvoCodeBench 2025, BigCodeBench 2024):
Dodają wymiary efficiency, robustness, adaptability. Wciąż mierzą per zadanie
(mikro), nie per projekt (makro). Oceniają MODEL („który LLM lepszy?"),
nie KOD („czy ten PR psuje architekturę?").

Sabra et al. (2025): Jedyny paper stosujący statyczną analizę jakości
(SonarQube) do kodu LLM. Ale SonarQube = analiza per plik.

**Luka:** Nie istnieje benchmark ani narzędzie mierzące jakość
architektoniczną kodu generowanego przez AI na poziomie grafu zależności.

### 3.6 Podsumowanie luki badawczej

| Aspekt | Stan wiedzy | Luka |
|---|---|---|
| Metryki per plik | Dojrzałe (CK, CC, SQ) | Nie widzą architektury |
| Metryki grafowe | Opisane (Newman, Tarjan) | Nie zaimplementowane w CI |
| Fitness functions | Koncepcja + ArchUnit | Java-only, nie deklaratywne |
| Erozja architektoniczna | Opisana (Perry & Wolf) | Nie badana przy AI code gen |
| Jakość kodu AI | Sabra (SQ per plik) | Nikt nie mierzy architektury |
| Quality gate CI | SonarQube (per plik) | Brak gate na poziomie grafu |
| Quality drift AI | Nie badany | Brak mechanizmu ochronnego |

---

## 4. HIPOTEZY BADAWCZE

**H1 — Korelacja AGQ z jakością:**
Composite score AGQ (Modularity + Acyclicity + Stability + Cohesion) koreluje
z defect density silniej niż SonarQube Maintainability Rating.
Kryterium: Pearson r_AGQ > r_SQ, mierzone na N≥100 repozytoriów open-source.

**H2 — AGQ gate redukuje defekty:**
Kod generowany przez LLM z aktywnym AGQ gate wykazuje istotnie niższy defect
density niż kod bez gate.
Kryterium: istotna statystycznie różnica w kontrolowanym eksperymencie
(ten sam model, te same prompty, z/bez AGQ w pętli CI).

**H3 — Redukcja code review:**
Ratchet mechanism w połączeniu z deklaratywnymi constraints redukuje potrzebę
human code review o ≥70%.
Kryterium: % pull requestów wymagających interwencji człowieka spada z ~100%
do ≤30% przy zachowaniu lub poprawie jakości architektonicznej.

**H4 — Pokrycie defektów:**
Metryki AGQ adresują ≥80% kategorii defektów wykrywanych w kodzie LLM.
Kryterium: formalne mapowanie metryk AGQ na taksonomię defektów Sabra et al.,
zwalidowane na rzeczywistych repozytoriach.

**H5 — Architecture-agnosticism:**
Korelacja AGQ z defect density jest stabilna niezależnie od wybranego wzorca
architektonicznego (DDD, hexagonal, clean, microservices, modular monolith).
Kryterium: Pearson r ≥ 0.5 dla KAŻDEJ kategorii architektonicznej osobno
(nie tylko w agregacie), mierzone na datasecie multi-architecture (WP1).

---

## 5. PYTANIA BADAWCZE

**RQ1:** Czy metryki grafowe (Modularity, Acyclicity, Stability, Cohesion)
korelują z defect density w repozytoriach open-source?
Kryterium sukcesu: Pearson r ≥ 0.5 dla composite score AGQ.

**RQ2:** Czy AGQ score potrafi wykryć degradację architektoniczną niewidoczną
dla SonarQube?
Kryterium sukcesu: istnieją repozytoria gdzie SQ Maintainability = A (pass),
ale AGQ < 0.5 (fail), i te repozytoria mają wyższy defect density.

**RQ3:** Czy deklaratywne constraints (forbidden edges) pokrywają dominujące
kategorie defektów w kodzie LLM?
Kryterium sukcesu: mapowanie pokrywa ≥80% kategorii z taksonomii Sabra.

**RQ4:** Czy ratchet mechanism skutecznie blokuje quality drift w CI przy
ciągłej generacji kodu przez AI?
Kryterium sukcesu: brak statystycznie istotnego spadku AGQ score w ciągu
6 miesięcy ciągłego użytkowania z AI code generation.

**RQ5:** Czy metryki AGQ są architecture-agnostic — czy korelacja z defect
density utrzymuje się niezależnie od wzorca architektonicznego?
Kryterium sukcesu: Pearson r ≥ 0.5 per architektura (DDD, hexagonal,
clean, microservices, modular monolith, spaghetti) — nie tylko w agregacie.

---

## 6. METODYKA BADAWCZA

### 6.1 Podejście ogólne

Projekt łączy cztery dyscypliny:
- **Analizę statyczną kodu** (AST parsing, dependency extraction)
- **Teorię grafów** (community detection, cycle detection, metryki grafowe)
- **Statystyczną walidację empiryczną** (korelacja, regresja, testy istotności)
- **Inżynierię oprogramowania** (CI/CD integration, fitness functions)

### 6.2 Dwupoziomowa architektura AGQ

**Level 1 — UNIVERSAL (zero-config, deterministyczny):**
Input: kod źródłowy w dowolnym obsługiwanym języku
Proces: AST parsing → extraction import/dependency graph → metryki grafowe
Output: AGQ score ∈ [0, 1]
Nie wymaga konfiguracji. Nie wymaga LLM. W pełni deterministyczny i powtarzalny.

**Level 2 — CONTEXTUAL (opt-in):**
Wariant A: użytkownik deklaruje constraints (forbidden edges) w YAML
Wariant B: LLM sugeruje constraints → użytkownik zatwierdza → constraints
stają się deterministyczne w CI (LLM NIE jest w scoring path)

Kluczowa decyzja projektowa: LLM nigdy w core scoring path, ponieważ:
- Nie jest powtarzalny (ten sam input → różny output)
- Nie jest audytowalny
- „Zero-config oparty na LLM" = „random-config"
LLM pełni wyłącznie rolę asystenta onboardingu — sugeruje constraints,
ale ostateczna decyzja i egzekucja są deterministyczne.

### 6.3 Metryki AGQ — definicje formalne

```
AGQ = w1·Modularity + w2·Acyclicity + w3·Stability + w4·Cohesion
```

Gdzie:

**Modularity (Q):**
Newman's Modularity Q wyznaczane algorytmem Louvain community detection
na grafie importów/zależności.
Q ∈ [-0.5, 1], normalizowane do [0, 1].
Interpretacja: jak dobrze kod dzieli się na niezależne, luźno powiązane moduły.
Wysoki Q = wyraźne granice modułów, niski coupling między nimi.

**Acyclicity:**
Acyclicity = 1 - (nodes_in_cycles / total_nodes), ∈ [0, 1]
Wyznaczane algorytmem Tarjan (Strongly Connected Components).
Interpretacja: jaki procent kodu nie jest uwikłany w cykliczne zależności.
Acyclicity = 1.0 oznacza DAG (directed acyclic graph) — ideał.

**Stability:**
Stability = 1 - mean(|A_i + I_i - 1|) per moduł i, ∈ [0, 1]
Gdzie I_i = Ce/(Ca+Ce) (Martin's Instability), A_i = abstrakcyjność modułu.
A_i = (klasy abstrakcyjne: ABC, Protocol, @abstractmethod) / (wszystkie klasy).
|A + I - 1| = Distance from Main Sequence.
Interpretacja: jak dobrze moduły przestrzegają Stable Dependencies Principle
(stabilne moduły powinny być abstrakcyjne, niestabilne — konkretne).
UWAGA: Pominięcie A (A=0) fałszuje wynik — interfejsy i abstrakcje zostają
penalizowane jako „stabilny konkret". Wykrywanie klas abstrakcyjnych
(ABC, Protocol, @abstractmethod) jest wymagane dla poprawności metryki.

**Cohesion:**
Cohesion = 1 - mean(LCOM4) per klasa, ∈ [0, 1]
LCOM4: graph-based Lack of Cohesion of Methods.
Interpretacja: jak spójne wewnętrznie są klasy (metody używają tych samych pól).
Wysoki Cohesion = klasy mają jedną odpowiedzialność.

**Wagi w1-w4:** wyznaczane empirycznie w ramach walidacji (WP3):
optymalizacja korelacji composite score z defect density na datasecie
referencyjnym. Metoda: grid search + 5-fold cross-validation.

### 6.4 Constraints Engine — forbidden edges

Deklaratywna konfiguracja architektonicznych reguł:

```yaml
constraints:
  - name: "no_direct_db_from_api"
    from: "src/api/**"
    to:   "src/db/**"
    type: forbidden
    rationale: "API layer must not access database directly"
```

Constraints są **architecture-agnostic** — user definiuje SWOJE reguły,
narzędzie nie narzuca żadnego wzorca. Opcjonalne presety ułatwiają start:

```yaml
# Preset DDD:
preset: ddd
layer_order: [presentation, application, domain, infrastructure]

# Preset Hexagonal:
preset: hexagonal
constraints:
  - {from: "adapters/**", to: "core/**", type: forbidden}

# Preset Clean Architecture:
preset: clean
constraints:
  - {from: "entities/**", to: "frameworks/**", type: forbidden}

# Bez presetu — user pisze własne reguły lub używa Level 1 (zero-config)
```

**Constraint Score:**
C = 1 - (violations / total_cross_boundary_edges), ∈ [0, 1]

**Rozszerzona formuła:**
AGQ_full = α·AGQ_core + β·C
gdzie α + β = 1, AGQ_core = metryki grafowe (Level 1), C = constraint
compliance (Level 2, opt-in). Dla użytkowników bez constraints: β = 0,
AGQ_full = AGQ_core.

### 6.5 Ratchet Mechanism

Zasada: AGQ score na branchu main nigdy nie może spaść poniżej ostatniej
zatwierdzonej wartości. Każdy PR musi spełniać: AGQ(PR) ≥ AGQ(main).

```
PR → AGQ scan → AGQ(PR) ≥ AGQ(main)?
                  TAK → auto-approve (quality gate PASS)
                  NIE → block + raport → human review wymagany
```

Hipoteza: ten mechanizm fizycznie uniemożliwia quality drift, ponieważ
score jest monotonicznie niemalejący. Degradacja wymaga świadomej decyzji
człowieka (override gate), co przywraca intencjonalność do procesu.

### 6.6 Mapowanie metryk AGQ na kategorie defektów

Formalna walidacja H4 — które metryki AGQ łapią które kategorie defektów
z taksonomii Sabra et al.:

**Code smells (90-93% defektów):**

| Defekt (Sabra) | Metryka AGQ | Mechanizm |
|---|---|---|
| Dead/Unused/Redundant (14-43%) | Cohesion (LCOM4), Modularity | Klasa z nieużywanymi metodami = wysoki LCOM; izolowane node'y w grafie |
| Design violations (11-22%) | Constraints, Stability | Forbidden edge violation; niestabilny moduł z wieloma dependentami |
| Cognitive complexity (4-8%) | CC (cyclomatic) | Bezpośredni pomiar złożoności per funkcja |

**Bugs (5-8%):**

| Defekt (Sabra) | Metryka AGQ | Mechanizm |
|---|---|---|
| Control-flow (14-48%) | CC, Acyclicity | Wysoki CC = więcej ścieżek = więcej błędów; cykle w grafie = nieprzewidywalny flow |
| Exception handling (11-17%) | Cohesion (LCOM4) | Niska spójność klasy → logika obsługi wyjątków rozproszona |
| Resource leaks (7-15%) | Stability (Ca/Ce) | Niestabilny moduł z wieloma zależnymi → zasoby bez jasnego ownership |

**Vulnerabilities (~2%):**

| Defekt (Sabra) | Metryka AGQ | Mechanizm |
|---|---|---|
| Injection (31-34%) | Constraints | api→filesystem forbidden |
| Credentials (14-30%) | Poza zakresem AGQ | Domena SAST/secret scanning |
| Crypto misconfig (19-25%) | Poza zakresem AGQ | Domena SAST |

**Szacowane pokrycie ważone: ~80% defektów adresowalnych przez AGQ.**
AGQ jest komplementarny do SonarQube/Snyk, nie zastępuje ich.

---

## 7. PLAN PRAC B+R (24 miesiące)

### FAZA 1: Badania przemysłowe (miesiące 1-12)

#### WP1: Multi-Architecture Benchmark Dataset (mies. 1-5)
**Cel:** Zbudowanie referencyjnego datasetu obejmującego RÓŻNE architektury,
potwierdzającego że metryki AGQ są architecture-agnostic.

Zadania:
- Z1.1: Selekcja N≥100 repozytoriów OSS (Python, Java, TS, Go)
  z publiczną historią bugów (GitHub Issues z tagiem „bug").
  Kryteria selekcji: >1000 commitów, >10 kontrybutorów, aktywne w 2024-2026.
  **Kluczowe: zróżnicowanie architektoniczne:**
  - DDD / Layered: min. 15 repo
  - Hexagonal / Ports & Adapters: min. 15 repo
  - Clean Architecture: min. 15 repo
  - Microservices: min. 15 repo
  - Modular monolith: min. 15 repo
  - Bez wyraźnej architektury (spaghetti): min. 15 repo (baseline)
- Z1.2: Ekstrakcja dependency graph dla każdego repo (AST/tree-sitter parsing)
- Z1.3: Wyznaczenie defect density per repo (bugs/KLOC z historii issues,
  normalizowane temporalnie)
- Z1.4: Annotacja architektoniczna — klasyfikacja wzorca per repo
  (ręczna, na próbce 30 repo weryfikowana przez 2 niezależnych annotatorów)
- Z1.5: **LLM-assisted pre-anotacja defektów:** klasyfikacja issues z GitHub
  ("czy ten bug dotyczy architektury?") przez LLM z human review.
  Redukcja czasu anotacji z ~6 miesięcy na ~2 miesiące.
  LLM w roli pre-filtra — ostateczna decyzja zawsze ludzka.
- Z1.6: Walidacja cross-architecture: czy rozkład AGQ scores różni się
  istotnie między architekturami? (ANOVA / Kruskal-Wallis)
- Z1.7: **Analiza historyczna na HPC:** ekstrakcja snapshotów grafu zależności
  z pełnej historii git (N commitów × 100+ repo = setki tysięcy grafów).
  Każde repo niezależne = embarrassingly parallel.
  Infrastruktura: klaster HPC, 1 repo = 1 task, 100 rdzeni = 100× szybciej.
  Bez HPC przetwarzanie historii 100+ repo trwa tygodnie; z HPC — godziny.

**Kamień milowy KM1:** Dataset ≥100 repo × 6 architektur z dependency graphs
+ defect density + klasyfikacja architektoniczna + pełna historia grafowa.
**Deliverable:** D1.1 — publiczny benchmark dataset (anonimizowany).

**Hipoteza do weryfikacji w WP1:** Metryki grafowe AGQ korelują z defect
density NIEZALEŻNIE od wybranej architektury — korelacja r ≥ 0.5 powinna
utrzymywać się dla każdej kategorii architektonicznej osobno, nie tylko
w agregacie.

#### WP2: High-Performance AGQ Engine (mies. 3-8)
**Cel:** Implementacja produkcyjnego silnika AGQ w Rust z multi-language
parserem, zdolnego do analizy repo 100K+ LOC w <5 sekund.

**Uzasadnienie wyboru Rust:** Prototyp Python (TRL 3) potwierdził poprawność
algorytmów, ale jest za wolny na produkcyjne zastosowanie. Python `ast` parsuje
~2K LOC/s, networkx (pure Python) jest 10-50× wolniejszy od natywnych bibliotek
grafowych. Dla repo 100K LOC czas skanowania w Pythonie wynosi ~45s; cel
produkcyjny to <5s. Rust zapewnia:
- tree-sitter (parser C z bindingami Rust): ~50K LOC/s, **25× szybszy**
  od Python ast, incremental, 100+ grammarów językowych
- petgraph (natywna biblioteka grafowa): Louvain, Tarjan, union-find —
  **10-50× szybsze** od networkx
- PyO3/maturin: kompilacja do .whl, Python wrapper `import agq_core` —
  zachowanie kompatybilności z ekosystemem Python CI/CD

**Dystrybucja: single binary, zero dependencies.**
Produkt końcowy to statycznie zlinkowany binary (~10-15MB) dystrybuowany jako:
- `curl -sSf https://agq.dev/install | sh` (Linux/macOS)
- pre-built `.whl` (Python ecosystem: `pip install agq`)
- GitHub Action / GitLab CI component (pre-cached binary)
Nie wymaga JVM, Node.js, Pythona ani żadnych zależności na CI runnerze.

**Zero-config auto-detect języka.**
Użytkownik uruchamia `agq scan .` — bez konfiguracji języka. Silnik:
1. Glob: `*.py`, `*.java`, `*.ts`, `*.tsx`, `*.js`, `*.go`, `*.cs`, `*.rs`
2. Per plik: rozszerzenie → tree-sitter grammar (automatyczny dobór)
3. Per język: extraction rules (~20 linii konfiguracji) definiujące co jest
   importem w danym języku (np. Python: `import_from_statement`,
   Java: `import_declaration`, TS: `import_statement`, Go: `import_declaration`)
4. Zunifikowany dependency graph — import Pythonowy i Javowy to ta sama
   krawędź A→B. Metryki grafowe nie wiedzą w jakim języku jest kod.
Dodanie nowego języka to ~20 linii extraction rules + gotowy tree-sitter
grammar (dostępne dla 100+ języków). Nie wymaga pisania parsera.

Zadania:
- Z2.1: **Rust core engine** — parser (tree-sitter) + graf (petgraph) +
  metryki (Modularity/Louvain, Acyclicity/Tarjan, Stability/DMS, Cohesion/LCOM4).
  Kompilacja do single binary (static linking) + Python wrapper (PyO3/maturin).
- Z2.2: **Universal language support** — tree-sitter extraction rules dla
  Python, Java, TypeScript, Go, C#, Rust. Auto-detect z rozszerzenia pliku.
  Repo z mieszanką języków (np. Python backend + TS frontend) → jeden graf,
  jeden score. Tree-sitter ma gotowe grammary — dodanie języka to konfiguracja.
- Z2.3: **ML classifier abstrakcyjności** — problem: Python duck-typing sprawia
  że heurystyka (ABC, Protocol, @abstractmethod) wykrywa ~30% klas abstrakcyjnych.
  Klasa `UserRepository` jest interfejsem ale nie dziedziczy po ABC.
  Rozwiązanie: klasyfikator ML "czy ta klasa jest abstrakcją?" trenowany na
  cechach AST (puste metody, brak stanu, wzorce nazewnictwa, type hints).
  Training data: 100+ repo z benchmarku WP1, ręczna anotacja ~1000 klas.
  **ML NIE jest w scoring path** — classifier generuje zbiór `abstract_modules`
  PRZED obliczeniem metryk. Metryki pozostają deterministyczne.
  Bez poprawnej detekcji abstrakcyjności Stability daje fałszywe wyniki
  (interfejsy karane jak beton: D=1.0 zamiast D≈0.0).
- Z2.4: Walidacja poprawności: testy na znanych grafach + porównanie
  wyników Rust vs Python prototype na próbce 30 repo (bit-exact validation).

**Estymacja przyspieszenia:**

| Komponent | Python (TRL 3) | Rust (cel) | Speedup |
|---|---|---|---|
| Parsing AST | ~2K LOC/s | ~50K LOC/s (tree-sitter) | 25× |
| Graf (Louvain, Tarjan) | networkx (pure Python) | petgraph (natywny) | 10-50× |
| LCOM4 per klasa | networkx connected_components | union-find (Rust) | 100× |
| Full scan 100K LOC | ~45s | ~1-2s | ~30× |

**Kamień milowy KM2:** Single binary `agq` obliczający score dla dowolnego repo
(6+ języków), zero-config, full scan <5s na 100K LOC, incremental <1s.
**Deliverable:** D2.1 — open-source `agq` binary (Rust) + Python wrapper `agq-core`.

#### WP3: Walidacja korelacji AGQ vs defect density (mies. 6-12)
**Cel:** Weryfikacja H1 — empiryczny dowód wartości predykcyjnej AGQ.

**Wykorzystanie HPC:** WP3 to najintensywniejsze obliczeniowo zadanie projektu.
Kalibracja wag wymaga obliczenia AGQ score na 100+ repo × pełna historia git
× przestrzeń wag (grid search 4 wymiary × 6 architektur × 5-fold CV).
Szacunkowa skala: ~500K punktów obliczeniowych (snapshotów grafu).
Sekwencyjnie na 1 maszynie: tygodnie. Na klastrze HPC (100 rdzeni): godziny.

Zadania:
- Z3.1: **Masowe obliczenie AGQ na HPC** — score dla wszystkich repo z datasetu
  WP1, w tym pełna historia commitów (snapshotów grafu z Z1.7).
  Każde repo niezależne = embarrassingly parallel. Orkiestracja: Slurm/PBS.
- Z3.2: Obliczenie SonarQube Maintainability Rating (baseline porównawczy)
- Z3.3: Analiza korelacji Pearson/Spearman: AGQ vs defect density
- Z3.4: Analiza korelacji Pearson/Spearman: SQ vs defect density
- Z3.5: Porównanie R²: regresja AGQ→DD vs SQ→DD
- Z3.6: **Optymalizacja wag na HPC** — wagi w₁-w₄ (Modularity, Acyclicity,
  Stability, Cohesion) optymalizowane by zmaksymalizować korelację z defect
  density. Grid search 4D + 5-fold CV + 6 architektur = ~10K konfiguracji.
  Bayesian optimization (Optuna) jako alternatywa dla grid search.
  **Kluczowe: kalibracja per architektura** — wagi mogą różnić się między
  DDD a microservices. Bez tej kalibracji AGQ byłby niedokładny.
- Z3.7: **Analiza temporalna na HPC** — predykcja: spadek AGQ w commit N →
  wzrost bugów w commitach N+1..N+k (Granger causality).
  Wymaga przetworzenia pełnej historii 100+ repo = setki tysięcy snapshotów.
- Z3.8: Analiza per język — czy korelacja jest stabilna cross-language
- Z3.9: Analiza per architektura — czy korelacja jest stabilna cross-architecture
  (walidacja H5/RQ5: DDD, hexagonal, clean, microservices, monolith, spaghetti)

**Kamień milowy KM3:** Potwierdzenie lub odrzucenie H1 z danymi statystycznymi.
Skalibrowane wagi per architektura. Analiza temporalna.
**Deliverable:** D3.1 — raport walidacyjny + paper naukowy (cel: ICSE/MSR).

#### WP4: Constraint Inference Engine (mies. 8-12)
**Cel:** Opracowanie mechanizmu deklaratywnych constraints + walidacja pokrycia.

Zadania:
- Z4.1: Specyfikacja formatu constraints YAML (grammar, semantyka, walidacja)
- Z4.2: Engine do walidacji constraints na dependency graph (pattern matching
  na ścieżkach grafu)
- Z4.3: Formalne mapowanie constraints → kategorie defektów Sabra (H4)
- Z4.4: Heurystyczny generator constraints: Louvain clusters → suggested
  forbidden cross-cluster edges (zero-config → suggested config)
- Z4.5: LLM-assisted onboarding (poza scoring path): LLM analizuje strukturę
  repo → sugeruje constraints → user zatwierdza → deterministic enforcement

**Kamień milowy KM4:** Constraints engine + potwierdzone pokrycie ≥80% defektów.
**Deliverable:** D4.1 — constraints engine + mapping document.

### FAZA 2: Prace rozwojowe / eksperymentalne (miesiące 13-24)

#### WP5: CI/CD Integration + Ratchet + Temporal Analysis (mies. 13-17)
**Cel:** Implementacja AGQ jako quality gate w pipeline CI/CD oraz walidacja
mechanizmu ratchet na danych historycznych.

**Docelowy UX w CI (zero-config):**
```yaml
# .github/workflows/agq.yml — CAŁY wymagany config
- uses: agq/scan@v1
  with:
    threshold: 0.75    # opcjonalne, default 0.70
```
Pobranie single binary (~10MB, pre-built), `agq scan .`, auto-detect języków,
dependency graph, metryki, score vs threshold → PASS/FAIL jako status check na PR.
Nie wymaga konfiguracji języka, parsera ani reguł.

Zadania:
- Z5.1: GitHub Action — single binary download + `agq scan` na PR trigger.
  Pre-cached binary, startup <100ms, scan <5s. Status check na PR.
- Z5.2: GitLab CI component (analogiczny)
- Z5.3: Ratchet mechanism — persisted baseline, monotonic enforcement
- Z5.4: Dashboard webowy — trend AGQ w czasie, top violations, diff per PR
- Z5.5: REST API — integracja z dowolnym CI/CD
- Z5.6: **Retroaktywna walidacja ratchet na HPC:** uruchomienie ratchet
  na pełnej historii 30+ repo z WP1 (tysiące commitów per repo).
  Pytanie: "Gdyby AGQ gate działał od początku, ile bugów by zablokował?"
  Porównanie: commity które obniżyły AGQ → ile z nich poprzedzało bugi.
  Wymaga masowego przetwarzania historii git — naturalny workload HPC.

**Kamień milowy KM5:** Działający quality gate w GitHub Actions + GitLab CI
+ analiza retroaktywna na 30+ repo.
**Deliverable:** D5.1 — AGQ CI integration + raport retroaktywny.

#### WP6: Walidacja na kodzie AI-generated (mies. 15-20)
**Cel:** Weryfikacja H2 i H3 — centralny eksperyment projektu.

Zadania:
- Z6.1: Kontrolowany eksperyment — design:
  - 50 zadań programistycznych (zróżnicowane: CRUD, API, data pipeline, domain logic)
  - 3 LLM (Claude, GPT, open-source)
  - Grupa A: generacja z AGQ gate (ratchet + constraints)
  - Grupa B: generacja bez gate (baseline)
  - Mierzone: defect density, AGQ score, SQ score, czas do completion
- Z6.2: Analiza defect density: grupa A vs B (walidacja H2)
- Z6.3: Symulacja długoterminowa: 6 miesięcy ciągłej generacji kodu AI
  na jednym projekcie z ratchetem → pomiar quality drift (walidacja RQ4)
- Z6.4: Pomiar redukcji code review: % PR z auto-approve vs wymagających
  interwencji człowieka w grupie A (walidacja H3)
- Z6.5: Analiza jakościowa: jakie typy defektów AGQ łapie skutecznie,
  jakie przechodzą (false negatives)

**Kamień milowy KM6:** Wyniki eksperymentu z danymi statystycznymi.
**Deliverable:** D6.1 — raport eksperymentalny + paper naukowy (cel: ESEC/FSE).

#### WP7: Prototyp platformy + AI Recommendations (mies. 18-24)
**Cel:** Prototyp gotowy do walidacji z użytkownikami, z warstwą AI
generującą rekomendacje naprawcze.

Zadania:
- Z7.1: Multi-tenant architecture (SaaS)
- Z7.2: Onboarding flow (connect repo → first scan → suggested constraints)
- Z7.3: **AI-powered recommendations** — warstwa generatywna nad deterministycznym
  score. AGQ mówi "Modularity = 0.45, za niskie" ale NIE mówi co naprawić.
  LLM analizuje graf zależności i generuje konkretne sugestie:
  - "Moduł X importuje z 7 pakietów — rozważ facade pattern"
  - "Klasy A, B, C mają LCOM4=5 — rozważ podział na 3 klasy"
  - "Cykl user→order→product→user — przerwij przez dependency inversion"
  **Kluczowe: AI NIE wpływa na score.** Score deterministyczny (AGQ engine).
  Rekomendacja generatywna (LLM). Architektura: score = Rust engine,
  rekomendacja = API call do Claude/GPT, oddzielna warstwa prezentacyjna.
  Użytkownik widzi: score + co naprawić + jak naprawić.
- Z7.4: **LLM-assisted onboarding:** LLM analizuje strukturę nowego repo →
  sugeruje constraints ("wygląda na hexagonal, sugeruję: api/ nie może
  importować z domain/ bezpośrednio") → user zatwierdza → deterministic
  enforcement. Zero-config z intelligent defaults.
- Z7.5: Pilot z min. 3 zespołami developerskimi (walidacja product-market fit)
- Z7.6: Zbieranie feedbacku → iteracja na metrykach i UX
- Z7.7: Dokumentacja techniczna

**Kamień milowy KM7:** Prototyp z AI recommendations + min. 3 użytkowników.
**Deliverable:** D7.1 — platforma prototypowa (TRL 7-8).

---

## 8. POTENCJAŁ PROBLEMU I WPŁYW

### 8.1 Skala problemu

Rynek static code analysis: ~$2.5B (2026), CAGR 15%+.
Ponad 40% kodu enterprise generowane przez AI (GitHub, 2025).
Żadne narzędzie na rynku światowym nie mierzy architektury w CI gate.

AGQ jako jedyny w niezajętym kwadrancie: makro + architektura + CI + AI focus.

Pozycjonowanie względem incumbentów:
- SonarQube ($4.7B): mierzy pliki (mikro). AGQ mierzy graf (makro). Komplementarne.
- Snyk ($7.4B): security. AGQ: architecture quality. Inne domeny.
- ArchUnit: architektura, ale Java-only, nie SaaS. AGQ: multi-lang, SaaS.

### 8.2 Implikacja naukowa

Projekt adresuje trzy otwarte problemy w software engineering:

1. **Brak empirycznej walidacji metryk grafowych w CI** — metryki Newmana,
   Martina, Tarjana opisane w literaturze, ale nie zwalidowane jako
   predyktory defect density na dużej próbie.

2. **Brak badań nad jakością architektoniczną kodu AI** — Sabra et al. zbadali
   jakość per plik. Nikt nie zbadał, jak LLM wpływają na architekturę systemu
   jako całości.

3. **Brak mechanizmu ochrony przed quality drift w erze AI** — erozja
   architektoniczna (Perry & Wolf) zbadana w kontekście rozwoju ręcznego,
   nie w kontekście ciągłej generacji przez AI.

### 8.3 Implikacja praktyczna

**Dla przedsiębiorstw:** Możliwość bezpiecznego zwiększenia udziału kodu
generowanego przez AI bez ryzyka degradacji architektonicznej. Redukcja
potrzeby code review o ≥70% (H3) przy zachowaniu jakości.

**Dla branży narzędzi developerskich:** Nowa kategoria produktowa —
„Architecture Quality as a Service" / „Policy as a Service" —
komplementarna do istniejących SAST/SCA.

**Dla społeczności naukowej:** Benchmark dataset (D1.1) + empiryczna
walidacja metryk grafowych (D3.1) + pierwszy eksperyment z quality gate
dla kodu AI (D6.1) — trzy contribucje publikowalne w venue top-tier
(ICSE, ESEC/FSE, MSR).

### 8.4 Scenariusz „co jeśli nie" (bez AGQ)

Bez deterministycznego quality gate na poziomie architektury:
- Firmy zwiększają użycie AI code generation (trend nieunikniony)
- Pass@1 rośnie → więcej kodu przechodzi testy → więcej defektów na produkcji
- Code review nie skaluje się → bottleneck lub pomijane
- Quality drift przyspiesza 10-100× → masowa erozja architektoniczna
- Koszty maintenance rosną wykładniczo
- „Kod działa" ale nikt nie wie dlaczego, nikt nie umie go zmienić

AGQ przerywa to sprzężenie zwrotne wprowadzając deterministyczną barierę
jakościową w jedynym miejscu, które się skaluje: CI pipeline.

---

## 9. INNOWACYJNOŚĆ W SKALI KRAJOWEJ

### 9.1 Nowość rozwiązania — dlaczego nikt tego nie zrobił?

Poszczególne algorytmy składowe AGQ istnieją od dekad:
- Tarjan SCC: 1972 (stosowany w kompilatorach, nie eksponowany jako metryka)
- LCOM: 1994 (mierzony per klasa w SonarQube, nie agregowany na graf)
- Martin's Instability: 2003 (JDepend/Java, NDepend/.NET — per pakiet, nie CI gate)
- Louvain: 2008 (stosowany w network science, nie w software engineering)
- Cycle detection: IntelliJ IDE (warning, nie gate)

Żadne istniejące narzędzie nie złożyło tych elementów w composite score,
nie zwalidowało korelacji z defect density na dużej próbie, nie wstawiło
do CI jako gate z ratchetem, i nie skierowało na kod AI-generated.

Przyczyny:
1. Elementy pochodzą z różnych dyscyplin (teoria grafów, SE, DevOps)
   — badacze nie czytają swoich paperów nawzajem.
2. Incumbenty (SonarQube) dawały iluzję wystarczalności — nikt nie mierzył
   co SonarQube NIE łapie, aż Sabra et al. (2025) to wykazali.
3. Przed AI nie było potrzeby — człowiek pisze wolno, code review nadąża.
   AI pisze 10-100× szybciej → code review nie skaluje się → potrzeba gate.
4. JDepend/NDepend były najbliżej (Instability, Abstractness od 2001),
   ale: single-language, brak composite score, brak CI gate, brak SaaS.

AGQ jest pierwszym narzędziem łączącym:
1. Deterministyczne metryki grafowe (nie heurystyki, nie LLM — algorytmy
   z opublikowaną złożonością obliczeniową i gwarancjami)
2. Architecture-agnostic scoring (nie zakłada DDD, hexagonal ani żadnego wzorca)
3. Deklaratywne constraints architektoniczne (konfiguracja, nie kod)
4. Ratchet mechanism w CI/CD (monotoniczna ochrona przed driftem)
5. Multi-language support (tree-sitter, nie per-language parsers)
6. Specjalizację w kodzie generowanym przez AI
7. Native-performance engine (Rust) z Python ecosystem compatibility
8. AI-powered recommendations (LLM) z deterministycznym scoringiem

**Bariery wejścia — dlaczego replikacja jest trudna:**

Algorytmy są publiczne (Louvain 2008, Tarjan 1972, Martin 2003). Każdy
może napisać prototyp w Pythonie w 2 tygodnie — i to DOKŁADNIE to, co
zrobiliśmy na TRL 3. Ale prototyp ≠ produkt. Bariery:

| Bariera | Czas replikacji | Komentarz |
|---|---|---|
| Algorytmy (Louvain, Tarjan, LCOM4) | 2 tygodnie | Publiczne, trywialne |
| Rust engine + tree-sitter multi-lang | 3-6 miesięcy | Inżynieria, nie nauka |
| **Benchmark 100+ repo z ground truth** | **12+ miesięcy** | **Prawdziwy moat** |
| **Skalibrowane wagi per architektura** | **wymaga benchmarku** | Nie da się skrócić |
| ML abstractness classifier | wymaga anotacji z benchmarku | Dane = bariera |
| Ratchet + CI integration | 1-2 miesiące | Inżynieria |

**Benchmark + kalibracja = 18 miesięcy przewagi.** Kto nie ma ground truth
(defect density per repo per architektura), nie wie jakie wagi ustawić.
Kto nie wie jakie wagi, nie może powiedzieć czy AGQ=0.6 to dobrze czy źle.
A bez tego narzędzie jest bezużyteczne — kolejny dashboard z liczbami
bez kontekstu. Walidacja empiryczna na 100+ repo jest centralnym
deliverable'em projektu i jednocześnie główną barierą wejścia.

### 9.2 Porównanie z rozwiązaniami dostępnymi na rynku polskim

Na rynku polskim nie istnieje narzędzie do automatycznego pomiaru jakości
architektonicznej kodu. Polskie firmy korzystają z SonarQube (mikro),
Snyk (security), Semgrep (custom rules per plik) — żadne z nich nie
mierzy grafu zależności.

### 9.3 Porównanie z rozwiązaniami światowymi

| Cecha | SonarQube | Snyk | ArchUnit | Semgrep | CodeScene | **AGQ** |
|---|---|---|---|---|---|---|
| Poziom | Plik | Plik+deps | Pakiet | Plik | Plik+behav | **Graf** |
| Architektura | Nie | Nie | Tak | Nie | Częściowo | **Tak** |
| Deklaratywne | Nie | Nie | Nie | Tak (per plik) | Nie | **Tak** |
| Ratchet | Nie | Nie | Nie | Nie | Nie | **Tak** |
| AI code focus | Nie | Częściowo | Nie | Nie | Nie | **Tak** |
| Multi-lang | Tak | Tak | Nie (Java) | Tak | Tak | **Tak (tree-sitter)** |
| Native perf | Java | Go | Java | Go/OCaml | .NET | **Rust** |
| AI recommen. | AutoCodeRover | Nie | Nie | Nie | Nie | **Tak (LLM)** |
| SaaS | Tak | Tak | Nie | Tak | Tak | **Tak** |

**Kluczowa differentiacja technologiczna:**
- **Rust core + tree-sitter:** jedyny silnik architektoniczny w Rust; multi-language
  od dnia 1 bez osobnych parserów per język (vs ArchUnit = Java-only, SonarQube
  = osobny parser per każdy z 30 języków).
- **AI w warstwie UX, nie w scoringu:** SonarQube kupił AutoCodeRover (2025) do
  AI-fixów ale scoring nadal rule-based per plik. AGQ odwraca: scoring grafowy
  (deterministyczny), AI w rekomendacjach naprawczych (generatywny).
- **HPC-validated calibration:** żadne istniejące narzędzie nie kalibruje wag
  empirycznie na benchmarku 100+ repo. SonarQube i Semgrep mają ręcznie
  ustawione progi. AGQ wagi optymalizowane per architektura na danych.

---

## 10. SKALOWALNOŚĆ I INFRASTRUKTURA OBLICZENIOWA

### 10.1 Złożoność obliczeniowa algorytmów

| Algorytm | Złożoność | Komentarz |
|---|---|---|
| AST parsing (Python) | O(N) per plik | N = linie kodu, liniowe — BOTTLENECK |
| AST parsing (tree-sitter) | O(N) per plik | 25× szybsze, incremental |
| Graph construction | O(F + E) | F = pliki, E = importy |
| Tarjan SCC | O(V + E) | V = moduły, E = importy, liniowe |
| Louvain | O(V·log V) | Prawie liniowe |
| Martin's I per node | O(V) | Liniowe — in/out degree |
| LCOM4 per klasa | O(M²) | M = metody, małe per klasa (<50 metod) |

Wszystkie algorytmy grafowe są liniowe lub quasi-liniowe.
Bottleneck to **parsing, nie obliczenia na grafie** — dlatego Rust + tree-sitter.

### 10.2 Rozmiar grafu vs rozmiar kodu

Repo 100K LOC (5000 plików) generuje graf z ~3000-5000 node'ów
i ~5000-20000 krawędzi. To jest MALUTKI graf — petgraph (Rust) przetwarza
grafy z milionami node'ów w milisekundy, Tarjan jest liniowy.

Parsing 100K LOC → 90% czasu (Python) / 80% czasu (Rust/tree-sitter).
Metryki grafowe na grafie 5000 node'ów → <5% czasu w obu wariantach.

### 10.3 Estymacja czasu per rozmiar repo

**Python prototype (TRL 3) vs Rust engine (cel WP2):**

| Rozmiar | LOC | Python (teraz) | Rust (cel) | PR incr. (Rust) |
|---|---|---|---|---|
| Startup | 10K | ~2s | <0.1s | <0.1s |
| Mid-size SaaS | 100K | ~45s | ~1-2s | <0.5s |
| Enterprise | 500K | ~4 min | ~5-10s | ~2s |
| Duży enterprise | 1M | ~8 min | ~15-20s | ~3s |
| Monorepo | 10M+ | >1h | ~2-3 min | ~10s |

Porównanie z konkurencją:
- SonarQube na 100K LOC = 2-5 min (~550 reguł per linię)
- AGQ Rust na 100K LOC = 1-2s (mierzymy topologię grafu, nie per linię)
- **AGQ 60-150× szybsze od SonarQube** na tym samym repo

### 10.4 Architektura silnika: single binary + opcjonalne warstwy

```
Użytkownik w CI:  agq scan .  (zero-config, auto-detect)

┌─────────────────────────────────────────┐
│  agq binary (single static binary)      │  ← curl install, ~10MB
│  ├── CLI (clap)                         │  ← agq scan, agq gate
│  ├── auto-detect (rozszerzenie → lang)  │  ← *.py→Python, *.java→Java
│  └── JSON/SARIF output                  │  ← CI status check
├─────────────────────────────────────────┤
│  agq-core (Rust)                        │
│  ├── tree-sitter parser (multi-lang)    │  ← 50K LOC/s, incremental
│  │   └── extraction rules per lang      │  ← ~20 linii per język
│  ├── petgraph (dependency graph)        │  ← Louvain, Tarjan, DMS
│  ├── union-find (LCOM4)                 │  ← O(α(n)) per operację
│  └── rayon (parallel parsing)           │  ← N cores = N× szybciej
├─────────────────────────────────────────┤
│  PyO3 wrapper (opcjonalny)              │  ← pip install agq-core
├─────────────────────────────────────────┤
│  ML classifier (abstrakcyjność)         │  ← ONNX Runtime, wbudowany w binary
├─────────────────────────────────────────┤
│  LLM recommendations (opcjonalne)       │  ← Claude/GPT API, SaaS only
└─────────────────────────────────────────┘

Dystrybucja:
  CI:     curl -sSf https://agq.dev/install | sh && agq scan .
  Python: pip install agq-core && python -c "import agq_core"
  Action: uses: agq/scan@v1
```

### 10.5 Strategie optymalizacji

**Incremental parsing (tree-sitter native):** Tree-sitter ma wbudowany
incremental parsing — edycja pliku wymaga re-parse tylko zmienionego
fragmentu. Cache grafu per commit, invalidate per zmieniony plik.
PR zmienia typowo 5-20 plików → scan <1s nawet dla 1M LOC repo.

**Parallel parsing (rayon):** Pliki są niezależne → wielowątkowość.
Rayon (Rust work-stealing scheduler): N rdzeni ≈ N× szybszy parsing.
CI runnery mają 2-8 rdzeni; HPC nodes 32-128.

**Granulacja node'ów:** Opcja coarse (node = pakiet zamiast plik)
redukuje graf 10-50× dla monorepo. Przełącznik per konfigurację.

**Two-pass architecture:** Shallow pass (importy only, O(N) szybki)
generuje dependency graph. Deep pass (LCOM4, metody, atrybuty) — on-demand,
tylko dla modułów z niskim score lub na żądanie.

### 10.6 Wykorzystanie HPC w projekcie

HPC jest wykorzystywane w 3 fazach projektu — NIE do uruchamiania AGQ
na pojedynczym repo (to działa na laptopie), lecz do **masowego
przetwarzania benchmarku i kalibracji**:

| Faza | Zadanie | Skala | Bez HPC | Z HPC |
|---|---|---|---|---|
| WP1 | Ekstrakcja grafów z historii 100+ repo | ~500K snapshotów | Tygodnie | Godziny |
| WP3 | Kalibracja wag (grid search 4D × 6 arch × 5-fold) | ~10K konfiguracji × 100 repo | Miesiąc | Dni |
| WP3 | Analiza temporalna (Granger causality) | ~500K par (commit, bugs) | Tygodnie | Godziny |
| WP5 | Retroaktywna walidacja ratchet | ~100K commitów × 30 repo | Tygodnie | Godziny |

Architektura HPC: Slurm/PBS job scheduler, 1 repo = 1 task (embarrassingly
parallel). Brak potrzeby GPU — obliczenia czysto CPU-bound (grafowe).

### 10.7 Rola AI w projekcie — uczciwe podsumowanie

AI jest wykorzystywana w AGQ w 3 warstwach, z jasnym rozgraniczeniem:

| Warstwa | Rola AI | Determinizm | Wymagana? |
|---|---|---|---|
| **Pre-scoring** | ML classifier abstrakcyjności (Z2.3) | Deterministyczny (ONNX, frozen model) | Opcjonalna (fallback: heurystyka AST) |
| **Pre-scoring** | LLM pre-anotacja benchmarku (Z1.5) | Nie — human review required | Tylko w fazie badawczej |
| **Scoring** | BRAK — metryki deterministyczne | TAK | — |
| **Post-scoring** | LLM rekomendacje naprawcze (Z7.3) | Nie — generatywne | Opcjonalna (warstwa UX) |
| **Post-scoring** | LLM-assisted onboarding (Z7.4) | Nie — sugestie, user zatwierdza | Opcjonalna |

**Zasada: LLM NIGDY w scoring path.** Score jest deterministyczny —
ten sam kod = ten sam wynik, zawsze. AI wzmacnia dane wejściowe
(classifier abstrakcyjności) i interpretuje wyniki (rekomendacje),
ale NIE liczy score'u.

### 10.8 Target performance

Cel produkcyjny (TRL 7-8):
- Full scan: <5s na repo 100K LOC (Rust engine, single CI runner)
- PR scan: <1s incremental na repo do 1M LOC
- Benchmark processing: <1h na 100+ repo z pełną historią (HPC, 100 rdzeni)

---

## 11. ANALIZA RYZYK BADAWCZYCH

| # | Ryzyko | Prawdop. | Wpływ | Mitygacja |
|---|---|---|---|---|
| R1 | Korelacja AGQ vs DD < 0.5 (H1 odrzucona) | Średnie | Wysoki | Zwiększenie N, dodatkowe metryki grafowe, analiza per-język, analiza nieliniowa |
| R2 | Tree-sitter nie pokrywa edge cases parsowania | Niskie | Średni | Fallback na AST per język, community parsers, testy na 100+ repo |
| R3 | Wagi w1-w4 niestabilne cross-language | Średnie | Średni | Per-language weights, meta-learning, walidacja cross-validation |
| R4 | Ratchet zbyt restrykcyjny (blokuje valid PRs) | Średnie | Średni | Configurable tolerance (±δ), per-metric thresholds, override z audit log |
| R5 | SonarQube doda metryki grafowe (competitive response) | Niskie | Wysoki | First-mover advantage, focus na AI code, open-source community |
| R6 | LLM stają się lepsze architektonicznie (problem znika) | Niskie | Wysoki | AGQ wartościowy również dla kodu ręcznego; SWE-bench Pro 2026 = 23% multi-file — problem daleki od rozwiązania |
| R7 | Korelacja AGQ nie utrzymuje się cross-architecture (H5 odrzucona) | Średnie | Wysoki | Per-architecture wagi, constraints Level 2 jako fallback, analiza które metryki failują i dlaczego |
| R8 | Skalowalność na dużych repo (>1M LOC) | Niskie | Średni | Rust engine (25×), incremental tree-sitter, coarse granulacja, parallel parsing (rayon) |
| R9 | Rust engine nie osiąga target performance | Niskie | Średni | Fallback: Python prototype z igraph (C bindings) zamiast networkx; tree-sitter ma Python bindings (py-tree-sitter) |
| R10 | ML classifier abstrakcyjności niedokładny | Średnie | Niski | Fallback: heurystyka AST (ABC/Protocol/@abstractmethod) — gorszy recall ale zero false positives. Classifier opcjonalny |

---

## 12. OCHRONA WŁASNOŚCI INTELEKTUALNEJ (DRAFT)

### 12.1 Wzór użytkowy (Urząd Patentowy RP)

Planowany termin zgłoszenia: miesiąc 12-15 (po walidacji WP3).

Przedmiot zgłoszenia: „System do automatycznego pomiaru i egzekwowania
jakości architektonicznej kodu źródłowego w pipeline CI/CD, obejmujący:
(a) ekstrakcję grafu zależności z kodu źródłowego wielojęzycznego,
(b) wyznaczanie composite score jakości architektonicznej na podstawie
metryk grafowych (modularność, acykliczność, stabilność, spójność),
(c) deklaratywną konfigurację reguł architektonicznych (constraints),
(d) mechanizm monotonicznej ochrony przed degradacją (ratchet)."

Uzasadnienie wyboru wzoru użytkowego zamiast patentu:
- Niższy próg nowości (nie wymaga „poziomu wynalazczego")
- Rejestracja 6-12 mies. (patent: 2-4 lata — przekracza horyzont projektu)
- Koszt ~3-5K PLN (patent: 20-50K PLN)
- Ochrona 10 lat
- Oprogramowanie per se nie podlega ochronie patentowej w EU;
  wzór użytkowy chroni rozwiązanie techniczne (system/proces),
  nie algorytm

### 12.2 Tajemnica przedsiębiorstwa (trade secret)

Elementy chronione jako know-how (nie publikowane, nie w open-source):

| Element | Uzasadnienie |
|---|---|
| Wagi w1-w4 composite score | Kluczowy wynik kalibracji WP3 — odtworzenie score wymaga tych wag |
| Kalibracja per język/architektura | Know-how z walidacji na 100+ repo |
| Heurystyki optymalizacyjne parsera | Progi shallow/deep, strategie cache |
| Thresholdy ratchet (tolerance δ) | Tuning z pilotaży enterprise |
| Presety constraints per branża | Gotowe szablony — wynik analizy 100+ repo |

Zabezpieczenie formalne:
- Klauzule poufności w umowach z zespołem B+R i podwykonawcami
- Oznaczenie dokumentów wewnętrznych jako „TAJEMNICA PRZEDSIĘBIORSTWA"
- Ograniczony dostęp (nie w open-source repozytorium)
- Regulamin ochrony informacji w firmie

### 12.3 Prawa autorskie (copyright)

Ochrona automatyczna (bez rejestracji) obejmuje:
- Kod źródłowy AGQ (implementacja algorytmów, pipeline, SaaS)
- Dokumentację techniczną i użytkownika
- Benchmark dataset (ochrona sui generis baz danych w EU — Dyrektywa 96/9/WE)
- Publikacje naukowe (2 papery)

### 12.4 Model licencyjny — open core

```
agq-core (licencja MIT, open-source):
  - Algorytmy (Louvain, Tarjan, Martin, LCOM4)
  - CLI (command-line interface)
  - Formuła AGQ (publiczna — opisana w paperze naukowym)
  - GitHub Action (basic, free)
  Cel: budowanie community, adopcja, zaufanie, cytowania naukowe

agq-cloud (licencja proprietary, SaaS):
  - Wagi w1-w4 i kalibracja (trade secret)
  - Suggested constraints (trade secret)
  - Dashboard webowy, ratchet persistence
  - Multi-tenant, SSO, audit log, compliance
  - Incremental cache, optymalizacje wydajnościowe
  Cel: monetyzacja, revenue
```

Precedensy rynkowe: Semgrep (open-source engine + proprietary cloud),
GitLab (open core), Elastic (open-source + proprietary features).

### 12.5 Publikacje naukowe jako ochrona pierwszeństwa

2 planowane publikacje (D3.1, D6.1) pełnią podwójną rolę:
- Utrwalenie pierwszeństwa naukowego (prior art — utrudnia patentowanie
  konkurentom tego samego podejścia)
- Budowanie rozpoznawalności i wiarygodności marki AGQ

### 12.6 Podsumowanie strategii IP

| Warstwa ochrony | Co chroni | Koszt | Termin |
|---|---|---|---|
| Wzór użytkowy | System/proces AGQ jako całość | ~3-5K PLN | Mies. 12-15 |
| Trade secret | Wagi, kalibracja, heurystyki, presety | ~0 PLN (klauzule) | Od mies. 1 |
| Copyright | Kod, dokumentacja, dataset | 0 PLN (automatyczny) | Od mies. 1 |
| Open core model | Rozdział: community (MIT) vs revenue (prop.) | 0 PLN | Od mies. 6 |
| Publikacje | Pierwszeństwo naukowe, prior art | Wliczone w WP3/WP6 | Mies. 12, 20 |

---

## 13. REFERENCJE NAUKOWE

1. Sabra A., Schmitt O., Tyler J. (2025). Assessing Quality & Security of LLM-Generated Code. Preprint 2508.14727.
2. Perry D., Wolf A. (1992). Foundations for the Study of Software Architecture. ACM SIGSOFT Software Engineering Notes.
3. Garcia J., Ivkovic I., Medvidovic N. (2013). A Comparative Analysis of Software Architecture Recovery Techniques. IEEE/ACM ASE.
4. Ford N., Parsons R., Kua P. (2017). Building Evolutionary Architectures: Support Constant Change. O'Reilly.
5. Kruchten P., Nord R., Ozkaya I. (2012). Technical Debt: From Metaphor to Theory and Practice. IEEE Software.
6. Martin R. (2003). Agile Software Development: Principles, Patterns, and Practices. Prentice Hall.
7. Newman M. (2006). Modularity and Community Structure in Networks. PNAS 103(23).
8. Chidamber S., Kemerer C. (1994). A Metrics Suite for Object-Oriented Design. IEEE TSE 20(6).
9. McCabe T. (1976). A Complexity Measure. IEEE TSE SE-2(4).
10. ISO/IEC 25010:2011. Systems and Software Quality Requirements and Evaluation (SQuaRE).
11. Tarjan R. (1972). Depth-First Search and Linear Graph Algorithms. SIAM Journal on Computing.
12. Blondel V. et al. (2008). Fast Unfolding of Communities in Large Networks. JSTAT.
13. EvoCodeBench (2025). Preprint 2602.10171.
14. ProxyWar (2025). Preprint 2602.04296.
15. Chen M. et al. (2021). Evaluating Large Language Models Trained on Code. Preprint 2107.03374. (HumanEval)
16. Scale AI (2026). SWE-Bench Pro: Can AI Agents Solve Long-Horizon Software Engineering Tasks? https://scale.com/leaderboard/swe_bench_pro_public
17. DependEval: Benchmarking LLMs for Repository Dependency Understanding (2025). ACL Findings. https://aclanthology.org/2025.findings-acl.373.pdf
18. Liu N.F. et al. (2024). Lost in the Middle: How Language Models Use Long Contexts. TACL 12, 157-173. https://arxiv.org/abs/2307.03172
19. Zhang T. et al. (2025). Code Graph Model (CGM): A Graph-Integrated Large Language Model for Repository-Level Software Engineering Tasks. arXiv 2505.16901.
20. Retrieval-Augmented Code Generation: A Survey with Focus on Repository-Level Approaches (2025). arXiv 2510.04905.
21. Databricks (2025). Long Context RAG Performance of LLMs. https://www.databricks.com/blog/long-context-rag-performance-llms
22. Nature Machine Intelligence (2025). Densing Law of LLMs. https://www.nature.com/articles/s42256-025-01137-0
23. Tree-sitter (2018-). Brunsfeld M. et al. Tree-sitter — An incremental parsing system for programming tools. https://tree-sitter.github.io/tree-sitter/
24. petgraph (2015-). Bluss et al. Graph data structure library for Rust. https://github.com/petgraph/petgraph
25. PyO3 (2017-). Rust bindings for Python. https://pyo3.rs/
26. Blondel V. et al. (2008). Louvain method: Fast Unfolding of Communities in Large Networks. JSTAT P10008. [benchmarki: >10M nodes w sekundy]
27. Akiba T. et al. (2019). Optuna: A Next-generation Hyperparameter Optimization Framework. KDD. [Bayesian optimization do kalibracji wag]
