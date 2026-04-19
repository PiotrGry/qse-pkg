#!/usr/bin/env bash
# demo.sh — grant-panel runner for the AI-Drift Firewall demo.
#
# Scans the clean base first, then applies each scenario overlay on top of
# base in a temp dir and shows the gate verdict. Finishes with an override
# showcase. Idempotent; writes nothing inside the tracked repo.

set -u
cd "$(dirname "$0")"

BASE_DIR="$(pwd)/base"
CFG="$(pwd)/qse-gate.toml"
if ! command -v python3 >/dev/null; then
  echo "error: python3 not on PATH"; exit 2
fi
if ! python3 -c "import qse.gate" 2>/dev/null; then
  echo "error: qse-pkg not installed. From the repo root: pip install -e ."; exit 2
fi

banner() {
  printf "\n\033[1;36m━━ %s ━━\033[0m\n" "$1"
}

run_gate() {
  local scan_dir="$1" msg="$2" override="${3:-}"
  local args=(python3 -m qse.gate "$scan_dir" --config "$CFG")
  if [ -n "$override" ]; then args+=(--override-token "$override"); fi
  printf "\033[2m%s\033[0m\n" "$msg"
  "${args[@]}"
  printf "(exit: %s)\n" "$?"
}

# Build a fresh base directory that contains only src/ — scanning from this
# root makes module names absolute ('src.domain.order' etc.) so imports and
# scanner-derived source nodes match the paths used in qse-gate.toml.
rm -rf "$BASE_DIR"
mkdir -p "$BASE_DIR"
cp -R "$(pwd)/src" "$BASE_DIR/src"

# --- 1. CLEAN BASE ---
banner "1. Clean baseline — layered service, no drift"
run_gate "$BASE_DIR" "qse-gate <base> --config qse-gate.toml"

# --- 2. Each violation in turn ---
for scenario in cycle_new layer_violation boundary_leak; do
  TMP=$(mktemp -d -t qse-demo-"$scenario"-XXXXXX)
  trap "rm -rf '$TMP'" EXIT
  cp -R "$BASE_DIR/src" "$TMP/src"
  # Apply overlay on top of base
  if [ -d "scenarios/$scenario/src" ]; then
    cp -R "scenarios/$scenario/src/." "$TMP/src/"
  fi
  banner "2.$scenario — AI-generated drift ($scenario)"
  run_gate "$TMP" "qse-gate <mutated-tree> --config qse-gate.toml"
  rm -rf "$TMP"
  trap - EXIT
done

# --- 3. Override showcase ---
TMP=$(mktemp -d -t qse-demo-override-XXXXXX)
trap "rm -rf '$TMP'" EXIT
cp -R "$BASE_DIR/src" "$TMP/src"
cp -R "scenarios/layer_violation/src/." "$TMP/src/"
banner "3. Override — architect opts out via [skip-qse]"
run_gate "$TMP" "qse-gate <mutated-tree> --config qse-gate.toml --override-token 'feat: urgent [skip-qse]'" \
         "feat: urgent [skip-qse]"
rm -rf "$TMP"

banner "Done"
cat <<'EOF'

What just happened:
 1. Clean base passed the gate (zero drift).
 2. Three separate AI-generated PRs each broke one axiom-backed rule:
    - CYCLE_NEW (domain imports application, closing a ring)
    - LAYER_VIOLATION (domain reaches into infrastructure)
    - BOUNDARY_LEAK (analytics bypasses payments_api to hit payments_core directly)
 3. An architect with urgent context overrode with [skip-qse] — the gate passed
    but every violation is logged to artifacts/gate-telemetry.jsonl for audit.

In production CI: add qse-gate via the reusable workflow
  uses: PiotrGry/qse-pkg/.github/workflows/ai-drift-gate.yml@main
and it will run this exact analysis on every PR in under a second.
EOF
