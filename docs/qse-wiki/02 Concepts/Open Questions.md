---
type: concept
language: pl
---

# Otwarte pytania (Open Questions)

## Prostymi słowami

Projekt badawczy uczciwy wobec siebie dokumentuje nie tylko to co wie, ale też co nie wie. QSE ma kilka fundamentalnych pytań bez odpowiedzi. To nie jest słabość — to mapa priorytetów dla kolejnych eksperymentów i przyszłych prac naukowych.

## Szczegółowy opis

### Pytania badawcze pierwszorzędne

**O1: Czy AGQ v3c generalizuje z Javy i Pythona na Go?**

Java n=59 (MW p=0.000221) i Python n=30 (flat_score p=0.007). Go jest przebadane tylko benchmarkiem (n=30) bez Ground Truth panelowego. Go ma strukturalnie inne właściwości (brak dziedziczenia klas → Cohesion=1.0 zawsze, ekosystem wymusza brak cykli → Acyclicity≈1.0). Czy metryki M i S nadal dyskryminują jakość dla Go?

*Kryterium sukcesu:* n≥20 Go repos z panelem, MW p<0.05.

**O2: Detekcja Type 2 Legacy Monolith w Pythonie**

Buildbot (Panel=2.75) ma flat_score=0.95 (bo ma głęboką hierarchię) ale jest złą architekturą. "Legacy monolith z hierarchią" to odrębny anty-wzorzec niewidoczny dla flat_score. Jak go wykryć?

Hipoteza: kombinacja wysokiego NSdepth z niskim Cohesion i wysokim CD. Do sprawdzenia.

**O3: Czy AGQ v3c jest lepsza od AGQ v2 na zbiorze Jolak?**

Wyniki sesji Turn 36-37: v3c i v2 mają identyczną moc na Javie (partial r=+0.524 vs +0.543). Jolak cross-validation potwierdziła S i CD. Ale czy v3c (equal 0.20 wagi) jest stabilniejsze na zewnętrznym zbiorze testowym?

**O4: Czy metryki namespace (NSdepth, NSgini) poprawiają AGQ dla Pythona?**

NSdepth ma silny sygnał dla Javy (partial r=+0.698, p=0.008) ale słaby dla Pythona (p=0.122 ns). NSgini jest ns wszędzie. Czy kombinacja NSdepth + flat_score + AGQ_v3c da lepszą moc dla Pythona?

**O5: Dlaczego CD ma odwrócony kierunek dla Pythona?**

Java: wyższe CD → NEG (p=0.034). Python: wyższe CD → POS (odwrotnie). Wyjaśnienie robocze: youtube-dl (NEG) ma 895 modułów w jednym namespace z minimalną liczbą krawędzi (brak struktury) → niski CD. Saleor (POS) ma wiele krawędzi między warstwami → wyższy CD. Ale to hipoteza, nie sprawdzony mechanizm.

### Pytania metodologiczne

**Czy symulowany panel jest wystarczający do publikacji naukowej?**

Panel ekspertów w QSE to cztery role symulowane przez LLM — nie prawdziwi eksperci. To ograniczenie metodologiczne. Dla publikacji naukowej może być potrzebna walidacja z prawdziwymi ekspertami (co najmniej n=3 niezależnych recenzentów).

**Czy AGQ-adj (korekta rozmiaru) jest potrzebna?**

Małe projekty (< 50 węzłów) mają zawyżone AGQ z powodów strukturalnych (trywialnie brak cykli w 10 plikach). AGQ-adj normalizuje względem rozmiaru. Czy to poprawia moc predykcyjną? Dane benchmarkowe sugerują r=+0.236 dla AGQ-adj vs hotspot_ratio — ale wymagają dalszej walidacji.

**Jak mierzyć jakość w mikrousługach?**

W systemie mikrousług każda usługa to osobne repozytorium. AGQ per-repo mierzy jakość jednej usługi, ale nie mierzy jakości systemu jako całości (sprzężeń między serwisami przez API). Jak QSE powinno obsłużyć multi-repo systemy?

### Pytania o praktyczne zastosowanie

**Jaki próg AGQ jako quality gate?**

Benchmark pokazuje: Go mean=0.783, Python mean=0.748, Java mean=0.627. Próg 0.75 może być sensowny dla Pythona/Go, ale zablokuje ~50% projektów Java. AGQ-z jest lepszym mechanizmem gate'owania — ale "jak dużo poniżej średniej jest zbyt mało?"

**Czy AGQ jest stabilne w czasie?**

Projekt może mieć AGQ=0.72 w Q1 i 0.68 w Q2. Czy to degradacja architektoniczna? Czy tylko normalny szum wynikający z nowych modułów? Brak danych temporalnych — to kierunek przyszłych badań.

## Lista otwartych pytań (format wiki)

- [[O1 AGQv3c Java to Go]] — generalizacja na Go
- [[O2 Type 2 Legacy Monolith Detection]] — wykrywanie legacy monolith  
- [[O3 AGQv3c vs AGQv2 on Jolak]] — porównanie wersji
- [[O4 Namespace Metrics for Python]] — rozszerzenie dla Pythona
- [[O5 Python CD Direction]] — odwrócony kierunek CD

## Definicja formalna

Otwarte pytanie \(Q\) spełnia:

- \(Q\) jest falsyfikowalne (istnieje eksperyment który odpowie TAK lub NIE)
- \(Q\) dotyczy mierzalnej właściwości systemu AGQ
- \(Q\) nie jest jeszcze odpowiedziane w żadnym eksperymencie \(E_1, \ldots, E_k\)

Pytania nie-falsyfikowalne (np. "czy AGQ jest filozoficznie poprawne?") nie należą do tej listy.

## Zobacz też

- [[Hypotheses Register]] — formalne hipotezy do przetestowania
- [[Experiments Index]] — zrealizowane eksperymenty
- [[Hypothesis]] — jak tworzyć hipotezy w QSE
- [[Open Questions Expanded]] — rozszerzona wersja tej listy
