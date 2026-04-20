# Agent-Time Architectural Gate — Dokumentacja

Hook dla Claude Code który blokuje architektoniczne naruszenia **zanim** AI zapisze plik na dysk.

## Demo

Otwórz w przeglądarce (można pauzować i przewijać):
```
examples/sample-ai-drift-demo/demo-hook-player.html
```

Lub obejrzyj GIF:
```
examples/sample-ai-drift-demo/demo-hook-slow.gif
```

---

## Jak działa

```
Claude Code pisze plik
       ↓
PreToolUse hook odpalany PRZED zapisem
       ↓
qse.gate.hook_runner odczytuje proponowaną treść ze stdin JSON
       ↓
Kopiuje repo do temp dir, podmienia jeden plik na proponowany
       ↓
Uruchamia qse-gate (reguły: CYCLE_NEW, LAYER_VIOLATION, BOUNDARY_LEAK)
       ↓
Brak naruszeń → exit 0 → Claude zapisuje plik
Naruszenie    → exit 2 → Claude WIDZI aksjom + hint, może się poprawić
```

---

## Instalacja (nowy projekt)

### 1. Zainstaluj qse-pkg

```bash
pip install git+https://github.com/PiotrGry/qse-pkg.git
```

### 2. Stwórz konfigurację `qse-gate.toml` w katalogu projektu

```toml
[gate]
language = "python"

# Zdefiniuj warstwy architektoniczne
[layers]
domain         = ["src/domain/**",         "src.domain.*"]
application    = ["src/application/**",    "src.application.*"]
infrastructure = ["src/infrastructure/**", "src.infrastructure.*"]

# Scope skanowania — tylko twój kod, bez vendored libraries
[scan]
include = ["src/**/*.py", "tests/**/*.py"]
exclude = ["**/__pycache__/**", "**/target/**", "**/.venv/**"]

# Reguły
[rules.cycle_new]
enabled = true
mode    = "any"   # "delta" w CI żeby porównywać z base branch

[rules.layer_violation]
enabled = true
forbidden = [
    { from = "domain",      to = "infrastructure" },
    { from = "domain",      to = "application"    },
    { from = "application", to = "infrastructure" },
]

[rules.boundary_leak]
enabled = false   # włącz jeśli masz protected modules
```

### 3. Utwórz hook script `.claude/hooks/qse-gate-hook.sh`

```bash
mkdir -p .claude/hooks
cat > .claude/hooks/qse-gate-hook.sh << 'EOF'
#!/usr/bin/env bash
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$PROJECT_DIR" || exit 0
exec python3 -m qse.gate.hook_runner
EOF
chmod +x .claude/hooks/qse-gate-hook.sh
```

### 4. Zarejestruj hook w `.claude/settings.json`

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/qse-gate-hook.sh",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

Plik `.claude/settings.json` commituj do repo — hook jest aktywny dla wszystkich którzy używają Claude Code w tym projekcie.

### 5. Zweryfikuj działanie

```bash
# Test blokady — powinien wypisać naruszenie i wrócić exit 2
python3 -c "
import json, os, sys
payload = {
  'tool_name': 'Write',
  'tool_input': {
    'file_path': os.path.abspath('src/domain/example.py'),
    'content': 'from src.infrastructure.db import save\n'
  },
  'cwd': os.getcwd()
}
print(json.dumps(payload))
" | python3 -m qse.gate.hook_runner
echo "exit: $?"   # powinno być 2

# Test przepuszczenia — brak output, exit 0
python3 -c "
import json, os
payload = {
  'tool_name': 'Write',
  'tool_input': {
    'file_path': os.path.abspath('src/domain/example.py'),
    'content': 'from dataclasses import dataclass\n'
  },
  'cwd': os.getcwd()
}
print(json.dumps(payload))
" | python3 -m qse.gate.hook_runner
echo "exit: $?"   # powinno być 0
```

---

## Konfiguracja zaawansowana

### Protected modules (BOUNDARY_LEAK)

```toml
[rules.boundary_leak]
enabled = true
protected = [
    { module = "src.payments.core.*", allowed_callers = ["src.payments.api.*"] }
]
```

Tylko `src.payments.api.*` może importować `src.payments.core`. Każdy inny moduł → blokada.

### Scope skanowania

Hook skanuje cały repo przez temp overlay. Dla dużych projektów ogranicz scope:

```toml
[scan]
include = [
    "src/**/*.py",
    "lib/**/*.py",
]
exclude = [
    "**/vendor/**",
    "**/migrations/**",
    "**/__pycache__/**",
    "**/target/**",
    "**/node_modules/**",
]
```

Bez `[scan]` skaner przejdzie przez cały katalog włącznie z vendored libraries — latencja wzrośnie drastycznie (przykład: qse-pkg bez scope: 68s; z scope: 300ms).

### Tryb delta w CI (`mode = "delta"`)

W hoogu lokalnym `mode = "any"` flaguje wszystkie cykle. W CI ustaw `mode = "delta"` żeby blokować tylko **nowe** cykle (nieistniejące w base branch):

```toml
[rules.cycle_new]
enabled = true
mode    = "delta"
```

W CI uruchom z `--base-ref`:
```bash
qse-gate . --config qse-gate.toml --base-ref origin/main
```

---

## Jak Claude reaguje na blokadę

Po exit 2 Claude widzi stderr z hookiem:

```
qse-gate: blocked — this change would introduce a structural violation.

  [LAYER_VIOLATION] src.domain.order → src.infrastructure.db
    axiom: layering (MDL: high-level layer compressed independently of low-level)
    fix:   Define a port/interface in domain that infrastructure implements.
           Depend on the port, not the concrete.
```

Claude dostaje: **regułę**, **aksjom** (dlaczego to jest złe), **hint naprawy** (co zrobić).
W praktyce model zazwyczaj aplikuje hint bez dodatkowych promptów.

---

## Znane ograniczenia

| Ograniczenie | Status |
|---|---|
| Tylko Python | Java/Go w Sprint 0.5 |
| Symlinki w source tree | Hook loguje warning i przepuszcza (rzadki case) |
| Latencja cold: ~350ms | Cache base graph → <50ms warm (zaplanowane) |
| RCE jeśli hook importuje z untrusted checkout | Odroczone — wymaga sandbox |

---

## Struktura plików

```
.claude/
├── hooks/
│   └── qse-gate-hook.sh      ← shell wrapper (commituj)
└── settings.json             ← rejestracja hooku (commituj)

qse-gate.toml                 ← konfiguracja reguł (commituj)

qse/gate/
├── hook_runner.py            ← główna logika hooku
├── config.py                 ← ładowanie qse-gate.toml
├── rules.py                  ← CYCLE_NEW / LAYER_VIOLATION / BOUNDARY_LEAK
└── runner.py                 ← _build_graph (skaner grafu)
```

---

## Ponowne nagranie dema

```bash
cd examples/sample-ai-drift-demo

# Nagraj
TERM=xterm-256color asciinema rec demo-hook-slow.cast \
  --command ./demo-hook-slow.sh \
  --cols 90 --rows 36 \
  --quiet --overwrite

# Konwertuj do GIF (wymaga: wget https://github.com/asciinema/agg/releases)
agg demo-hook-slow.cast demo-hook-slow.gif --speed 1.0 --idle-time-limit 3

# Odpal interaktywny player w przeglądarce
xdg-open demo-hook-player.html   # Linux
open demo-hook-player.html        # macOS
```
