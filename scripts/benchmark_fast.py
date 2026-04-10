#!/usr/bin/env python3
"""
benchmark_fast.py — Maksymalnie szybki benchmark QSE.

Architektura:
  - N scanner workerów równolegle (domyślnie: cpu_count)
  - 1 cleanup worker w tle (usuwa repo natychmiast po skanowaniu)
  - Disk semaphore: max DISK_SLOTS repo na dysku jednocześnie
  - Auto-push do GitHub co PUSH_EVERY repo
  - Atomic JSONL checkpoint — resume po przerwaniu
  - Sparse clone: depth=1, filter=blob:none (~1-5MB/repo)

Zużycie dysku: workers × ~5MB = ~40MB przy 8 workerach

Użycie:
  python3 scripts/benchmark_fast.py
  python3 scripts/benchmark_fast.py --workers 8 --iter 4
  python3 scripts/benchmark_fast.py --resume --iter 4
  python3 scripts/benchmark_fast.py --lang Python --limit 50

Zmienne środowiskowe:
  WORKERS=8        (domyślnie: liczba CPU)
  DISK_SLOTS=16    (max repo na dysku jednocześnie, domyślnie: workers×2)
  PUSH_EVERY=10    (push do GitHub co N repo, domyślnie: 10)
  ITER=4
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
from typing import Dict, List, Optional

try:
    from scipy import stats as sp_stats
    HAS_SP = True
except ImportError:
    HAS_SP = False

# Wykryj właściwy Python interpreter (venv jeśli dostępny)
def _find_python() -> str:
    """Zwraca ścieżkę do Pythona z venv lub systemowego."""
    import sys
    # Sprawdź czy jesteśmy w venv
    if hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    ):
        return sys.executable  # już jesteśmy w venv
    # Szukaj venv w katalogu projektu i rodziców
    here = Path(__file__).resolve().parent
    for d in [here, here.parent, here.parent.parent]:
        for venv in ['.venv', 'venv', 'env']:
            py = d / venv / 'bin' / 'python'
            if py.exists():
                return str(py)
            py = d / venv / 'bin' / 'python3'
            if py.exists():
                return str(py)
    return sys.executable  # fallback: systemowy

PYTHON = _find_python()

# ── Kolory ─────────────────────────────────────────────────────────────────
_G = '\033[0;32m'; _R = '\033[0;31m'; _Y = '\033[1;33m'
_C = '\033[0;36m'; _B = '\033[1m';    _D = '\033[2m';   _N = '\033[0m'

_PRINT_LOCK = threading.Lock()

def _p(*args, **kw):
    with _PRINT_LOCK:
        print(*args, **kw, flush=True)


# ═══════════════════════════════════════════════════════════════════════════
# SPARSE CLONE
# ═══════════════════════════════════════════════════════════════════════════

def clone_for_scan(url: str, dest: Path, timeout: int = 90) -> bool:
    """Klonuje tylko pliki kodu (bez historii) — dla AGQ scan.

    --depth 1 + --filter=blob:none: pobiera tree i blobs ostatniego
    commita. Rozmiar: ~1-5MB zamiast ~50-500MB.
    """
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    try:
        r = subprocess.run(
            ["git", "clone",
             "--depth", "1",
             "--single-branch",
             "--filter=blob:none",
             "--no-tags",
             url, str(dest)],
            capture_output=True, timeout=timeout)
        return r.returncode == 0
    except (subprocess.TimeoutExpired, Exception):
        return False


def clone_for_churn(url: str, dest: Path, timeout: int = 120) -> bool:
    """Klonuje historię git bez plików — dla churn.

    --no-checkout + --filter=blob:none:
      - pobiera commit objects i tree objects (potrzebne dla git log --name-only)
      - NIE pobiera blob objects (zawartości plików)
      - Rozmiar: ~2-10MB zamiast ~50-500MB
      - git log --name-only działa od razu (tree objects są dostępne)

    Uwaga: --filter=tree:0 (lazy tree fetch) powoduje timeout na git log
    bo tree objects są pobierane leniwie podczas traversal historii.
    --filter=blob:none jest poprawnym wyborem dla dostępu do historii.
    """
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    try:
        r = subprocess.run(
            ["git", "clone",
             "--no-checkout",        # nie checkout plików do working tree
             "--filter=blob:none",   # pobierz tree ale nie blob (pliki)
             "--no-tags",
             url, str(dest)],
            capture_output=True, timeout=timeout)
        return r.returncode == 0
    except (subprocess.TimeoutExpired, Exception):
        return False


def sparse_clone(url: str, dest: Path, timeout: int = 90) -> bool:
    """Alias dla wstecznej kompatybilności."""
    return clone_for_scan(url, dest, timeout)


# ═══════════════════════════════════════════════════════════════════════════
# AGQ SCAN
# ═══════════════════════════════════════════════════════════════════════════

def run_agq(repo_path: Path, timeout: int = 120) -> Optional[Dict]:
    """Uruchamia qse agq, zwraca ustandaryzowany dict."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        json_out = tf.name
    try:
        t0 = time.time()
        r = subprocess.run(
            [PYTHON, "-m", "qse", "agq", str(repo_path),
             "--output-json", json_out, "--threshold", "0.0"],
            capture_output=True, text=True, timeout=timeout)
        ms = round((time.time() - t0) * 1000)

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
                    "runtime_ms": ms,
                }
            except Exception:
                pass
        # Fallback text parse
        text = r.stdout + r.stderr
        if text.strip():
            return _parse_text(text, ms)
        return None
    finally:
        Path(json_out).unlink(missing_ok=True)


