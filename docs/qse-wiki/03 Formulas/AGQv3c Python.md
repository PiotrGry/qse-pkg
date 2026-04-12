---
type: formula
status: credible
languages: [python]
components: [M, A, S, C, CD, flatscore]
---

# AGQv3c Python

## Podsumowanie dla początkujących

AGQv3c Python to aktualnie najlepsza formuła zorientowana na Pythona w tej wiki.

Różni się od formuły javowej, ponieważ projekty w Pythonie wykazały odmienne wzorce w badaniach.

Co najważniejsze, przypisuje dużą wagę metryce [[flatscore]], ponieważ ten sygnał pomógł wykryć jeden ważny rodzaj złej architektury w Pythonie.

## Wzór

`0.15 M + 0.05 A + 0.20 S + 0.10 C + 0.15 CD + 0.35 flatscore`

## Dlaczego jest inaczej

- Python wykazywał inne zachowanie niż Java.
- [[Acyclicity]] miała małą użyteczną zmienność w Pythonie.
- [[flatscore]] stał się bardzo ważny.

## Uwagi

- Aktualnie najlepsza formuła dla Pythona.
- flatscore ma największą wagę.
- Nie stosować do repozytoriów w Javie.

## Czytaj dalej

- [[E6 flatscore]]
- [[W9 AGQv3c Python Discriminates Quality]]
- [[W10 flatscore Predicts Python Quality]]
