---
type: experiment
id: E3
status: wstrzymany
language: pl
tested_hypothesis: ~
sesja_turn: ~
---

# E3 — Package Layer Classifier

## Prostymi słowami

Pomysł: zamiast mierzyć hierarchię instability (E1), po prostu skalsyfikuj każdy pakiet jako `domain`, `infrastructure` lub `application` na podstawie jego pełnej nazwy (FQN — fully qualified name). Następnie sprawdź, czy projekt z „poprawnym" rozkładem warstw jest lepszy od projektu z chaotycznym. Eksperyment nie został przeprowadzony — napotkał dwie blokady i został odłożony na rzecz E5 i E6.

## Hipoteza

> Binarna klasyfikacja pakietów na podstawie FQN (domain/infrastructure/application) koreluje z oceną ekspertów — projekty z wyraźną separacją warstw mają wyższy Panel score.

Formalnie: przypisz każdy pakiet do jednej z trzech warstw na podstawie FQN (np. `.domain.`, `.infra.`, `.application.`), oblicz odsetek pakietów w „poprawnej\" warstwie; H₁: r(layer_ratio, Panel) > 0, p < 0.05.

## Dane wejściowe (planowane)

- **Dataset:** GT Java, n≥13 (ścieżka A: n=13 — możliwa, ale nie przeprowadzona)
- **GT:** panel ekspertów, σ < 2.0
- **Wymaganie:** FQN węzłów (pełne nazwy kwalifikowane pakietów) — wymaga re-skanu repozytoriów

## Dlaczego wstrzymany

### Blokada 1: Brak FQN w istniejących danych

Skaner w momencie planowania E3 nie zapisywał FQN węzłów w formacie wymaganym do klasyfikacji warstw. Przeprowadzenie eksperymentu wymagało re-skanu całego GT Java z nową wersją skanera zapisującą pełne ścieżki pakietów. Re-skan nie został wykonany — priorytety przesunięto na E5 (metryki przestrzeni nazw) i E6 (flat_score).

### Blokada 2: Ground Truth obalony jako podstawa

GT bazujący na BLT (ang. Binary Layer Test — wstępna metodologia) został obalony jako wiarygodny Ground Truth przed wykonaniem E3. Ścieżka A (GT n=13, panel ekspertów) pozostała możliwa technicznie, jednak przy n=13 wyniki byłyby słabo wiarygodne statystycznie.

### Kontekst decyzji

Po tym jak E1 pokazał, że S_hierarchy nie działa, E3 był planowany jako prostsze podejście — zamiast mierzyć kolejność instability, po prostu patrzeć na nazwy pakietów. Problem w tym, że wiele projektów nie używa standardowych konwencji nazewnictwa warstw (`.domain.`, `.infra.`), więc klasyfikator oparty na FQN byłby ograniczony do podzbioru repozytoriów. Eksperymenty E5 (metryki głębokości namespace) i E6 (flat_score) zaproponowały bardziej ogólne podejście niewymagające konwencji nazewnictwa.

## Status i dalsze kroki

| Ścieżka | Opis | Status |
|---|---|---|
| Ścieżka A | GT n=13, re-skan z FQN | Możliwa, nie przeprowadzona |
| Ścieżka B | Pełny GT n=59 z FQN | Wymaga re-skanu + rozbudowy GT |

Eksperyment może być wznowiony jeśli:
1. Skaner zostanie zaktualizowany do zapisywania FQN w nowym formacie
2. Wyniki E5/E6 okażą się niewystarczające i potrzebna będzie klasyfikacja warstwowa

## Alternatywy (zrealizowane)

- **E5 Namespace Metrics** — głębokość przestrzeni nazw jako proxy hierarchii, bez wymagania konwencji nazewnictwa
- **E6 flat_score** — odsetek węzłów na płytkich głębokościach namespace (skuteczny dla Pythona)

## Zobacz też

- [[E1 Stability Hierarchy]] — poprzedni eksperyment z hierarchią (obalony)
- [[E5 Namespace Metrics]] — alternatywne podejście (zrealizowane)
- [[W7 Stability Hierarchy Score]] — hipoteza stojąca za E1 (obalona)
- [[How to Read Experiments]] — protokół eksperymentów QSE
