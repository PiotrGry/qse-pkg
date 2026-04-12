---
type: formula
status: active-experiment
languages: [java]
components: [M, A, S, C, CD]
---

# AGQv2

## Podsumowanie dla początkujących

AGQv2 to nowsza formuła, która ulepszyła AGQv1 poprzez dodanie jednego sygnału: [[CD]].

Mówiąc prosto, celem było lepsze uchwycenie stopnia splątania struktury projektu.

Formuła działa wiarygodnie dla Javy, ale nie powinna być traktowana jako formuła uniwersalna dla każdego języka.

## Wzór

`0.20 M + 0.20 A + 0.35 S + 0.05 C + 0.20 CD`

## Co zmieniło się w stosunku do AGQv1

- [[Stability]] otrzymała mniejszą wagę.
- Dodano [[CD]].
- Formuła lepiej odróżnia architektury Javy wyższej i niższej jakości.

## Uwagi

- Ważna dla Javy.
- Nie jest metryką wielojęzykową.

## Czytaj dalej

- [[E2 Coupling Density]]
- [[W4 AGQv2 Beats AGQv1 on Java GT]]
