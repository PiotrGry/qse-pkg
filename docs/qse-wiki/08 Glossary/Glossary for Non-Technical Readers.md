---
type: glossary-nontechnical
language: pl
---

# Słowniczek dla niespecjalistów

> Ten dokument tłumaczy pojęcia QSE bez zakładania wiedzy technicznej. Jeśli znasz programowanie i chcesz pełnych definicji — zajrzyj do [[Glossary|Słownika technicznego]].

---

## Część A — Pojęcia architektoniczne

### Architektura oprogramowania
Jak zorganizowany jest kod projektu jako całość — kto z kim „rozmawia", kto komu wydaje polecenia, kto jest „fundamentem", a kto „dekoracją". Dobra architektura to jak dobrze zaprojektowane miasto: dzielnice, drogi, hierarchia. Zła architektura to chaos — każda uliczka połączona z każdą inną.

### Cykl zależności
Moduł A zależy od B, B zależy od C, C zależy od A — pętla. Jak zamknięte koło: żeby zmienić A, musisz zmienić B, żeby zmienić B, musisz zmienić C, żeby zmienić C, musisz zmienić A. Koniec — nie możesz zacząć. Dobra architektura: zależności idą w jednym kierunku, bez pętli.

### Graf zależności
Mapa: kto importuje kogo? Moduły to „miasta na mapie", importy to „drogi między miastami". QSE buduje tę mapę automatycznie i analizuje jej właściwości: czy drogi tworzą sensowną hierarchię, czy każde miasto połączone jest z każdym innym, itp.

### Moduł / Pakiet
Moduł to jeden plik z kodem (np. `user_service.py`). Pakiet to folder zawierający kilka modułów (np. `services/`). QSE analizuje zależności między modułami — kto importuje kogo.

### Warstwa (Layer)
Poziom w hierarchii projektu. Jak piętra w budynku: parter (baza danych), pierwsze piętro (logika biznesowa), drugie piętro (interfejs użytkownika). Dobre projekty mają wyraźne warstwy — wyższe warstwy korzystają z niższych, ale nie odwrotnie.

### Dług techniczny
Nagromadzone „złe decyzje" z przeszłości, które teraz kosztują czas i wysiłek przy każdej zmianie. Jak pożyczka: najpierw szybko i tanio, potem spłacasz z odsetkami. Dług architektoniczny to najdroższa forma długu technicznego.

---

## Część B — Metryki QSE

### AGQ — Architecture Graph Quality
Jedna liczba od 0 do 1 opisująca jakość architektoniczną całego projektu. 1 = idealna architektura (jak wieża Babel z instrukcją), 0 = chaos total (jak szuflada z wszystkim wymieszanym). Typowe projekty open-source: 0.70 – 0.80.

### Modularity (Modularność)
Czy kod jest podzielony na wyraźne „moduły" — grupy, które bardziej rozmawiają między sobą niż z resztą? Jak dobra szafa: koszule razem, spodnie razem, skarpetki razem. Zła szafa: wszystko razem, w każdej szufladzie po trochu każdego.

### Acyclicity (Acykliczność)
Brak pętli zależności. 1.0 = zero pętli, idealny przepływ w jednym kierunku. 0.5 = połowa kodu w pętlach. Pętle to złodziej czasu dewelopera: każda zmiana ciągnie za sobą zmiany w kółko.

### Stability (Stabilność)
Czy projekt ma wyraźne „fundamenty" i „dekoracje"? Fundamenty (interfejsy, klasy abstrakcyjne) powinny być stabilne — nic nie rusza. Dekoracje (konkretne implementacje) mogą się zmieniać swobodnie. Projekt ze wszystkim na jednym poziomie — jak dom bez piwnicy — jest niestabilny architektonicznie.

### Cohesion (Spójność)
Czy każda klasa/moduł robi jedną rzecz? Dobra klasa: jak kalkulator — tylko liczby. Zła klasa: jak „wszystko-w-jednym" — kalkulator + tłumacz + prognoza pogody. Niska spójność = klasy-kombajny = trudne do testowania i rozumienia.

### Coupling Density (Gęstość powiązań)
Jak gęsto powiązane są moduły? Sparse (rzadkie) powiązania = każdy moduł zna kilku sąsiadów. Dense (gęste) = każdy zna każdego. Rzadsze = lepsze: łatwiej zmienić jeden moduł nie dotykając innych.

