---
type: explainer
audience: beginner
---

# Jak działa QSE – prosto

QSE skanuje projekt oprogramowania i buduje mapę jego wewnętrznej struktury. Ta mapa nosi nazwę [[Dependency Graph]].

Następnie mierzy kilka ważnych właściwości:

- [[Modularity]]: czy elementy są dobrze od siebie oddzielone?
- [[Acyclicity]]: czy elementy unikają cyklicznych zależności?
- [[Stability]]: czy ważne elementy pozostają niezawodne?
- [[Cohesion]]: czy rzeczy wewnątrz jednego pakietu do siebie pasują?
- [[CD]]: czy graf nie jest zbyt gęsto połączony?
- [[flatscore]]: w Pythonie – czy projekt nie jest zbyt płaski i chaotyczny?

Sygnały te są łączone w jeden końcowy wynik za pomocą [[AGQ Formula]].
