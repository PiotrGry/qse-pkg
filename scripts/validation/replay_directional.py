"""Directional replay with ablation.

For each pair (parent_sha, sha):
  - gate(parent → sha)         FORWARD: real chronological direction
  - gate(sha → parent)         REVERSE: undoing the change

For each direction record:
  - passed (gate result)
  - rules fired
  - delta_agq (after - before)
  - delta_stability (after - before)

This lets us compare:
  - archfix reverse FAIL rate vs control reverse FAIL rate
  - whether ΔAGQ < 0 alone separates as well as gate
  - whether ΔStability < 0 alone separates as well as gate
"""
from __future__ import annotations

import argparse
import io
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from qse.gate.gate_check import gate_check
from qse.graph_metrics import compute_agq, compute_lcom4
from qse.scanner import scan_repo, DEFAULT_EXCLUDES


def archive(repo: str, sha: str, dest: str) -> None:
    r = subprocess.run(["git", "archive", sha, "--format=tar"],
                       cwd=repo, capture_output=True, check=True)
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as t:
        t.extractall(dest)


def replay_pair(pair: dict, repos_dir: str) -> dict:
    repo = str(Path(repos_dir) / pair["repo"])
    parent = pair["parent_sha"]
    sha = pair["sha"]

    a = tempfile.mkdtemp(prefix="qse-p3-a-")
    b = tempfile.mkdtemp(prefix="qse-p3-b-")
    try:
        archive(repo, parent, a)
        archive(repo, sha, b)
        an_a = scan_repo(a, exclude=DEFAULT_EXCLUDES)
        an_b = scan_repo(b, exclude=DEFAULT_EXCLUDES)
        G_a, G_b = an_a.graph, an_b.graph

        lcom_a = [compute_lcom4(c.method_attrs)
                  for c in an_a.classes.values() if c.method_attrs]
        lcom_b = [compute_lcom4(c.method_attrs)
                  for c in an_b.classes.values() if c.method_attrs]
        abs_a = {c.name for c in an_a.classes.values() if c.is_abstract}
        abs_b = {c.name for c in an_b.classes.values() if c.is_abstract}

        m_a = compute_agq(G_a, abstract_modules=abs_a, classes_lcom4=lcom_a)
        m_b = compute_agq(G_b, abstract_modules=abs_b, classes_lcom4=lcom_b)

        gr_fwd = gate_check(G_a, G_b, language="python")
        gr_rev = gate_check(G_b, G_a, language="python")

        return {
            **pair,
            "fwd_passed": gr_fwd.passed,
            "fwd_rules": [v.rule if hasattr(v, "rule") else str(v)
                          for v in gr_fwd.violations],
            "rev_passed": gr_rev.passed,
            "rev_rules": [v.rule if hasattr(v, "rule") else str(v)
                          for v in gr_rev.violations],
            "agq_before": m_a.agq_score,
            "agq_after":  m_b.agq_score,
            "stab_before": m_a.stability,
            "stab_after":  m_b.stability,
            "mod_before":  m_a.modularity,
            "mod_after":   m_b.modularity,
            "acy_before":  m_a.acyclicity,
            "acy_after":   m_b.acyclicity,
            "coh_before":  m_a.cohesion,
            "coh_after":   m_b.cohesion,
            "nodes_before": G_a.number_of_nodes(),
            "nodes_after":  G_b.number_of_nodes(),
        }
    except Exception as e:
        return {**pair, "error": f"{type(e).__name__}: {e}"}
    finally:
        shutil.rmtree(a, ignore_errors=True)
        shutil.rmtree(b, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", required=True)
    ap.add_argument("--repos-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    pairs = [json.loads(l) for l in open(args.pairs) if l.strip()]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    done = 0
    errs = 0
    with ProcessPoolExecutor(max_workers=args.workers) as pool, \
         open(args.out, "w") as f:
        futs = {pool.submit(replay_pair, p, args.repos_dir): p for p in pairs}
        for fut in as_completed(futs):
            r = fut.result()
            f.write(json.dumps(r) + "\n"); f.flush()
            done += 1
            if r.get("error"):
                errs += 1
            if done % 10 == 0 or done == len(pairs):
                print(f"  [{done}/{len(pairs)}] errs={errs}", file=sys.stderr)
    print(f"done: {done}/{len(pairs)} errs={errs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