def _parse_text(text: str, ms: int) -> Optional[Dict]:
    pats = {
        "agq_score":  r"AGQ[=:\s]+([0-9.]+)",
        "modularity": r"[Mm]odularity[=:\s]+([0-9.]+)",
        "acyclicity": r"[Aa]cyclicity[=:\s]+([0-9.]+)",
        "stability":  r"[Ss]tability[=:\s]+([0-9.]+)",
        "cohesion":   r"[Cc]ohesion[=:\s]+([0-9.]+)",
        "nodes":      r"[Nn]odes?[=:\s]+([0-9]+)",
    }
    result: Dict = {"runtime_ms": ms}
    for k, p in pats.items():
        m = re.search(p, text)
        if m:
            result[k] = float(m.group(1))
    return result if "agq_score" in result else None


# ═══════════════════════════════════════════════════════════════════════════
# GROUND TRUTH — GitHub API (bez dysku)
# ═══════════════════════════════════════════════════════════════════════════

def get_churn(repo_path: Path) -> Optional[Dict]:
    """Oblicza churn z historii git.

    Wymaga klonu z clone_for_churn() — --no-checkout --filter=tree:0.
    Historia jest dostępna mimo braku plików w working tree.
    """
    r = subprocess.run(
        ["git", "-C", str(repo_path), "log",
         "-n", "500",
         "--name-only",
         "--pretty=format:--C--"],
        capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return None

    test_re = re.compile(
        r"(^|/)tests?/|test_.*\.(py|go|java)$|_test\.(py|go|java)$|Test\.java$")
    counts: Dict[str, int] = {}
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line or line == "--C--":
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
        "mean_churn":    round(mean_c, 3),
    }


def get_bug_lead_time(full_name: str) -> Optional[Dict]:
    r = subprocess.run(
        ["gh", "api", f"repos/{full_name}/issues",
         "-X", "GET", "-f", "state=closed", "-f", "labels=bug",
         "-f", "per_page=100",
         "--jq", "[.[] | select(.pull_request==null) | "
                 "{c:.created_at,cl:.closed_at}]"],
        capture_output=True, text=True, timeout=25)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        issues = json.loads(r.stdout)
    except Exception:
        return None
    if not issues:
        return None
    from datetime import datetime as _dt
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    lt = []
    for i in issues:
        try:
            lt.append((_dt.strptime(i["cl"], fmt) -
                       _dt.strptime(i["c"], fmt)).days)
        except Exception:
            pass
    if not lt:
        return None
    lt = sorted(lt)
    n = len(lt)
    return {
        "n_bugs":           n,
        "mean_lead_days":   round(statistics.mean(lt), 1),
        "median_lead_days": round(statistics.median(lt), 1),
        "p90_lead_days":    round(lt[min(int(n * .9), n-1)], 1),
    }


