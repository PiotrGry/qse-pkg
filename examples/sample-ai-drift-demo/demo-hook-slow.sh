#!/usr/bin/env bash
# demo-hook-slow.sh — czytelna, wolna wersja demo do nagrywania
# Użycie:
#   asciinema rec demo-hook-slow.cast --command ./demo-hook-slow.sh --cols 90 --rows 36 --quiet

set -e
cd "$(dirname "$0")"

B='\033[1m'
G='\033[0;32m'
R='\033[0;31m'
Y='\033[1;33m'
C='\033[0;36m'
D='\033[2m'
N='\033[0m'

p()  { sleep "${1:-1.5}"; }   # pause
hr() { printf "${D}  ─────────────────────────────────────────────────────────────${N}\n"; }

clear
p 1

# ── Tytuł ─────────────────────────────────────────────────────────────────
printf "${B}${C}  AI-Drift Firewall — Agent-Time Hook${N}\n"
printf "${D}  Wykrywanie architektury w czasie generowania kodu${N}\n\n"
printf "  Platforma : Claude Code (PreToolUse hook)\n"
printf "  Reguły    : CYCLE_NEW · LAYER_VIOLATION · BOUNDARY_LEAK\n"
printf "  Latencja  : ~350ms per edit\n"
p 3

# ── Architektura demo ──────────────────────────────────────────────────────
hr
printf "\n${B}  Architektura serwisu (src/)${N}\n\n"
printf "    domain/          ← czyste value objects, zero I/O\n"
printf "    application/     ← orkiestracja, zależy od domain\n"
printf "    infrastructure/  ← adaptery bazy danych, SMTP itp.\n"
printf "    payments_api/    ← jedyna autoryzowana brama do payments_core\n\n"
printf "  ${D}Reguła: domain NIE może importować infrastructure${N}\n"
printf "  ${D}Reguła: domain NIE może tworzyć cyklu z application${N}\n"
p 4

# ── Czysty baseline ────────────────────────────────────────────────────────
hr
printf "\n${B}  KROK 1/3 — Czysty baseline${N}\n\n"
printf "${D}  \$ cat src/domain/order.py${N}\n\n"
p 1.5
cat src/domain/order.py
p 3

printf "\n  ${G}✓ Zero naruszeń. Czysty DAG.${N}\n"
p 3

# ── Naruszenie warstwy ────────────────────────────────────────────────────
hr
printf "\n${B}  KROK 2/3 — AI agent dodaje forbidden import${N}\n\n"
printf "  Scenariusz: agent \"helpfully\" optymalizuje kod\n"
printf "  i dodaje bezpośredni import do infrastructure.db\n\n"
p 3

printf "${D}  ── Proponowana zmiana: ───────────────────────────────────────${N}\n"
printf "  ${R}+ from src.infrastructure.db import save${N}\n"
printf "  ${R}+ save(self)  # persist directly from domain${N}\n"
printf "${D}  ──────────────────────────────────────────────────────────────${N}\n\n"
p 3

printf "${Y}  [PreToolUse hook] → skanowanie propozycji…${N}\n"
p 1.5

PAYLOAD=$(python3 -c "
import json, os
print(json.dumps({
  'tool_name': 'Write',
  'tool_input': {
    'file_path': os.path.abspath('src/domain/order.py'),
    'content': '''from dataclasses import dataclass
from src.infrastructure.db import save

@dataclass(frozen=True)
class Order:
    id: str
    customer_id: str
    total_cents: int

    def validate(self) -> None:
        if self.total_cents < 0:
            raise ValueError(\"total_cents must be non-negative\")
        save(self)
'''
  },
  'cwd': os.getcwd()
}))
")

set +e
echo "$PAYLOAD" | python3 -m qse.gate.hook_runner 2>&1
EXIT=$?
set -e
p 1

if [ "$EXIT" = "2" ]; then
    printf "\n  ${R}${B}✗ ZABLOKOWANO (exit 2)${N}\n"
    printf "  ${D}Claude widzi naruszenie aksjomatu i poprawia kod.${N}\n"
fi
p 4

# ── Cykl ─────────────────────────────────────────────────────────────────
hr
printf "\n${B}  KROK 3/3 — AI agent zamyka cykl zależności${N}\n\n"
printf "  Scenariusz: agent dodaje wygodny import w odwrotnym kierunku\n"
printf "  domain.order → application.order_service → (powrót do domain)\n\n"
p 3

printf "${D}  ── Proponowana zmiana: ───────────────────────────────────────${N}\n"
printf "  ${R}+ from src.application.order_service import notify${N}\n"
printf "${D}  ──────────────────────────────────────────────────────────────${N}\n\n"
p 3

printf "${Y}  [PreToolUse hook] → skanowanie propozycji…${N}\n"
p 1.5

PAYLOAD2=$(python3 -c "
import json, os
print(json.dumps({
  'tool_name': 'Edit',
  'tool_input': {
    'file_path': os.path.abspath('src/domain/order.py'),
    'old_string': 'from dataclasses import dataclass',
    'new_string': 'from dataclasses import dataclass\nfrom src.application.order_service import notify'
  },
  'cwd': os.getcwd()
}))
")

set +e
echo "$PAYLOAD2" | python3 -m qse.gate.hook_runner 2>&1
EXIT2=$?
set -e
p 1

if [ "$EXIT2" = "2" ]; then
    printf "\n  ${R}${B}✗ ZABLOKOWANO (exit 2)${N}\n"
    printf "  ${D}Cykl wykryty. Aksjom acykliczności naruszony.${N}\n"
fi
p 4

# ── Dobry zapis ───────────────────────────────────────────────────────────
hr
printf "\n${B}  BONUS — Czysty zapis (brak naruszeń)${N}\n\n"
printf "${Y}  [PreToolUse hook] → skanowanie propozycji…${N}\n"
p 1.5

PAYLOAD3=$(python3 -c "
import json, os
content = open('src/domain/order.py').read()
print(json.dumps({
  'tool_name': 'Write',
  'tool_input': {
    'file_path': os.path.abspath('src/domain/order.py'),
    'content': content
  },
  'cwd': os.getcwd()
}))
")

set +e
OUT=$(echo "$PAYLOAD3" | python3 -m qse.gate.hook_runner 2>&1)
EXIT3=$?
set -e

if [ "$EXIT3" = "0" ] && [ -z "$OUT" ]; then
    printf "${G}${B}  ✓ PRZEPUSZCZONO — brak output, brak blokady${N}\n"
fi
p 4

# ── Podsumowanie ───────────────────────────────────────────────────────────
hr
printf "\n${B}  Podsumowanie${N}\n\n"
printf "  LAYER_VIOLATION (domain → infrastructure)   ${R}ZABLOKOWANO${N}\n"
printf "  CYCLE_NEW (domain ↔ application)            ${R}ZABLOKOWANO${N}\n"
printf "  Czysty zapis                                ${G}PRZEPUSZCZONO${N}\n\n"
printf "  ${D}Latencja:  ~350ms  |  Czytelność: aksjom + hint naprawy${N}\n"
printf "  ${D}Hook aktywny dla każdego Edit/Write w Claude Code${N}\n"
hr
p 3
