#!/usr/bin/env bash
# Reproduce QSE AGQ benchmark from scratch.
#
# Usage:
#   ./scripts/reproduce_benchmark.sh              # all 3 languages
#   ./scripts/reproduce_benchmark.sh python        # Python-80 only
#   ./scripts/reproduce_benchmark.sh java go       # Java + Go
#
# Prerequisites:
#   - git, python3 >= 3.10
#   - Rust toolchain + maturin (for Java/Go scanner)
#   - pip install -e .  (QSE package)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CLONE_DIR="${QSE_CLONE_DIR:-/tmp/qse-benchmark-repos}"
OUTPUT_DIR="$PROJECT_DIR/artifacts/benchmark"

LANGS="${@:-python java go}"

clone_repos() {
    local json_file="$1"
    local lang="$2"
    local dest="$CLONE_DIR/$lang"
    mkdir -p "$dest"

    echo "==> Cloning $lang repos to $dest"
    python3 -c "
import json, subprocess, sys, os
with open('$json_file') as f:
    repos = json.load(f)
dest = '$dest'
ok, fail = 0, 0
for r in repos:
    name = r['name']
    target = os.path.join(dest, name)
    if os.path.isdir(target):
        ok += 1
        continue
    url = r['url']
    commit = r.get('commit')
    if commit:
        # Clone at pinned commit
        ret = subprocess.run(
            ['git', 'clone', '--single-branch', url, target],
            capture_output=True, timeout=120)
        if ret.returncode == 0 and commit:
            subprocess.run(['git', '-C', target, 'checkout', commit],
                           capture_output=True, timeout=30)
        if ret.returncode == 0:
            ok += 1
            print(f'  {name}: {commit[:12] if commit else \"HEAD\"}')
        else:
            fail += 1
            print(f'  {name}: CLONE FAILED')
    else:
        ret = subprocess.run(
            ['git', 'clone', '--depth', '1', url, target],
            capture_output=True, timeout=120)
        if ret.returncode == 0:
            ok += 1
            print(f'  {name}: HEAD (no pinned commit)')
        else:
            fail += 1
            print(f'  {name}: CLONE FAILED')
print(f'  Cloned: {ok}, Failed: {fail}')
"
}

run_benchmark() {
    local lang="$1"
    echo "==> Running AGQ benchmark: $lang"

    case "$lang" in
        python)
            python3 "$SCRIPT_DIR/agq_multilang_benchmark.py" \
                --repos-file "$SCRIPT_DIR/repos_oss80_benchmark.json" \
                --repos-dir "$CLONE_DIR/python" \
                --output-json "$OUTPUT_DIR/reproduced_python80.json" \
                --output-md "$OUTPUT_DIR/reproduced_python80.md"
            ;;
        java)
            python3 "$SCRIPT_DIR/agq_multilang_benchmark.py" \
                --repos-file "$SCRIPT_DIR/repos_java80_benchmark.json" \
                --repos-dir "$CLONE_DIR/java" \
                --output-json "$OUTPUT_DIR/reproduced_java80.json" \
                --output-md "$OUTPUT_DIR/reproduced_java80.md"
            ;;
        go)
            python3 "$SCRIPT_DIR/agq_multilang_benchmark.py" \
                --repos-file "$SCRIPT_DIR/repos_go80_benchmark.json" \
                --repos-dir "$CLONE_DIR/go" \
                --output-json "$OUTPUT_DIR/reproduced_go80.json" \
                --output-md "$OUTPUT_DIR/reproduced_go80.md"
            ;;
    esac
}

compare_results() {
    local lang="$1"
    local ref="$OUTPUT_DIR/agq_enhanced_${lang}80.json"
    local new="$OUTPUT_DIR/reproduced_${lang}80.json"

    if [ ! -f "$new" ]; then
        echo "  SKIP: $new not found"
        return
    fi
    if [ ! -f "$ref" ]; then
        echo "  SKIP: $ref (reference) not found"
        return
    fi

    echo "==> Comparing $lang results"
    python3 -c "
import json, sys

with open('$ref') as f:
    ref = json.load(f)
with open('$new') as f:
    new = json.load(f)

ref_by_name = {r['name']: r for r in ref['results']}
new_by_name = {r['name']: r for r in new['results']}

diffs = []
for name in ref_by_name:
    if name not in new_by_name:
        diffs.append(f'  MISSING: {name}')
        continue
    r_agq = ref_by_name[name].get('agq', {}).get('agq_score')
    n_agq = new_by_name[name].get('agq', {}).get('agq_score')
    if r_agq is not None and n_agq is not None:
        d = abs(r_agq - n_agq)
        if d > 0.001:
            diffs.append(f'  DIFF {name}: ref={r_agq:.4f} new={n_agq:.4f} delta={d:.4f}')

if diffs:
    print(f'  {len(diffs)} differences found:')
    for d in diffs[:10]:
        print(d)
else:
    print(f'  MATCH: all {len(ref_by_name)} repos within ±0.001')
"
}

# Main
echo "QSE Benchmark Reproduction"
echo "Clone dir: $CLONE_DIR"
echo "Languages: $LANGS"
echo ""

for lang in $LANGS; do
    case "$lang" in
        python) clone_repos "$SCRIPT_DIR/repos_oss80_benchmark.json" python ;;
        java)   clone_repos "$SCRIPT_DIR/repos_java80_benchmark.json" java ;;
        go)     clone_repos "$SCRIPT_DIR/repos_go80_benchmark.json" go ;;
    esac
done

for lang in $LANGS; do
    run_benchmark "$lang"
done

echo ""
echo "=== Comparison with reference ==="
for lang in $LANGS; do
    compare_results "$lang"
done

echo ""
echo "Done. Results in $OUTPUT_DIR/reproduced_*.json"
