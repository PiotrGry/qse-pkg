# Acyclicity

Acyclicity (acykliczność) oznacza, że projekt unika zależności cyklicznych.

Zależność cykliczna powstaje, gdy część A zależy od części B, a część B ostatecznie zależy z powrotem od części A.

Takie pętle mogą utrudniać modyfikację systemu i rozumowanie o nim.

QSE wykrywa takie pętle przy użyciu algorytmu [[Tarjan SCC]].