def get_repo_meta(full_name: str) -> Optional[Dict]:
    r = subprocess.run(
        ["gh", "api", f"repos/{full_name}",
         "--jq", "{stars:.stargazers_count, forks:.forks_count, "
                 "size_kb:.size, open_issues:.open_issues_count, "
                 "pushed_at:.pushed_at}"],
        capture_output=True, text=True, timeout=15)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════
# CHECKPOINT — atomowy JSONL + auto-push
# ═══════════════════════════════════════════════════════════════════════════

class Checkpoint:
    """Atomowy checkpoint z auto-push do GitHub.

    Zapisuje każdy wynik jako osobna linia JSON (JSONL).
    Auto-push co PUSH_EVERY repo — wyniki zawsze w repo.
    """

    def __init__(self, path: Path, output_dir: Path,
                 push_every: int = 10, iter_n: int = 4):
        self.path       = path
        self.output_dir = output_dir
        self.push_every = push_every
        self.iter_n     = iter_n
        self.lock       = threading.Lock()
        self.done:  set = set()
        self._since_push = 0
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        for line in self.path.read_text().splitlines():
            try:
                self.done.add(json.loads(line)["name"])
            except Exception:
                pass

    def is_done(self, name: str) -> bool:
        return name in self.done

    def save(self, result: Dict) -> None:
        """Atomowy zapis + ewentualny auto-push."""
        with self.lock:
            with open(self.path, "a") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
            self.done.add(result["name"])
            self._since_push += 1

            if self._since_push >= self.push_every:
                self._push()
                self._since_push = 0

    def _push(self) -> None:
        """Push do GitHub w tle — nie blokuje workerów."""
        def _do_push():
            try:
                subprocess.run(
                    ["git", "add", str(self.output_dir)],
                    capture_output=True, timeout=15)
                n = len(self.done)
                subprocess.run(
                    ["git", "commit", "-m",
                     f"experiment/iter{self.iter_n}: {n} repos [auto]"],
                    capture_output=True, timeout=15)
                subprocess.run(
                    ["git", "push", "origin", "perplexity"],
                    capture_output=True, timeout=30)
                _p(f"  {_G}↑ AUTO-PUSH{_N} {n} repo → GitHub")
            except Exception as e:
                _p(f"  {_Y}↑ push failed: {e}{_N}")
        threading.Thread(target=_do_push, daemon=True).start()

    def final_push(self) -> None:
        """Finalny push po zakończeniu benchmarku."""
        self._push()

    def load_all(self) -> List[Dict]:
        if not self.path.exists():
            return []
        results = []
        for line in self.path.read_text().splitlines():
            try:
                results.append(json.loads(line))
            except Exception:
                pass
        return results

    @property
    def count(self) -> int:
        return len(self.done)


# ═══════════════════════════════════════════════════════════════════════════
# CLEANUP WORKER — osobny wątek usuwa repo w tle
# ═══════════════════════════════════════════════════════════════════════════

class CleanupWorker:
    """Osobny wątek który usuwa sklonowane repo w tle.

    Scanner wrzuca ścieżkę do cleanup_queue po zakończeniu skanowania.
    Cleanup worker usuwa w tle — scanner nie czeka na usunięcie.
    disk_semaphore jest zwalniany po usunięciu.
    """

    def __init__(self, disk_semaphore: threading.Semaphore):
        self.queue    = Queue()
        self.sem      = disk_semaphore
        self._running = True
        self._thread  = threading.Thread(
            target=self._run, daemon=True, name="Cleanup")
        self._thread.start()

    def schedule(self, path: Path) -> None:
        """Zleca usunięcie katalogu. Non-blocking."""
        self.queue.put(path)

    def _run(self) -> None:
        while self._running or not self.queue.empty():
            try:
                path = self.queue.get(timeout=1)
            except Empty:
                continue
            try:
                shutil.rmtree(path, ignore_errors=True)
            except Exception:
                pass
            finally:
                # Zwolnij slot na dysku
                try:
                    self.sem.release()
                except Exception:
                    pass
                self.queue.task_done()

    def stop(self) -> None:
        self._running = False
        self.queue.join()  # Czekaj aż wszystko zostanie usunięte


