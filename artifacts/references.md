# QSE — Bibliografia / References

Zebrane źródła naukowe i techniczne na potrzeby pracy doktorskiej i walidacji QSE.
Data: 2026-03-22 (updated)

---

## 1. Metryki modularności

**Newman (2006)**
Modularity and community structure in networks.
_PNAS, 103(23)_
https://www.pnas.org/doi/10.1073/pnas.0601602103

**Pisch, Cai, Kazman, Lefever, Fang (2024)**
M-score: An Empirically Derived Software Modularity Metric.
_Proc. 18th ACM/IEEE ESEM, Barcelona_
https://dl.acm.org/doi/10.1145/3674805.3686697

**Sarkar et al. (2008)**
Metrics for Measuring the Quality of Modularization.
_Purdue University RVL_
https://engineering.purdue.edu/RVL/Publications/Sarkar08Metrics.pdf

**Sarkar, Rama, Kak (2007)**
API-based and information-theoretic metrics for measuring the quality of software modularization.
_IEEE Trans. Softw. Eng., 33(1), pp. 14–32_
Definiuje **MISI** (Module Interaction Stability Index) — metryka pokrewna z QSE stability.
MISI(m) = |SD(m)| / |fanout(m)|, gdzie SD = zbiór stabilnych zależności do niższych warstw.
Cytowana w SEI CMU SAM2014 jako fundament metryk stabilności modułowej.

**Milić et al. (2020)**
Measuring Software Modularity Based on Software Networks.
_Entropy, MDPI_
https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7514828/

**Primadani et al. (2023)**
Measuring Modularity in JavaScript-Based Microservices.
_CEUR-WS ISE2023_
https://ceur-ws.org/Vol-3655/ISE2023_06_Primadani_Measuring_Modularity.pdf

---

## 2. Cykle i acykliczność

**Schnoor et al. (2013)**
A study of cyclic dependencies on defect profile of software components.
_Journal of Systems and Software, Elsevier_
https://www.sciencedirect.com/science/article/abs/pii/S0164121213001878
https://www.researchgate.net/publication/259098636

**Dietrich et al.**
Circular Dependencies and Change-Proneness: An Empirical Study.
_ResearchGate_
https://www.researchgate.net/publication/273757421

**Nistor et al. (2019)**
Investigating the impact of multiple dependency structures on software defects.
_ICSE 2019_
https://dl.acm.org/doi/abs/10.1109/ICSE.2019.00069

**Gnoyke, Schulze, Krüger (2024)**
Evolution Patterns of Software-Architecture Smells: An Empirical Study
of Intra- and Inter-Version Smells.
_Journal of Systems and Software, Vol. 217_
https://jacobkrueger.github.io/assets/papers/Gnoyke2024ArchitectureSmellEvolution.pdf

---

## 3. Spójność (Cohesion) i LCOM

**Tiwari & Rathore (2018)**
Coupling and Cohesion Metrics for Object-Oriented Software: A Systematic Mapping Study.
_Semantic Scholar_
https://www.semanticscholar.org/paper/Coupling-and-Cohesion-Metrics-for-Object-Oriented-A-Tiwari-Rathore/0aa7782834e682874ad6651aeeec710daa07f0d6

**Mäkelä (PhD thesis)**
Cohesion Metrics for Improving Software Quality.
_University of Turku_
https://www.utupub.fi/bitstream/10024/123338/2/D211.digi.pdf
https://scispace.com/pdf/cohesion-metrics-for-improving-software-quality-1w7z5jzrxf.pdf

**New Conceptual Cohesion Metrics (2022)**
New Conceptual Cohesion Metrics: Assessment for Software Defect Prediction.
_IEEE Xplore_
https://ieeexplore.ieee.org/document/9700365/

**Predicting Software Cohesion Metrics with ML (2023)**
Predicting Software Cohesion Metrics with Machine Learning Techniques.
_Applied Sciences, MDPI_
https://www.mdpi.com/2076-3417/13/6/3722

---

## 4. Stabilność i metryki Martina

**Martin R.C.**
Instability and Abstractness — Distance from Main Sequence.
_"Agile Software Development — Principles, Patterns, and Practices"_
(brak linku — książka)

