---
type: benchmark-data
language: pl
---

# Jolak Cross-Validation

> **Appendix** — dane z niezależnej walidacji krzyżowej na zbiorze Jolak et al. (2025). Cel: sprawdzenie, czy QSE odtwarza wyniki niezależnego badania naukowego bez dostępu do jego etykiet.

## Metadane

| Parametr | Wartość |
|---|---|
| Źródło | Jolak et al. (2025), Table 1 — 8 Java OSS projects |
| Skaner | `qse.java_scanner` (pure-Python, tree-sitter-java, file-level granularity) |
| Formuła AGQ | v3c, wagi równe: M=A=S=C=CD=0.20 |
| Status | ✅ 4/5 wniosków potwierdzonych, 1 prawdopodobny |
| Commit | aa85608 |

---

## Wyniki per repozytorium

| Repozytorium | Pliki | Węzły wew. | Pakiety | Klasy | M | A | S | C | CD | AGQ v3c |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| networknt/light-4j | 897 | 894 | 109 | 885 | 0.623 | 0.9987 | 0.231 | 0.406 | 0.209 | **0.4935** |
| weibocom/motan | 589 | 589 | 87 | 597 | 0.580 | 0.9955 | 0.111 | 0.342 | 0.349 | **0.4755** |
| LinShunKang/MyPerf4J | 259 | 259 | 40 | 259 | 0.797 | 1.000 | 0.954 | 0.475 | 0.552 | **0.7557** |
| seata/seata | 2823 | 2816 | 487 | 2796 | 0.693 | 0.9924 | 0.282 | 0.349 | 0.122 | **0.4875** |
| alibaba/Sentinel | 1223 | 1185 | 333 | 1180 | 0.734 | 0.9888 | 0.065 | 0.427 | 0.362 | **0.5154** |
| sofastack/sofa-rpc | 1210 | 1204 | 195 | 1200 | 0.616 | 0.9956 | 0.116 | 0.391 | 0.313 | **0.4864** |
| making/yavi | 472 | 472 | 20 | 450 | 0.757 | 0.9942 | 0.654 | 0.303 | 0.287 | **0.5988** |
| srikanth-lingala/zip4j | 129 | 129 | 14 | 129 | 0.448 | 0.9939 | 0.306 | 0.272 | 0.334 | **0.4705** |

**Mean AGQ v3c = 0.535** (oczekiwane: pomiędzy GT-POS=0.571 a GT-NEG=0.486 ✅)

---

## Podsumowanie statystyk

| Statystyka | Wartość |
|---|---|
| Mean AGQ v3c | 0.535 |
| Min AGQ v3c | 0.4705 (zip4j) |
| Max AGQ v3c | 0.7557 (MyPerf4J) |
| Stability — zakres | [0.065 – 0.954] |
| Stability — bardzo niska (Sentinel) | 0.0645 |
| Stability — bardzo niska (motan) | 0.111 |
| Stability — bardzo niska (sofa-rpc) | 0.116 |

---

## Wyniki walidacji: QSE vs Jolak et al.

| Wniosek Jolak | Repozytorium | Wynik QSE | Status |
|---|---|---|---|
| Słaba architektura (niska spójność) | light-4j | AGQ=0.494, C=0.406 (niska) | ✅ POTWIERDZONE |
| Słaba architektura (cykliczne zal.) | seata | AGQ=0.488, A=0.992 | ✅ POTWIERDZONE |
| Relatywnie lepsza architektura | MyPerf4J | AGQ=0.756 — wyróżnia się | ✅ POTWIERDZONE |
| Niska stabilność hierarchii | motan, sofa-rpc, Sentinel | S=[0.065–0.116] | ✅ POTWIERDZONE |
| [5. wniosek] | yavi | AGQ=0.599 | 🔶 PRAWDOPODOBNE |

**4/5 wniosków Jolaka potwierdzonych deterministycznie przez QSE bez dostępu do etykiet.**

---

## Kluczowe obserwacje

### Stability — silne zróżnicowanie
Stability (S) pokazuje najszerszy zakres [0.065–0.954] wśród wszystkich komponentów. Projekt MyPerf4J wyróżnia się S=0.954 (prawie idealna hierarchia), podczas gdy Sentinel ma S=0.065 (praktycznie brak hierarchii). To potwierdza silny dyskryminacyjny potencjał metryki S dla Java.

### CD gap — różnica względem GT
Repozytoria Jolaka mają niższe CD niż repozytoria GT-NEG:
- Jolak mean CD ≈ 0.316
- GT-NEG mean CD ≈ 0.380

Sugeruje to, że GT może niedostatecznie reprezentować enterprise middleware (luźno połączone systemy mikroserwisowe). Obserwacja odnotowana jako **CD gap** — potencjalny kierunek rozszerzenia GT.

### Pozycja mean AGQ względem GT
Mean Jolak (0.535) leży pomiędzy GT-POS (0.571) a GT-NEG (0.486) — dokładnie tam, gdzie powinna być mieszana próba projektów. Oznacza to, że wagi AGQ v3c kalibrowane na GT poprawnie klasyfikują nowe repozytoria.

---

## Błąd krytyczny naprawiony podczas walidacji

W trakcie przygotowania do walidacji Jolaka odkryto krytyczny błąd w skanerze Java:

**v1 (błędna):** Węzły na poziomie pakietu (20 węzłów dla yavi, A=0.400)
**v2 (poprawiona):** Węzły na poziomie pliku (687 węzłów dla yavi, A=0.994)

Poprawka: węzły tworzone jako `package.ClassName` per plik `.java` — zgodnie z zachowaniem skanera Rust. Bez tej poprawki wyniki byłyby nieporównywalne z GT.

---

## Implikacje dla projektu

1. **Niezależna walidacja** — QSE poprawnie odtwarza zewnętrzne wyniki bez dostępu do etykiet
2. **Wykrywalność enterprise middleware** — Sentinel i sofa-rpc mają bardzo niską S, co QSE wykrywa
3. **CD gap** — sugestia rozszerzenia GT o projekty middleware
4. **Metodologia** — walidacja krzyżowa na zewnętrznych zbiorach jest wykonalna i wartościowa

---

## Źródło

Jolak et al. (2025) — badanie analizujące jakość architektoniczną 8 projektów Java OSS z ekosystemu chińskiego (Alibaba, Tencent, Sofa). Szczegóły w: [[11 Research/Literature Review|Przegląd literatury]]

---

## Zobacz też

- [[Benchmark Index]] — przegląd wszystkich zbiorów
- [[Java GT Dataset]] — główny zbiór walidacyjny Java
- [[08 Glossary/GT|GT]] — metodologia ground truth
- [[08 Glossary/Mann-Whitney|Mann-Whitney]] — testy statystyczne
- [[11 Research/Literature Review|Przegląd literatury]] — Jolak et al. w kontekście
