# Twoja aplikacja działa. Ale czy jest gotowa na skalowanie?

Platformy takie jak Loveable, Bolt czy v0 zrewolucjonizowały tworzenie oprogramowania. Startup może mieć działający produkt w kilka godzin, bez zatrudniania zespołu programistów. Kod działa. Testy przechodzą. Klient jest zadowolony.

Do momentu gdy produkt zaczyna rosnąć.

Skalowanie aplikacji to nie tylko więcej serwerów. To przede wszystkim pytanie o **wewnętrzną strukturę kodu** - czy moduły są od siebie niezależne, czy zależności między nimi tworzą błędne pętle, czy system ma czytelną hierarchię pozwalającą na rozbudowę bez rozsypywania tego co już działa.

Modele AI generujące kod optymalizują pod kątem "działa teraz". Nie mają dostępu do globalnej struktury zależności projektu. Każdy dodany feature może niepostrzeżenie dokładać dług architektoniczny - niewidoczny dla klienta, niewidoczny dla standardowych narzędzi jakości, widoczny dopiero gdy jest już za późno i zbyt drogo.

**Klient kupuje działający produkt. Nikt nie mówi mu w jakim stanie jest jego architektura.**

---

## Co budujemy

**QSE (Quality Score Engine)** to projekt badawczy, którego celem jest stworzenie mierzalnej, automatycznej metryki jakości architektonicznej oprogramowania.

Opracowana metryka **AGQ** (*Architecture Graph Quality*) analizuje graf zależności między modułami projektu i oblicza wynik [0–1] na podstawie czterech właściwości strukturalnych: braku cykli zależności, spójności klas, hierarchii warstw i izolacji modułów. Niezależnie od tego kto napisał kod - człowiek czy model AI.

---

## Co już pokazaliśmy

W wstępnych eksperymentach na ~240 repozytoriach open-source (Python, Java, Go) uzyskaliśmy kilka obiecujących wyników:

- **AGQ wykrywa problemy których SonarQube nie widzi** - zidentyfikowaliśmy projekty z najwyższą oceną Sonar i jednocześnie zdegradowaną architekturą. Korelacja między AGQ a metrykami SonarQube jest bliska zeru (p>0.10) - narzędzia mierzą niezależne wymiary jakości.

- **AGQ ma mierzalny związek z kosztami utrzymania kodu** - po normalizacji względem rozmiaru projektu metryka koreluje z częstością zmian w najbardziej "gorących" plikach (r=+0.24, p<0.001). Efekt umiarkowany, ale statystycznie powtarzalny na zbiorze 234 projektów.

- **71% przebadanych projektów Java ma cykliczne zależności między modułami** - zjawisko powszechne, rzadko mierzone i rzadko zarządzane. W Go: 0% - różnica wynikająca z paradygmatu języka, nie z jakości programistów.

- **Analiza trwa 0.32 sekundy** - co otwiera możliwość automatycznego sprawdzania architektury przy każdym commicie, bez spowalniania pracy zespołu.

---

## Gdzie jesteśmy i dokąd zmierzamy

Projekt jest na etapie badawczym. Mamy działający prototyp, wstępne wyniki empiryczne i otwarte pytania, które warto zbadać formalnie:

- Czy aplikacje generowane przez platformy no-code/AI degradują architektonicznie szybciej niż pisane ręcznie?
- Czy możemy przewidywać ryzyko utrzymaniowe i skalowania łącząc AGQ z historią zmian?
- Jak dać klientowi końcowemu czytelny sygnał o stanie architektonicznym jego produktu - zanim zdecyduje się go skalować?

Szukamy partnerów badawczych i przemysłowych, którzy chcieliby wspólnie eksplorować ten obszar.

---

*Projekt open-source · Python / Java / Go · github.com/PiotrGry/qse-pkg*
