# Metryki AGQ — proste wyjaśnienia (2026-03-06)

## Modularity (Q) — "Czy klocki leżą w swoich pudełkach?"

Masz klocki Lego. Czerwone to samochody, niebieskie to domki, zielone to drzewka.

Dobrze: Czerwone w jednym pudełku, niebieskie w drugim, zielone w trzecim.
Jak chcesz zbudować samochód — sięgasz do jednego pudełka.

Źle: Wszystko wymieszane. Żeby zbudować samochód musisz grzebać we wszystkich.

Mierzy: czy rzeczy które do siebie pasują są razem, a te które nie pasują — osobno?

Formalnie: Newman's Modularity Q via Louvain community detection na grafie importów.

---

## Acyclicity — "Czy nie chodzisz w kółko?"

Instrukcja budowania: 1. koła → 2. rama → 3. przyczep koła.

Dobrze: Jasna kolejność. Krok 1 → 2 → 3. Gotowe.

Źle: "Żeby zbudować koła potrzebujesz ramy, ale żeby zbudować ramę potrzebujesz kół."
Chodzisz w kółko.

Mierzy: czy da się zbudować wszystko po kolei, bez chodzenia w kółko?

Formalnie: 1 - (nodes_in_cycles / total_nodes) via Tarjan SCC.

---

## Stability — "Czy fundamenty są stabilne a dekoracje łatwe do zmiany?"

Fundament (podłoga, ściany) — trzyma wszystko, nie wolno go ruszać.
Dekoracja (kwiatek na parapecie) — nic na nim nie stoi, można zmieniać.

Dobrze: Fundamenty mocne i stabilne. Dekoracje łatwo wymienić.
Źle: Kwiatek trzyma ścianę. Ruszysz kwiatek → dom się wali.

Mierzy: czy ważne rzeczy są stabilne, a mało ważne — łatwe do zmiany?

Formalnie: 1 - mean(|A + I - 1|) per moduł (Martin's Distance from Main Sequence).

---

## Cohesion (LCOM) — "Czy Twój plecak ma sens?"

Dobrze: Zeszyt, piórnik, książka — jeden plecak, jedna sprawa (szkoła).
Źle: Zeszyt, wiertarka, marchewka, piłka — 4 różne rzeczy, lepiej 4 torby.

Mierzy: czy każda klasa ma jedną sprawę, i wszystko w niej do siebie pasuje?

Formalnie: 1 - mean(LCOM4) per klasa. LCOM4 = connected components w grafie metoda↔atrybut.

---

## Constraints — "Zasady w domu"

Mama mówi: "Nie wolno jeść cukierków przed obiadem." = forbidden edge.

Możesz mieć różne zasady:
- Nie wolno wchodzić w butach do salonu
- Nie wolno brać zabawek brata bez pytania

Mierzy: czy przestrzegasz zasad (architektonicznych)?

Formalnie: C = 1 - (violations / cross_boundary_edges). Reguły w YAML.

---

## Ratchet — "Już umiesz jeździć na rowerze — nie oduczysz się"

Wczoraj jechałeś 10 metrów. Dziś musisz co najmniej 10. Nigdy nie cofasz się.

Mierzy: czy kod jest co najmniej tak dobry jak wczoraj?

Formalnie: AGQ(PR) >= AGQ(main). Monotoniczny wzrost. Drift fizycznie niemożliwy.

---

## Wszystko razem

```
AGQ = Czy klocki w pudełkach?     (Modularity)
    + Czy nie chodzisz w kółko?    (Acyclicity)
    + Czy fundamenty stabilne?     (Stability)
    + Czy plecak ma sens?          (Cohesion)
    + Czy przestrzegasz zasad?     (Constraints)
    + Czy nie cofasz się?          (Ratchet)
```

Każda odpowiedź od 0 (źle) do 1 (super). Średnia ważona = AGQ score.
