---
type: research
language: pl
---

# Ograniczenia i uczciwe zastrzeżenia

## Prostymi słowami

Każde narzędzie naukowe ma ograniczenia — i uczciwe ich opisanie jest znakiem dojrzałości projektu. QSE wie, co mierzy dobrze, a czego nie. Ten dokument to mapa znanych limitów, nie lista wymówek.

> „Nie upraszczaj danych — podawaj pełne wyniki" — styl wiki QSE.

---

## L1 — Language Bias (bias językowy)

### Opis
Formuła AGQ jest inaczej kalibrowana dla każdego języka i nie jest bezpośrednio porównywalna między językami:

| Język | Formuła | Kalibracja |
|---|---|---|
| Java | 0.20·M + 0.20·A + 0.20·S + 0.20·C + 0.20·CD | n=59 GT + Jolak |
| Python | 0.15·M + 0.05·A + 0.20·S + 0.10·C + 0.15·CD + 0.35·flat_score | n=74 OSS (kalibracja eksperymentalna) |
| Go | 0.20·M + 0.20·A + 0.20·S + 0.20·C + 0.20·CD | Brak GT, n=30 benchmark |
| TypeScript | 0.20·M + 0.20·A + 0.20·S + 0.20·C + 0.20·CD | 73% repo nodes=0 — NIEWIARYGODNE |

### Konsekwencje
- Nie można bezpośrednio porównywać AGQ Java=0.70 z AGQ Python=0.70
- TypeScript dane w benchmarku iter6 są artefaktem parsera, nie rzeczywistą oceną
- Go ma zbyt mały benchmark (n=30) do silnych wniosków statystycznych

### Plan naprawy
- Cross-language unification przez normalizację per-język
- Naprawa parsera TypeScript
- Rozszerzenie benchmarku Go do n≥50

---

## L2 — Małe projekty (Small Project Bias)

### Opis
Projekty o małej liczbie węzłów (n_nodes < 20) mogą mieć sztucznie wysokie AGQ:
- Brak węzłów = brak krawędzi = brak cykli → Acyclicity = 1.0
- Mało modułów = łatwa separacja → wysoka Modularity
- Prosta struktura = czyste klasy → wysoka Cohesion

**Efekt:** małe, proste projekty mogą wyglądać doskonale architektonicznie, mimo że są po prostu małe.

### Empiryczny dowód
Z benchmarku spaghetti vs mainstream (n=9 spaghetti repo):
- Mediana węzłów spaghetti: **7** (vs 97 w mainstream)
- AGQ mean spaghetti: **0.694** (vs 0.634 w mainstream) — paradoksalnie wyższy!
- Ale smells/KLOC: 43.04 vs 12.20 (3.5× więcej problemów w spaghetti)

### Konsekwencje
- Benchmarki z małymi projektami mogą zaniżać wykrywanie problemów architektonicznych
- AGQ nie jest dobrym narzędziem dla projektów < 20 węzłów (skrypty, przykłady)
- Zbiór spaghetti OSS był zbyt mały (n_nodes ≈ 7) do rzetelnej oceny

### Plan naprawy
- Próg minimalny: ostrzeżenie gdy n_nodes < 20
- Skalowanie: AGQ-adj (AGQ normalizowany na rozmiar projektu)
- Category-aware normalization

---

## L3 — Kalibracja OSS-Python (bias próby)

### Opis
Wagi AGQ Python-specific były kalibrowane na zbiorze OSS-Python n=74–80 repozytoriów wybranych z popularnych projektów GitHub. Zbiór ten ma systematyczny bias:
- **Stars bias:** wybrano popularne projekty → mogą być lepiej utrzymane od średniego projektu komercyjnego
- **Framework dominacja:** Flask, Django, FastAPI, Requests dominują → nie reprezentują aplikacji domenowych
- **Brak closed-source:** cały benchmark to OSS — kod korporacyjny może mieć inne charakterystyki

### Konsekwencje
- Wagi AGQ Python mogą nie być optymalne dla projektów korporacyjnych
- Progi (AGQ < 0.55 = TANGLED) kalibrowane na OSS mogą być błędne dla enterprise
- `flat_score` z wagą 0.35 to heurystyka, nie wynik rygorystycznej optymalizacji

### Empiryczne potwierdzenie problemu
Python GT (n=30): problem odwróconego kierunku dla Modularity. Wagi OSS-Python nie przenoszą się dobrze nawet na małe GT. Sugeruje to konieczność osobnej kalibracji per typ projektu.

### Plan naprawy
- Rozszerzenie GT Python do n≥50
- Category-aware normalization
- Walidacja na projektach korporacyjnych (WP5 grantu)

---

## L4 — Brak walidacji przemysłowej

### Opis
Cała walidacja QSE opiera się na publicznych repozytoriach open-source (GitHub). Nie przeprowadzono żadnej walidacji na zamkniętym kodzie korporacyjnym (closed-source).

### Dlaczego to problem
- Kod korporacyjny może mieć inne wzorce architektoniczne niż OSS
- AGQ kalibrowane na OSS może być błędnie skalibrowane dla enterprise
- Nie wiadomo, jak AGQ radzi sobie z mikrousługami, monorepo, wewnętrznymi bibliotekami

