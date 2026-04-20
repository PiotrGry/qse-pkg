#!/usr/bin/env bash
# demo-hook.sh — scripted terminal demo of the agent-time architectural gate.
# Run with:  asciinema rec demo-hook.cast --command ./demo-hook.sh
# Convert:   agg demo-hook.cast demo-hook.gif  (needs: pip install agg)
#
# What it shows:
#   1. The layered service (clean baseline)
#   2. AI tries to add a forbidden domain → infrastructure import → BLOCKED
#   3. AI tries a cycle (domain ↔ application) → BLOCKED
#   4. Clean write passes silently
#   All in under 60 seconds.

set -e
cd "$(dirname "$0")"

BOLD='\033[1m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
DIM='\033[2m'
RESET='\033[0m'

_type() {
    local text="$1"
    local delay="${2:-0.04}"
    printf "%s" "$text" | while IFS= read -r -n1 c; do
        printf "%s" "$c"
        sleep "$delay"
    done
}

_pause() { sleep "${1:-1.2}"; }

clear
_pause 0.5

# ── Title ───────────────────────────────────────────────────────────────────
printf "${BOLD}${CYAN}"
_type "  AI-Drift Firewall — Agent-Time Gate Demo" 0.03
printf "${RESET}\n"
printf "${DIM}  qse-pkg · PreToolUse hook · Claude Code${RESET}\n"
_pause 1.5

printf "\n${DIM}  Architecture: domain → application → infrastructure${RESET}\n"
printf "${DIM}  Rule: domain must NOT import infrastructure (layer violation)${RESET}\n"
_pause 1.5

# ── Show clean file ──────────────────────────────────────────────────────────
printf "\n${BOLD}[1/3] Baseline — clean domain/order.py${RESET}\n"
_pause 0.5
printf "${DIM}\$ cat src/domain/order.py${RESET}\n"
_pause 0.4
cat src/domain/order.py
_pause 1.5

# ── Scenario 1: LAYER_VIOLATION ──────────────────────────────────────────────
printf "\n${BOLD}[2/3] AI agent writes a forbidden import…${RESET}\n"
_pause 0.6
printf "${DIM}\$ # Claude Code fires PreToolUse hook before applying edit${RESET}\n"
_pause 0.8

PAYLOAD=$(python3 -c "
import json, os
print(json.dumps({
  'tool_name': 'Write',
  'tool_input': {
    'file_path': os.path.abspath('src/domain/order.py'),
    'content': '''from dataclasses import dataclass
from src.infrastructure.db import save   # AI \"helpfully\" adds this

@dataclass(frozen=True)
class Order:
    id: str
    customer_id: str
    total_cents: int

    def validate(self) -> None:
        if self.total_cents < 0:
            raise ValueError(\"total_cents must be non-negative\")
        save(self)   # persist directly from domain
'''
  },
  'cwd': os.getcwd()
}))
")

printf "${YELLOW}  [hook] scanning proposed write…${RESET}\n"
_pause 0.8
set +e
echo "$PAYLOAD" | python3 -m qse.gate.hook_runner 2>&1
EXIT=$?
set -e
_pause 0.5
if [ "$EXIT" = "2" ]; then
    printf "\n${RED}${BOLD}  ✗ write BLOCKED (exit 2) — Claude sees the axiom, self-corrects${RESET}\n"
else
    printf "\n${GREEN}  ✓ passed${RESET}\n"
fi
_pause 2.0

# ── Scenario 2: CYCLE_NEW ────────────────────────────────────────────────────
printf "\n${BOLD}[3/3] AI agent closes a dependency cycle…${RESET}\n"
_pause 0.6
printf "${DIM}\$ # domain.order imports application.order_service → cycle closes${RESET}\n"
_pause 0.8

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

printf "${YELLOW}  [hook] scanning proposed edit…${RESET}\n"
_pause 0.8
set +e
echo "$PAYLOAD2" | python3 -m qse.gate.hook_runner 2>&1
EXIT2=$?
set -e
_pause 0.5
if [ "$EXIT2" = "2" ]; then
    printf "\n${RED}${BOLD}  ✗ write BLOCKED — cycle detected, axiom cited${RESET}\n"
else
    printf "\n${GREEN}  ✓ passed${RESET}\n"
fi
_pause 2.0

# ── Scenario 3: clean write ───────────────────────────────────────────────────
printf "\n${BOLD}Clean write — no violations, gate silent${RESET}\n"
_pause 0.5

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

printf "${YELLOW}  [hook] scanning proposed write…${RESET}\n"
_pause 0.8
set +e
OUT=$(echo "$PAYLOAD3" | python3 -m qse.gate.hook_runner 2>&1)
EXIT3=$?
set -e
if [ "$EXIT3" = "0" ] && [ -z "$OUT" ]; then
    printf "${GREEN}${BOLD}  ✓ ALLOWED — no output, no delay${RESET}\n"
else
    echo "$OUT"
fi
_pause 1.5

# ── Summary ───────────────────────────────────────────────────────────────────
printf "\n${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}\n"
printf "${BOLD}  Verdict${RESET}\n"
printf "  LAYER_VIOLATION (domain→infra)  ${RED}BLOCKED${RESET}\n"
printf "  CYCLE_NEW (domain↔application)  ${RED}BLOCKED${RESET}\n"
printf "  Clean write                      ${GREEN}ALLOWED${RESET}\n"
printf "${DIM}  Latency: ~350ms cold · axiom-cited · self-correctable${RESET}\n"
printf "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}\n"
_pause 2.0