# ═══════════════════════════════════════════════════════════════════════════
# PROGRESS TRACKER
# ═══════════════════════════════════════════════════════════════════════════

class Progress:
    def __init__(self, total: int):
        self.total   = total
        self.done    = 0
        self.ok      = 0
        self.failed  = 0
        self.skipped = 0
        self.lock    = threading.Lock()
        self.t0      = time.time()

    def inc(self, status: str) -> None:
        with self.lock:
            self.done += 1
            if status == "ok":    self.ok += 1
            elif status == "fail": self.failed += 1
            elif status == "skip": self.skipped += 1

    def eta(self) -> str:
        elapsed = time.time() - self.t0
        if self.done == 0:
            return "n/a"
        rate = self.done / elapsed
        rem  = (self.total - self.done) / rate
        h, r = divmod(int(rem), 3600)
        m, s = divmod(r, 60)
        return (f"{h}h{m:02d}m" if h else
                f"{m}m{s:02d}s" if m else f"{s}s")

    def bar(self) -> str:
        pct    = self.done / self.total * 100 if self.total else 0
        filled = int(30 * pct / 100)
        bar    = "█" * filled + "░" * (30 - filled)
        elapsed = int(time.time() - self.t0)
        speed  = self.done / max(elapsed, 1) * 60  # repo/min
        return (f"  [{bar}] {pct:5.1f}%  "
                f"{self.done}/{self.total}  "
                f"{_G}✓{self.ok}{_N} {_R}✗{self.failed}{_N} "
                f"↷{self.skipped}  "
                f"{speed:.1f}/min  ETA:{self.eta()}")


# ═══════════════════════════════════════════════════════════════════════════
# SCANNER WORKER
# ═══════════════════════════════════════════════════════════════════════════

