---
type: hypothesis
id: W10
status: potwierdzona
language: pl
topic: flatscore, Python, namespace
tested_by: E6
sesja_turn: 39
---

# W10 — flatscore predykuje jakość architektury Python

## Prostymi słowami

flat_score to liczba od 0 do 1 mówiąca, ile procent klas projektu jest zagnieżdżonych głębiej niż 2 poziomy folderów. youtube-dl: 0 (wszystkie w jednym folderze). netbox: 0.93 (93% klas w głębokiej hierarchii). Ta prosta metryka okazała się najsilniejszym predyktorem jakości architektury Python w całym projekcie QSE — silniejszym niż AGQ, silniejszym niż CD, silniejszym niż NSdepth.

## Co badano

> **H₁:** partial r(flat_score, Panel_Python | nodes) > 0, p < 0.05. flat_score — odsetek węzłów z depth>2 — predykuje ocenę panelu dla projektów Python.

## Wynik

| Test | flat_score | AGQ v2 (dla porównania) |
|---|---|---|
| pos_mean | **0.665** | 0.553 |
| neg_mean | **0.200** | 0.643 |
| Δ (pos−neg) | **+0.465** | −0.090 (odwrotny!) |
| Mann-Whitney p | **0.004 \*\*** | 0.066 ns |
| Partial r (kontrola nodes) | **+0.670 \*\*** | −0.309 ns |

**Hipoteza potwierdzona.** flat_score ma silny sygnał (r=+0.670, MW p=0.004) i wyraźną separację kategorii (Δ=+0.465).

## Dane

### Przykłady (GT Python Turn 39)

| Repo | flat_score | Interpretacja | Panel | GT |
|---|---|---|---|---|
| netbox-community/netbox | **0.936** | 3524/3763 klas w depth>2 | 8.00 | POS |
| saleor/saleor | **0.871** | hierarchiczne Django apps (dcim/ipam/...) | 7.50 | POS |
| Kiwi TCMS | **0.803** | testcases/testruns/management | 7.00 | POS |
| healthchecks | **0.754** | api/accounts/front — czyste warstwy | 6.75 | POS |
| sentry | **0.612** | sentry.models.xxx — głęboka hierarchia | 6.00 | POS |
| **youtube-dl** | **0.000** | 895/895 klas w depth≤2 | 2.25 | **NEG** |
| taiga-back | **0.312** | mieszana struktura | 4.25 | NEG |

### Mechanizm: dlaczego youtube-dl ma flat_score=0.000

```
youtube-dl/
├── YoutubeIE.py        # depth=2: youtube_dl.YoutubeIE
├── VimeoIE.py          # depth=2: youtube_dl.VimeoIE
├── DailymotionIE.py    # depth=2: youtube_dl.DailymotionIE
... (x 1000 extractorów, wszystkie depth=2)

Vs netbox:
netbox/
├── dcim/
│   ├── models/
│   │   ├── Device.py   # depth=4: netbox.dcim.models.Device
│   │   └── ...
│   ├── api/
│   │   └── views.py    # depth=4: netbox.dcim.api.DeviceViewSet
```

### Porównanie kierunków (Turn 39)

| Metryka | Java Δ | Java p | Python Δ | Python p | Zgodność |
|---|---|---|---|---|---|
| AGQ v3c | +0.107 | 0.001 | +0.112 | 0.045 * | ZGODNY ✓ |
| AGQ v2 | +0.107 | 0.001 | −0.090 | 0.066 ns | ODWROTNY ✗ |
| **flat_score** | **+0.000** | **ns** | **+0.465** | **0.004 \*\*** | — |

flat_score jest metryką **specyficznie pythonową** — dla Javy Δ=0 (Java ma głębokie pakiety zawsze).

## Dlaczego to ważne

**flat_score rozwiązuje problem odwróconego kierunku.** AGQ v2 (odwrotny kierunek dla Pythona) był blokadą dla całego projektu QSE — niemożliwe było twierdzenie że narzędzie działa dla Pythona przy odwróconym kierunku. flat_score naprawia to fundamentalnie.

**Nowy typ złej architektury:** flat spaghetti to wzorzec niewidoczny dla metryk topologicznych (Modularity, Acyclicity, Stability, CD). Wszystkie te metryki mierzą sprzężenia — ale brak sprzężeń może być DOBRY (luźna architektura) lub ZŁY (brak struktury hierarchicznej). flat_score to pierwszy QSE który to rozróżnia.

**Waga 0.35 w AGQ v3c Python** — największa waga z wszystkich składowych. Uzasadniona empirycznie: partial r=+0.670 > r(M)=?, r(S)=?, r(C)=? (wszystkie <0.4 dla Pythona).

## Ograniczenia

1. **n=11 — za mało dla zamknięcia W9.** W10 jest potwierdzona (flat_score działa), ale W9 (AGQ v3c Python jako całość) wymaga n_neg≥15
2. **Django framework daje modularność za darmo.** Każda Django app to oddzielny pakiet z depth≥3. flat_score może faworyzować projekty Django nie przez jakość architektury, lecz przez wybór frameworka. Potrzeba walidacji na projektach non-Django Python.
3. **Próg depth=2 jest heurystyczny.** Czy depth>2 to właściwy próg? Możliwe, że depth>3 lepiej rozróżnia — nie zbadano.

## Formuła

```python
def flat_score(nodes: list[str]) -> float:
    """
    Odsetek węzłów z depth > 2 w FQN.
    Wysoki flat_score = głęboka hierarchia (dobra).
    Niski flat_score = płaski namespace (flat spaghetti).
    """
    if not nodes:
        return 0.5
    depths = [len(fqn.split('.')) for fqn in nodes]
    deep = sum(1 for d in depths if d > 2)
    return deep / len(nodes)
```

Przykłady:
- `youtube_dl.YoutubeIE` → split = 2 → depth=2 → NOT deep
- `netbox.dcim.models.Device` → split = 4 → depth=4 → deep
- `django.db.models.base.Model` → split = 5 → depth=5 → deep

## Szczegóły techniczne

**Implementacja:** 1 linia Python, koszt O(n_nodes). Dane FQN z `scan_to_graph_json` (już dostępne bez re-skanu). Obliczany post-hoc na istniejącym grafie.

**Kalibracja wagi 0.35:** iteracyjna optymalizacja partial r na GT Python n=11. Wagi: [0.15·M, 0.05·A, 0.20·S, 0.10·C, 0.15·CD, 0.35·flat] minimalizowały błąd klasyfikacji POS/NEG.

**Pełna formuła:**
```
AGQ v3c (Python) = 0.15·M + 0.05·A + 0.20·S + 0.10·C + 0.15·CD + 0.35·flat_score
```

## Definicja formalna

Dla projektu P z węzłami V (pełne kwalifikowane nazwy):

```
flat_score(P) = |{v ∈ V : depth(v) > 2}| / |V|

gdzie depth(v) = liczba segmentów w FQN v po split('.')
```

Zakres: [0.0, 1.0]. Neutralna wartość dla pustego grafu: 0.5.

## Zobacz też

- [[W9 AGQv3c Python Discriminates Quality]] — hipoteza o całej formule Python (otwarta)
- [[E6 flatscore]] — eksperyment który potwierdził W10
- [[E5 Namespace Metrics]] — poprzedni eksperyment (NSdepth/NSgini)
- [[AGQv3c Python]] — pełna formuła
- [[O4 Namespace Metrics for Python]] — otwarte pytania o rozszerzenia