### Obecna odpowiedź
- Walidacja face validity na 4 projektach Apache Java → ranking zgodny z Dai et al. (Nature Scientific Reports) — ograniczona wiarygodność
- Jolak cross-validation: 8 projektów enterprise-ish (ale OSS, nie zamknięty kod)

### Plan naprawy
- WP5 grantu FENG: partnerstwa z firmami, dostęp do closed-source
- Walidacja na co najmniej 2 firmach partnerskich

---

## L5 — Panel ekspertów symulowany

### Opis
Etykiety Ground Truth (POS/NEG) są generowane przez **symulowany panel** 4 recenzentów — nie przez prawdziwych, niezależnych ekspertów architektonicznych.

### Konsekwencje
- Potencjalny bias autora symulacji
- Brak inter-rater reliability na prawdziwych ekspertach
- Panel Score nie jest porównywalny z opiniami rzeczywistych architektów

### Obecna odpowiedź
- Procedura panelowa jest udokumentowana i powtarzalna
- Zgodność wyników z niezależnymi pracami (Jolak, Dai) sugeruje, że panel nie jest systematycznie błędny
- σ ≤ 2.0 jako kryterium akceptacji eliminuje skrajne przypadki

### Plan naprawy
- Badanie inter-rater reliability z 3+ prawdziwymi ekspertami
- Weryfikacja panelu na podzbioru GT przez zewnętrznych recenzentów (WP5)

---

## L6 — Brak predykcji — tylko pomiar

### Opis
AGQ mierzy jakość architektoniczną **w danym momencie** — jest miarą statyczną. Nie przewiduje przyszłych problemów, nie mówi kiedy architektura zacznie się degradować, nie szacuje ryzyka.

> Analogia: rentgen (co jest teraz) vs historia medyczna + prognoza (co może się stać).

### Konsekwencje
- AGQ=0.75 dzisiaj nie mówi nic o AGQ=? za 6 miesięcy
- Brak alertu o trendzie degradacji
- Nie nadaje się do wyznaczania momentu potrzeby refaktoryzacji

### Plan naprawy
- Warstwa Predictor (Kierunek 4 w [[11 Research/Future Directions|Future Directions]])
- Wymaga: benchmark longitudinalny (historia AGQ per commit per repo)

---

## L7 — Ograniczenia parsera (skanera)

### Opis
Skaner QSE ma znane ograniczenia wykrywania:

| Problem | Język | Status |
|---|---|---|
| TypeScript nodes=0 (73% repo) | TypeScript | Aktywny bug |
| Django false-negative (P3) | Python | Znany, odłożony |
| Abstrakcyjność klas — heurystyka | Python | Częściowe rozwiązanie |
| Namespace packages Python | Python | Partial support |
| Intra-package detection | Java | Potrzeba poprawy |

### Konsekwencje
- TypeScript dane benchmarku są niewiarygodne
- Django i podobne projekty mogą być błędnie klasyfikowane
- Heurystyki detekcji klas abstrakcyjnych (ABC, Protocol) mogą zawodzić

### Plan naprawy
- Naprawa parsera TypeScript (priorytet P1)
- Poprawiona detekcja struktury wewnętrznej paczki Django
- Benchmark dla skanerów: znane-poprawne vs znane-błędne wyniki

---

## Podsumowanie tabelaryczne

| ID | Ograniczenie | Wpływ | Status naprawy |
|---|---|---|---|
| L1 | Language bias — różne formuły per język | Wysoki | Planowana (cross-language unification) |
| L2 | Małe projekty — artefakty metryk | Średni | Częściowe (próg ostrzegawczy) |
| L3 | Kalibracja OSS-Python — bias próby | Wysoki | Planowana (rozszerzenie GT) |
| L4 | Brak walidacji przemysłowej | Wysoki | Planowana (WP5 FENG) |
| L5 | Panel symulowany | Średni | Planowana (prawdziwy panel WP5) |
| L6 | Brak predykcji | Średni | Planowana (Predictor layer) |
| L7 | Ograniczenia parsera | Wysoki (TS) | Aktywne (TypeScript fix) |

---

## Definicja formalna — uczciwość naukowa

Zgodnie z filozofią projektu QSE: wszystkie ograniczenia są jawnie dokumentowane i nie są ukrywane. Każdy wynik prezentowany jest z kontekstem metodologicznym. Celem jest budowanie zaufania przez transparentność, nie przez ukrywanie słabości.

Porównaj z wymaganiami FENG SMART B+R: projekt musi wykazać aktualny stan (TRL 3) i realistyczny plan dojścia do TRL 7-8 — co wymaga jawnego opisu ograniczeń obecnego etapu.

---

## Zobacz też

- [[11 Research/Future Directions|Kierunki badań]] — jak planujemy naprawić ograniczenia
- [[11 Research/Research Thesis|Teza badawcza]] — pytania badawcze (uwzględniają ograniczenia)
- [[07 Benchmarks/Python GT Dataset|Python GT]] — L1, L3 in action
- [[07 Benchmarks/Benchmark 558|Benchmark 558]] — L2, L7 in action
- [[10 Handbook/QSE Podrecznik|Podręcznik QSE]] — sekcja 10 Ograniczenia
