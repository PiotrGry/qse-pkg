---
type: guide
audience: beginner
language: pl
---

# Zacznij tutaj

## Prostymi słowami

Wyobraź sobie, że kupujesz używane mieszkanie. Możesz sprawdzić czy ściany są czyste, czy okna nie są pobrudzone, czy żarówki działają — to jakość na poziomie „cegieł". Ale czy ściany nośne stoją w dobrych miejscach? Czy instalacja elektryczna nie krzyżuje się z wentylacją? Tego samym okiem nie widać. QSE robi dokładnie to samo dla oprogramowania: sprawdza **budynek**, nie cegły.

---

## Czego dowiesz się z tej wiki

Ta wiki wyjaśnia projekt **QSE — Quality Score Engine** na trzech poziomach głębokości:

1. **Prostymi słowami** — analogie i intuicja, bez wiedzy technicznej
2. **Szczegółowy opis** — jak to naprawdę działa, diagramy, tabele z danymi
3. **Definicja formalna** — wzory, p-value, dane empiryczne z eksperymentów

Możesz czytać dowolnym poziomem — każda strona ma wszystkie trzy.

---

## Dlaczego QSE powstał

Każdy projekt oprogramowania zaczyna się od prostego pomysłu. Po kilku miesiącach ma dziesiątki modułów, setki klas, tysiące funkcji. Nikt tego specjalnie nie planuje złośliwie — moduł A potrzebuje czegoś z modułu B, więc ktoś dodaje import. Za tydzień B potrzebuje czegoś z C, C z D, D z A. Mamy cykl. System zaczyna „rozmawiać sam ze sobą".

Z zewnątrz kod wygląda normalnie. Testy przechodzą. CI jest zielone. Ale zmiana jednej rzeczy wymaga zmian w pięciu innych miejscach. Bugi pojawiają się w miejscach pozornie niezwiązanych ze zmianą. To jest **dług architektoniczny** — i większość narzędzi go nie wykrywa.

**SonarQube** analizuje każdy plik osobno i dobrze wykrywa błędy, code smells i luki bezpieczeństwa. Ale **nie patrzy na graf zależności** — nie wie, jak moduły są ze sobą powiązane i czy ta sieć powiązań ma zdrową strukturę. QSE wypełnia tę lukę.

Szczegóły: [[Why QSE Exists]]

---

## Cztery właściwości dobrej architektury

QSE pyta o cztery konkretne rzeczy:

| Właściwość | Analogia | Pytanie | Jeśli źle... |
|---|---|---|---|
| **Modularność** | Dzielnice w mieście | Czy moduły są wyraźnie od siebie oddzielone? | Zmiana jednego dotyka wszystkich |
| **Brak cykli** | Hierarchia w firmie | Czy zależności idą w jednym kierunku? | Nie można zmienić nic bez zmieniania wszystkiego |
| **Warstwowość** | Armia z rangami | Czy system ma wyraźne „jądro" i „obrzeże"? | Nikt nie wie co jest ważne |
| **Spójność** | Pracownik z jednym stanowiskiem | Czy każda klasa robi jedną rzecz? | Klasy to „człowiek-orkiestra" — trudne w testowaniu |

Szczegóły z formułami: [[AGQ Formulas]]

---

## Analogia: miasto vs spaghetti

**Dobrze zaprojektowane miasto:**
- Ma dzielnice — mieszkalna, przemysłowa, centrum
- Granice między dzielnicami są jasne (drogi główne, nie podwórka)
- Zamknięcie jednej uliczki nie zatrzymuje ruchu w całym mieście

**Miasto bez planu:**
- Każdy budował gdzie chciał
- Każde podwórko połączone z każdym innym
- Zamknięcie jednej uliczki blokuje połowę ruchu, bo 47 tras przypadkowo tędy biegnie

W oprogramowaniu „miasto bez planu" to **big ball of mud** — najgorszy anty-pattern architektoniczny, gdzie wszystko zależy od wszystkiego.

QSE mierzy, w którą stronę zmierza Twój projekt.

---

## Jak działa QSE — w skrócie

```
Kod źródłowy
    ↓ skaner Rust (< 1 sekunda)
Graf zależności między modułami
    ↓ cztery algorytmy grafowe
AGQ = liczba [0, 1] z wyjaśnieniem
    ↓ Quality Gate w CI/CD
PASS lub FAIL z rekomendacją
```

Szczegóły krok po kroku: [[How QSE Works Simply]]

---

## Trzy ścieżki czytania

### Ścieżka 1 — Nowy czytelnik (student, junior developer)
Zacznij tu i czytaj w tej kolejności:

1. **Ta strona** ✓
2. [[What is QSE in Simple Words]] — pełne wyjaśnienie czym jest QSE
3. [[Why QSE Exists]] — problem który rozwiązuje
4. [[How QSE Works Simply]] — pipeline krok po kroku
5. [[Current State in Simple Words]] — co już działa

### Ścieżka 2 — Technik (senior developer, architekt)
Znasz temat, chcesz szczegóły:

1. [[QSE Canon]] — precyzyjna definicja projektu
2. [[Architecture]] — architektura 5-warstwowa
3. [[AGQ Formulas]] — wzory, kalibracja, wagi
4. [[Scanner]] — jak działa skaner, znane bugi i historia
5. [[Invariants]] — niezmienniki projektu

### Ścieżka 3 — Badacz (PhD, researcher)
Chcesz zrozumieć metodologię:

1. [[Ground Truth]] — pełne dane GT Java n=59, Python n=30
2. [[Hypotheses Register]] — W1–W10, co obalono, co potwierdzone
3. [[Experiments Index]] — protokoły E1–E6
4. [[Current Priorities]] — co jest następne (P0–P4)

---

## Warto wiedzieć przed lekturą

- Do przeczytania pierwszych stron **nie jest potrzebna wiedza programistyczna** — analogie wystarczą
- Gdy strona używa trudniejszego pojęcia, zawiera link do prostszej notatki
- Dane empiryczne są konkretne: nie „wyniki są dobre", ale „MW p=0.000221, n=59, AUC=0.767"
- Projekt ma uczciwe zastrzeżenia — każda strona mówi co zostało udowodnione, a co jest jeszcze otwarte
- Wikilinki `[[...]]` prowadzą do powiązanych stron (kliknij w Obsidian)

---

## Zobacz też
[[Home]] · [[What is QSE in Simple Words]] · [[Why QSE Exists]] · [[How QSE Works Simply]] · [[QSE Canon]]
