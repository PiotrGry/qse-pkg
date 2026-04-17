---
type: research
language: pl
---

# Analiza rynku i krajobrazu konkurencyjnego

## Prostymi słowami

Rynek narzędzi do analizy jakości kodu to ~2.5 miliarda dolarów i rośnie o 15%+ rocznie. Wszyscy gracze patrzą na pojedyncze pliki — nikt nie patrzy na architekturę całego systemu jako gate w CI/CD. AGQ zajmuje puste miejsce na mapie.

---

## Wielkość rynku

| Segment | 2026 | 2030–2035 | CAGR |
|---|---|---|---|
| Static Code Analysis (całość) | $1.45–1.74B | $2.76–6.17B | 7–15% |
| SAST (security focus) | $0.55–0.73B | $1.24–1.55B | 7–23% |
| Software Composition Analysis | $0.41–0.71B | $0.77–3.3B | 7–21% |
| **Łącznie adresowalny** | **~$2.5–3B** | **~$5–10B** | |

Cloud/SaaS = 62.5% rynku, CAGR 19.3%. Segment napędzany przez AI-generated code: wzrost liczby commitów + wzrost ryzyka strukturalnego = wzrost popytu na narzędzia jakości.

---

## Mapa konkurencji

| Narzędzie | Revenue/Wycena | Co mierzy | Poziom | Języki | AI? | Architektura? |
|---|---|---|---|---|---|---|
| **SonarQube** | $98–175M ARR, val. $4.7B | Code smells, bugs, vulns | Plik (mikro) | 30+ | Nie* | **NIE** |
| **Snyk** | $408M ARR, val. $7.4B | Security vulns, deps | Plik + deps | 30+ | Tak | **NIE** |
| **Semgrep** | $34M ARR, val. $0.5–1B | Custom SAST rules | Plik (mikro) | 30+ | Tak | **NIE** |
| **Qodana** | JetBrains (prywatny) | IDE inspections | Plik (mikro) | 20+ | Tak | **NIE** |
| **DeepSource** | $1.8M ARR | Code smells, security | Plik (mikro) | 12+ | Tak | **NIE** |
| **CodeScene** | €7.5M funding | Hotspots, tech debt, org | Plik + behawioralny | 28+ | Nie | Częściowo |
| **Sigrid (SIG)** | Prywatny (consulting) | ISO 25010, benchmark | System | Multi | Nie | Częściowo |
| **CAST Highlight** | $180M+ rev | Portfolio, cloud readiness | Portfolio | 50+ | Nie | Częściowo |
| **ArchUnit** | Open source | Arch rules | Pakiet | **Java only** | Nie | **TAK** |
| **AGQ/QSE** | $0 (badania) | Graf zależności | **Makro** | Python/Java/Go | Opt. | **TAK** |

*SonarSource kupił AutoCodeRover (luty 2025) — zaczynają AI play, ale nie architektura.

---

## Pozycjonowanie strategiczne

```
                    MIKRO (plik)          MAKRO (architektura)
                    ────────────          ────────────────────
Security focus  │  Snyk, Semgrep     │  (pusto)
                │  $7.4B + $1B       │
                │                    │
Code quality    │  SonarQube,        │  ArchUnit (Java only)
                │  DeepSource,       │  CodeScene (częściowo)
                │  Qodana            │  Sigrid (consulting)
                │  $4.7B + $10M      │
                │                    │
Architektura    │  (pusto)           │  ◄── AGQ TUTAJ
+ AI code gate  │                    │  (nikt nie jest)
```

**AGQ = jedyny w kwadrancie: makro + architektura + CI gate + AI code focus.**

---

## Analiza poszczególnych graczy

### SonarQube — incumbent, ale mikro-only

- Revenue: $98–175M ARR (getlatka.com), wycena $4.7B (SiliconAngle, 2022)
- Metryki per plik: code smells, bugs, vulnerabilities
- **Nie patrzy na graf zależności** — potwierdzono empirycznie: n=78, wszystkie korelacje AGQ vs SonarQube p>0.10
- Strategie AI: zakup AutoCodeRover (luty 2025) — AI naprawia bugi, nie architekt
- Wniosek: naturalny komplementarny partner, nie konkurent

### Snyk — security-first

- Revenue: $408M ARR, wycena $7.4B (sdxcentral.com)
- Focus: vulnerabilities, dependency scanning
- Growth spowalnia (12% YoY) — rynek szuka nowych kategorii
- Nie zajmuje się architekturą systemu

