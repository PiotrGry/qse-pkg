# QSE — Quality Score Engine
## Brief badawczy

---

### Problem badawczy

Istniejące narzędzia analizy jakości kodu (SonarQube, linters) operują na poziomie pliku — wykrywają błędy, problemy stylistyczne i luki bezpieczeństwa. Brakuje narzędzi mierzących **jakość strukturalną systemu jako całości**: cykliczne zależności między modułami, brak hierarchii warstw, rozpad spójności klas. Ten wymiar jakości pozostaje trudno mierzalny i słabo zbadany empirycznie.

Temat nabiera nowego znaczenia w kontekście rosnącego udziału kodu generowanego przez modele językowe. Modele optymalizują lokalną poprawność, nie mając dostępu do globalnej struktury zależności projektu. Hipoteza, że AI-assisted development może systematycznie degradować architekturę mimo "zielonych" testów, pozostaje otwartym pytaniem badawczym.

---

### Proponowane podejście

W ramach projektu opracowano mierzalną metrykę jakości architektonicznej — **AGQ** (*Architecture Graph Quality*) — ważoną sumę czterech metryk grafowych obliczanych na grafie zależności między modułami projektu:

| Metryka | Co mierzy | Waga (wstępna) |
|---|---|---|
| Acyclicity | Brak cykli zależności | **0.73** |
| Cohesion | Spójność klas | 0.17 |
| Stability | Hierarchia warstw | 0.05 |
| Modularity | Izolacja modułów | 0.00 |

Wagi wyznaczono wstępnie metodą numerycznej optymalizacji (L-BFGS-B) z walidacją krzyżową (LOO-CV — model testowany kolejno na każdym projekcie pominiętym podczas uczenia). Wymagają replikacji na szerszych zbiorach i innych językach.

---

### Co zostało empirycznie potwierdzone

W ramach wstępnych eksperymentów na ~240 repozytoriach open-source (Python, Java, Go) zweryfikowano pięć tez:

**T1 — AGQ jest deterministyczne** ✅
Wielokrotne uruchomienie na tych samych danych daje identyczny wynik (delta=0.000 na 80 repo). Warunek konieczny dla narzędzia klasy produkcyjnej.

**T2 — AGQ mierzy wymiar komplementarny do SonarQube** ✅ (REVISED)
Cross-validation z SonarQube (n=79, metryki per KLOC): AGQ composite nie koreluje ze smells/KLOC (r=-0.11, n.s.) ani bugs/KLOC (r=-0.09, n.s.). Jednak składowe AGQ wykazują istotny związek: stability↔bugs/KLOC r=-0.32 (p=0.003), cohesion↔complexity/KLOC r=-0.28 (p=0.01). AGQ i Sonar mierzą komplementarne wymiary — z mierzalnym overlap: lepsza architektura → mniej bugów i mniejsza złożoność.

**T3 — AGQ wykrywa problemy niewidoczne dla SonarQube** ✅
W zbiorze zidentyfikowano projekty z oceną Sonar=A i AGQ<0.7 — przypadki klasyfikowane przez standardowe narzędzia jako "czyste", a przez QSE jako architektonicznie problematyczne.

**T4 — AGQ jest wystarczająco szybkie do integracji z CI/CD** ✅
Mediana analizy: 0.32 s. Umożliwia użycie jako automatyczna bramka jakości przy każdym commicie bez spowalniania pracy.

**T5 — AGQ różnicuje projekty pod względem jakości architektonicznej** ✅ (WZMOCNIONE)
Spread=0.425, std=0.065. Walidacja face validity: 10 known-good vs 10 known-bad repos — **p<0.001, Cohen's d=3.22**. 80% dobrych = LAYERED, 60% złych = FLAT/LOW_COHESION.

**T6 — AGQ daje wyniki spójne z niezależnymi badaniami** ✅ (NOWE)
Ranking AGQ na 4 projektach Apache Java = ranking Dai et al. (2026, Nature Sci. Reports) architectural integrity z trained GNN (Spearman rho=1.0). AGQ dodatkowo daje diagnostykę: god classes, flat architecture, cykle.
Spread wyników: 0.425, std=0.065 na zbiorze Python. Metryka rzeczywiście rozróżnia projekty dobre od słabych.

**Dodatkowo:** po normalizacji względem rozmiaru projektu (AGQ-adj) metryka wykazuje statystycznie istotny związek z częstością zmian w kodzie — hotspot_ratio: r=+0.24, p<0.001; churn_gini: r=−0.15, p=0.018 (n=234, korelacja rang Spearmana). Efekt umiarkowany (~5% wyjaśnionej zmienności), ale powtarzalny — co sugeruje, że jakość architektoniczna ma mierzalny związek z kosztami utrzymania kodu.

---

### Obecny stan

Zaimplementowano: AGQ Core + warstwa Enhanced (normalizacja per-język, klasyfikacja wzorca architektonicznego, ocena powagi cykli), CLI (`qse agq / gate / discover`), skaner Rust (tree-sitter, Python/Java/Go), 244 testy automatyczne.

---

### Kierunki dalszych badań

- Formalna walidacja na szerokich zbiorach danych, wielu językach i domenach
- Kalibracja wag per-język i per-domena
- Budowa warstwy predykcyjnej (ML) łączącej AGQ z cechami temporalnymi i procesowymi z historii git
- Walidacja na projektach przemysłowych (closed-source)
- Analiza wpływu AI-assisted development na drift architektoniczny w czasie

---

### Potencjał praktyczny

Przy pozytywnej walidacji empirycznej AGQ może stanowić podstawę narzędzia do automatycznego monitorowania jakości architektonicznej w procesach CI/CD — uzupełniając istniejące narzędzia o dotychczas nieobsługiwany wymiar strukturalny, szczególnie istotny przy rosnącym udziale kodu generowanego przez AI.

---

*Projekt w fazie badawczej · Python / Java / Go · github.com/PiotrGry/qse-pkg*