def scanner_worker(
    scan_queue:   Queue,
    checkpoint:   Checkpoint,
    progress:     Progress,
    cleanup:      CleanupWorker,
    disk_sem:     threading.Semaphore,
    scratch_dir:  Path,
    no_lead_time: bool,
    worker_id:    int,
) -> None:
    """Jeden wątek: clone → scan → enqueue cleanup → checkpoint."""

    while True:
        try:
            repo = scan_queue.get(timeout=3)
        except Empty:
            break

        name      = repo["name"]
        url       = repo["url"]
        lang      = repo.get("lang", "Python")
        full_name = repo.get("full_name",
                             url.replace("https://github.com/", ""))
        layer     = repo.get("layer", "B")

        # Resume
        if checkpoint.is_done(name):
            progress.inc("skip")
            scan_queue.task_done()
            continue

        # Zdobądź slot na dysku (blokuje jeśli za dużo repo naraz)
        disk_sem.acquire()

        dest = scratch_dir / f"w{worker_id}_{name}"

        try:
            # ── Klon 1: pliki kodu → AGQ scan ─────────────────────
            dest_code  = dest.parent / f"{dest.name}_code"
            dest_hist  = dest.parent / f"{dest.name}_hist"

            t_clone = time.time()
            ok_code = clone_for_scan(url, dest_code)
            clone_ms = round((time.time() - t_clone) * 1000)

            if not ok_code:
                cleanup.schedule(dest_code)
                cleanup.schedule(dest_hist)
                progress.inc("fail")
                checkpoint.save({
                    "name": name, "lang": lang, "layer": layer,
                    "status": "clone_fail", "agq": None,
                    "churn": None, "bug_lead_time": None, "meta": None,
                })
                _p(f"  {_R}✗{_N} [W{worker_id}] {name} clone FAIL ({clone_ms}ms)")
                scan_queue.task_done()
                continue

            # ── AGQ scan ───────────────────────────────────────────────────
            agq = run_agq(dest_code)

            # Usuń pliki kodu NATYCHMIAST po skanowaniu — zwalnia dysk
            cleanup.schedule(dest_code)

            if not agq:
                progress.inc("fail")
                checkpoint.save({
                    "name": name, "lang": lang, "layer": layer,
                    "status": "agq_fail", "agq": None,
                    "churn": None, "bug_lead_time": None, "meta": None,
                })
                _p(f"  {_R}✗{_N} [W{worker_id}] {_B}{name:25}{_N} AGQ FAIL")
                scan_queue.task_done()
                continue

            # ── Klon 2: historia → churn (równolegle z bug_lead_time) ──────
            # --no-checkout --filter=tree:0: tylko historia, ~2-20MB
            ok_hist = clone_for_churn(url, dest_hist)
            churn = None
            if ok_hist:
                churn = get_churn(dest_hist)
                cleanup.schedule(dest_hist)   # usuń historię
            else:
                cleanup.schedule(dest_hist)

            # ── Bug lead time + meta (GitHub API — zero dysku) ─────────────
            bug_lt = None
            if not no_lead_time:
                bug_lt = get_bug_lead_time(full_name)
            meta = get_repo_meta(full_name)

            # ── Zapisz wynik ───────────────────────────────────────────────
            result = {
                "name":          name,
                "lang":          lang,
                "layer":         layer,
                "full_name":     full_name,
                "status":        "ok",
                "agq":           agq,
                "churn":         churn,
                "clone_ms":      clone_ms,
                "bug_lead_time": bug_lt,
                "meta":          meta,
            }
            checkpoint.save(result)
            progress.inc("ok")

            # ── Log ────────────────────────────────────────────────────────
            agq_s  = f"{agq.get('agq_score', 0):.4f}"
            nodes  = agq.get("nodes", "?")
            churn_s = (f"churn={churn['churn_gini']:.2f}"
                       if churn else "no_churn")
            bug_s  = (f"bug={bug_lt['median_lead_days']}d"
                      if bug_lt else "")
            stars  = f"★{meta['stars']}" if meta else ""
            _p(f"  {_G}✓{_N} [W{worker_id}] "
               f"{_B}{name:25}{_N} "
               f"AGQ={_C}{agq_s}{_N} "
               f"n={nodes} {churn_s} {bug_s} {_D}{stars}{_N}")
            _p(progress.bar())

        except Exception as e:
            cleanup.schedule(dest)
            progress.inc("fail")
            checkpoint.save({
                "name": name, "lang": lang, "layer": layer,
                "status": "exception", "error": str(e),
                "agq": None, "bug_lead_time": None, "meta": None,
            })
            _p(f"  {_R}✗{_N} [W{worker_id}] {name} EXCEPTION: {e}")

        finally:
            scan_queue.task_done()


# ═══════════════════════════════════════════════════════════════════════════
# KORELACJE
# ═══════════════════════════════════════════════════════════════════════════

def correlations(results: List[Dict]) -> List[Dict]:
    if not HAS_SP:
        return []

    def extr(key: str, src: str):
        out = []
        for r in results:
            if src == "agq":
                v = (r.get("agq") or {}).get(key)
            elif src == "bug":
                v = (r.get("bug_lead_time") or {}).get(key)
            elif src == "churn":
                v = (r.get("churn") or {}).get(key)
            elif src == "meta":
                v = (r.get("meta") or {}).get(key)
            else:
                v = None
            out.append(v)
        return out

    PREDS = [
        ("agq_score",  "agq",  "AGQ"),
        ("acyclicity", "agq",  "Acyclicity"),
        ("stability",  "agq",  "Stability"),
        ("cohesion",   "agq",  "Cohesion"),
        ("modularity", "agq",  "Modularity"),
    ]
    TGTS = [
        ("median_lead_days", "bug",    "bug_median_days"),
        ("mean_lead_days",   "bug",    "bug_mean_days"),
        ("churn_gini",       "churn",  "churn_gini"),
        ("hotspot_ratio",    "churn",  "hotspot_ratio"),
        ("open_issues",      "meta",   "open_issues"),
        ("size_kb",          "meta",   "repo_size_kb"),
    ]

    out = []
    for pk, ps, pl in PREDS:
        for tk, ts, tl in TGTS:
            pairs = [
                (x, y) for x, y in zip(extr(pk, ps), extr(tk, ts))
                if x is not None and y is not None
                and not (math.isnan(float(x)) or math.isnan(float(y)))
            ]
            if len(pairs) < 5:
                continue
            xs, ys = zip(*pairs)
            r_s, p = sp_stats.spearmanr(xs, ys)
            if math.isnan(float(r_s)):
                continue
            out.append({
                "predictor": pl, "target": tl,
                "r_s": round(float(r_s), 4), "p": round(float(p), 4),
                "n": len(pairs), "sig": bool(p < 0.05),
                "abs_r": abs(r_s),
                "strength": (
                    "STRONG"   if abs(r_s) >= 0.7 else
                    "moderate" if abs(r_s) >= 0.5 else
                    "weak"     if abs(r_s) >= 0.3 else
                    "v.weak"),
            })
    return sorted(out, key=lambda x: x["abs_r"], reverse=True)


