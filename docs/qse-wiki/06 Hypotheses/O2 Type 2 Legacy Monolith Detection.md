---
type: hypothesis
id: O2
status: otwarta
language: pl
topic: legacy, monolith, anomalia
sesja_turn: Turn 34 (sentry)
---

# O2 — Wykrywanie Type 2 Legacy Monolith

## Prostymi słowami

Wyobraź sobie stary moloch: 5000 klas, nikt nie odważy się nic zmieniać, ale każda klasa robi swoje. Niemal zero cykli, dobre AGQ — bo nikt niczego nie dotknął od lat. To jest Type 2 Legacy Monolith: projekt który *wygląda* jak dobra architektura topologicznie, ale jest złą architekturą przez przeterminowanie, tech debt i brak aktywnego utrzymania.

## Co badano

> **H₁:** Istnieje charakterystyczny fingerprint Type 2 Legacy Monolith w metrykach QSE: A≈1.0 (brak cykli — bo nikt niczego nie rusza), S niskie (bo każda klasa robi swoje, ale ich sieć jest nieuporządkowana), CD niskie (bo projekt jest rozrośnięty, dużo klas, gęstość mała), Panel≈2.0.

Wzorzec fingerprintu: wysoki AGQ v2, ale niski Panel. **Type 1 False Positive.**

## Status

**OTWARTA** — wzorzec zaobserwowany na 1 projekcie (sentry), niezwalidowany.

## Obserwacja z GT Python (Turn 34)

```
sentry (GitHub: ~60k stars, duży projekt):
  nodes = 4863
  ratio = 8.32 (bardzo wysokie — tangled imports!)
  M = 0.617
  A = 0.837
  S = 0.589
  C = 0.509
  AGQ v2 = 0.640
  Panel = 6.00 (POS — choć wysoki ratio sugeruje problemy)
```

Sentry jest **pozytywnym** w GT (Panel=6.00) mimo ratio=8.32 — to kontrprzykład dla E2. Interpretacja panelu: duży projekt enterprise z aktywnym utrzymaniem. Ale jeśli Panel byłby niższy (2.0), ten wzorzec wyglądałby jak Type 2.

Prawdziwy Type 2 Legacy: **nie wykryty** jeszcze w GT — nie mamy repo z A≈1.0, S niskie, CD niskie, Panel≈2.0.

## Wzorzec fingerprintu

| Metryka | Type 1 (dobra) | Type 2 (legacy false positive) | Type 3 (tangled) |
|---|---|---|---|
| A (Acyclicity) | ~1.0 | ~1.0 | < 0.9 |
| S (Stability) | ~0.2–0.5 | < 0.2 | ~0.1–0.3 |
| CD | 0.5–0.7 | < 0.4 | < 0.3 |
| Panel | 7–9 | 2–3 | 2–3 |
| AGQ v2 | ~0.55 | ~0.55 | ~0.42 |
| flat_score (Python) | > 0.6 | > 0.6 | < 0.3 |

Type 2 i Type 1 są **nierozróżnialne** przez AGQ v2. To poważny problem praktyczny.

## Potencjalne metryki diagnostyczne

1. **Age metrics:** wiek ostatniego commit na moduł — stary = brak utrzymania
2. **Churn ratio:** współczynnik zmian na plik — legacy = małe (nikt nie rusza)
3. **Dependency staleness:** czy zależności zewnętrzne są przeterminowane
4. **Test coverage decay:** czy testy coverage spada — legacy = brak nowych testów

Żadna z tych metryk nie jest w obecnym QSE. Wymagają dostępu do historii VCS.

## Dlaczego to ważne

False positive Type 2 to największe ryzyko praktyczne QSE: użytkownik dostaje „dobry AGQ" dla projektu który w praktyce jest nie do utrzymania. Odkrycie i opisanie tego wzorca jest konieczne zanim QSE zostanie użyty w produkcji.

## Warunki zamknięcia

1. Zebrać ≥5 repozytoriów które pasują do wzorca (stary, duży, wysoki AGQ, Panel<3.0)
2. Ocenić panelowo
3. Sprawdzić czy metryki VCS (churn, age) odróżniają je od Type 1

## Powiązania

- [[O3 AGQv3c vs AGQv2 on Jolak]] — Jolak ma projekty enterprise (potencjalny Type 2?)
- [[E2 Coupling Density]] — kontrprzykład spring-security (wysoki ratio, dobry Panel)
- [[Hypotheses Register]] — pełna lista hipotez
