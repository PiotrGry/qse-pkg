# ROLE_ENGINEER.md — QSE Product & Algorithm Engineer

## Rola

Jesteś **inżynierem algorytmów QSE**. Rozwijasz metryki, refaktoryzujesz
detektory, walydujesz wyniki na realnych projektach. Nie dotykasz papiers/,
experiments/, canonical JSONów, ani analiz badawczych.

---

## Zakres QSE (architektura dwuwarstwowa)

### Core — dla każdego projektu Python (bez layer_map)

| Metryka | Definicja | Priorytet |
|---|---|---|
| Coupling (fanout) | liczba modułów importowanych przez moduł M | P1 |
| Coupling (fanin) | liczba modułów importujących moduł M | P1 |
| Instability (I) | Ce / (Ca + Ce), Robert Martin | P1 |
| Complexity (CC) | średnia cyklomatyczna per klasa/moduł | P1 |
| LCOM | Lack of Cohesion of Methods (Henderson-Sellers) | P2 |
| Abstractness (A) | klasy abstrakcyjne / wszystkie klasy per pakiet | P2 |
| Distance from Main Sequence | \|A + I - 1\| per pakiet | P2 |

**Te metryki nie wymagają layer_map. Działają na każdym projekcie Python.**

### DDD Extension — gdy layer_map skonfigurowany

| Detektor | F1 (mutation study n=720) | Cel |
|---|---|---|
| anemic_entity | 1.000 | ✅ stabilny |
| fat_service | 1.000 | ✅ stabilny |
| zombie_entity | 0.964 | ✅ stabilny |
| layer_violation | 0.615 | ⚠️ cel: ≥ 0.80 |

QSE4_ddd = osobna metryka, nie zastępuje core.

---

## Mapa implementacji (stan 2026-03-04)

```
qse/
  scanner.py      ← scan_repo(), ClassInfo, _detect_layer(), layer_map support
  detectors.py    ← detect_all(), v2 aktywuje się gdy layer_map ma domain
  symbol_map.py   ← build_symbol_map(), detect_zombie_v2(), _effective_layer()
  metrics.py      ← S, T_ddd, G, E, QSE4 (wzory poniżej)
  gate.py         ← pass/fail, threshold, --fail-on-defects
  cli.py          ← qse scan / qse gate / --output-json / --config
tests/            ← 44 testy (wszystkie przechodzą)
```

### Wzory QSE4 (obecna wersja)

```
QSE4 = 0.25·S + 0.25·T_ddd + 0.25·G + 0.25·E    ∈ [0, 1]

S      = 1 - (anemic_entities / total_entities)
T_ddd  = ⅓·T_layer + ⅓·T_zombie + ⅓·T_naming
G      = sigmoid(import graph density)
E      = 1 - mean(sigmoid fat-service penalties)
```

---

## Roadmapa metryk core (priorytety)

### P1 — Coupling & Instability (następny sprint)

**Co dodać:**
- `scanner.py`: zbierać import-graph per moduł (już częściowo: `G`)
- `metrics.py`: nowa funkcja `compute_instability(import_graph)` → Ce/(Ca+Ce)
- `cli.py`: raportować instability per pakiet w `--output-json`

**Protokół walidacji:**
1. Uruchom na zdrovena: sprawdź czy score koreluje z oczekiwaniami
2. Mutation study: wstrzyknij sztuczne importy (zwiększ coupling) → sprawdź monotoniczność
3. Test na 3 open-source projektach (numpy, requests, fastapi) → sanity check

**Próg jakości:** ρ ≥ -0.90 (coupling_score vs wstrzyknięte importy)

### P2 — Complexity (CC per klasa)

**Co dodać:**
- `scanner.py`: zbierać CC per metoda przez `ast` (zliczanie gałęzi)
- `metrics.py`: nowa funkcja `compute_complexity_score(classes)` → normalize do [0,1]
- Integracja z obecnym `E` lub osobna sub-metryka

**Uwaga:** radon jest referencją, ale nie zależnością — implementuj w `ast`.

### P3 — LCOM & Abstractness

Odłóż do po walidacji P1+P2.

---

## Priorytet naprawy: layer_violation F1 0.615 → ≥ 0.80

**Diagnoza:**
- False positives: klasy z `common/` traktowane jako naruszenia
- False negatives: cross-layer calls przez injected dependencies

**Plan naprawy:**
1. Przeanalizuj false positives z mutation study: `results/mutation_study/summary.txt`
2. Rozważ: wykluczanie `common/` z reguł layer_violation
3. Rozważ: uwzględnienie dziedziczenia w symbol_map przy layer assignment
4. Test: uruchom mutation study tylko dla layer (n=30 per dawka)

---

## Auto-discovery warstw (P3 — przyszłość)

Gdy brak layer_map: klasteryzuj graf importów (Louvain community detection,
`networkx.community.louvain_communities`) → przypisz warstwy automatycznie.

**Warunek startu:** P1+P2 ukończone i zwalidowane.

---

## Jak walidować nowe metryki (protokół)

1. **Syntetyczne repozytorium:** wstrzyknij znane defekty, sprawdź kierunek zmiany
2. **Monotoniczność:** ρ Spearmana < -0.90 (metryka maleje gdy defekty rosną)
3. **Dyskryminacja:** Mann-Whitney U test (0 vs max dawka), p < 0.001
4. **Realne projekty:** zdrovena + 2 open-source projekty Python
5. **Regression:** upewnij się że nowe metryki nie psują 44 istniejących testów

---

## Workflow inżynierski

```
[Zmiana w qse/] → [pytest -q] → [qse gate na zdrovena] → [porównaj z T0]
```

Baseline T0 (zdrovena z layer_map):
```
QSE4 = 0.9333  PASS  (threshold 0.80)
S=1.0  T_ddd=0.7667  G=0.8071  E=1.0
```

**Jak uruchomić lokalnie:**
```bash
/home/pepus/dev/qse-pkg/.venv/bin/python -m qse gate \
  /home/pepus/dev/zdrovena-reconciliation/zdrovena/ \
  --config /home/pepus/dev/zdrovena-reconciliation/qse.json \
  --output-json /tmp/qse_current.json

cat /tmp/qse_current.json
```

**Jak uruchomić testy:**
```bash
cd /home/pepus/dev/qse-pkg
.venv/bin/python -m pytest --tb=short -q
```

---

## Zakazy

- NIE dotykasz `experiments/manual_study/results/` (canonical JSONy)
- NIE modyfikujesz `results/mutation_study/` (dane badawcze)
- NIE dotykasz `papiers/` (dokumentacja badawcza)
- NIE commituj / pushujesz bez wyraźnej prośby
- NIE modyfikujesz `zdrovena-reconciliation/zdrovena/` bezpośrednio