# ═══════════════════════════════════════════════════════════════════════════
# RAPORT MARKDOWN
# ═══════════════════════════════════════════════════════════════════════════

def make_report(results: List[Dict], corrs: List[Dict],
                iter_n: int) -> str:
    ok = [r for r in results if r.get("status") == "ok"]
    agq_vals = [r["agq"]["agq_score"] for r in ok
                if (r.get("agq") or {}).get("agq_score") is not None]

    by_lang: Dict[str, List] = {}
    fps: Dict[str, int] = {}
    for r in ok:
        agq = r.get("agq") or {}
        v = agq.get("agq_score")
        if v is not None:
            by_lang.setdefault(r["lang"], []).append(v)
        a = agq.get("acyclicity", 0)
        s = agq.get("stability", 0)
        c = agq.get("cohesion", 0)
        if a >= 0.98 and s >= 0.6 and c >= 0.7:   fp = "CLEAN"
        elif a >= 0.98 and s >= 0.4:               fp = "LAYERED"
        elif a < 0.80:                              fp = "CYCLIC"
        elif c < 0.5:                               fp = "LOW_COHESION"
        elif s < 0.3:                               fp = "FLAT"
        else:                                       fp = "MODERATE"
        fps[fp] = fps.get(fp, 0) + 1

    lines = [
        f"# Benchmark Totalny — Iteracja {iter_n}",
        f"",
        f"- generated: `{datetime.now(timezone.utc).isoformat()}`",
        f"- repos_ok: **{len(ok)}**",
        f"- z bug lead time: {sum(1 for r in ok if r.get('bug_lead_time'))}",
        f"- AGQ mean: `{round(statistics.mean(agq_vals), 4) if agq_vals else 'n/a'}`",
        f"- AGQ std: `{round(statistics.pstdev(agq_vals), 4) if agq_vals else 'n/a'}`",
        "",
        "## AGQ per język",
        "| Język | n | mean | std | min | max |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for lang in ["Python", "Java", "Go", "TypeScript"]:
        vals = by_lang.get(lang, [])
        if vals:
            lines.append(
                f"| {lang} | {len(vals)} "
                f"| {statistics.mean(vals):.4f} "
                f"| {statistics.stdev(vals) if len(vals)>1 else 0:.4f} "
                f"| {min(vals):.4f} | {max(vals):.4f} |")

    lines += [
        "", "## Fingerprints",
        "| Pattern | n | % |",
        "|---|---:|---:|",
    ]
    for fp, n in sorted(fps.items(), key=lambda x: -x[1]):
        lines.append(f"| {fp} | {n} | {n/len(ok)*100:.1f}% |")

    if corrs:
        lines += [
            "", "## Korelacje",
            "| Predyktor | → Cel | r_s | p | n | Sig | Siła |",
            "|---|---|---:|---:|---:|---|---|",
        ]
        for c in corrs[:15]:
            sig = ("***" if c["p"]<0.001 else "**" if c["p"]<0.01
                   else "*" if c["p"]<0.05 else "")
            lines.append(
                f"| {c['predictor']} | {c['target']} "
                f"| {c['r_s']:+.4f} | {c['p']:.4f} "
                f"| {c['n']} | {sig} | {c['strength']} |")

    lines += [
        "", "## Wyniki per repo (top 50 AGQ)",
        "| Repo | Lang | AGQ | Acy | Stab | Coh | Mod | Nodes | BugMedian |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    top = sorted(ok,
                 key=lambda x: (x.get("agq") or {}).get("agq_score", 0),
                 reverse=True)[:50]
    for r in top:
        a = r.get("agq") or {}
        b = r.get("bug_lead_time") or {}
        lines.append(
            f"| {r['name']} | {r['lang']} "
            f"| {a.get('agq_score','-')} "
            f"| {a.get('acyclicity','-')} "
            f"| {a.get('stability','-')} "
            f"| {a.get('cohesion','-')} "
            f"| {a.get('modularity','-')} "
            f"| {a.get('nodes','-')} "
            f"| {b.get('median_lead_days','-')} |")

    return "\n".join(lines) + "\n"


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    cpu = os.cpu_count() or 4

    parser = argparse.ArgumentParser(
        description="QSE Fast Benchmark — sparse clone + multithreaded + auto-push")
    parser.add_argument("--repos",
                        default="scripts/repos_experiment_total.json")
    parser.add_argument("--workers",    type=int,
                        default=int(os.environ.get("WORKERS", cpu)))
    parser.add_argument("--disk-slots", type=int,
                        default=int(os.environ.get("DISK_SLOTS", 0)))
    parser.add_argument("--push-every", type=int,
                        default=int(os.environ.get("PUSH_EVERY", 10)))
    parser.add_argument("--output-dir",
                        default="artifacts/experiment_total")
    parser.add_argument("--iter",       type=int,
                        default=int(os.environ.get("ITER", 4)))
    parser.add_argument("--lang",       default=os.environ.get("LANG_FILTER"))
    parser.add_argument("--limit",      type=int,
                        default=int(os.environ.get("LIMIT", 0)) or None)
    parser.add_argument("--resume",     action="store_true")
    parser.add_argument("--no-lead-time", action="store_true")
    parser.add_argument("--scratch",    default="/tmp/qse_fast")
    args = parser.parse_args()

    # Domyślny disk_slots = workers × 2
    disk_slots = args.disk_slots or args.workers * 2

    scratch_dir = Path(args.scratch)
    output_dir  = Path(args.output_dir) / f"iter_{args.iter}"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Czyść stary scratch żeby nie zostawiać resztek po poprzednim runie
    for d in scratch_dir.iterdir():
        shutil.rmtree(d, ignore_errors=True)

    checkpoint = Checkpoint(
        output_dir / "checkpoint.jsonl",
        output_dir,
        push_every=args.push_every,
        iter_n=args.iter,
    )

    # Wczytaj listę repo
    repo_list = json.loads(Path(args.repos).read_text())
    if args.lang:
        repo_list = [r for r in repo_list if r.get("lang") == args.lang]
    if args.limit:
        repo_list = repo_list[:args.limit]

    todo = [r for r in repo_list if not checkpoint.is_done(r["name"])]
    done_already = len(repo_list) - len(todo)

    # Sprawdź rate limit GitHub
    rl = subprocess.run(
        ["gh", "api", "rate_limit",
         "--jq", '"\(.resources.core.remaining)/\(.resources.core.limit)"'],
        capture_output=True, text=True, timeout=10)
    rl_str = rl.stdout.strip() if rl.returncode == 0 else "unknown"

    # Banner
    _p(f"\n{_B}{'═'*65}{_N}")
    _p(f"{_B}  QSE Fast Benchmark — iteracja {args.iter}{_N}")
    _p(f"{_B}{'═'*65}{_N}")
    _p(f"  Repo:          {len(repo_list)} ({done_already} gotowych, {len(todo)} do zrobienia)")
    _p(f"  Workers:       {args.workers}")
    _p(f"  Disk slots:    {disk_slots} (max repo naraz na dysku)")
    _p(f"  Auto-push co:  {args.push_every} repo")
    _p(f"  Lang:          {args.lang or 'wszystkie'}")
    _p(f"  GitHub API:    {rl_str} req remaining")
    _p(f"  Scratch:       {scratch_dir}")
    _p(f"  Checkpoint:    {output_dir}/checkpoint.jsonl")
    est_min = len(todo) * 25 // 60 // args.workers
    _p(f"  Szacowany czas: ~{est_min}min przy {args.workers} workerach")
    _p()

    if not todo:
        _p(f"  {_G}Wszystkie repo w checkpoincie. Generuję raport...{_N}")
    else:
        # Inicjalizacja komponentów
        disk_sem   = threading.Semaphore(disk_slots)
        cleanup    = CleanupWorker(disk_sem)
        scan_queue: Queue = Queue()
        progress   = Progress(len(todo))

        for r in todo:
            scan_queue.put(r)

        _p(f"{_C}  Startuję {args.workers} workerów + 1 cleanup worker...{_N}\n")

        # Uruchom scanner workery
        threads = []
        for i in range(args.workers):
            t = threading.Thread(
                target=scanner_worker,
                args=(scan_queue, checkpoint, progress,
                      cleanup, disk_sem, scratch_dir,
                      args.no_lead_time, i + 1),
                daemon=True,
                name=f"Scanner-{i+1}",
            )
            t.start()
            threads.append(t)

        # Czekaj na zakończenie skanowania
        scan_queue.join()
        for t in threads:
            t.join(timeout=5)

        # Zatrzymaj cleanup worker i poczekaj aż wyczyści wszystko
        cleanup.stop()

        elapsed = int(time.time() - progress.t0)
        _p(f"\n{_B}{'═'*65}{_N}")
        _p(f"  {_G}Skanowanie zakończone!{_N}")
        _p(f"  OK:    {progress.ok}")
        _p(f"  FAIL:  {progress.failed}")
        _p(f"  Skip:  {progress.skipped}")
        _p(f"  Czas:  {elapsed//60}m{elapsed%60:02d}s")
        _p(f"  Speed: {progress.ok / max(elapsed/60, 0.1):.1f} repo/min")

    # Generuj końcowy raport
    all_results = checkpoint.load_all()
    ok_results  = [r for r in all_results if r.get("status") == "ok"]
    agq_vals    = [r["agq"]["agq_score"] for r in ok_results
                   if (r.get("agq") or {}).get("agq_score") is not None]

    _p(f"\n{_C}  Obliczam korelacje ({len(ok_results)} repo)...{_N}")
    corrs = correlations(ok_results)

    if corrs:
        _p(f"\n  {'Predyktor':15} {'→ Cel':22} {'r_s':>7} {'p':>7} {'n':>4}  Sig")
        _p(f"  {'-'*65}")
        for c in corrs[:10]:
            sig = ("***" if c["p"]<0.001 else "** " if c["p"]<0.01
                   else "*  " if c["p"]<0.05 else "   ")
            _p(f"  {c['predictor']:15} → {c['target']:22} "
               f"{c['r_s']:+7.4f} {c['p']:7.4f} {c['n']:4}  {sig} {c['strength']}")

    # Zapisz pliki wyników
    report_dict = {
        "generated_at":      datetime.now(timezone.utc).isoformat(),
        "iter":              args.iter,
        "repos_total":       len(repo_list),
        "repos_ok":          len(ok_results),
        "repos_failed":      len([r for r in all_results if r.get("status") != "ok"]),
        "repos_with_bug_lt": sum(1 for r in ok_results if r.get("bug_lead_time")),
        "agq_mean":  round(statistics.mean(agq_vals), 4) if agq_vals else None,
        "agq_std":   round(statistics.pstdev(agq_vals), 4) if agq_vals else None,
        "correlations": corrs,
        "results":      ok_results,
    }

    (output_dir / "results.json").write_text(
        json.dumps(report_dict, indent=2))
    (output_dir / "results.md").write_text(
        make_report(all_results, corrs, args.iter))
    (output_dir / "correlations.json").write_text(
        json.dumps(corrs, indent=2))

    # Finalny push
    _p(f"\n{_C}  Finalny push do GitHub...{_N}")
    checkpoint.final_push()

    _p(f"\n  {_G}Zapisano:{_N}")
    _p(f"    {output_dir}/results.json")
    _p(f"    {output_dir}/results.md")
    _p(f"    {output_dir}/checkpoint.jsonl")
    _p(f"\n  {_G}GitHub:{_N}")
    _p(f"    https://github.com/PiotrGry/qse-pkg/tree/perplexity/{output_dir}\n")


if __name__ == "__main__":
    main()