**Drotbohm (2024)**
The Instability-Abstractness-Relationship — An Alternative View.
_Blog post z krytyką metryki_
http://odrotbohm.github.io/2024/09/the-instability-abstractness-relationsship-an-alternative-view/
Kluczowy argument: "extracting an interface raises Abstractness but is not semantically more abstract."
Uzasadnia decyzję QSE o użyciu variance(I) bez Abstractness (A) i Distance (D).

**A Validation of Martin's Metric (brak walidacji empirycznej)**
https://www.researchgate.net/publication/31598248_A_Validation_of_Martin_s_Metric

**Malenezi (papier)**
Software Architecture Quality Measurement: Stability and Understandability.
https://malenezi.github.io/malenezi/pdfs/Paper_75-Software_Architecture_Quality_Measurement_Stability.pdf

**Package-level metrics (IJACSA)**
Evaluating Dependency based Package-level Metrics for Multi-objective Maintenance Tasks.
https://thesai.org/Downloads/Volume8No10/Paper_45-Evaluating_Dependency_based_Package_level_Metrics.pdf

---

## 5. Predykcja defektów — ground truth

**Nagappan & Ball (ICSE 2005)**
Use of Relative Code Churn Measures to Predict System Defect Density.
_Microsoft Research_
https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/icse05churn.pdf
https://dl.acm.org/doi/10.1145/1062455.1062514

**Hassan, A.E. (ICSE 2009)**
Predicting Faults Using the Complexity of Code Changes.
_Proc. 31st International Conference on Software Engineering (ICSE), IEEE_
https://dl.acm.org/doi/10.1109/ICSE.2009.5070510
Precedens dla progu korelacji r≈0.55: obserwacyjne r≈0.20 na metrykach złożoności
→ kontrolowane r≈0.55 po eliminacji confounders. Cytowany w uzasadnieniu KPI-04.

**D'Ambros, Lanza et al. (WCRE 2009)**
On the Relationship Between Change Coupling and Software Defects.
_IEEE Xplore_
https://ieeexplore.ieee.org/document/5328803/
https://www.researchgate.net/publication/221200492

**Fuller, W.A. (1987)**
Measurement Error Models.
_John Wiley & Sons, New York_
ISBN: 978-0-471-86187-4
Korekcja atenuacji korelacji: r_true = r_obs / √(reliability_x × reliability_y).
Standardowa metoda korygowania osłabienia korelacji spowodowanego błędem pomiaru.

**Zhou et al. (ESEM 2024)**
Enhancing Change Impact Prediction by Integrating Evolutionary Coupling
with Software Change Relationships.
https://dl.acm.org/doi/10.1145/3674805.3686668

**Sharma et al.**
An Empirical Investigation on the Relationship between Architectural Smells
and Source Code Metrics.
https://www.tusharma.in/preprints/architecture_smells.pdf

**Co-Change Graph Entropy (arXiv 2025)**
Co-Change Graph Entropy: A New Process Metric for Defect Prediction.
_arXiv:2504.18511_
https://arxiv.org/abs/2504.18511
https://arxiv.org/html/2504.18511

**Rebro (2023)**
Source Code Metrics for Software Defects Prediction.
_arXiv_
https://arxiv.org/pdf/2301.08022

**Unified Bug Dataset (2024)**
Software Defect Prediction Based on Machine Learning and Deep Learning Techniques.
https://www.mdpi.com/2673-2688/5/4/86

---

## 6. Architektoniczne smelle (Architectural Smells)

**Fontana, Pigazzini et al. (2017)**
Arcan: A Tool for Architectural Smells Detection.
_IEEE Xplore_
https://ieeexplore.ieee.org/document/7958506/
https://www.researchgate.net/publication/317919636

**Arcan tool website**
https://www.arcan.tech/architectural-smell-analysis/

**Automatic Detection of Instability Architectural Smells**
https://www.researchgate.net/publication/312485573

**On the evolution and impact of architectural smells (2022)**
_Empirical Software Engineering, Springer_
https://link.springer.com/article/10.1007/s10664-022-10132-7

**Systematic Mapping Study on Architectural Smells Detection**
https://kblincoe.github.io/publications/2020_JSS_ArchSmellsSMS.pdf

---

## 7. Composite metrics / Modularity Maturity Index

