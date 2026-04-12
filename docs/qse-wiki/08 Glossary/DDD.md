---
type: glossary
language: pl
---

# DDD — Domain-Driven Design

## Prostymi słowami

DDD to sposób projektowania oprogramowania, w którym centrum jest „dziedzina" — czyli rzeczywisty problem biznesowy. Zamiast myśleć „co baza danych może przechowywać", myślisz „co bank naprawdę robi z kontem klienta". DDD daje słownik: encja, agregat, kontekst, serwis domenowy — każde pojęcie ma precyzyjne znaczenie i miejsce w kodzie.

## Szczegółowy opis

**Domain-Driven Design (DDD)** to podejście do projektowania oprogramowania wprowadzone przez Erica Evansa (2003). Kluczową ideą jest, że złożoność oprogramowania powinna być zarządzana przez **odzwierciedlenie domeny biznesowej** w strukturze kodu.

### Podstawowe pojęcia DDD

| Pojęcie | Opis | Przykład |
|---|---|---|
| **Entity** (Encja) | Obiekt z tożsamością — istnieje niezależnie od atrybutów | Konto bankowe (ma unikalny numer) |
| **Value Object** | Obiekt bez tożsamości — równość przez wartości | Kwota (100 PLN = 100 PLN) |
| **Aggregate** | Klaster encji z jednym korzeniem | Zamówienie + pozycje + adres |
| **Aggregate Root** | Punkt wejścia do agregatu | Order (zarządza OrderLines) |
| **Domain Service** | Logika biznesowa, która nie pasuje do encji | TransferService(from, to, amount) |
| **Repository** | Hermetyzacja dostępu do danych | OrderRepository.findById() |
| **Bounded Context** | Granica semantyczna modelu | Kontekst „Sprzedaży" vs. „Magazynu" |
| **Ubiquitous Language** | Wspólny słownik biznes + dev | „Zamówienie" = jedno pojęcie w obu światach |

### DDD w kontekście QSE

QSE używa DDD jako **opcjonalny preset** (Level 2), nie jako warunek walidacji. Architektura DDD powinna dawać wysokie wyniki AGQ — to test face validity:

| Wniosek DDD | Oczekiwanie AGQ | Wynik (GT Java) |
|---|---|---|
| Wyraźne Bounded Context | Wysoka Modularity (M) | Potwierdzone: M(POS) > M(NEG) |
| Strict layer separation | Wysoka Stability (S) | Potwierdzone: S(POS)=0.344 vs S(NEG)=0.238 |
| Bogata logika domenowa | Wysoka Cohesion (C) | Potwierdzone: C(POS)=0.393 vs C(NEG)=0.269 |
| Acykliczne zależności | Wysoka Acyclicity (A) | Potwierdzone |

Repozytoria DDD w GT Java z panelem ≥ 7.0:
- `citerus/dddsample-core` — klasyczny przykład DDD (panel=8.25)
- `VaughnVernon/IDDD_Samples` — „Implementing DDD" Vernona (panel=7.75)
- `ddd-by-examples/library` — wzorcowa aplikacja (panel=8.50)

### Preset DDD w QSE

```bash
qse agq /projekt --preset ddd
```

Preset DDD (`qse/presets/ddd/`) dodaje:
- **Detektory DDD** — wykrywa naruszenia architectural rules (np. domain importuje infrastructure)
- **Forbidden edges** — `domain/*` → `infrastructure/*` zabronione
- **Gate DDD** — dodatkowe metryki warstw

Preset jest **opt-in** — nie wymagany do podstawowego działania. Można go używać niezależnie od tego, czy projekt używa DDD.

### DDD Level 2 vs. Level 1

```
Level 1 (zero-config):  AGQ Core — metryki grafowe, architecture-agnostic
Level 2 (opt-in):       Constraints + presets (DDD, hexagonal, clean)
```

QSE jest **architecture-agnostic** na Level 1 — mierzy cechy grafu, nie wzorzec. Wzorzec pojawia się dopiero na Level 2 jako deklaratywna polityka.

## Definicja formalna

DDD definiuje hierarchię modeli przez Bounded Contexts z relacjami: Partnership, Shared Kernel, Customer-Supplier, Conformist, Anticorruption Layer (ACL), Open Host Service, Published Language.

W notacji AGQ: poprawna architektura DDD to taka, gdzie graf G = (V, E) można podzielić na spójne podgrafy G₁...Gₖ (Bounded Contexts) z minimalnymi krawędziami między nimi (wysokie M) i acyklicznym grafem zależności między kontekstami (A = 1).

## Zobacz też

- [[AGQ|AGQ]] — metryka architektoniczna
- [[Layer|Warstwa]] — hierarchia w architekturze
- [[CRUD|CRUD]] — podejście bez domeny
- [[07 Benchmarks/Java GT Dataset|Java GT Dataset]] — repozytoria DDD w GT
- [[11 Research/Research Thesis|Teza badawcza]] — DDD jako wzorzec referencyjny
