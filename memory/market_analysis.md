# Analiza rynku i konkurencji AGQ (2026-03-06)

## Wielkość rynku

| Segment | 2026 | 2030-2035 | CAGR |
|---|---|---|---|
| Static Code Analysis (cały) | $1.45-1.74B | $2.76-6.17B | 7-15% |
| SAST (security focus) | $0.55-0.73B | $1.24-1.55B | 7-23% |
| Software Composition Analysis | $0.41-0.71B | $0.77-3.3B | 7-21% |
| Łącznie adresowalny rynek | ~$2.5-3B | ~$5-10B | |

Cloud/SaaS = 62.5% rynku, CAGR 19.3%.

## Mapa konkurencji

| Narzędzie | Revenue/Valuation | Co mierzy | Poziom | Języki | AI? | Architektura? |
|---|---|---|---|---|---|---|
| SonarQube | $98-175M ARR, val. $4.7B | Code smells, bugs, vulns | Plik (mikro) | 30+ | Nie* | NIE |
| Snyk | $408M ARR, val. $7.4B | Security vulns, deps | Plik + deps | 30+ | Tak | NIE |
| Semgrep | $34M ARR, val. $0.5-1B | Custom SAST rules | Plik (mikro) | 30+ | Tak | NIE |
| Qodana | JetBrains (private) | IDE inspections | Plik (mikro) | 20+ | Tak | NIE |
| DeepSource | $1.8M ARR, $10.6M funding | Code smells, security | Plik (mikro) | 12+ | Tak | NIE |
| CodeScene | €7.5M funding | Hotspots, tech debt, org | Plik + behav. | 28+ | Nie | Częściowo |
| Sigrid (SIG) | Private (consulting) | ISO 25010, benchmark | System | Multi | Nie | Częściowo |
| CAST Highlight | CAST $180M+ rev | Portfolio, cloud readiness | Portfolio | 50+ | Nie | Częściowo |
| ArchUnit | Open source (0) | Arch rules | Pakiet | Java only | Nie | TAK |
| AGQ | $0 | Graf zależności | Makro | Python* | Opt. | TAK |

*SonarSource kupilo AutoCodeRover (luty 2025) — zaczynaja AI play.

## Pozycjonowanie

```
                    MIKRO (plik)                    MAKRO (architektura)
                    ────────────                    ────────────────────
Security focus  │  Snyk, Semgrep                │  (pusto)
                │  $7.4B + $1B                  │
                │                               │
Code quality    │  SonarQube, DeepSource,       │  ArchUnit (Java only)
                │  Qodana                       │  CodeScene (częściowo)
                │  $4.7B + $10M + JetBrains     │  Sigrid (consulting)
                │                               │
Architektura    │  (pusto)                      │  AGQ TUTAJ
+ AI code gate  │                               │  (nikt nie jest)
```

AGQ jedyny w kwadrancie: makro + architektura + CI gate + AI code focus.

## Dlaczego nikt tu nie jest

1. SonarQube — pre-AI era, mierzy pliki. AutoCodeRover to AI-fix, nie architektura.
2. Snyk — security-first, nie quality/architektura. $408M ARR ale spowolnienie (12% YoY).
3. Semgrep — custom rules per plik, nie widzi grafu.
4. ArchUnit — jedyny z regulami architektonicznymi, ale Java only, nie SaaS, nie multi-lang.
5. CodeScene — najbliższy konkurent, behawioralny + hotspots, nie mierzy grafu deterministycznie.
6. Sigrid — ISO 25010 benchmark, zamkniety consulting model, nie self-service SaaS.

## Sizing AGQ

| Metryka | Wartość | Założenia |
|---|---|---|
| TAM (Total Addressable) | ~$2.5B (2026) | Caly rynek static analysis + SCA |
| SAM (Serviceable Available) | ~$400-600M | Firmy z CI/CD + generujace kod AI |
| SOM (Serviceable Obtainable) | ~$5-20M (rok 3-5) | SaaS, self-service, niche "arch quality" |

Benchmark cenowy:
- SonarQube: $0 (community) do ~$50K/rok (enterprise)
- CodeScene: €18/aktywny autor/miesiąc
- DeepSource: $8-24/dev/miesiąc
- Sigrid: consulting, dziesiątki tys. EUR
- Model AGQ: $15-30/dev/miesiąc → 1000 devów = $180-360K ARR per klient enterprise

## Kluczowe wnioski

1. Rynek $2.5B i rosnie 15%+/rok — napedzany AI-generated code
2. Nikt nie mierzy architektury w CI — luka rynkowa potwierdzona
3. SonarQube = incumbent ale mikro-only, powolna innowacja
4. Snyk spowalnia (12% growth) — rynek szuka nowych kategorii
5. ArchUnit jedyny architektoniczny ale Java-only, nie SaaS
6. AGQ = nowa kategoria: "Architecture Quality as a Service" / "Policy as a Service"

## Źródła

- Static Code Analysis Market: businessresearchinsights.com/market-reports/103252
- SAST Market: mordorintelligence.com/industry-reports/static-application-security-testing-market
- SonarSource $4.7B: siliconangle.com (2022-04-26)
- SonarSource revenue: getlatka.com/companies/sonarsource.com
- Snyk $408M ARR: getlatka.com/companies/snyk
- Snyk $8.5B val: sdxcentral.com
- Semgrep $100M Series D: semgrep.dev/blog/2025/series-d-announcement
- Semgrep $34M rev: getlatka.com/companies/semgrep.dev
- DeepSource: techcrunch.com (2020-06-16)
- CodeScene: codescene.com/pricing, Wikipedia
- SCA Market: mordorintelligence.com/industry-reports/software-composition-analysis-market
