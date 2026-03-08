#!/usr/bin/env python3
"""Multi-language AGQ benchmark using Rust qse-core scanner.

Runs AGQ on Java and Go OSS repositories, computes metrics,
correlates with code churn ground truth.

Usage:
    python3 scripts/agq_multilang_benchmark.py \
        --repos-file scripts/repos_java30_benchmark.json \
        --repos-dir /tmp/qse_java_bench \
        --output-json artifacts/benchmark/agq_java30.json \
        --output-md artifacts/benchmark/agq_java30.md
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

try:
    from _qse_core import scan_and_compute_agq
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    print("[warn] _qse_core not available — build with maturin first")


_TEST_RE = re.compile(r"(^|/)tests?/|test_.*\.py$|_test\.py$|Test\.java$|Tests\.java$")


def _run(cmd: Sequence[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), cwd=str(cwd) if cwd else None,
                          capture_output=True, text=True, timeout=300)


def _clone(name: str, url: str, repos_dir: Path, no_clone: bool) -> Optional[Path]:
    dest = repos_dir / name
    if dest.exists():
        return dest
    if no_clone:
        return None
    print(f"  cloning {name}...", end="", flush=True)
    proc = subprocess.run(
        ["git", "clone", "--depth", "1", "--single-branch", url, str(dest)],
        capture_output=True, timeout=600
    )
    if proc.returncode != 0:
        print(f" FAILED")
        return None
    print(f" ok")
    return dest


def _churn(repo_path: Path, since: str = "2 years ago") -> Optional[Dict]:
    proc = _run(["git", "-C", str(repo_path), "log", "--since", since,
                 "--name-only", "--pretty=format:--COMMIT--"])
    if proc.returncode != 0:
        return None
    counts: Dict[str, int] = {}
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or line == "--COMMIT--":
            continue
        if _TEST_RE.search(line):
            continue
        counts[line] = counts.get(line, 0) + 1
    if not counts:
        return None
    vals = list(counts.values())
    mean_c = sum(vals) / len(vals)
    hotspot = sum(1 for v in vals if v > mean_c * 2) / len(vals)
    sorted_v = sorted(vals)
    n = len(sorted_v)
    cum = sum((i + 1) * v for i, v in enumerate(sorted_v))
    gini = (2 * cum) / (n * sum(sorted_v)) - (n + 1) / n if sum(sorted_v) > 0 else 0.0
    return {"hotspot_ratio": round(hotspot, 4), "churn_gini": round(gini, 4),
            "n_files": n, "mean_churn": round(mean_c, 3)}


def _spearman(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    def ranks(v):
        idx = sorted(enumerate(v), key=lambda x: x[1])
        r = [0.0] * len(v)
        i = 0
        while i < len(idx):
            j = i
            while j + 1 < len(idx) and idx[j+1][1] == idx[i][1]: j += 1
            rv = (i + j + 2) / 2.0
            for k in range(i, j+1): r[idx[k][0]] = rv
            i = j + 1
        return r
    def pearson(a, b):
        n = len(a); ma, mb = sum(a)/n, sum(b)/n
        num = sum((x-ma)*(y-mb) for x,y in zip(a,b))
        da = math.sqrt(sum((x-ma)**2 for x in a))
        db = math.sqrt(sum((y-mb)**2 for y in b))
        return num/(da*db) if da*db > 0 else 0
    return pearson(ranks(xs), ranks(ys))


def _p_value(r: Optional[float], n: int) -> Optional[float]:
    if r is None or n < 3: return None
    r2 = r * r
    if r2 >= 1.0: return 0.0
    t = abs(r) * math.sqrt((n-2)/(1-r2))
    df = n - 2
    x = df / (df + t*t)
    def betai(a, b, x):
        if x <= 0: return 0.0
        if x >= 1: return 1.0
        lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a+b)
        fpmin = 1e-30
        c, d = 1.0, 1.0 - (a+b)*x/(a+1)
        if abs(d) < fpmin: d = fpmin
        d = 1.0/d; h = d
        for m in range(1, 101):
            m2 = 2*m
            aa = m*(b-m)*x/((a-1+m2)*(a+m2))
            d = 1.0+aa*d
            if abs(d) < fpmin: d = fpmin
            c = 1.0+aa/c
            if abs(c) < fpmin: c = fpmin
            d = 1.0/d; h *= d*c
            aa = -(a+m)*(a+b+m)*x/((a+m2)*(a+1+m2))
            d = 1.0+aa*d
            if abs(d) < fpmin: d = fpmin
            c = 1.0+aa/c
            if abs(c) < fpmin: c = fpmin
            d = 1.0/d; delta = d*c; h *= delta
            if abs(delta-1.0) < 3e-7: break
        return math.exp(math.log(x)*a + math.log(1-x)*b - lbeta)*h/a
    return betai(0.5*df, 0.5, x)


def _fmt(v, d=4):
    return f"{v:.{d}f}" if v is not None else "n/a"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos-file", required=True)
    parser.add_argument("--repos-dir", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--no-clone", action="store_true")
    parser.add_argument("--since", default="2 years ago")
    args = parser.parse_args()

    if not RUST_AVAILABLE:
        raise SystemExit("Build qse-py first: python3 -m maturin develop --release -m qse-py/Cargo.toml")

    repos = json.loads(Path(args.repos_file).read_text())
    repos_dir = Path(args.repos_dir)
    repos_dir.mkdir(parents=True, exist_ok=True)

    print(f"Benchmarking {len(repos)} repos in {repos_dir}\n")

    results = []
    for repo in repos:
        name, url = repo["name"], repo["url"]
        print(f"[{name}] ", end="", flush=True)

        repo_path = _clone(name, url, repos_dir, args.no_clone)
        if repo_path is None:
            print("SKIP")
            results.append({"name": name, "error": "missing"})
            continue

        try:
            import time
            t0 = time.perf_counter()
            agq = scan_and_compute_agq(str(repo_path))
            ms = (time.perf_counter() - t0) * 1000

            churn = _churn(repo_path, args.since)

            print(f"lang={agq['language']} agq={agq['agq_score']:.4f} "
                  f"n={agq['nodes']} {ms:.0f}ms"
                  + (f" hotspot={churn['hotspot_ratio']:.2f}" if churn else ""))

            # Compute enhanced metrics
            try:
                import sys as _sys; _sys.path.insert(0, str(Path(__file__).parents[1]))
                from qse.agq_enhanced import compute_agq_enhanced
                enh = compute_agq_enhanced(
                    agq["agq_score"], agq["modularity"], agq["acyclicity"],
                    agq["stability"], agq["cohesion"],
                    agq["nodes"], agq["language"]
                ).to_dict()
            except Exception:
                enh = None

            results.append({"name": name, "url": url, "agq": agq,
                            "churn": churn, "enhanced": enh,
                            "runtime_ms": round(ms, 1)})
        except Exception as exc:
            print(f"ERROR: {exc}")
            results.append({"name": name, "error": str(exc)})

    # Stats
    ok = [r for r in results if "agq" in r and r["agq"]["nodes"] > 0]
    agq_vals = [r["agq"]["agq_score"] for r in ok]
    churn_ok = [r for r in ok if r.get("churn") and r["churn"].get("hotspot_ratio") is not None]

    correlations = {}
    if len(churn_ok) >= 3:
        agq_c = [r["agq"]["agq_score"] for r in churn_ok]
        for key in ["hotspot_ratio", "churn_gini"]:
            target = [r["churn"][key] for r in churn_ok]
            rs = _spearman(agq_c, target)
            correlations[f"spearman_agq_vs_{key}"] = {
                "r_s": round(rs, 4) if rs else None,
                "p": round(_p_value(rs, len(churn_ok)), 4) if rs else None,
                "n": len(churn_ok)
            }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repos_file": args.repos_file,
        "repos_total": len(repos),
        "repos_ok": len(ok),
        "agq_mean": round(statistics.mean(agq_vals), 4) if agq_vals else None,
        "agq_spread": round(max(agq_vals) - min(agq_vals), 4) if agq_vals else None,
        "agq_std": round(statistics.pstdev(agq_vals), 4) if agq_vals else None,
        "correlations": correlations,
        "results": results,
    }

    Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_json).write_text(json.dumps(report, indent=2))

    # Markdown
    langs = set(r["agq"]["language"] for r in ok)
    lines = [f"# AGQ Multi-Language Benchmark", "",
             f"- generated: `{report['generated_at']}`",
             f"- languages: {', '.join(sorted(langs))}",
             f"- repos_ok: `{len(ok)}/{len(repos)}`",
             f"- agq_mean: `{_fmt(report['agq_mean'])}`  spread: `{_fmt(report['agq_spread'])}`",
             "", "## Correlations", ""]
    for k, c in correlations.items():
        sig = " **p<0.05**" if (c["p"] or 1) < 0.05 else ""
        lines.append(f"- {k}: r_s={_fmt(c['r_s'])} p={_fmt(c['p'])} n={c['n']}{sig}")
    lines += ["", "## Results", "",
              "| Repo | Lang | AGQ | Nodes | Mod | Acy | Stab | Coh | Hotspot | ms |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in sorted(ok, key=lambda x: x["agq"]["agq_score"], reverse=True):
        a = r["agq"]; c = r.get("churn") or {}
        lines.append(f"| {r['name']} | {a['language']} | {_fmt(a['agq_score'])} | "
                     f"{a['nodes']} | {_fmt(a['modularity'])} | {_fmt(a['acyclicity'])} | "
                     f"{_fmt(a['stability'])} | {_fmt(a['cohesion'])} | "
                     f"{_fmt(c.get('hotspot_ratio'))} | {r['runtime_ms']:.0f}ms |")
    lines.append("")
    Path(args.output_md).write_text("\n".join(lines) + "\n")

    print(f"\n=== Summary ===")
    print(f"Repos OK: {len(ok)}/{len(repos)}")
    if agq_vals:
        print(f"AGQ: mean={_fmt(statistics.mean(agq_vals))} spread={_fmt(max(agq_vals)-min(agq_vals))}")
    for k, c in correlations.items():
        sig = " *" if (c["p"] or 1) < 0.05 else ""
        print(f"  {k}: r_s={_fmt(c['r_s'])} p={_fmt(c['p'])}{sig}")
    print(f"\nJSON: {args.output_json}\nMD:   {args.output_md}")


if __name__ == "__main__":
    main()
