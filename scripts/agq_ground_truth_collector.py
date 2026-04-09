#!/usr/bin/env python3
"""Collect architectural ground truth metrics for AGQ benchmark repos.

Enriches existing benchmark JSON with:
1) Bugfix Blast Radius - files/dirs/packages touched per bugfix commit.
2) GitHub Bug Issues - issue counts, MTTR from GitHub API.
3) Composite architectural defect score - rank-normalized aggregate.

Usage:
    python3 scripts/agq_ground_truth_collector.py \
        --input-json artifacts/benchmark/agq_oss30_full.json \
        --repos-dir /tmp/agq_oss_30 \
        --output-json artifacts/benchmark/agq_oss30_ground_truth.json \
        --bugfix-since "2 years ago"
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

BUGFIX_RE = re.compile(r"\b(fix|bug|regress|hotfix|issue|patch)\b", re.IGNORECASE)
TEST_PATH_RE = re.compile(r"(^|/)tests?/|/testing/|conftest\.py$")
SKIP_FILES = {"setup.py", "setup.cfg", "noxfile.py", "fabfile.py"}
COMMIT_SEP = "---COMMIT_SEP---"


def _run(
    cmd: Sequence[str],
    cwd: Optional[Path] = None,
    timeout_s: int = 300,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(cmd),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )


def _float(x: object) -> Optional[float]:
    if isinstance(x, (int, float)):
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    return None


def _percentile(vals: Sequence[float], pct: float) -> float:
    s = sorted(vals)
    idx = pct / 100.0 * (len(s) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(s) - 1)
    frac = idx - lo
    return s[lo] * (1 - frac) + s[hi] * frac


# ---------------------------------------------------------------------------
# Pearson / Spearman / p-value (self-contained, no scipy)
# ---------------------------------------------------------------------------

def _pearson(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    mx = statistics.mean(xs)
    my = statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    den = denx * deny
    if den == 0.0:
        return None
    return num / den


def _ranks(xs: Sequence[float]) -> List[float]:
    indexed = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(indexed):
        j = i
        while j < len(indexed) and xs[indexed[j]] == xs[indexed[i]]:
            j += 1
        avg_rank = (i + j - 1) / 2.0 + 1.0
        for k in range(i, j):
            ranks[indexed[k]] = avg_rank
        i = j
    return ranks


def _spearman(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    return _pearson(_ranks(xs), _ranks(ys))


def _betai(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    if x > (a + 1.0) / (a + b + 2.0):
        return 1.0 - _betai(b, a, 1.0 - x)
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x)) / a
    f = 1.0
    c = 1.0
    d = 1.0 - (a + b) * x / (a + 1.0)
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    f = d
    for m in range(1, 200):
        num = m * (b - m) * x / ((a + 2.0 * m - 1.0) * (a + 2.0 * m))
        d = 1.0 + num * d
        if abs(d) < 1e-30:
            d = 1e-30
        d = 1.0 / d
        c = 1.0 + num / c
        if abs(c) < 1e-30:
            c = 1e-30
        f *= d * c
        num = -(a + m) * (a + b + m) * x / ((a + 2.0 * m) * (a + 2.0 * m + 1.0))
        d = 1.0 + num * d
        if abs(d) < 1e-30:
            d = 1e-30
        d = 1.0 / d
        c = 1.0 + num / c
        if abs(c) < 1e-30:
            c = 1e-30
        delta = d * c
        f *= delta
        if abs(delta - 1.0) < 1e-10:
            break
    return front * f


def _p_value(r: Optional[float], n: int) -> Optional[float]:
    if r is None or n < 3:
        return None
    r2 = r * r
    if r2 >= 1.0:
        return 0.0
    df = n - 2
    t_stat = abs(r) * math.sqrt(df / (1.0 - r2))
    x = df / (df + t_stat * t_stat)
    return _betai(0.5 * df, 0.5, x)


# ---------------------------------------------------------------------------
# Bugfix Blast Radius
# ---------------------------------------------------------------------------

def _find_python_root(repo_path: Path, repo_name: str) -> Path:
    candidates = [
        repo_path / "src" / repo_name,
        repo_path / "src",
        repo_path / repo_name,
        repo_path,
    ]
    for candidate in candidates:
        if candidate.is_dir():
            for _root, _dirs, files in os.walk(candidate):
                if any(f.endswith(".py") for f in files):
                    return candidate
    return repo_path


def _bugfix_blast_radius(
    repo_path: Path,
    source_root: Path,
    since: str,
) -> Optional[Dict[str, object]]:
    """Compute blast radius metrics for bugfix commits."""
    proc = _run(
        [
            "git", "-C", str(repo_path),
            "log", "--no-merges",
            "--since", since,
            f"--pretty={COMMIT_SEP}%H|||%s",
            "--name-only",
        ],
        timeout_s=120,
    )
    if proc.returncode != 0:
        return None

    output = proc.stdout
    if not output.strip():
        return None

    # Parse commits: split by COMMIT_SEP, extract SHA+subject and file list
    source_root_rel = os.path.relpath(str(source_root), str(repo_path))
    if source_root_rel == ".":
        source_root_rel = ""

    commits_raw = output.split(COMMIT_SEP)
    bugfix_file_counts: List[int] = []
    bugfix_dir_counts: List[int] = []
    bugfix_pkg_counts: List[int] = []
    total_bugfix = 0
    cross_package = 0
    wide_fixes = 0

    for block in commits_raw:
        block = block.strip()
        if not block:
            continue

        lines = block.split("\n")
        if not lines:
            continue

        # First line: SHA|||subject
        header = lines[0]
        sep_idx = header.find("|||")
        if sep_idx < 0:
            continue
        subject = header[sep_idx + 3:]

        if not BUGFIX_RE.search(subject):
            continue

        total_bugfix += 1

        # Remaining lines: file paths (all source files, not just .py)
        files = [f.strip() for f in lines[1:] if f.strip()]

        # Filter out test files, setup files, docs, CI configs
        src_files = []
        for fpath in files:
            basename = os.path.basename(fpath)
            if basename in SKIP_FILES:
                continue
            if TEST_PATH_RE.search(fpath):
                continue
            # Skip non-source files (docs, CI, configs at repo root)
            if fpath.startswith(("docs/", ".github/", ".circleci/")):
                continue
            if basename in (".gitignore", ".gitattributes", "LICENSE",
                            "MANIFEST.in", "Makefile", "Dockerfile"):
                continue
            # Skip binary/media files
            ext = os.path.splitext(fpath)[1].lower()
            if ext in (".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
                        ".woff", ".woff2", ".ttf", ".eot", ".pyc", ".pyo",
                        ".so", ".dylib", ".whl", ".egg"):
                continue
            src_files.append(fpath)

        if not src_files:
            continue

        # Compute per-commit metrics
        n_files = len(src_files)
        dirs = set()
        packages = set()
        for fpath in src_files:
            dirs.add(os.path.dirname(fpath))
            # Package = first directory component under source root
            if source_root_rel:
                rel = fpath[len(source_root_rel):].lstrip("/")
            else:
                rel = fpath
            parts = rel.split("/")
            if len(parts) > 1:
                packages.add(parts[0])
            else:
                packages.add("__root__")

        bugfix_file_counts.append(n_files)
        bugfix_dir_counts.append(len(dirs))
        bugfix_pkg_counts.append(len(packages))
        if len(packages) > 1:
            cross_package += 1
        if n_files > 5:
            wide_fixes += 1

    n_analyzed = len(bugfix_file_counts)
    if n_analyzed < 3:
        return {
            "n_bugfix_total": total_bugfix,
            "n_analyzed": n_analyzed,
            "insufficient_data": True,
        }

    return {
        "n_bugfix_total": total_bugfix,
        "n_analyzed": n_analyzed,
        "insufficient_data": False,
        "mean_files_per_fix": round(statistics.mean(bugfix_file_counts), 3),
        "median_files_per_fix": round(statistics.median(bugfix_file_counts), 3),
        "p90_files_per_fix": round(_percentile(bugfix_file_counts, 90), 3),
        "max_files_per_fix": max(bugfix_file_counts),
        "mean_dirs_per_fix": round(statistics.mean(bugfix_dir_counts), 3),
        "median_dirs_per_fix": round(statistics.median(bugfix_dir_counts), 3),
        "mean_packages_per_fix": round(statistics.mean(bugfix_pkg_counts), 3),
        "median_packages_per_fix": round(statistics.median(bugfix_pkg_counts), 3),
        "pct_cross_package_fixes": round(cross_package / n_analyzed, 4),
        "pct_wide_fixes": round(wide_fixes / n_analyzed, 4),
    }


# ---------------------------------------------------------------------------
# GitHub Bug Issues
# ---------------------------------------------------------------------------

class GitHubClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.base_url = "https://api.github.com"

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "qse-benchmark/1.0",
        }
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def request_json(
        self,
        path: str,
        params: Optional[Dict[str, str]] = None,
    ) -> Tuple[object, Dict[str, str]]:
        query = ""
        if params:
            query = "?" + urlencode(params)
        url = f"{self.base_url}{path}{query}"
        req = Request(url=url, method="GET", headers=self._headers())
        try:
            with urlopen(req, timeout=30) as resp:
                headers = {k.lower(): v for k, v in resp.getheaders()}
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else [], headers
        except HTTPError as exc:
            if exc.code == 404:
                return [], {}
            if exc.code == 403:
                # Rate limit
                return [], {"x-ratelimit-remaining": "0"}
            payload = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"GitHub API {path} failed ({exc.code}): {payload[:200]}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(f"GitHub API {path} network error: {exc}") from exc

    def get_all_pages(
        self,
        path: str,
        params: Optional[Dict[str, str]] = None,
        max_pages: int = 10,
    ) -> List[Dict]:
        all_items: List[Dict] = []
        current_params = dict(params or {})
        current_params.setdefault("per_page", "100")

        for _page in range(max_pages):
            data, headers = self.request_json(path, current_params)
            if not isinstance(data, list):
                break
            all_items.extend(data)
            if len(data) < int(current_params.get("per_page", "100")):
                break

            # Parse Link header for next page
            link_header = headers.get("link", "")
            next_url = None
            for part in link_header.split(","):
                if 'rel="next"' in part:
                    start = part.find("<") + 1
                    end = part.find(">")
                    if start > 0 and end > start:
                        next_url = part[start:end]
                    break

            if not next_url:
                break

            # Extract page number from next_url
            page_match = re.search(r"[?&]page=(\d+)", next_url)
            if page_match:
                current_params["page"] = page_match.group(1)
            else:
                break

            # Rate limit check
            remaining = headers.get("x-ratelimit-remaining", "100")
            if remaining == "0":
                print("  [WARN] GitHub rate limit reached, stopping pagination")
                break

        return all_items


def _parse_owner_repo(url: str) -> Optional[Tuple[str, str]]:
    """Extract (owner, repo) from a GitHub URL."""
    cleaned = url.rstrip("/").removesuffix(".git")
    parts = cleaned.split("/")
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    return None


def _github_bug_issues(
    client: GitHubClient,
    repo_url: str,
    ncloc: Optional[float],
) -> Optional[Dict[str, object]]:
    parsed = _parse_owner_repo(repo_url)
    if not parsed:
        return None

    owner, repo = parsed
    path = f"/repos/{owner}/{repo}/issues"

    try:
        issues = client.get_all_pages(
            path,
            params={"labels": "bug", "state": "all", "per_page": "100"},
            max_pages=10,
        )
    except RuntimeError as exc:
        print(f"  [WARN] GitHub API failed for {owner}/{repo}: {exc}")
        return None

    # Filter out pull requests (GitHub returns PRs in issues endpoint)
    bug_issues = [i for i in issues if "pull_request" not in i]

    total = len(bug_issues)
    opened = sum(1 for i in bug_issues if i.get("state") == "open")
    closed = sum(1 for i in bug_issues if i.get("state") == "closed")

    # MTTR: median time from created_at to closed_at (for closed issues)
    close_times_days: List[float] = []
    for iss in bug_issues:
        if iss.get("state") != "closed" or not iss.get("closed_at"):
            continue
        try:
            created = datetime.fromisoformat(iss["created_at"].replace("Z", "+00:00"))
            closed_at = datetime.fromisoformat(iss["closed_at"].replace("Z", "+00:00"))
            delta = (closed_at - created).total_seconds() / 86400.0
            if delta >= 0:
                close_times_days.append(delta)
        except (ValueError, KeyError):
            continue

    result: Dict[str, object] = {
        "bug_issues_total": total,
        "bug_issues_open": opened,
        "bug_issues_closed": closed,
        "bug_issues_per_kloc": None,
        "median_close_time_days": None,
    }

    if ncloc and ncloc > 0:
        result["bug_issues_per_kloc"] = round(total / (ncloc / 1000.0), 3)

    if close_times_days:
        result["median_close_time_days"] = round(
            statistics.median(close_times_days), 2
        )

    return result


# ---------------------------------------------------------------------------
# Composite Architectural Defect Score
# ---------------------------------------------------------------------------

def _rank_normalize(values: List[Optional[float]]) -> List[Optional[float]]:
    """Rank-normalize non-None values to [0, 1]. None stays None."""
    valid_indices = [i for i, v in enumerate(values) if v is not None]
    if len(valid_indices) < 2:
        return [None] * len(values)

    valid_vals = [values[i] for i in valid_indices]
    ranked = _ranks(valid_vals)
    n = len(valid_vals)
    normalized = [(r - 1.0) / (n - 1.0) for r in ranked]

    result: List[Optional[float]] = [None] * len(values)
    for idx, norm_val in zip(valid_indices, normalized):
        result[idx] = norm_val
    return result


def _compute_composite_scores(
    rows: List[Dict[str, object]],
) -> List[Optional[float]]:
    """Compute composite arch_defect_score for each row. Higher = worse."""

    # Component 1: log1p(mean_files_per_fix)
    comp1 = []
    for r in rows:
        br = r.get("blast_radius")
        if isinstance(br, dict) and not br.get("insufficient_data"):
            v = _float(br.get("mean_files_per_fix"))
            comp1.append(math.log1p(v) if v is not None else None)
        else:
            comp1.append(None)

    # Component 2: pct_cross_package_fixes (already 0-1 ish)
    comp2 = []
    for r in rows:
        br = r.get("blast_radius")
        if isinstance(br, dict) and not br.get("insufficient_data"):
            comp2.append(_float(br.get("pct_cross_package_fixes")))
        else:
            comp2.append(None)

    # Component 3: bug_issues_per_kloc
    comp3 = []
    for r in rows:
        gh = r.get("github")
        if isinstance(gh, dict):
            comp3.append(_float(gh.get("bug_issues_per_kloc")))
        else:
            comp3.append(None)

    # Rank-normalize each component
    norm1 = _rank_normalize(comp1)
    norm2 = _rank_normalize(comp2)
    norm3 = _rank_normalize(comp3)

    # Equal-weight average (skip None components)
    scores: List[Optional[float]] = []
    for i in range(len(rows)):
        components = [v for v in [norm1[i], norm2[i], norm3[i]] if v is not None]
        if len(components) >= 2:
            scores.append(round(statistics.mean(components), 4))
        else:
            scores.append(None)

    return scores


# ---------------------------------------------------------------------------
# Thesis Checks
# ---------------------------------------------------------------------------

def _pair_values_from_rows(
    rows: List[Dict], key_x: str, key_y: str,
) -> Tuple[List[float], List[float]]:
    xs, ys = [], []
    for r in rows:
        vx = _float(r.get(key_x))
        vy = _float(r.get(key_y))
        if vx is not None and vy is not None:
            xs.append(vx)
            ys.append(vy)
    return xs, ys


def _evaluate_theses(
    flat_rows: List[Dict],
) -> List[Dict[str, object]]:
    theses = []

    # T6: |r(AGQ, pct_cross_pkg)| > |r(AGQ, bugfix_ratio)|
    xs_blast, ys_blast = _pair_values_from_rows(
        flat_rows, "agq_score", "pct_cross_package_fixes"
    )
    xs_bugfix, ys_bugfix = _pair_values_from_rows(
        flat_rows, "agq_score", "bugfix_ratio"
    )
    r_blast = _spearman(xs_blast, ys_blast)
    r_bugfix = _spearman(xs_bugfix, ys_bugfix)
    p_blast = _p_value(r_blast, len(xs_blast))

    abs_blast = abs(r_blast) if r_blast is not None else 0.0
    abs_bugfix = abs(r_bugfix) if r_bugfix is not None else 0.0
    theses.append({
        "id": "T6",
        "title": "Blast radius correlates with AGQ stronger than bugfix_ratio",
        "passed": abs_blast > abs_bugfix,
        "evidence": (
            f"|r_s(AGQ, pct_cross_pkg)|={abs_blast:.4f} "
            f"vs |r_s(AGQ, bugfix_ratio)|={abs_bugfix:.4f}, "
            f"n_blast={len(xs_blast)}, p_blast={p_blast}"
        ),
    })

    # T7: Composite arch_quality_proxy yields significant correlation with AGQ
    xs_comp, ys_comp = _pair_values_from_rows(
        flat_rows, "agq_score", "arch_quality_proxy"
    )
    r_comp = _spearman(xs_comp, ys_comp)
    p_comp = _p_value(r_comp, len(xs_comp))

    theses.append({
        "id": "T7",
        "title": "Composite arch_quality_proxy correlates significantly with AGQ",
        "passed": p_comp is not None and p_comp < 0.10,
        "evidence": (
            f"spearman={r_comp:.4f}, p={p_comp:.4f}, n={len(xs_comp)}"
            if r_comp is not None else "insufficient data"
        ),
    })

    # T8: mean_files_per_fix negatively correlates with AGQ
    xs_fpf, ys_fpf = _pair_values_from_rows(
        flat_rows, "agq_score", "mean_files_per_fix"
    )
    r_fpf = _spearman(xs_fpf, ys_fpf)
    p_fpf = _p_value(r_fpf, len(xs_fpf))
    theses.append({
        "id": "T8",
        "title": "mean_files_per_fix negatively correlates with AGQ",
        "passed": r_fpf is not None and r_fpf < 0,
        "evidence": (
            f"spearman={r_fpf:.4f}, p={p_fpf:.4f}, n={len(xs_fpf)}"
            if r_fpf is not None else "insufficient data"
        ),
    })

    return theses


# ---------------------------------------------------------------------------
# Inline Correlation Summary
# ---------------------------------------------------------------------------

def _corr_entry(
    flat_rows: List[Dict], x_key: str, y_key: str,
) -> Dict[str, object]:
    xs, ys = _pair_values_from_rows(flat_rows, x_key, y_key)
    r_p = _pearson(xs, ys)
    r_s = _spearman(xs, ys)
    return {
        "x": x_key,
        "y": y_key,
        "n": len(xs),
        "pearson": round(r_p, 4) if r_p is not None else None,
        "pearson_p": round(_p_value(r_p, len(xs)), 4) if _p_value(r_p, len(xs)) is not None else None,
        "spearman": round(r_s, 4) if r_s is not None else None,
        "spearman_p": round(_p_value(r_s, len(xs)), 4) if _p_value(r_s, len(xs)) is not None else None,
    }


def _build_correlation_matrix(flat_rows: List[Dict]) -> List[Dict]:
    agq_metrics = ["agq_score", "modularity", "acyclicity", "stability", "cohesion"]
    gt_targets = [
        "bugfix_ratio",
        "mean_files_per_fix",
        "median_files_per_fix",
        "pct_cross_package_fixes",
        "pct_wide_fixes",
        "mean_packages_per_fix",
        "bug_issues_per_kloc",
        "median_close_time_days",
        "arch_quality_proxy",
    ]
    matrix = []
    for agq_m in agq_metrics:
        for target in gt_targets:
            matrix.append(_corr_entry(flat_rows, agq_m, target))
    return matrix


# ---------------------------------------------------------------------------
# Markdown Report
# ---------------------------------------------------------------------------

def _generate_markdown(
    results: List[Dict],
    theses: List[Dict],
    correlation_matrix: List[Dict],
    config: Dict,
) -> str:
    lines = [
        "# AGQ Ground Truth Analysis",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Source: `{config.get('input_json', 'n/a')}`",
        "",
        "## Thesis Checks",
        "",
        "| ID | Thesis | Passed | Evidence |",
        "|---|---|---|---|",
    ]
    for t in theses:
        passed = "PASS" if t["passed"] else "FAIL"
        lines.append(f"| {t['id']} | {t['title']} | {passed} | {t['evidence']} |")
    lines.append("")

    # Per-repo blast radius table
    lines.extend([
        "## Per-Repo Blast Radius",
        "",
        "| Repo | AGQ | Files/fix | Dirs/fix | Pkgs/fix | Cross-pkg% | Wide% | GH bugs | MTTR(d) | Defect Score |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for r in sorted(results, key=lambda x: x.get("agq_score", 0)):
        br = r.get("blast_radius", {}) or {}
        gh = r.get("github", {}) or {}
        insuf = br.get("insufficient_data", True) if br else True

        agq_s = f"{r.get('agq_score', 0):.3f}" if r.get("agq_score") else "n/a"
        fpf = f"{br['mean_files_per_fix']:.1f}" if not insuf and br.get("mean_files_per_fix") else "n/a"
        dpf = f"{br['mean_dirs_per_fix']:.1f}" if not insuf and br.get("mean_dirs_per_fix") else "n/a"
        ppf = f"{br['mean_packages_per_fix']:.1f}" if not insuf and br.get("mean_packages_per_fix") else "n/a"
        cpkg = f"{br['pct_cross_package_fixes']*100:.1f}%" if not insuf and br.get("pct_cross_package_fixes") is not None else "n/a"
        wide = f"{br['pct_wide_fixes']*100:.1f}%" if not insuf and br.get("pct_wide_fixes") is not None else "n/a"
        gh_bugs = str(gh.get("bug_issues_total", "n/a")) if gh else "n/a"
        mttr = f"{gh['median_close_time_days']:.1f}" if gh and gh.get("median_close_time_days") is not None else "n/a"
        ds = f"{r['arch_defect_score']:.3f}" if r.get("arch_defect_score") is not None else "n/a"

        lines.append(
            f"| {r['name']} | {agq_s} | {fpf} | {dpf} | {ppf} | {cpkg} | {wide} | {gh_bugs} | {mttr} | {ds} |"
        )
    lines.append("")

    # Correlation matrix
    lines.extend([
        "## Correlation Matrix: AGQ vs Ground Truth",
        "",
        "| AGQ metric | Target | n | Pearson | p | Spearman | p |",
        "|---|---|---:|---:|---:|---:|---:|",
    ])
    for c in correlation_matrix:
        r_p = f"{c['pearson']:.4f}" if c["pearson"] is not None else "n/a"
        p_p = f"{c['pearson_p']:.4f}" if c["pearson_p"] is not None else "n/a"
        r_s = f"{c['spearman']:.4f}" if c["spearman"] is not None else "n/a"
        p_s = f"{c['spearman_p']:.4f}" if c["spearman_p"] is not None else "n/a"
        lines.append(
            f"| {c['x']} | {c['y']} | {c['n']} | {r_p} | {p_p} | {r_s} | {p_s} |"
        )
    lines.append("")

    # Top correlations (|spearman| > 0.2)
    significant = [
        c for c in correlation_matrix
        if c["spearman"] is not None and abs(c["spearman"]) > 0.2
    ]
    significant.sort(key=lambda c: abs(c["spearman"] or 0), reverse=True)
    if significant:
        lines.extend([
            "## Top Correlations (|r_s| > 0.2)",
            "",
            "| Pair | Spearman | p-value | Strength |",
            "|---|---:|---:|---|",
        ])
        for c in significant:
            abs_r = abs(c["spearman"])
            strength = (
                "strong" if abs_r >= 0.6 else
                "moderate" if abs_r >= 0.4 else
                "weak"
            )
            lines.append(
                f"| {c['x']} vs {c['y']} | {c['spearman']:.4f} | "
                f"{c['spearman_p']:.4f} | {strength} |"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect architectural ground truth for AGQ benchmark."
    )
    parser.add_argument(
        "--input-json",
        default="artifacts/benchmark/agq_oss30_full.json",
        help="Existing benchmark JSON to enrich.",
    )
    parser.add_argument(
        "--repos-dir",
        default="/tmp/agq_oss_30",
        help="Directory containing cloned repos.",
    )
    parser.add_argument(
        "--output-json",
        default="artifacts/benchmark/agq_oss30_ground_truth.json",
        help="Output enriched JSON.",
    )
    parser.add_argument(
        "--output-md",
        default="",
        help="Output Markdown report (default: same as --output-json with .md).",
    )
    parser.add_argument(
        "--github-token",
        default=os.environ.get("GITHUB_TOKEN", ""),
        help="GitHub personal access token (default: $GITHUB_TOKEN).",
    )
    parser.add_argument(
        "--no-github",
        action="store_true",
        help="Skip GitHub API calls.",
    )
    parser.add_argument(
        "--bugfix-since",
        default="2 years ago",
        help="Time window for bugfix analysis.",
    )
    args = parser.parse_args()

    inp = Path(args.input_json)
    if not inp.exists():
        print(f"ERROR: Input file not found: {inp}")
        sys.exit(1)

    repos_dir = Path(args.repos_dir)
    data = json.loads(inp.read_text())
    raw_results = [r for r in data.get("results", []) if "error" not in r]

    print(f"Loaded {len(raw_results)} repos from {inp}")

    # GitHub client
    github: Optional[GitHubClient] = None
    if not args.no_github and args.github_token:
        github = GitHubClient(token=args.github_token)
        print("GitHub API enabled (token provided)")
    elif not args.no_github:
        github = GitHubClient(token=None)
        print("GitHub API enabled (no token - 60 req/hour limit)")
    else:
        print("GitHub API disabled (--no-github)")

    # Process each repo
    enriched_results: List[Dict[str, object]] = []
    for i, row in enumerate(raw_results):
        name = row["name"]
        url = row.get("url", "")
        print(f"\n[{i+1}/{len(raw_results)}] {name}")

        repo_path = repos_dir / name
        if not repo_path.exists():
            print(f"  SKIP: repo path not found: {repo_path}")
            enriched_results.append({
                "name": name,
                "url": url,
                "error": f"repo path not found: {repo_path}",
            })
            continue

        # Get AGQ info from existing data
        agq = row.get("agq", {})
        run1 = agq.get("run1", {}) if isinstance(agq, dict) else {}
        agq_score = agq.get("score_mean")

        # Find source root
        source_root_from_data = run1.get("source_root", "")
        if source_root_from_data:
            source_root = Path(source_root_from_data)
            if not source_root.exists():
                source_root = _find_python_root(repo_path, name)
        else:
            source_root = _find_python_root(repo_path, name)

        # Blast radius
        print(f"  Computing blast radius...")
        blast = _bugfix_blast_radius(repo_path, source_root, args.bugfix_since)
        if blast and not blast.get("insufficient_data"):
            print(
                f"  Blast: {blast['n_analyzed']} commits, "
                f"mean={blast['mean_files_per_fix']:.1f} files/fix, "
                f"cross-pkg={blast['pct_cross_package_fixes']*100:.0f}%"
            )
        elif blast:
            print(f"  Blast: insufficient data ({blast.get('n_analyzed', 0)} commits)")
        else:
            print(f"  Blast: failed")

        # GitHub issues
        gh_data = None
        if github:
            print(f"  Fetching GitHub issues...")
            ncloc = None
            sonar = row.get("sonar", {})
            if isinstance(sonar, dict):
                ncloc = _float(sonar.get("ncloc"))
            gh_data = _github_bug_issues(github, url, ncloc)
            if gh_data:
                print(
                    f"  GitHub: {gh_data['bug_issues_total']} bug issues, "
                    f"MTTR={gh_data.get('median_close_time_days', 'n/a')}d"
                )
            else:
                print(f"  GitHub: no data")
            time.sleep(0.5)  # Be gentle with API

        enriched_results.append({
            "name": name,
            "url": url,
            "agq_score": agq_score,
            "agq": agq,
            "defect_proxy": row.get("defect_proxy", {}),
            "sonar": row.get("sonar", {}),
            "blast_radius": blast,
            "github": gh_data,
        })

    # Compute composite scores
    print("\nComputing composite scores...")
    scores = _compute_composite_scores(enriched_results)
    for row, score in zip(enriched_results, scores):
        if "error" not in row:
            row["arch_defect_score"] = score
            row["arch_quality_proxy"] = round(1.0 - score, 4) if score is not None else None

    # Flatten for correlation analysis
    flat_rows: List[Dict] = []
    for r in enriched_results:
        if "error" in r:
            continue
        flat: Dict[str, object] = {
            "name": r["name"],
            "agq_score": r.get("agq_score"),
        }
        agq = r.get("agq", {})
        run1 = agq.get("run1", {}) if isinstance(agq, dict) else {}
        flat["modularity"] = run1.get("modularity")
        flat["acyclicity"] = run1.get("acyclicity")
        flat["stability"] = run1.get("stability")
        flat["cohesion"] = run1.get("cohesion")

        defect = r.get("defect_proxy", {})
        if isinstance(defect, dict):
            flat["bugfix_ratio"] = defect.get("bugfix_ratio")

        br = r.get("blast_radius")
        if isinstance(br, dict) and not br.get("insufficient_data"):
            flat["mean_files_per_fix"] = br.get("mean_files_per_fix")
            flat["median_files_per_fix"] = br.get("median_files_per_fix")
            flat["pct_cross_package_fixes"] = br.get("pct_cross_package_fixes")
            flat["pct_wide_fixes"] = br.get("pct_wide_fixes")
            flat["mean_packages_per_fix"] = br.get("mean_packages_per_fix")

        gh = r.get("github")
        if isinstance(gh, dict):
            flat["bug_issues_per_kloc"] = gh.get("bug_issues_per_kloc")
            flat["median_close_time_days"] = gh.get("median_close_time_days")

        flat["arch_quality_proxy"] = r.get("arch_quality_proxy")
        flat["arch_defect_score"] = r.get("arch_defect_score")

        flat_rows.append(flat)

    # Theses
    print("Evaluating theses...")
    theses = _evaluate_theses(flat_rows)
    for t in theses:
        status = "PASS" if t["passed"] else "FAIL"
        print(f"  {t['id']}: {status} - {t['evidence']}")

    # Correlation matrix
    print("Computing correlation matrix...")
    corr_matrix = _build_correlation_matrix(flat_rows)

    # Output
    output_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_report": str(inp),
        "config": {
            "bugfix_since": args.bugfix_since,
            "github_enabled": github is not None,
            "repos_dir": str(repos_dir),
        },
        "summary": {
            "repos_processed": len(enriched_results),
            "repos_with_blast_radius": sum(
                1 for r in enriched_results
                if isinstance(r.get("blast_radius"), dict)
                and not r.get("blast_radius", {}).get("insufficient_data")
            ),
            "repos_with_github": sum(
                1 for r in enriched_results
                if isinstance(r.get("github"), dict) and r["github"]
            ),
            "repos_with_composite": sum(
                1 for r in enriched_results
                if r.get("arch_defect_score") is not None
            ),
        },
        "theses": theses,
        "results": enriched_results,
        "correlation_matrix": corr_matrix,
    }

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(output_data, indent=2, default=str) + "\n")
    print(f"\nJSON: {out_json}")

    # Markdown
    out_md_path = args.output_md or str(out_json).replace(".json", ".md")
    out_md = Path(out_md_path)
    md_content = _generate_markdown(
        enriched_results, theses, corr_matrix,
        {"input_json": str(inp)},
    )
    out_md.write_text(md_content)
    print(f"Markdown: {out_md}")

    # Summary
    print("\n=== Summary ===")
    print(f"Repos with blast radius: {output_data['summary']['repos_with_blast_radius']}")
    print(f"Repos with GitHub data: {output_data['summary']['repos_with_github']}")
    print(f"Repos with composite score: {output_data['summary']['repos_with_composite']}")
    for t in theses:
        status = "PASS" if t["passed"] else "FAIL"
        print(f"{t['id']}: {status}")


if __name__ == "__main__":
    main()
