---
type: experiment
id: S-sensitivity
status: zakończony
language: pl
---

# S Sensitivity Investigation

**Data:** kwiecień 2026
**Status:** ZAKOŃCZONE — udokumentowane ograniczenia

---

## Tło

Podczas Pilot OSS (refactoring `qse-pilot-enterprise`), metryka S pozostała niezmieniona (S=0.19 → 0.19) pomimo 5 zmian DIP (port/adapter pattern, przeniesienie implementacji repozytoriów do infrastruktury, naprawienie naruszeń DIP).

AGQ delta: +0.002 (szum). To wzbudziło podejrzenie, że S jest nieczuły na zmiany kierunku zależności.

## Odkrycie 1: Variance jest symetryczne

**S = var(I_pkg) / 0.25** gdzie I = Ce/(Ca+Ce) per second-level package.

**Twierdzenie:** var(I) jest matematycznie niezmienne przy odwróceniu wszystkich krawędzi.

Dowód:
- Po odwróceniu: I' = Ca/(Ca+Ce) = 1 - I
- var(1-I) = var(I)  ∎

Weryfikacja empiryczna (3 repozytoria):

| Repo | S oryginalne | S po odwróceniu | Delta |
|---|---|---|---|
| Apollo | 0.1052 | 0.1052 | 0.0000 |
| Dropwizard | 0.1150 | 0.1150 | 0.0000 |
| Canal | 0.1461 | 0.1461 | 0.0000 |

**Wniosek:** S mierzy ZRÓŻNICOWANIE warstw (czy pakiety mają różne role), NIE POPRAWNOŚĆ warstw (czy zależności wskazują we właściwym kierunku).

## Odkrycie 2: Grupowanie na poziomie 2 ukrywa wewnętrzne refaktoryzacje

Pilot enterprise ma **1 pakiet aplikacyjny** na poziomie 2: `com.mycompany` (I=1.0) + 19 pakietów bibliotecznych (wszystkie I=0.0).

Refactoring DDD (domain→infrastructure, port/adapter) odbywa się WEWNĄTRZ `com.mycompany`:
- `com.mycompany.domain.UserRepository` → `com.mycompany.infrastructure.UserRepositoryImpl`
- Na poziomie 2: oba to wciąż `com.mycompany`
- Żadne krawędzie cross-package nie zmieniły się → S niezmienione

To jest głębszy problem niż symetria variance — nawet kierunkowa metryka byłaby ślepa.

## Eksploracja: głębsze grupowanie

Porównanie S przy różnych głębokościach pakietów:

| Repo | S(d=2) | S(d=3) | S(d=4) | #pkg2 | #pkg3 | #pkg4 |
|---|---|---|---|---|---|---|
| Apollo | 0.105 | 0.022 | 0.011 | 37 | 178 | 378 |
| Dropwizard | 0.115 | 0.317 | 0.852 | 66 | 355 | 1066 |
| Canal | 0.146 | 0.034 | 0.034 | 47 | 224 | 405 |
| AxonFramework | 0.074 | 0.154 | 0.586 | 53 | 308 | 848 |
| TheAlgorithms | 0.222 | 0.759 | 0.412 | 17 | 117 | 1370 |
| PilotEnterprise | 0.190 | 0.057 | 0.051 | 20 | 69 | 78 |

Na d=3 `PilotEnterprise` rozbija się na `com.mycompany.domain`, `.service`, `.infrastructure` — co by umożliwiło wykrycie zmian DIP. Ale:
- Wyniki nie są monotoniczne (Apollo spada, Dropwizard rośnie)
- Wymagałoby re-walidacji całego GT (59 repos)
- Grozi overfitting na strukturę pakietów specyficzną dla Java

## Rekomendacja

1. **NIE zmieniaj S** — obecna formuła jest poprawna dla swojego celu (mierzenie zróżnicowania warstw)
2. **Udokumentuj ograniczenie** — S nie jest metryką DIP compliance
3. **Jeśli potrzebna detekcja DIP:** rozważ osobną metrykę (np. boundary crossing direction ratio) — ale to nowa metryka (wymaga `nie dodawaj nowych metryk bez jawnego uzasadnienia`)
4. **Nie zmieniaj grouping depth** bez pełnej re-walidacji GT

## Wpływ na Claims & Evidence

Claim "S measures architectural layering" wymaga caveatu:
> S measures layering **differentiation** (whether packages have differentiated stability roles), not layering **correctness** (whether dependencies follow the Dependency Inversion Principle). Fixing DIP violations within a single top-level package may not change S.

---

*Powiązane:* [[Pilot OSS]], [[Pilot Multi-Repo Scan]], [[Ground Truth]]