**MMI — Software Architecture Metrics (O'Reilly)**
Improve Your Architecture with the Modularity Maturity Index.
https://www.oreilly.com/library/view/software-architecture-metrics/9781098112226/ch04.html

**MMI Backstage plugin proposal**
https://github.com/backstage/backstage/issues/28535

**Automatic Measurement of Microservice Architecture Quality
with Cohesion, Coupling, and Complexity Metrics (2023)**
_10th International Conference on Advanced Informatics_
https://www.researchgate.net/publication/377448728

---

## 8. Porównanie z SonarQube

**A machine and deep learning analysis among SonarQube rules,
product, and process metrics for fault prediction (2022)**
_Empirical Software Engineering, Springer_
https://link.springer.com/article/10.1007/s10664-022-10164-z

**CodeScene vs SonarQube (2025)**
SonarQube vs CodeScene: 6x improvement over SonarQube.
https://codescene.com/blog/6x-improvement-over-sonarqube

**Jin et al. (2023)**
A Quantitative Analysis of Open Source Software Code Quality:
Insights from Metric Distributions.
https://www.researchgate.net/publication/372584277

---

## 9. Cross-project defect prediction — ograniczenia

**Zimmermann et al. (FSE 2009)**
Cross-project defect prediction.
https://dl.acm.org/doi/10.1145/1595696.1595713

**How Far We Have Progressed (2018)**
An Examination of Cross-Project Defect Prediction.
_ACM TOSEM_
https://dl.acm.org/doi/10.1145/3183339

---

## 10. Narzędzia open-source (krajobraz)

**tach — dependency enforcer (Rust, 2.7k stars)**
https://github.com/tach-org/tach

**import-linter**
https://github.com/seddonym/import-linter

**emerge v2.0.7 — dependency visualization + Louvain modularity (~1k stars)**
https://github.com/glato/emerge
Python, 12 języków. Metryki: Louvain Q, fan-in/fan-out, SLOC, TF-IDF.
Cross-validation z QSE: Louvain Q r=0.06 (n=16) — wartość Q zależy od definicji grafu, nie tylko od struktury kodu.
Dane: `artifacts/benchmark/emerge_vs_qse_comparison.json`

**CodeCharta — 3D code visualization (426 stars)**
https://github.com/MaibornWolff/codecharta
TypeScript/Kotlin, importuje metryki z Sonar/Tokei/CSV. Wizualizacja, nie analiza.

**pydeps**
https://github.com/thebjorn/pydeps

**cohesion tool**
https://github.com/mschwager/cohesion

---

## 11. IP / ochrona prawna

**UPRP — Wytyczne dotyczące wynalazków (PDF)**
https://uprp.gov.pl/sites/default/files/inline-files/Og%C3%B3lne%20wytyczne%20Prezesa%20Urz%C4%99du%20Patentowego%20RP%20w%20zakresie%20wynalazk%C3%B3w%20i%20wzor%C3%B3w%20u%C5%BCytkowych.pdf

**EY — Ulga IP Box i działalność B+R**
https://www.ey.com/pl_pl/insights/tax/dzialalnosc-badawczo-rozwojowa-i-ulga-ip-box-co-to-jest-kwalifikowane-prawo-wlasnosci-intelektualnej

**LAWMORE — Patentowanie algorytmów**
https://lawmore.pl/patentowanie-algorytmow-i-oprogramowania/

**PARP — Patentowanie programów komputerowych**
https://www.parp.gov.pl/component/content/article/85768:patentowanie-programow-komputerowych

---

## 12. Dodatkowe (MSR / empiryczne SE)

**From Bugs to Benchmarks: A Comprehensive Survey of Software Defect Datasets (2025)**
https://arxiv.org/pdf/2504.17977

**Emerging Trends in Software Architecture from the Practitioner's Perspective (2025)**
https://arxiv.org/pdf/2507.14554

**Using complexity, coupling, and cohesion metrics as early indicators of vulnerabilities**
_Journal of Systems and Real-Time Systems, Elsevier_
https://www.sciencedirect.com/science/article/abs/pii/S1383762110000615

---

## 13. Architectural metrics — graph-level (nowe źródła 2025)

**Dai, Zhu, Wu, He (2026)**
An integrated graph neural network model for joint software defect prediction
and code quality assessment.
_Scientific Reports 16:1677_
https://doi.org/10.1038/s41598-025-31209-5
Multi-level graph (AST+CFG+DFG), dual-branch GNN, F1=0.811, AUC=0.896.
5 wymiarów quality: maintainability, readability, complexity, testability, architectural integrity.
AGQ ranking = Dai architectural integrity ranking (Spearman rho=1.0, n=4).
Dane: `artifacts/benchmark/dai_et_al_comparison.json`

**Sutoyo, Avgeriou, Capiluppi (2025)**
Tracing the Lifecycle of Architecture Technical Debt in Software Systems: A Dependency Approach.
_arXiv:2501.15387v2, University of Groningen_
https://arxiv.org/html/2501.15387v2
FAN-IN/OUT vs change frequency: r=0.175–0.241 (weak), n=57 ATD items, 103 Apache projects.
Wniosek: "FAN-IN/OUT should be combined with other measures" — potwierdza potrzebę composite score.

**Šora (2013)**
Software Architecture Reconstruction Through Clustering: Finding the Right Similarity Metric.
_Polytechnic University of Timișoara_
https://staff.cs.upt.ro/~ioana/papers/SoraWorkshop2013.pdf
Indirect coupling via ESM (Edge Strength Metric, Chiricota 2003).
Similarity(A,B) = DC(A,B) · IC(A,B) · LA(A,B). Trzy czynniki: direct coupling,
indirect coupling (wspólni sąsiedzi), architectural layer distance.
QSE nie implementuje IC — potencjalne ulepszenie.

**Koziolek, Nord, Ozkaya, Avgeriou (2014)**
1st International Workshop on Software Architecture Metrics (SAM2014).
_SEI CMU_
https://www.sei.cmu.edu/documents/5417/2014_017_001_88179.pdf
Definiuje "software architecture metric" jako quality metric concerning architecture.
Prezentuje MISI (Sarkar 2007), Module Interaction Stability Index — pokrewne z QSE stability.

**Lakos (1996)**
Large-Scale C++ Software Design.
_Addison-Wesley_
ISBN: 978-0-201-63362-5
Definiuje CCD (Cumulative Component Dependency) = Σ |reachable(v)|.
QSE nie implementuje CCD — potencjalne ulepszenie.

**Chidamber & Kemerer (1994)**
A Metrics Suite for Object Oriented Design.
_IEEE Trans. Softw. Eng., 20(6), pp. 476–493_
Definiuje CBO (Coupling Between Objects), LCOM, DIT, NOC, WMC, RFC.
Fundament dla QSE cohesion (LCOM4 jest rozwinięciem ich LCOM).

---

## 14. Walidacja QSE — wyniki własne (2026-03-21)

Dane w `artifacts/benchmark/`. Skrypty w `scripts/`.

**SonarQube cross-validation (n=79 Python)**
AGQ composite orthogonal do Sonar (0/8 absolute correlations sig.).
Po normalizacji per KLOC:
- stability vs bugs/KLOC: r=-0.32, p=0.003
- cohesion vs complexity/KLOC: r=-0.28, p=0.01
Interpretacja: AGQ mierzy inny wymiar; dwa składowe mają związek z defektami.
Dane: `sonar_vs_agq_validation.json`, Skrypt: `sonar_cross_validation.py`

**Known-good vs known-bad (n=20 Python)**
10 community-recognized well-architected repos vs bottom-10 AGQ.
Mann-Whitney U=0, p<0.001, Cohen's d=3.22 (very large).
80% good = LAYERED fingerprint, 60% bad = FLAT/LOW_COHESION.
Główny dyskryminator: stability (mean 0.84 vs 0.44).
Dane: `known_good_bad_validation.json`, Skrypt: `known_good_bad_validation.py`

**Emerge cross-validation (n=16 Python)**
Louvain Q nie jest porównywalny między narzędziami (r=0.06) — graph definition dependent.
QSE stability jest size-invariant; Emerge fan-out confounded by repo size (r=0.67).
Dane: `emerge_vs_qse_comparison.json`, Skrypt: `compare_emerge.py`

**Dai et al. comparison (n=4 Java)**
Apache Ant, Eclipse JDT, Apache Camel, Apache Hadoop.
AGQ ranking = Dai architectural integrity ranking (Spearman rho=1.0).
AGQ daje actionable diagnostykę (god classes, flat architecture, cycles).
Dane: `dai_et_al_comparison.json`, Skrypt: `dai_et_al_comparison.py`
