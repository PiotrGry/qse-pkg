#!/bin/bash
# =============================================================================
# run_total_benchmark.sh — QSE Benchmark Totalny
#
# Daje pełny live output: każde repo, każda metryka, postęp, korelacje.
#
# Użycie:
#   chmod +x scripts/run_total_benchmark.sh
#   ./scripts/run_total_benchmark.sh
#
# Opcje środowiskowe:
#   LANG_FILTER=Python   # tylko Python (domyślnie: wszystkie)
#   LIMIT=100            # max repo (domyślnie: wszystkie)
#   ITER=3               # numer iteracji (domyślnie: 3)
#   REPOS_DIR=~/bench    # katalog do klonowania (domyślnie: ~/qse_total_bench)
#   NO_LEAD_TIME=1       # pomiń GitHub Issues (szybciej)
#   NO_CLONE=0           # pomiń klonowanie już istniejących (domyślnie: 0)
#
# Przykład szybkiego testu:
#   LANG_FILTER=Python LIMIT=20 ./scripts/run_total_benchmark.sh
# =============================================================================

set -e

# ── Kolory ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

ok()   { echo -e "${GREEN}  ✓${NC} $*"; }
fail() { echo -e "${RED}  ✗${NC} $*"; }
info() { echo -e "${CYAN}  →${NC} $*"; }
hdr()  { echo -e "\n${BOLD}${BLUE}$*${NC}"; }

# ── Parametry ────────────────────────────────────────────────────────────────
ITER="${ITER:-3}"
REPOS_DIR="${REPOS_DIR:-${HOME}/qse_total_bench}"
LANG_FILTER="${LANG_FILTER:-}"
LIMIT="${LIMIT:-}"
NO_LEAD_TIME="${NO_LEAD_TIME:-0}"
QSE_DIR="${HOME}/qse-pkg"
BRANCH="perplexity"
LOG_FILE="/tmp/qse_benchmark_iter${ITER}.log"

# ── Banner ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║         QSE Benchmark Totalny — Iteracja ${ITER}             ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Repos dir : ${CYAN}${REPOS_DIR}${NC}"
echo -e "  QSE dir   : ${CYAN}${QSE_DIR}${NC}"
echo -e "  Branch    : ${CYAN}${BRANCH}${NC}"
echo -e "  Lang      : ${CYAN}${LANG_FILTER:-wszystkie}${NC}"
echo -e "  Limit     : ${CYAN}${LIMIT:-brak}${NC}"
echo -e "  Lead time : ${CYAN}$([ "$NO_LEAD_TIME" = "1" ] && echo 'wyłączony' || echo 'włączony (GitHub Issues)')${NC}"
echo -e "  Log       : ${CYAN}${LOG_FILE}${NC}"
echo ""

START_TIME=$(date +%s)

# ── 1. Klonuj / zaktualizuj qse-pkg ─────────────────────────────────────────
hdr "[1/5] Pobieranie qse-pkg (branch: ${BRANCH})"

if [ ! -d "$QSE_DIR/.git" ]; then
    info "Klonuję qse-pkg..."
    git clone --branch "$BRANCH" \
        "https://github.com/PiotrGry/qse-pkg.git" "$QSE_DIR" \
        2>&1 | tee -a "$LOG_FILE" | grep -E "Cloning|done\."
    ok "Sklonowano do $QSE_DIR"
else
    info "Aktualizuję istniejące repo..."
    cd "$QSE_DIR"
    git fetch origin 2>/dev/null
    git checkout "$BRANCH" 2>/dev/null
    BEHIND=$(git rev-list HEAD..origin/"$BRANCH" --count 2>/dev/null || echo 0)
    if [ "$BEHIND" -gt 0 ]; then
        git pull origin "$BRANCH" 2>&1 | grep -E "Updating|Fast-forward|Already"
        ok "Zaktualizowano ($BEHIND nowych commitów)"
    else
        ok "Już aktualne"
    fi
fi

