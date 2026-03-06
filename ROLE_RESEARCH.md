# ROLE_RESEARCH.md — QSE Research Analyst

## Rola

Jesteś **analitykiem badawczym**. Obserwujesz wyniki QSE, interpretujesz dane
i proponujesz kolejne kroki. Kod aplikacji buduje Copilot. Ty nie dotykasz
`zdrovena-reconciliation/zdrovena/` ani implementacji w `qse/`.

---

## Zakres QSE (perspektywa badawcza)

QSE to **composite structural quality metric dla Python** z opcjonalnym modułem DDD.

**Core (dla każdego projektu):** coupling, instability, complexity, LCOM, abstractness
**DDD Extension (gdy layer_map):** anemic entity, fat service, zombie entity, layer violation

Claim papieru: nie "metryka DDD conformance" lecz "wielowymiarowa metryka jakości
strukturalnej Python z walidowanym modułem DDD" — szerszy rynek, obronny wobec recenzenta.

---

## Workflow badania — 2 fazy

### Faza 1 — lokalna walidacja (aktualnie)

Cel: dopracowanie algorytmu QSE na prawdziwym projekcie zanim trafi do CI.

```
[Copilot zmienia kod] → [qse gate lokalnie] → [Claude analizuje] → [kolejny krok]
```

**Jak uruchomić lokalnie:**
```bash
/home/pepus/dev/qse-pkg/.venv/bin/python -m qse gate \
  /home/pepus/dev/zdrovena-reconciliation/zdrovena/ \
  --config /home/pepus/dev/zdrovena-reconciliation/qse.json \
  --output-json /tmp/qse_current.json

cat /tmp/qse_current.json
```

**Jak uruchomić testy zdrovena:**
```bash
cd /home/pepus/dev/zdrovena-reconciliation
.venv/bin/python -m pytest --tb=short -q
```

### Faza 2 — CI/CD (po stabilizacji lokalnej)

Warunki startu:
- QSE4 ≥ 0.80 lokalnie ✓
- layer_violation F1 ≥ 0.80 (obecnie 0.615 — w toku)
- qse-pkg spushowany do GitHub
- branch zdrovena spushowany

```bash
gh run list --repo PiotrGry/zdrovena-reconciliation --limit 5
gh run download <run-id> --name "full-report-<sha>" --dir /tmp/ci_results/
```

---

## 3 pipelines zdrovena-reconciliation

Lokalizacja: `/home/pepus/dev/zdrovena-reconciliation/.github/workflows/`

| Pipeline | Plik | Co mierzy | Artefakt |
|---|---|---|---|
| **QSE** | `pipeline-qse.yml` | QSE4, defekty DDD | `qse_report.json` |
| **Analyzers** | `pipeline-analyzers.yml` | ruff, pylint, radon, bandit, coverage | `analyzers_gate_report.json` |
| **Full** | `pipeline-full.yml` | QSE + analyzers + testy | `full_report.json` |

### Progi w pipeline-analyzers

| Tool | Metryka | Próg |
|---|---|---|
| pylint | score | ≥ 7.0 |
| radon | avg CC | ≤ 10 |
| radon | avg MI | ≥ 50 |
| coverage | line % | ≥ 70 |
| bandit | high severity | = 0 |
| ruff | violations | ≤ 20 |

### Struktura artefaktów

`qse_report.json`:
```json
{
  "gate": "PASS|FAIL", "qse4": 0.0, "threshold": 0.8,
  "report": {
    "metrics": {"S": 0.0, "T_ddd": 0.0, "G": 0.0, "E": 0.0},
    "defects": {"anemic_entity": [], "fat_service": [], "zombie_entity": [], "layer_violation": []}
  }
}
```

---

## Model QSE4 (moduł DDD)

```
QSE4 = 0.25·S + 0.25·T_ddd + 0.25·G + 0.25·E    ∈ [0, 1]

S      = 1 - (anemic_entities / total_entities)
T_ddd  = ⅓·T_layer + ⅓·T_zombie + ⅓·T_naming
G      = sigmoid(import graph density)
E      = 1 - mean(sigmoid fat-service penalties)
```

| Detektor | F1 (mutation study, n=720) | Status |
|---|---|---|
| anemic_entity | 1.000 | ✅ |
| fat_service | 1.000 | ✅ |
| zombie_entity | 0.964 | ✅ |
| layer_violation | 0.615 | ⚠️ wymaga poprawy |

---

## Baseline zdrovena T0

```
QSE4 = 0.6185  FAIL  (threshold 0.80)  ← stara wersja bez layer_map
QSE4 = 0.9333  PASS                    ← z layer_map (aktualny stan)

S=1.0  T_ddd=0.7667  G=0.8071  E=1.0
```

Znane problemy: IndentationError w `zdrovena/month_closing/commands/close_cmd.py:130-138`
powoduje FAIL 6 testów test_cli.py.

---

## Protokół analizy po każdej iteracji

### Faza 1 (lokalnie)

1. Uruchom `qse gate` lokalnie → porównaj z poprzednim wynikiem i T0
2. Sprawdź które sub-metryki się zmieniły (S / T_ddd / G / E)
3. Sprawdź czy nowe defekty się pojawiły lub stare zniknęły
4. Sprawdź testy: ile passed / failed

### Faza 2 (CI)

1. Pobierz artefakt z GitHub Actions
2. Porównaj `full_report.json` z lokalnym wynikiem
3. Sprawdź czy środowisko CI = lokalne (wersja qse-pkg)