---

## Część C — Dane i statystyki

### n (liczebność)
Ile projektów/obserwacji mamy w danych. Java GT: n=59. Python GT: n=30. Im większe n, tym bardziej można ufać wynikom statystycznym.

### p-value (wartość p)
Prawdopodobieństwo, że wynik jest dziełem przypadku. p=0.05 → 5% szans na przypadek (akceptowalny). p=0.001 → 0.1% szans (bardzo pewny wynik). p=0.000221 (Java GT AGQ) → prawie niemożliwe, żeby to był przypadek.

### AUC-ROC
Miara jakości klasyfikatora w skali 0.5–1.0. AUC=0.5 → losowe zgadywanie. AUC=1.0 → idealna klasyfikacja. AUC=0.767 (Java GT AGQ) → 76.7% szans, że losowy dobry projekt ma wyższy AGQ niż losowy zły projekt.

### Spearman ρ (rho)
Korelacja rangowa — jak silnie dwie zmienne chodzą razem? ρ=1.0 → idealnie razem (wyższy AGQ zawsze = lepszy panel). ρ=0 → brak związku. ρ=0.38 (Java GT) → umiarkowany związek, statystycznie pewny.

### POS / NEG
Skróty dla pozytywnego (dobra architektura) i negatywnego (słaba architektura) przykładu w zbiorze GT. Nie mają nic wspólnego z „pozytywnym nastawieniem" — to czysto techniczne etykiety.

### Ground Truth (GT)
Zestaw projektów z „kluczem odpowiedzi" — wiemy z góry, które są dobre, a które złe (na podstawie ekspertów). Używany do sprawdzenia, czy AGQ prawidłowo klasyfikuje projekty.

---

## Część D — Kontekst badawczy

### Vibe coding
Potoczna nazwa programowania z pomocą AI (GitHub Copilot, Claude Code, Cursor itp.), gdzie developer opisuje zamiar, a AI generuje kod. Szybkie, ale rodzi ryzyko „architektura popada w chaos, bo AI nie widzi całego projektu".

### Quality Gate
Automatyczna brama w procesie CI/CD — kod może zostać scalony tylko jeśli przejdzie test jakości. SonarQube to gate na poziomie pliku. AGQ to gate na poziomie architektury (grafu). Razem tworzą kompletniejsze zabezpieczenie.

### CI/CD
Continuous Integration / Continuous Deployment — automatyczny proces: deweloper wgrywa kod → system automatycznie testuje → jeśli OK, wdraża na serwer. QSE wplata się w ten proces jako dodatkowy test jakości architektonicznej.

### SonarQube
Popularne narzędzie jakości kodu. Sprawdza każdy plik osobno: czy kod jest czytelny, czy nie ma błędów, luk bezpieczeństwa. Nie patrzy na relacje między modułami — to właśnie robi QSE.

### Open Source Software (OSS)
Oprogramowanie z publicznie dostępnym kodem źródłowym. QSE waliduje się głównie na OSS (django, flask, spring, hibernate itp.) — bo mamy dostęp do kodu i można mierzyć metryki.

---

## Część E — Co QSE robi i czego nie robi

### Co QSE robi ✅
- Mierzy jakość architektury jako całości (poziom grafu zależności)
- Wykrywa cykliczne zależności między modułami
- Ocenia hierarchię warstw i spójność klas
- Działa w mniej niż sekundę na typowy projekt
- Może być zintegrowany z CI/CD jako gate

### Czego QSE nie robi ❌
- Nie sprawdza poprawności logicznej kodu (to robią testy)
- Nie wykrywa luk bezpieczeństwa (to robi SonarQube/Snyk)
- Nie przewiduje przyszłych bugów (planowana warstwa Predictor)
- Nie mówi jak naprawić problem — tylko gdzie jest
- Nie zastępuje code review przez człowieka — uzupełnia go

---

## Zobacz też

- [[Glossary|Słownik techniczny]] — pełne definicje formalne
- [[AGQ|AGQ]] — szczegóły metryki
- [[Benchmark Index|Indeks benchmarków]] — gdzie QSE był testowany
- [[Research Thesis|Teza badawcza]] — naukowe pytania projektu
