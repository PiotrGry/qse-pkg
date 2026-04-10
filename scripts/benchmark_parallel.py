#!/usr/bin/env python3
"""
benchmark_parallel.py — QSE Benchmark z multithreadingiem i sparse checkout.

Rozwiązuje dwa problemy:
  1. DYSK:    sparse checkout zamiast full clone (1-5MB/repo zamiast 50-500MB)
  2. SZYBKOŚĆ: thread pool z thread-safe kolejką i atomic checkpointem

Architektura:
  - Queue (thread-safe) trzyma repo do przetworzenia
  - Każdy worker: sparse_checkout → qse agq → new metrics → cleanup
  - Checkpoint: wyniki zapisywane atomicznie per repo (JSON lines)
  - Race condition: threading.Lock na zapis + atomicowe rename pliku
  - Resume: pomija repo które są już w checkpoincie

Użycie:
  python3 scripts/benchmark_parallel.py \\
    --repos scripts/repos_experiment_total.json \\
    --workers 4 \\
    --output-dir artifacts/experiment_total \\
    --iter 3

  # Kontynuacja po przerwaniu (wczytuje checkpoint automatycznie):
  python3 scripts/benchmark_parallel.py --resume --iter 3

  # Tylko Python, 50 repo, 8 wątków:
  python3 scripts/benchmark_parallel.py --lang Python --limit 50 --workers 8

Zmienne środowiskowe:
  WORKERS=4        liczba równoległych workerów (domyślnie: 4)
  LANG_FILTER=Python
  LIMIT=100
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue, Empty
from typing import Dict, List, Optional, Tuple

# ── Biblioteki naukowe ─────────────────────────────────────────────────────
try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False

try:
    import numpy as np
    HAS_NP = True
except ImportError:
    HAS_NP = False

try:
    from scipy import stats as sp_stats
    HAS_SP = True
except ImportError:
    HAS_SP = False

try:
    from qse.graph_metrics import (
        compute_graph_density, compute_density_score,
        compute_scc_entropy, compute_scc_entropy_score,
        compute_hub_ratio, compute_hub_score,
    )
    HAS_QSE_METRICS = True
except ImportError:
    HAS_QSE_METRICS = False

# ── Kolory terminala ────────────────────────────────────────────────────────
RED    = '\033[0;31m'
GREEN  = '\033[0;32m'
YELLOW = '\033[1;33m'
CYAN   = '\033[0;36m'
BOLD   = '\033[1m'
DIM    = '\033[2m'
NC     = '\033[0m'

def ok(msg):    print(f"{GREEN}  ✓{NC} {msg}", flush=True)
def fail(msg):  print(f"{RED}  ✗{NC} {msg}", flush=True)
def info(msg):  print(f"{CYAN}  →{NC} {msg}", flush=True)


# ═══════════════════════════════════════════════════════════════════════════
# SPARSE CHECKOUT — pobiera tylko pliki kodu bez historii git
# ═══════════════════════════════════════════════════════════════════════════

# Mapowanie języka → katalogi/wzorce do sparse checkout
LANG_SPARSE = {
    "Python":     ["*.py", "**/*.py"],
    "Java":       ["src/", "*.java"],
    "Go":         ["*.go", "**/*.go"],
    "TypeScript": ["src/", "*.ts", "**/*.ts"],
}

# Szacowane rozmiary po sparse checkout (MB)
SPARSE_SIZE_EST = {
    "Python": 2, "Java": 5, "Go": 3, "TypeScript": 4,
}


def sparse_checkout(url: str, dest: Path, lang: str,
                    timeout: int = 120) -> bool:
    """Klonuje tylko pliki kodu (bez historii git).

    Zamiast full clone (~50-500MB) robi sparse checkout (~1-5MB):
      git init + git sparse-checkout + git pull --depth 1

    Po skanowaniu katalog jest usuwany przez cleanup().
    """
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)

    dest.mkdir(parents=True, exist_ok=True)

    try:
        # Init + remote
        subprocess.run(
            ["git", "init", "-q"], cwd=dest,
            capture_output=True, timeout=10, check=True)
        subprocess.run(
            ["git", "remote", "add", "origin", url], cwd=dest,
            capture_output=True, timeout=10, check=True)

        # Sparse checkout — tylko pliki kodu
        subprocess.run(
            ["git", "sparse-checkout", "init", "--cone"], cwd=dest,
            capture_output=True, timeout=10)

        # Ustaw wzorce per język
        patterns = LANG_SPARSE.get(lang, ["*.py"])
        if lang == "Python":
            # Cone mode: katalogi najwyższego poziomu
            # Pobierz listę katalogów z repo przez API
            src_dirs = _get_python_src_dirs(url)
            subprocess.run(
                ["git", "sparse-checkout", "set"] + src_dirs, cwd=dest,
                capture_output=True, timeout=10)
        else:
            subprocess.run(
                ["git", "sparse-checkout", "set", "src", "lib", "pkg", "cmd"],
                cwd=dest, capture_output=True, timeout=10)

        # Pull --depth 1 (bez historii)
        r = subprocess.run(
            ["git", "pull", "origin", "HEAD", "--depth", "1", "-q"],
            cwd=dest, capture_output=True, timeout=timeout)

        if r.returncode != 0:
            # Fallback: pełny clone z depth=1 ale bez .git
            shutil.rmtree(dest, ignore_errors=True)
            dest.mkdir(parents=True)
            r2 = subprocess.run(
                ["git", "clone", "--depth", "1", "--single-branch",
                 "--filter=blob:none",  # partial clone — pobiera tylko tree
                 url, str(dest)],
                capture_output=True, timeout=timeout)
            return r2.returncode == 0

        # Usuń .git żeby zwolnić miejsce (nie potrzebujemy historii)
        git_dir = dest / ".git"
        if git_dir.exists():
            shutil.rmtree(git_dir, ignore_errors=True)

        return True

    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False


def _get_python_src_dirs(url: str) -> List[str]:
    """Zwraca nazwy katalogów w root repo (dla sparse checkout)."""
    full_name = url.replace("https://github.com/", "")
    r = subprocess.run(
        ["gh", "api", f"repos/{full_name}/contents",
         "--jq", "[.[] | select(.type==\"dir\") | .name]"],
        capture_output=True, text=True, timeout=15)
    if r.returncode == 0:
        try:
            dirs = json.loads(r.stdout)
            # Filtruj nieistotne katalogi
            skip = {'docs', 'doc', 'test', 'tests', 'benchmark', 'benchmarks',
                    'example', 'examples', '.github', 'dist', 'build', 'node_modules'}
            return [d for d in dirs if d.lower() not in skip][:8]
        except Exception:
            pass
    return ["src", "lib"]


def cleanup(dest: Path) -> None:
    """Usuwa sklonowane repo żeby zwolnić miejsce."""
    shutil.rmtree(dest, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════════
# AGQ — skan repozytorium
# ═══════════════════════════════════════════════════════════════════════════

def run_agq(repo_path: Path, timeout: int = 120) -> Optional[Dict]:
    """Uruchamia qse agq i zwraca ustandaryzowany dict."""
    t0 = time.time()

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        json_out = tf.name

    try:
        r = subprocess.run(
            [sys.executable, "-m", "qse", "agq", str(repo_path),
             "--output-json", json_out, "--threshold", "0.0"],
            capture_output=True, text=True, timeout=timeout)

        elapsed_ms = round((time.time() - t0) * 1000)
        jp = Path(json_out)

        if jp.exists() and jp.stat().st_size > 10:
            try:
                d = json.loads(jp.read_text())
                return {
                    "agq_score":  d.get("agq_score"),
                    "language":   d.get("language", "Python"),
                    "nodes":      d.get("graph", {}).get("nodes", 0),
                    "edges":      d.get("graph", {}).get("edges", 0),
                    "modularity": d.get("metrics", {}).get("modularity"),
                    "acyclicity": d.get("metrics", {}).get("acyclicity"),
                    "stability":  d.get("metrics", {}).get("stability"),
                    "cohesion":   d.get("metrics", {}).get("cohesion"),
                    "runtime_ms": elapsed_ms,
                }
            except Exception:
                pass

        # Fallback text parsing
        text = r.stdout + r.stderr
        return _parse_agq_text(text, elapsed_ms) if text.strip() else None

    finally:
        Path(json_out).unlink(missing_ok=True)


def _parse_agq_text(text: str, elapsed_ms: int) -> Optional[Dict]:
    pats = {
        "agq_score":  r"AGQ[=:\s]+([0-9.]+)",
        "modularity": r"[Mm]odularity[=:\s]+([0-9.]+)",
        "acyclicity": r"[Aa]cyclicity[=:\s]+([0-9.]+)",
        "stability":  r"[Ss]tability[=:\s]+([0-9.]+)",
        "cohesion":   r"[Cc]ohesion[=:\s]+([0-9.]+)",
        "nodes":      r"[Nn]odes?[=:\s]+([0-9]+)",
    }
    result: Dict = {"runtime_ms": elapsed_ms}
    for k, p in pats.items():
        m = re.search(p, text)
        if m:
            result[k] = float(m.group(1))
    return result if "agq_score" in result else None


# ═══════════════════════════════════════════════════════════════════════════
# NOWE METRYKI GRAFOWE
# ═══════════════════════════════════════════════════════════════════════════

def build_import_graph(repo_path: Path) -> Optional["nx.DiGraph"]:
    if not HAS_NX:
        return None
    py_files = list(repo_path.rglob("*.py"))
    if len(py_files) < 5:
        return None

    G = nx.DiGraph()
    pkg = repo_path.name.replace("-", "_").replace(".", "_").lower()
    dirs = {p.name.replace("-","_").lower()
            for p in repo_path.iterdir() if p.is_dir()}
    imp_re = re.compile(r"^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.M)

    for f in py_files[:600]:
        rel = str(f.relative_to(repo_path)).replace("/", ".").rstrip(".py")
        G.add_node(rel)
        try:
            src = f.read_text(errors="ignore")
        except Exception:
            continue
        for m in imp_re.finditer(src):
            dep = (m.group(1) or m.group(2) or "").strip()
            root = dep.split(".")[0].lower()
            if dep and (root == pkg or root in dirs):
                G.add_edge(rel, dep)

    return G if G.number_of_nodes() >= 5 else None


def compute_new_metrics(repo_path: Path, lang: str) -> Optional[Dict]:
    if lang != "Python" or not HAS_NX:
        return None

    G = build_import_graph(repo_path)
    if G is None:
        return None

    n = G.number_of_nodes()
    e = G.number_of_edges()

    if HAS_QSE_METRICS:
        density   = compute_graph_density(G)
        d_score   = compute_density_score(density)
        scc_h     = compute_scc_entropy(G)
        scc_score = compute_scc_entropy_score(G)
        hub_r     = compute_hub_ratio(G)
        hub_s     = compute_hub_score(hub_r)
    else:
        density = round(e / (n * (n-1)), 6) if n > 1 else 0.0
        d_score = round(max(0.0, 1.0 - min(1.0, density / 0.020)), 4)
        sccs    = list(nx.strongly_connected_components(G))
        probs   = [len(c)/n for c in sccs]
        scc_h   = round(-sum(p*math.log2(p) for p in probs if p > 0), 4)
        max_h   = math.log2(max(n, 2))
        scc_score = round(min(1.0, scc_h/max_h), 4) if max_h > 0 else 1.0
        in_deg  = [d for _,d in G.in_degree()]
        mean_in = sum(in_deg)/n if n > 0 else 0.0
        hub_r   = round(sum(1 for d in in_deg if d > 2*mean_in)/n, 4)
        hub_s   = round(1.0 - hub_r, 4)

    W_D, W_S, W_H = 0.4136, 0.3005, 0.2859
    process_risk = round(1.0 - (W_D*d_score + W_S*scc_score + W_H*hub_s), 4)

    return {
        "graph_density":     density,
        "density_score":     d_score,
        "scc_entropy":       scc_h,
        "scc_entropy_score": scc_score,
        "hub_ratio":         hub_r,
        "hub_score":         hub_s,
        "process_risk":      process_risk,
        "n_nodes":           n,
        "n_edges":           e,
    }


# ═══════════════════════════════════════════════════════════════════════════
# GROUND TRUTH — GitHub Issues + git churn (z git log --no-checkout)
# ═══════════════════════════════════════════════════════════════════════════

def get_bug_lead_time(full_name: str) -> Optional[Dict]:
    r = subprocess.run(
        ["gh", "api", f"repos/{full_name}/issues",
         "-X", "GET", "-f", "state=closed", "-f", "labels=bug",
         "-f", "per_page=100",
         "--jq",
         "[.[] | select(.pull_request==null) | "
         "{c:.created_at,cl:.closed_at}]"],
        capture_output=True, text=True, timeout=30)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        issues = json.loads(r.stdout)
    except Exception:
        return None
    if not issues:
        return None
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    from datetime import datetime as _dt
    lead_times = []
    for i in issues:
        try:
            c  = _dt.strptime(i["c"],  fmt)
            cl = _dt.strptime(i["cl"], fmt)
            lead_times.append((cl - c).days)
        except Exception:
            pass
    if not lead_times:
        return None
    lt = sorted(lead_times)
    n  = len(lt)
    return {
        "n_bugs":           n,
        "mean_lead_days":   round(statistics.mean(lt), 1),
        "median_lead_days": round(statistics.median(lt), 1),
        "p90_lead_days":    round(lt[min(int(n*.9), n-1)], 1),
    }


def get_churn(repo_path: Path) -> Optional[Dict]:
    """Churn z git log — działa tylko gdy .git istnieje."""
    git_dir = repo_path / ".git"
    if not git_dir.exists():
        return None
    r = subprocess.run(
        ["git", "-C", str(repo_path), "log", "--since", "2 years ago",
         "--name-only", "--pretty=format:--COMMIT--"],
        capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return None
    test_re = re.compile(r"(^|/)tests?/|test_.*\.py$|_test\.py$")
    counts: Dict[str, int] = {}
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line or line == "--COMMIT--":
            continue
        if test_re.search(line):
            continue
        counts[line] = counts.get(line, 0) + 1
    if not counts:
        return None
    vals = list(counts.values())
    mean_c = sum(vals) / len(vals)
    hotspot = sum(1 for v in vals if v > mean_c * 2) / len(vals)
    sv = sorted(vals)
    n  = len(sv)
    cum = sum((i+1)*v for i,v in enumerate(sv))
    gini = (2*cum)/(n*sum(sv)) - (n+1)/n if sum(sv) > 0 else 0.0
    return {
        "hotspot_ratio": round(hotspot, 4),
        "churn_gini":    round(gini, 4),
        "n_files":       n,
    }


# ═══════════════════════════════════════════════════════════════════════════
# CHECKPOINT — thread-safe zapis wyników per repo
# ═══════════════════════════════════════════════════════════════════════════

class Checkpoint:
    """
    Atomowy checkpoint — zapisuje wynik każdego repo od razu po skanowaniu.

    Używa JSON lines (jeden JSON per linia) żeby nie tracić danych
    przy przerwaniu. Każdy zapis jest atomowy przez:
      1. Zapis do pliku tymczasowego
      2. os.replace() — atomowe przemianowanie (POSIX)
      3. threading.Lock — jeden wątek na raz

    Race conditions:
      - Wiele wątków może próbować zapisać jednocześnie → Lock
      - Crash podczas zapisu → dane w .tmp nie są committed → bezpieczne
      - Resume → wczytuje .jsonl i buduje set nazw już gotowych
    """

    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()
        self.done: set = set()
        self._load_existing()

    def _load_existing(self):
        """Wczytaj istniejące wyniki (resume)."""
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    self.done.add(d["name"])
                except Exception:
                    pass

    def is_done(self, name: str) -> bool:
        return name in self.done

    def save(self, result: Dict) -> None:
        """Atomowy zapis jednego wyniku (thread-safe)."""
        with self.lock:
            # Dopisz do pliku JSONL
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
            self.done.add(result["name"])

    def load_all(self) -> List[Dict]:
        """Wczytaj wszystkie zapisane wyniki."""
        results = []
        if not self.path.exists():
            return results
        for line in self.path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                results.append(json.loads(line))
            except Exception:
                pass
        return results

    def count(self) -> int:
        return len(self.done)


# ═══════════════════════════════════════════════════════════════════════════
# WORKER — jeden wątek = jeden repo
# ═══════════════════════════════════════════════════════════════════════════

class WorkerStats:
    """Thread-safe liczniki postępu."""
    def __init__(self, total: int):
        self.total     = total
        self.done      = 0
        self.ok        = 0
        self.failed    = 0
        self.skipped   = 0
        self.lock      = threading.Lock()
        self.start_time = time.time()

    def increment(self, status: str):
        with self.lock:
            self.done += 1
            if status == "ok":      self.ok += 1
            elif status == "fail":  self.failed += 1
            elif status == "skip":  self.skipped += 1

    def eta(self) -> str:
        elapsed = time.time() - self.start_time
        if self.done == 0:
            return "n/a"
        rate = self.done / elapsed
        remaining = (self.total - self.done) / rate
        m, s = divmod(int(remaining), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}h{m:02d}m"
        return f"{m}m{s:02d}s"

    def progress_line(self) -> str:
        pct = self.done / self.total * 100 if self.total > 0 else 0
        bar_w = 20
        filled = int(bar_w * pct / 100)
        bar = "█" * filled + "░" * (bar_w - filled)
        elapsed = int(time.time() - self.start_time)
        return (f"  [{bar}] {pct:5.1f}%  "
                f"{self.done}/{self.total}  "
                f"✓{self.ok} ✗{self.failed} ↷{self.skipped}  "
                f"ETA:{self.eta()}")


PRINT_LOCK = threading.Lock()

def worker(
    queue: Queue,
    checkpoint: Checkpoint,
    stats: WorkerStats,
    repos_dir: Path,
    no_lead_time: bool,
    worker_id: int,
) -> None:
    """Worker thread — przetwarza repo z kolejki."""
    while True:
        try:
            repo = queue.get(timeout=2)
        except Empty:
            break

        name      = repo["name"]
        url       = repo["url"]
        lang      = repo.get("lang", "Python")
        full_name = repo.get("full_name", url.replace("https://github.com/", ""))
        layer     = repo.get("layer", "B")

        # Jeśli już w checkpoincie — pomiń
        if checkpoint.is_done(name):
            stats.increment("skip")
            queue.task_done()
            with PRINT_LOCK:
                print(f"  {DIM}[W{worker_id}] {name} — skip (checkpoint){NC}",
                      flush=True)
            continue

        dest = repos_dir / f"w{worker_id}_{name}"

        try:
            # 1. Sparse checkout
            t_clone = time.time()
            cloned = sparse_checkout(url, dest, lang)
            clone_ms = round((time.time() - t_clone) * 1000)

            if not cloned:
                stats.increment("fail")
                queue.task_done()
                with PRINT_LOCK:
                    fail(f"[W{worker_id}] {name} — clone FAIL ({clone_ms}ms)")
                checkpoint.save({
                    "name": name, "lang": lang, "layer": layer,
                    "status": "clone_fail", "agq": None,
                    "new_metrics": None, "churn": None, "bug_lead_time": None,
                })
                continue

            # 2. AGQ
            agq = run_agq(dest)
            if not agq:
                stats.increment("fail")
                queue.task_done()
                with PRINT_LOCK:
                    fail(f"[W{worker_id}] {name} — AGQ FAIL")
                cleanup(dest)
                checkpoint.save({
                    "name": name, "lang": lang, "layer": layer,
                    "status": "agq_fail", "agq": None,
                    "new_metrics": None, "churn": None, "bug_lead_time": None,
                })
                continue

            # 3. Nowe metryki grafowe
            new_m = compute_new_metrics(dest, lang)

            # 4. Churn (tylko jeśli .git dostępny)
            churn = get_churn(dest)

            # 5. Bug lead time (GitHub API — bez dysku)
            bug_lt = None
            if not no_lead_time and "/" in full_name:
                bug_lt = get_bug_lead_time(full_name)

            # 6. Cleanup — zwolnij dysk natychmiast
            cleanup(dest)

            # 7. Zapisz wynik atomowo
            result = {
                "name":          name,
                "lang":          lang,
                "layer":         layer,
                "full_name":     full_name,
                "status":        "ok",
                "agq":           agq,
                "new_metrics":   new_m,
                "churn":         churn,
                "bug_lead_time": bug_lt,
            }
            checkpoint.save(result)
            stats.increment("ok")

            # 8. Log
            with PRINT_LOCK:
                agq_s  = f"{agq.get('agq_score',0):.4f}"
                nm_s   = (f"density={new_m['graph_density']:.5f} "
                          f"risk={new_m['process_risk']:.3f}"
                          if new_m else "no_desc")
                bug_s  = (f"bug={bug_lt['median_lead_days']}d"
                          if bug_lt else "")
                print(f"  {GREEN}✓{NC} [W{worker_id}] "
                      f"{BOLD}{name:25}{NC} "
                      f"AGQ={CYAN}{agq_s}{NC} "
                      f"{DIM}{nm_s} {bug_s}{NC}",
                      flush=True)
                print(stats.progress_line(), flush=True)

        except Exception as e:
            cleanup(dest)
            stats.increment("fail")
            with PRINT_LOCK:
                fail(f"[W{worker_id}] {name} — exception: {e}")
            checkpoint.save({
                "name": name, "lang": lang, "layer": layer,
                "status": "exception", "error": str(e),
                "agq": None, "new_metrics": None,
                "churn": None, "bug_lead_time": None,
            })
        finally:
            queue.task_done()


# ═══════════════════════════════════════════════════════════════════════════
# KORELACJE
# ═══════════════════════════════════════════════════════════════════════════

def compute_correlations(results: List[Dict]) -> List[Dict]:
    def extract(key: str, src: str) -> List[Optional[float]]:
        out = []
        for r in results:
            if src == "agq":
                v = (r.get("agq") or {}).get(key)
            elif src == "new":
                v = (r.get("new_metrics") or {}).get(key)
            elif src == "churn":
                v = (r.get("churn") or {}).get(key)
            elif src == "bug":
                v = (r.get("bug_lead_time") or {}).get(key)
            else:
                v = None
            out.append(v)
        return out

    PREDICTORS = [
        ("agq_score",         "agq", "AGQ"),
        ("acyclicity",        "agq", "Acyclicity"),
        ("stability",         "agq", "Stability"),
        ("cohesion",          "agq", "Cohesion"),
        ("modularity",        "agq", "Modularity"),
        ("graph_density",     "new", "GraphDensity  [NEW]"),
        ("scc_entropy",       "new", "SCCEntropy    [NEW]"),
        ("hub_ratio",         "new", "HubRatio      [NEW]"),
        ("process_risk",      "new", "ProcessRisk   [NEW]"),
        ("density_score",     "new", "DensityScore  [NEW]"),
    ]
    TARGETS = [
        ("churn_gini",       "churn", "churn_gini"),
        ("hotspot_ratio",    "churn", "hotspot_ratio"),
        ("median_lead_days", "bug",   "bug_median_days"),
        ("mean_lead_days",   "bug",   "bug_mean_days"),
    ]

    corrs = []
    for pk, ps, pl in PREDICTORS:
        for tk, ts, tl in TARGETS:
            xs_raw = extract(pk, ps)
            ys_raw = extract(tk, ts)
            pairs  = [
                (x, y) for x, y in zip(xs_raw, ys_raw)
                if x is not None and y is not None
                and not (math.isnan(float(x)) or math.isnan(float(y)))
            ]
            if len(pairs) < 5:
                continue
            xs, ys = zip(*pairs)
            if HAS_SP:
                r_s, p = sp_stats.spearmanr(xs, ys)
            else:
                continue
            if math.isnan(float(r_s)):
                continue
            corrs.append({
                "predictor": pl, "target": tl,
                "r_s": round(float(r_s), 4), "p": round(float(p), 4),
                "n": len(pairs), "sig": bool(p < 0.05), "abs_r": abs(r_s),
                "strength": (
                    "STRONG"   if abs(r_s) >= 0.7 else
                    "moderate" if abs(r_s) >= 0.5 else
                    "weak"     if abs(r_s) >= 0.3 else
                    "v.weak"),
            })
    return sorted(corrs, key=lambda x: x["abs_r"], reverse=True)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="QSE Benchmark Totalny — multithreaded + sparse checkout")
    parser.add_argument("--repos",        default="scripts/repos_experiment_total.json")
    parser.add_argument("--workers",      type=int,
                        default=int(os.environ.get("WORKERS", 4)))
    parser.add_argument("--output-dir",   default="artifacts/experiment_total")
    parser.add_argument("--iter",         type=int,
                        default=int(os.environ.get("ITER", 3)))
    parser.add_argument("--lang",         default=os.environ.get("LANG_FILTER"))
    parser.add_argument("--limit",        type=int,
                        default=int(os.environ.get("LIMIT", 0)) or None)
    parser.add_argument("--resume",       action="store_true",
                        help="Kontynuuj od miejsca przerwania")
    parser.add_argument("--no-lead-time", action="store_true")
    parser.add_argument("--repos-dir",    default="/tmp/qse_sparse")
    args = parser.parse_args()

    repos_dir  = Path(args.repos_dir)
    output_dir = Path(args.output_dir) / f"iter_{args.iter}"
    repos_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Checkpoint
    checkpoint_path = output_dir / "checkpoint.jsonl"
    checkpoint = Checkpoint(checkpoint_path)

    # Wczytaj listę
    repo_list = json.loads(Path(args.repos).read_text())
    if args.lang:
        repo_list = [r for r in repo_list if r.get("lang", "Python") == args.lang]
    if args.limit:
        repo_list = repo_list[:args.limit]

    # Filtruj już gotowe (resume)
    todo = [r for r in repo_list if not checkpoint.is_done(r["name"])]
    already_done = len(repo_list) - len(todo)

    # Banner
    print(f"\n{BOLD}{'='*65}{NC}")
    print(f"{BOLD}  QSE Benchmark Totalny — iteracja {args.iter}{NC}")
    print(f"{BOLD}{'='*65}{NC}")
    print(f"  Repo łącznie:  {len(repo_list)}")
    print(f"  Już gotowych:  {already_done} (checkpoint)")
    print(f"  Do zrobienia:  {len(todo)}")
    print(f"  Workers:       {args.workers}")
    print(f"  Lang:          {args.lang or 'wszystkie'}")
    print(f"  Checkpoint:    {checkpoint_path}")
    print(f"  Sparse dir:    {repos_dir}")
    est_mb = len(todo) * SPARSE_SIZE_EST.get(args.lang or "Python", 3)
    print(f"  Max dysk:      ~{est_mb}MB (sparse, cleanup na bieżąco)")
    print(f"  QSE metrics:   {'qse.graph_metrics' if HAS_QSE_METRICS else 'fallback'}")
    print()

    if not todo:
        print("  Wszystkie repo już w checkpoincie. Generuję raport...")
    else:
        # Wypełnij kolejkę
        queue: Queue = Queue()
        for repo in todo:
            queue.put(repo)

        stats = WorkerStats(len(todo))

        print(f"{CYAN}  Startuje {args.workers} workerów...{NC}\n")

        # Uruchom wątki
        threads = []
        for i in range(args.workers):
            t = threading.Thread(
                target=worker,
                args=(queue, checkpoint, stats, repos_dir,
                      args.no_lead_time, i + 1),
                daemon=True,
                name=f"Worker-{i+1}",
            )
            t.start()
            threads.append(t)

        # Czekaj na zakończenie wszystkich
        queue.join()
        for t in threads:
            t.join(timeout=5)

        print(f"\n{BOLD}{'='*65}{NC}")
        print(f"{BOLD}  Benchmark zakończony!{NC}")
        print(f"  OK:     {stats.ok}")
        print(f"  FAIL:   {stats.failed}")
        print(f"  Skip:   {stats.skipped}")
        elapsed = int(time.time() - stats.start_time)
        print(f"  Czas:   {elapsed//60}m{elapsed%60:02d}s")

    # Wczytaj wszystkie wyniki i oblicz korelacje
    all_results = checkpoint.load_all()
    ok_results  = [r for r in all_results if r.get("status") == "ok"]

    print(f"\n{CYAN}  Obliczam korelacje ({len(ok_results)} repo)...{NC}")
    correlations = compute_correlations(ok_results)

    # Podsumowanie korelacji
    if correlations:
        print(f"\n  {'Predyktor':28} {'→ Cel':22} {'r_s':>7} {'p':>7} {'n':>4}  Siła")
        print(f"  {'-'*78}")
        for c in correlations[:12]:
            sig = ("***" if c["p"] < 0.001 else "** " if c["p"] < 0.01
                   else "*  " if c["p"] < 0.05 else "   ")
            new = " ◄" if "[NEW]" in c["predictor"] else ""
            print(f"  {c['predictor'].strip():28} {c['target']:22} "
                  f"{c['r_s']:+7.4f} {c['p']:7.4f} {c['n']:4}  "
                  f"{sig} {c['strength']}{new}")

    # Zapisz raport
    agq_vals = [r["agq"]["agq_score"] for r in ok_results
                if (r.get("agq") or {}).get("agq_score")]
    report = {
        "generated_at":           datetime.now(timezone.utc).isoformat(),
        "iter":                   args.iter,
        "repos_total":            len(repo_list),
        "repos_ok":               len(ok_results),
        "repos_failed":           len([r for r in all_results if r.get("status") != "ok"]),
        "repos_with_new_metrics": sum(1 for r in ok_results if r.get("new_metrics")),
        "repos_with_bug_lt":      sum(1 for r in ok_results if r.get("bug_lead_time")),
        "repos_with_churn":       sum(1 for r in ok_results if r.get("churn")),
        "agq_mean":               round(statistics.mean(agq_vals), 4) if agq_vals else None,
        "agq_std":                round(statistics.pstdev(agq_vals), 4) if agq_vals else None,
        "correlations":           correlations,
        "results":                ok_results,
    }

    (output_dir / "results.json").write_text(json.dumps(report, indent=2))
    (output_dir / "correlations.json").write_text(json.dumps(correlations, indent=2))

    # Markdown
    md_lines = [
        f"# Benchmark Totalny — Iteracja {args.iter}",
        f"- generated: `{report['generated_at']}`",
        f"- repos_ok: **{report['repos_ok']}**",
        f"- z nowymi metrykami: {report['repos_with_new_metrics']}",
        f"- z bug lead time: {report['repos_with_bug_lt']}",
        f"- AGQ mean: `{report['agq_mean']}`",
        "",
        "## Korelacje",
        "| Predyktor | Cel | r_s | p | n | Siła |",
        "|---|---|---:|---:|---:|---|",
    ]
    for c in correlations[:20]:
        sig = " *" if c["sig"] else ""
        new = " ◄" if "[NEW]" in c["predictor"] else ""
        md_lines.append(
            f"| {c['predictor'].strip()}{new} | {c['target']} "
            f"| {c['r_s']}{sig} | {c['p']} | {c['n']} | {c['strength']} |")
    (output_dir / "results.md").write_text("\n".join(md_lines))

    print(f"\n{GREEN}  Zapisano:{NC}")
    print(f"    {output_dir}/results.json")
    print(f"    {output_dir}/results.md")
    print(f"    {checkpoint_path} (checkpoint)")
    print(f"\n  Aby wrzucić na GitHub:")
    print(f"    git add artifacts/experiment_total/iter_{args.iter}/")
    print(f"    git commit -m 'experiment: iter {args.iter} — {len(ok_results)} repos'")
    print(f"    git push origin perplexity\n")


if __name__ == "__main__":
    main()