cd "$QSE_DIR"

# ── 2. Instalacja zależności ─────────────────────────────────────────────────
hdr "[2/5] Instalacja zależności"

info "pip install qse-pkg..."
pip install -e . -q 2>&1 | tail -1 && ok "qse-pkg zainstalowany"

info "pip install networkx scipy numpy..."
pip install networkx scipy numpy -q 2>&1 | tail -1 && ok "Biblioteki naukowe OK"

# Sprawdź czy qse agq działa
if python3 -m qse --help &>/dev/null; then
    ok "qse CLI dostępny"
else
    fail "qse CLI niedostępny — sprawdź instalację"
    exit 1
fi

# Opcjonalnie: skaner Rust
if command -v maturin &>/dev/null; then
    info "Buduję skaner Rust (maturin)..."
    maturin develop -q 2>&1 | tail -1 \
        && ok "Skaner Rust zbudowany (7-46x szybszy)" \
        || info "Rust build failed — używam Python fallback"
else
    info "maturin nie znaleziony — Python scanner (wolniejszy, ale działa)"
fi

# ── 3. Przygotowanie ─────────────────────────────────────────────────────────
hdr "[3/5] Przygotowanie"

mkdir -p "$REPOS_DIR"
ok "Katalog benchmarku: $REPOS_DIR"

# Policz repo na liście
REPOS_FILE="scripts/repos_experiment_total.json"
if [ ! -f "$REPOS_FILE" ]; then
    fail "Brak pliku $REPOS_FILE"
    exit 1
fi

TOTAL=$(python3 -c "
import json
repos = json.load(open('$REPOS_FILE'))
if '$LANG_FILTER':
    repos = [r for r in repos if r.get('lang','Python') == '$LANG_FILTER']
if '$LIMIT':
    repos = repos[:int('$LIMIT')]
print(len(repos))
")

info "Lista repo: $REPOS_FILE"
info "Do przeskanowania: ${BOLD}${TOTAL} repo${NC}"

echo ""
echo -e "  ${YELLOW}Szacowany czas:${NC}"
echo -e "    Klonowanie:     ~${YELLOW}$(( TOTAL * 15 / 60 ))min${NC} (zależy od internetu)"
echo -e "    Skanowanie AGQ: ~${YELLOW}$(( TOTAL * 2 / 60 ))min${NC}"
echo -e "    GitHub Issues:  ~${YELLOW}$(( TOTAL * 5 / 60 ))min${NC}"
echo -e "    Łącznie:        ~${YELLOW}$(( TOTAL * 22 / 60 ))min${NC}"
echo ""
echo -e "  ${CYAN}Postęp będzie wyświetlany na bieżąco poniżej...${NC}"
echo ""

# ── 4. Benchmark ─────────────────────────────────────────────────────────────
hdr "[4/5] Uruchamiam experiment_total.py"
echo ""

# Buduj argumenty
ARGS="--repos $REPOS_FILE --repos-dir $REPOS_DIR --output-dir artifacts/experiment_total --iter $ITER"
[ -n "$LANG_FILTER"  ] && ARGS="$ARGS --lang $LANG_FILTER"
[ -n "$LIMIT"        ] && ARGS="$ARGS --limit $LIMIT"
[ "$NO_LEAD_TIME" = "1" ] && ARGS="$ARGS --no-lead-time"

echo -e "  ${CYAN}Komenda:${NC} python3 scripts/experiment_total.py $ARGS"
echo ""
echo -e "  ${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Uruchom z live outputem (tee do pliku + ekran)
python3 scripts/experiment_total.py $ARGS 2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}
echo -e "  ${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ "$EXIT_CODE" -ne 0 ]; then
    fail "Benchmark zakończył się błędem (exit code: $EXIT_CODE)"
    info "Sprawdź log: $LOG_FILE"
    exit 1
fi

