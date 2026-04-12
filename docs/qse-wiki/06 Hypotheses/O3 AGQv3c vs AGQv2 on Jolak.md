---
type: hypothesis
id: O3
status: otwarta
language: pl
topic: Jolak, walidacja zewnętrzna, AGQv3c
sesja_turn: Turn 9 (sesja 2)
---

# O3 — AGQ v3c bije AGQ v2 na benchmarku Jolak

## Prostymi słowami

Jolak et al. to zewnętrzne, niezależne badanie 8 projektów Java z ocenami jakości architektonicznej. AGQ był walidowany na tym zestawie wcześniej (wyniki W5 — wiarygodne). Pytanie: czy nowa formuła AGQ v3c (równe wagi, bez dominacji S) daje lepsze wyniki na Jolak niż AGQ v2?

## Co badano

> **H₁:** r(AGQ v3c Java, Jolak_scores) > r(AGQ v2, Jolak_scores)

AGQ v2 = 0.20·M + 0.20·A + 0.35·S + 0.05·C + 0.20·CD
AGQ v3c Java = 0.20·M + 0.20·A + 0.20·S + 0.20·C + 0.20·CD

## Status

**OTWARTA** — nie przeprowadzono re-walidacji z AGQ v3c.

## Znane wyniki Jolak (wcześniejsza walidacja)

| Test | AGQ v2 na Jolak | Interpretacja |
|---|---|---|
| Pokrycie | 4/5 potwierdzonych (1 prawdopodobne) | silny wynik |
| Korelacja | r=−0.751 | silny, negatywny (wysokie Jolak Score = niski AGQ u autorów) |
| Kierunek | zgodny z oczekiwaniem | zewnętrzna walidacja |

Uwaga: Jolak repos mają gęstsze coupling niż GT (CD=0.316 vs GT-NEG=0.380). Jolak nie reprezentuje enterprise middleware.

## Dlaczego O3 jest otwarta

AGQ v2 i AGQ v3c Java różnią się głównie wagą S (0.35 vs 0.20). Na GT Java n=14 wynik jest identyczny (Turn 38–41). Ale Jolak to inny dataset z inną dystrybucją — możliwe:

1. Jolak repos mają inne S-charakterystyki niż GT Panel → zmiana wagi S może mieć efekt
2. Jolak walidacja była z AGQ v2 → wyniki mogą być inne dla v3c (lepsze lub gorsze)

## Dane dostępne

Jolak et al. dataset: 8 repozytoriów Java z ocenami autorów. Dane były używane do W5 — ale bez re-skanu z AGQ v3c.

## Plan walidacji

1. Re-skan 8 Jolak repos z QSE (jeśli dane nie są w cache)
2. Oblicz AGQ v3c Java dla każdego
3. Porównaj r(AGQ v3c, Jolak) vs r(AGQ v2, Jolak)
4. Test: Mann-Whitney lub Spearman (n=8, bardzo mała próba)

Uwaga: n=8 to za mało na pewne wnioski, ale Jolak jest wartościową zewnętrzną walidacją nawet przy małym n.

## Implikacja

Jeśli O3 potwierdzona → AGQ v3c Java jest lepsza wersją niż v2 nawet zewnętrznie
Jeśli O3 obalona → zmiana wag S nie poprawia zewnętrznej walidacji → v2 jest wystarczający

## Powiązania

- [[W4 AGQv2 Beats AGQv1 on Java GT]] — poprzedni krok (AGQ v1 → v2)
- [[PCA Weights]] — skąd wziął się AGQ v3c (equal weights)
- [[AGQv3c Java]] — formuła do testowania
- [[Hypotheses Register]] — pełna lista hipotez