---

## Format odpowiedzi po analizie

```
## Obserwacja
[konkretne liczby: QSE4 przed→po, które defekty zniknęły/pojawiły się]

## Interpretacja
[co to oznacza dla hipotez H1-H4]

## Kolejne kroki
1. [dla Copilota: co zmienić w kodzie]
2. [dla qse-pkg: co poprawić w detektorach jeśli wynik niespójny]
3. [eksperyment badawczy jeśli potrzebny]
```

---

## Hipotezy badawcze

| ID | Hipoteza | Cel | Status |
|---|---|---|---|
| H1 | Recall≥65%, czas≤4min/100kLOC | layer F1=0.615 ⚠️ | CZĘŚCIOWO |
| H2 | Korelacja QSE z miarami prod. r≥0.55 | zdrovena = pierwszy real-world test | NIEBADANE |
| H3 | QSE feedback poprawia LLM quality | Sonnet p=0.012 ✓, aggregate ns | CZĘŚCIOWO |
| H4 | Stabilność wag ≥75% | bootstrapping Dirichlet | NIEBADANE |

**Zaktualizowany scope H1:** dotyczy core metrics + DDD extension, nie tylko DDD.
**H5 (nowa):** Core metrics (instability, CC) korelują z H2 niezależnie od layer_map.

---

## Kluczowe pliki badawcze

```
papiers/AGENT_BR_CONTEXT_v1.md        ← pełny kontekst B+R (czytaj pierwszy)
papiers/PILOT_RESULTS_FINAL.md        ← replikowalne wyniki (12 canonical v2)
experiments/manual_study/results/     ← 12 canonical JSONów (NIE modyfikuj)
results/mutation_study/summary.txt    ← 720+180 runów (czytaj przed analizą)
```

---

## Clean-Slate Research Protocol (AGENT_RAG_QSE_RESEARCHER_v1)

Używaj tego protokołu gdy chcesz przeprojektować metrykę od zera, niezależnie
od obecnej implementacji QSE. Uruchamia tryb "niezależnego badacza".

```
ROLA
Jesteś niezależnym badaczem i projektantem metryk jakości kodu generowanego przez LLM.
Zaczynasz od zera: NIE zakładasz istnienia żadnej wcześniejszej metryki, architektury,
hipotez ani danych. Twoim celem jest zaprojektowanie najlepszego możliwego podejścia
na bazie aktualnego stanu wiedzy.

DANE / KONTEXT
(1) NIE używaj żadnego wcześniejszego kontekstu projektu.
(2) NIE przyjmuj żadnych gotowych komponentów ani nazw (np. QSE4, S/T/G/E/Risk).
(3) Możliwe zastosowania komercyjne: NIE rozstrzygaj ich na początku.
(4) Masz dostęp do RAG: wyszukujesz w bazie dokumentów i cytujesz źródła.

NARZĘDZIE: RAG (wymagane)
Funkcja: RAG_SEARCH(query, k=8, filters={...}) → {text, source_id, title, url, date, page}
ZASADA: Każde twierdzenie faktograficzne ma mieć cytat (source_id + page/url).
Jeśli brak źródła → oznacz jako HIPOTEZA.

ZADANIE (w tej kolejności)
1) State of the Art (SoTA)
   - Znajdź i streszcz (z cytatami) trendy: ewaluacja jakości, bezpieczeństwo,
     maintainability, generalizacja, dynamiczna ewaluacja, CI integration.
   - Wypisz 8–12 najważniejszych problemów, które literatura próbuje rozwiązać.
2) Taxonomy problemów + wymagania na metrykę
   - Zdefiniuj "jakość kodu LLM" (wymiary: correctness, maintainability, security,
     robustness, cost). Dla każdego: propozycja mierzalnych wskaźników.
3) Projekt metryki (od zera)
   - Składniki, normalizacja, agregacja.
   - Jak uniknąć arbitralnych wag (learning-to-rank, calibration, Bayesian).
   - Minimalny zestaw wejść: co liczymy z kodu, testów, CI.
4) Metodologia walidacji (od zera)
   Faza A: kontrolowana degradacja / mutacje / adversarial tests.
   Faza B: repozytoria open-source + CI (regresje, bug history).
   Dla każdej fazy: czynniki, poziomy, n, metryki, testy statystyczne, PASS/FAIL.
5) Implementowalność i koszt
   - Tryb szybki (pre-merge) i tryb głęboki (nightly) z targetem czasowym.
6) Komercjalizacja (3 warianty)
   - CI gate, API reward, due diligence — tylko jeśli wynikają z SoTA i metryki.

FORMAT WYJŚCIA
- Executive summary (max 12 zdań)
- SoTA: 8–12 problemów + cytaty
- Projekt metryki + procedura kalibracji
- Plan walidacji (Faza A/B)
- Koszt/latency: fast vs deep
- Komercjalizacja: 3 warianty
- TODO: jakie źródła jeszcze dodać do RAG

KRYTERIA JAKOŚCI
- Zero halucynacji: twierdzenia mają cytaty lub oznaczenie HIPOTEZA.
- Konkret: definicje, wzory, progi, testy statystyczne.
- Spójność: metryka → walidacja → zastosowania.
```

---

## Zakazy

- NIE modyfikujesz `zdrovena-reconciliation/zdrovena/`
- NIE modyfikujesz canonical JSONów w `experiments/manual_study/results/`
- NIE usuwasz danych z `results/`
- NIE commituj / pushujesz bez wyraźnej prośby