### Semgrep — custom rules per plik

- Revenue: $34M ARR, seria D $100M (2025)
- Custom SAST rules per plik — potężne, ale widzi plik, nie graf
- Dobry dla team-specific reguł stylistycznych, nie dla makro-struktury

### ArchUnit — najbliższy architektonicznie

- Open source (bezpłatny)
- **Java only** — nie Python, Go, TypeScript
- Nie SaaS — wymaga konfiguracji per projekt
- Brak benchmarku/kalibracji statystycznej
- AGQ jest wielojęzykowy i statystycznie skalibrowany

### CodeScene — najbliższy komercyjny

- Funding: €7.5M
- Analiza hotspotów (gdzie kod zmienia się najczęściej) + organizational patterns
- Częściowo architektoniczny: widzi wzorce na poziomie modułu, ale nie mierzy grafu deterministycznie
- Cennik: €18/aktywny autor/miesiąc

### Sigrid (SIG) — ISO 25010

- Model consultingowy — nie self-service SaaS
- Benchmarking względem norm ISO 25010
- Drogie (dziesiątki tys. EUR), zamknięty model
- Nie mierzy grafu; ocena systemowa przez konsultantów

---

## Dlaczego nikt nie zajmuje kwadranta AGQ

| Gracz | Dlaczego nie jest w kwadrnacie AGQ |
|---|---|
| SonarQube | Pre-AI era, mierzy pliki. Powolna innowacja poza security. |
| Snyk | Security-first, nie quality/architektura. Spowalnia. |
| Semgrep | Custom rules per plik, nie widzi grafu. |
| ArchUnit | Java-only, nie SaaS, nie multi-lang, brak kalibracji. |
| CodeScene | Behawioralny + hotspots, nie mierzy grafu deterministycznie. |
| Sigrid | ISO 25010 benchmark, model consulting, nie self-service. |

Wnioski: lukę tworzy kombinacja wymagań: multi-language + makro (graf) + CI gate + deterministyczny + AI code focus + SaaS. Żaden gracz nie spełnia wszystkich pięciu.

---

## Sizing rynku dla AGQ

| Metryka | Wartość | Założenia |
|---|---|---|
| TAM (Total Addressable) | ~$2.5B (2026) | Cały rynek static analysis + SCA |
| SAM (Serviceable Available) | ~$400–600M | Firmy z CI/CD + generujące kod AI |
| SOM (Serviceable Obtainable, rok 3–5) | ~$5–20M | SaaS, self-service, niche „arch quality" |

**Benchmark cenowy:**
- SonarQube: $0 (community) do ~$50K/rok (enterprise)
- CodeScene: €18/aktywny autor/miesiąc
- DeepSource: $8–24/dev/miesiąc
- Model AGQ (szacunek): $15–30/dev/miesiąc → 1000 devów = $180–360K ARR per klient enterprise

---

## Kluczowe wnioski strategiczne

1. **Rynek $2.5B i rośnie 15%+/rok** — napędzany AI-generated code (więcej commitów = więcej popytu)
2. **Nikt nie mierzy architektury w CI** — luka rynkowa potwierdzona obiektywnie
3. **SonarQube = incumbent** ale mikro-only, powolna innowacja poza security
4. **Snyk spowalnia** (12% growth) — rynek szuka nowych kategorii
5. **ArchUnit = jedyny architektoniczny** ale Java-only, nie SaaS, brak kalibracji
6. **AGQ = nowa kategoria:** „Architecture Quality as a Service" / „Policy as a Service"
7. **Naturalny partner: SonarQube** — komplementarne narzędzia, możliwa integracja wtyczkowa

---

## Źródła danych rynkowych

- Static Code Analysis Market: businessresearchinsights.com/market-reports/103252
- SAST Market: mordorintelligence.com/industry-reports/static-application-security-testing-market
- SonarSource $4.7B: siliconangle.com (2022-04-26)
- SonarSource revenue: getlatka.com/companies/sonarsource.com
- Snyk $408M ARR: getlatka.com/companies/snyk
- Semgrep $100M Series D: semgrep.dev/blog/2025/series-d-announcement
- CodeScene pricing: codescene.com/pricing

---

## Zobacz też

- [[Research Thesis|Teza badawcza]] — dlaczego potrzebny jest AGQ
- [[Literature Review|Przegląd literatury]] — naukowe potwierdzenie luki
- [[Future Directions|Kierunki badań]] — komercjalizacja
- [[Blind Spot]] — co SonarQube pomija