# ── Sprawdź wyniki ────────────────────────────────────────────────────────────
RESULTS_JSON="artifacts/experiment_total/iter_${ITER}/results.json"
if [ ! -f "$RESULTS_JSON" ]; then
    fail "Brak pliku wyników: $RESULTS_JSON"
    exit 1
fi

# Parsuj statystyki
python3 << STATS
import json
d = json.load(open("$RESULTS_JSON"))
n = d.get("repos_ok", 0)
f = d.get("repos_failed", 0)
agq = d.get("agq_mean")
nm = d.get("repos_with_new_metrics", 0)
bl = d.get("repos_with_bug_lt", 0)
corrs = d.get("correlations", [])
sig = [c for c in corrs if c.get("sig")]
new_sig = [c for c in sig if "[NEW]" in c.get("predictor","")]

print(f"\n  Przeskanowanych:      {n} repo")
print(f"  Błędów:               {f} repo")
print(f"  Z nowymi metrykami:   {nm} repo")
print(f"  Z bug lead time:      {bl} repo")
print(f"  AGQ mean:             {agq}")
print(f"  Istotnych korelacji:  {len(sig)}")
print(f"  Nowych metryk sig:    {len(new_sig)}")
if new_sig:
    print(f"\n  TOP nowe metryki (p<0.05):")
    for c in new_sig[:5]:
        print(f"    {c['predictor'].strip():28} → {c['target']:18} r={c['r_s']:+.4f} p={c['p']:.4f}")
STATS

# ── 5. Commit i push ──────────────────────────────────────────────────────────
hdr "[5/5] Wrzucam wyniki na GitHub"

REPOS_OK=$(python3 -c "import json; print(json.load(open('$RESULTS_JSON')).get('repos_ok',0))")

info "git add artifacts/experiment_total/iter_${ITER}/"
git add "artifacts/experiment_total/iter_${ITER}/" 2>/dev/null || true

# Sprawdź czy jest coś do commitowania
if git diff --cached --quiet 2>/dev/null; then
    info "Nic nowego do commitowania (wyniki identyczne)"
else
    COMMIT_MSG="experiment/total: iter ${ITER} results — ${REPOS_OK} repos

Langs: ${LANG_FILTER:-all}
Repos OK: ${REPOS_OK}
Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)

Metryki: AGQ + GraphDensity + SCCEntropy + HubRatio + ProcessRisk
Ground truth: churn_gini, hotspot_ratio, bug_lead_time

Co-authored-by: Perplexity Computer <research@perplexity.ai>"

    git commit -m "$COMMIT_MSG" 2>&1 | grep -E "^\[|files? changed"
    ok "Commit utworzony"

    info "git push origin $BRANCH..."
    git push origin "$BRANCH" 2>&1 | grep -E "->|Everything"
    ok "Wyniki na GitHub!"
fi

# ── Podsumowanie ─────────────────────────────────────────────────────────────
END_TIME=$(date +%s)
ELAPSED=$(( END_TIME - START_TIME ))
MINS=$(( ELAPSED / 60 ))
SECS=$(( ELAPSED % 60 ))

echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║                    BENCHMARK GOTOWY!                    ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Czas:${NC}     ${MINS}min ${SECS}s"
echo -e "  ${BOLD}Repos:${NC}    ${REPOS_OK} przeskanowanych"
echo -e "  ${BOLD}Wyniki:${NC}   artifacts/experiment_total/iter_${ITER}/"
echo -e "  ${BOLD}GitHub:${NC}   https://github.com/PiotrGry/qse-pkg/tree/${BRANCH}/artifacts/experiment_total/iter_${ITER}"
echo -e "  ${BOLD}Log:${NC}      ${LOG_FILE}"
echo ""
echo -e "  ${CYAN}Następny krok: wróć do Perplexity Computer z wynikami${NC}"
echo -e "  ${CYAN}lub uruchom iter $((ITER+1)):${NC}"
echo -e "  ${CYAN}  ITER=$((ITER+1)) ./scripts/run_total_benchmark.sh${NC}"
echo ""
