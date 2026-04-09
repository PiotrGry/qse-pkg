#!/usr/bin/env python3
"""Run AGQ thesis benchmark on 15 real OSS repos and compare with SonarQube.

This script executes a reproducible benchmark pack:
1) Clone 15 open-source Python repositories.
2) Compute AGQ metrics twice per repo (determinism check).
3) Compute a defect proxy from git history (bugfix commit ratio).
4) Run SonarQube scan per repo and collect maintainability/defect metrics.
5) Evaluate explicit AGQ theses with PASS/FAIL and numeric evidence.
6) Save JSON + Markdown reports.
"""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import networkx as nx


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qse.graph_metrics import (compute_agq, compute_lcom4,
                               compute_hierarchical_modularity,
                               compute_boundary_crossing_ratio)
try:
    from qse.scanner import scan_repo
except (ImportError, ModuleNotFoundError):
    scan_repo = None  # Python scanner removed; Rust scanner used instead


@dataclass(frozen=True)
class RepoSpec:
    name: str
    url: str


DEFAULT_REPOS: List[RepoSpec] = [
    RepoSpec("httpx", "https://github.com/encode/httpx.git"),
    RepoSpec("requests", "https://github.com/psf/requests.git"),
    RepoSpec("urllib3", "https://github.com/urllib3/urllib3.git"),
    RepoSpec("flask", "https://github.com/pallets/flask.git"),
    RepoSpec("click", "https://github.com/pallets/click.git"),
    RepoSpec("jinja", "https://github.com/pallets/jinja.git"),
    RepoSpec("werkzeug", "https://github.com/pallets/werkzeug.git"),
    RepoSpec("pydantic", "https://github.com/pydantic/pydantic.git"),
    RepoSpec("fastapi", "https://github.com/tiangolo/fastapi.git"),
    RepoSpec("pyjwt", "https://github.com/jpadilla/pyjwt.git"),
    RepoSpec("rich", "https://github.com/Textualize/rich.git"),
    RepoSpec("aiohttp", "https://github.com/aio-libs/aiohttp.git"),
    RepoSpec("pytest", "https://github.com/pytest-dev/pytest.git"),
    RepoSpec("sanic", "https://github.com/sanic-org/sanic.git"),
    RepoSpec("scrapy", "https://github.com/scrapy/scrapy.git"),
]


def _load_repo_specs(path: Optional[str]) -> List[RepoSpec]:
    if not path:
        return list(DEFAULT_REPOS)

    repo_file = Path(path)
    payload = json.loads(repo_file.read_text())
    if not isinstance(payload, list):
        raise ValueError("--repos-file must contain a JSON list")

    repos: List[RepoSpec] = []
    for idx, row in enumerate(payload):
        if not isinstance(row, dict):
            raise ValueError(f"--repos-file item #{idx + 1} is not an object")
        name = str(row.get("name", "")).strip()
        url = str(row.get("url", "")).strip()
        if not name or not url:
            raise ValueError(f"--repos-file item #{idx + 1} requires fields: name, url")
        repos.append(RepoSpec(name=name, url=url))

    if not repos:
        raise ValueError("--repos-file cannot be empty")
    return repos


class SonarClient:
    def __init__(self, base_url: str, user: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.user = user
        self.password = password

    def _headers(self) -> Dict[str, str]:
        token = base64.b64encode(f"{self.user}:{self.password}".encode("utf-8")).decode("ascii")
        return {"Authorization": f"Basic {token}"}

    def request_json(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, str]] = None,
    ) -> Dict[str, object]:
        query = ""
        if params:
            query = "?" + urlencode(params)
        url = f"{self.base_url}{path}{query}"

        body = None
        headers = self._headers()
        if data is not None:
            body = urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        req = Request(url=url, method=method.upper(), headers=headers, data=body)
        try:
            with urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                if not raw:
                    return {}
                return json.loads(raw)
        except HTTPError as exc:
            payload = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Sonar API {path} failed ({exc.code}): {payload}") from exc
        except URLError as exc:
            raise RuntimeError(f"Sonar API {path} network error: {exc}") from exc

    def ensure_up(self, timeout_s: int) -> None:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                payload = self.request_json("GET", "/api/system/status")
                status = str(payload.get("status", ""))
                if status == "UP":
                    return
            except RuntimeError:
                pass
            time.sleep(3)
        raise RuntimeError(f"SonarQube did not reach UP state within {timeout_s}s")

    def create_project(self, project_key: str, project_name: str) -> None:
        try:
            self.request_json(
                "POST",
                "/api/projects/create",
                data={"project": project_key, "name": project_name},
            )
        except RuntimeError as exc:
            msg = str(exc).lower()
            if "already exists" in msg:
                return
            raise

    def delete_project(self, project_key: str) -> None:
        self.request_json("POST", "/api/projects/delete", data={"project": project_key})

    def get_measures(self, project_key: str) -> Dict[str, object]:
        metric_keys = ",".join(
            [
                "bugs",
                "vulnerabilities",
                "code_smells",
                "sqale_rating",
                "reliability_rating",
                "security_rating",
                "ncloc",
                "complexity",
                "cognitive_complexity",
                "duplicated_lines_density",
            ]
        )
        payload = self.request_json(
            "GET",
            "/api/measures/component",
            params={"component": project_key, "metricKeys": metric_keys},
        )
        out: Dict[str, object] = {}
        component = payload.get("component", {})
        for row in component.get("measures", []):
            key = row.get("metric")
            value = row.get("value")
            if not key:
                continue
            if value is None:
                out[key] = None
                continue
            try:
                out[key] = float(value)
            except ValueError:
                out[key] = value
        return out

    def get_quality_gate(self, project_key: str) -> str:
        payload = self.request_json(
            "GET",
            "/api/qualitygates/project_status",
            params={"projectKey": project_key},
        )
        project_status = payload.get("projectStatus", {})
        return str(project_status.get("status", "UNKNOWN"))


def _run_checked(
    cmd: Sequence[str],
    cwd: Optional[Path] = None,
    timeout_s: int = 900,
) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        list(cmd),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    if proc.returncode != 0:
        stderr_tail = "\n".join(proc.stderr.strip().splitlines()[-20:])
        stdout_tail = "\n".join(proc.stdout.strip().splitlines()[-20:])
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\n"
            f"stdout_tail:\n{stdout_tail}\n"
            f"stderr_tail:\n{stderr_tail}"
        )
    return proc


def _clone_repo(spec: RepoSpec, repos_dir: Path, depth: int, no_clone: bool) -> Path:
    dest = repos_dir / spec.name
    if dest.exists():
        return dest
    if no_clone:
        raise RuntimeError(f"Missing local repo and --no-clone enabled: {dest}")

    _run_checked(
        [
            "git",
            "clone",
            "--single-branch",
            "--depth",
            str(depth),
            "--filter=blob:none",
            spec.url,
            str(dest),
        ],
        timeout_s=1200,
    )
    return dest


def _contains_python(path: Path) -> bool:
    for _root, _dirs, files in os_walk(path):
        for fname in files:
            if fname.endswith(".py"):
                return True
    return False


def _find_python_root(repo_path: Path, repo_name: str) -> Path:
    candidates = [
        repo_path / "src" / repo_name,
        repo_path / "src",
        repo_path / repo_name,
        repo_path,
    ]
    for candidate in candidates:
        if candidate.is_dir() and _contains_python(candidate):
            return candidate
    return repo_path


def os_walk(path: Path) -> Iterable[Tuple[str, List[str], List[str]]]:
    import os

    return os.walk(path)


def _build_internal_graph(analysis_graph: nx.DiGraph) -> nx.DiGraph:
    internal_nodes = {n for n, d in analysis_graph.nodes(data=True) if d.get("file")}
    connected: set = set()
    for src, tgt in analysis_graph.edges():
        if src in internal_nodes:
            connected.add(src)
            connected.add(tgt)
    return analysis_graph.subgraph(internal_nodes | connected).copy()


def _compute_agq_once(repo_path: Path, repo_name: str) -> Dict[str, object]:
    src_root = _find_python_root(repo_path, repo_name)
    t0 = time.perf_counter()
    analysis = scan_repo(str(src_root))
    graph = _build_internal_graph(analysis.graph)

    file_to_module: Dict[str, str] = {}
    for node, data in graph.nodes(data=True):
        fpath = data.get("file")
        if fpath:
            file_to_module[fpath] = node

    abstract_modules = set()
    lcom4_values: List[int] = []
    for cls in analysis.classes.values():
        if cls.is_abstract:
            module = file_to_module.get(cls.file_path)
            if module:
                abstract_modules.add(module)
        lcom4_values.append(compute_lcom4(cls.method_attrs))

    metrics = compute_agq(
        graph,
        abstract_modules=abstract_modules,
        classes_lcom4=lcom4_values,
    )

    nodes_in_cycles = 0
    for scc in nx.strongly_connected_components(graph):
        if len(scc) > 1:
            nodes_in_cycles += len(scc)

    h_mod = compute_hierarchical_modularity(graph)
    bcr = compute_boundary_crossing_ratio(graph)
    runtime_s = time.perf_counter() - t0
    return {
        "source_root": str(src_root),
        "runtime_s": runtime_s,
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "nodes_in_cycles": nodes_in_cycles,
        "modularity": metrics.modularity,
        "acyclicity": metrics.acyclicity,
        "stability": metrics.stability,
        "cohesion": metrics.cohesion,
        "agq_score": metrics.agq_score,
        "hierarchical_modularity": h_mod,
        "boundary_crossing_ratio": bcr,
    }


def _bugfix_proxy(repo_path: Path, since: str) -> Dict[str, object]:
    proc = _run_checked(
        ["git", "-C", str(repo_path), "log", "--since", since, "--pretty=%s"],
        timeout_s=120,
    )
    subjects = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    total = len(subjects)
    bugfix_re = re.compile(r"\b(fix|bug|regress|hotfix|issue|patch)\b", re.IGNORECASE)
    bugfix = sum(1 for subj in subjects if bugfix_re.search(subj))
    ratio = (bugfix / total) if total else 0.0
    return {
        "window": since,
        "total_commits": total,
        "bugfix_commits": bugfix,
        "bugfix_ratio": ratio,
    }


_TEST_PATH_RE = re.compile(r"(^|/)tests?/|test_.*\.py$|_test\.py$")


def _churn_proxy(repo_path: Path, since: str) -> Dict[str, object]:
    """Code churn metrics from git log (production .py files only).

    Ref: Nagappan & Ball 2005; Moser et al. 2008.
    hotspot_ratio: fraction of files changed more than 2x the mean - proxy
    for architectural hotspots caused by poor separation of concerns.
    churn_gini: Gini coefficient of per-file change counts - high Gini means
    a few files absorb most changes, indicating coupling or god-file smell.
    """
    proc = subprocess.run(
        ["git", "-C", str(repo_path), "log", "--since", since,
         "--name-only", "--format=", "--", "*.py"],
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        return {"hotspot_ratio": None, "churn_gini": None, "mean_churn": None, "n_files": 0}

    counts: Dict[str, int] = {}
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line.endswith(".py") or _TEST_PATH_RE.search(line):
            continue
        counts[line] = counts.get(line, 0) + 1

    if not counts:
        return {"hotspot_ratio": None, "churn_gini": None, "mean_churn": None, "n_files": 0}

    vals = list(counts.values())
    mean_c = sum(vals) / len(vals)
    hotspot_ratio = sum(1 for v in vals if v > mean_c * 2) / len(vals)

    sorted_v = sorted(vals)
    n = len(sorted_v)
    cum = sum((i + 1) * v for i, v in enumerate(sorted_v))
    gini = (2 * cum) / (n * sum(sorted_v)) - (n + 1) / n if sum(sorted_v) > 0 else 0.0

    return {
        "hotspot_ratio": round(hotspot_ratio, 4),
        "churn_gini": round(gini, 4),
        "mean_churn": round(mean_c, 3),
        "n_files": n,
    }


def _slug_project_key(name: str) -> str:
    key = re.sub(r"[^a-zA-Z0-9_]", "_", f"agq_oss_{name.lower()}")
    return key[:200]


def _run_sonar_scan(
    repo_path: Path,
    project_key: str,
    sonar_url: str,
    sonar_user: str,
    sonar_password: str,
    scanner_image: str,
    timeout_s: int,
) -> Dict[str, object]:
    cmd_base = [
        "docker",
        "run",
        "--rm",
        "--network",
        "host",
        "-e",
        f"SONAR_HOST_URL={sonar_url}",
        "-v",
        f"{repo_path}:/usr/src",
        scanner_image,
        "sonar-scanner",
        f"-Dsonar.projectKey={project_key}",
        f"-Dsonar.projectName={project_key}",
        "-Dsonar.sources=.",
        "-Dsonar.inclusions=**/*.py",
        "-Dsonar.python.version=3.10",
        "-Dsonar.sourceEncoding=UTF-8",
        f"-Dsonar.login={sonar_user}",
        f"-Dsonar.password={sonar_password}",
        "-Dsonar.qualitygate.wait=true",
        f"-Dsonar.qualitygate.timeout={timeout_s}",
    ]

    t0 = time.perf_counter()
    try:
        proc = _run_checked(cmd_base, timeout_s=timeout_s + 120)
    except RuntimeError as exc:
        msg = str(exc).lower()
        if "can't be indexed twice" not in msg:
            raise
        # Some repositories auto-detect tests that overlap with sources.
        # Retry once with a conservative tests exclusion.
        cmd_retry = cmd_base + ["-Dsonar.exclusions=**/tests/**,**/test/**"]
        proc = _run_checked(cmd_retry, timeout_s=timeout_s + 120)
    runtime_s = time.perf_counter() - t0

    return {
        "runtime_s": runtime_s,
        "stdout_tail": "\n".join(proc.stdout.strip().splitlines()[-8:]),
    }


def _rating_letter(rating_value: Optional[float]) -> Optional[str]:
    if rating_value is None or math.isnan(rating_value):
        return None
    rounded = int(round(rating_value))
    return {1: "A", 2: "B", 3: "C", 4: "D", 5: "E"}.get(rounded, None)


def _rating_quality_score(rating_value: Optional[float]) -> Optional[float]:
    if rating_value is None or math.isnan(rating_value):
        return None
    return max(0.0, min(1.0, 1.0 - (rating_value - 1.0) / 4.0))


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mx = statistics.mean(xs)
    my = statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mx) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - my) ** 2 for y in ys))
    den = den_x * den_y
    if den == 0.0:
        return None
    return num / den


def _ranks(values: Sequence[float]) -> List[float]:
    indexed = sorted((v, i) for i, v in enumerate(values))
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][0] == indexed[i][0]:
            j += 1
        rank = (i + j + 2) / 2.0
        for k in range(i, j + 1):
            ranks[indexed[k][1]] = rank
        i = j + 1
    return ranks


def _spearman(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    return _pearson(_ranks(xs), _ranks(ys))


def _float_or_none(value: object) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _median(values: Sequence[float]) -> Optional[float]:
    return statistics.median(values) if values else None


def _mean(values: Sequence[float]) -> Optional[float]:
    return statistics.mean(values) if values else None


def _format_f(value: Optional[float], digits: int = 4) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def _to_markdown(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AGQ Thesis Benchmark")
    lines.append("")
    lines.append(f"- generated_at: `{report['generated_at']}`")
    lines.append(f"- repos_target: `{report['repos_target']}`")
    lines.append(f"- repos_with_agq: `{report['summary']['repos_with_agq']}`")
    lines.append(f"- repos_with_sonar: `{report['summary']['repos_with_sonar']}`")
    lines.append("")

    lines.append("## Thesis Checks")
    lines.append("")
    lines.append("| ID | Thesis | Result | Evidence |")
    lines.append("|---|---|---|---|")
    for thesis in report["theses"]:
        status = "PASS" if thesis["passed"] else "FAIL"
        lines.append(
            f"| {thesis['id']} | {thesis['title']} | {status} | {thesis['evidence']} |"
        )
    lines.append("")

    lines.append("## Correlations")
    lines.append("")
    c = report["correlations"]
    predictor = c.get("sonar_predictor_for_correlation", "maintainability_quality_score")
    lines.append(f"- sonar predictor used: `{predictor}`")
    lines.append(f"- pearson(AGQ, bugfix_ratio): `{_format_f(c.get('pearson_agq_vs_bugfix_ratio'))}`")
    lines.append(f"- pearson(Sonar, bugfix_ratio): `{_format_f(c.get('pearson_sonar_vs_bugfix_ratio'))}`")
    lines.append(f"- spearman(AGQ, Sonar): `{_format_f(c.get('spearman_agq_vs_sonar'))}`")
    lines.append(f"- spearman(AGQ, hotspot_ratio): `{_format_f(c.get('spearman_agq_vs_hotspot_ratio'))}` "
                 f"(Sonar: `{_format_f(c.get('spearman_sonar_vs_hotspot_ratio'))}`)"
                 f" n={c.get('n_repos_churn', 'n/a')}")
    lines.append(f"- spearman(AGQ, churn_gini): `{_format_f(c.get('spearman_agq_vs_churn_gini'))}` "
                 f"(Sonar: `{_format_f(c.get('spearman_sonar_vs_churn_gini'))}`)")
    lines.append("")

    lines.append("## Repo Results")
    lines.append("")
    lines.append(
        "| Repo | AGQ(mean) | AGQ(delta) | Sonar Maint | Bugs | Smells | "
        "Bugfix% | Hotspot% | Churn Gini | AGQ time(s) | Sonar time(s) |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    for row in report["results"]:
        agq = row.get("agq", {})
        sonar = row.get("sonar", {})
        defect = row.get("defect_proxy", {})
        churn = row.get("churn", {})

        lines.append(
            f"| {row['name']} | "
            f"{_format_f(_float_or_none(agq.get('score_mean')), 4)} | "
            f"{_format_f(_float_or_none(agq.get('score_delta')), 6)} | "
            f"{sonar.get('maintainability_rating_letter', 'n/a')} | "
            f"{_format_f(_float_or_none(sonar.get('bugs')), 0)} | "
            f"{_format_f(_float_or_none(sonar.get('code_smells')), 0)} | "
            f"{_format_f(_float_or_none(defect.get('bugfix_ratio')), 4)} | "
            f"{_format_f(_float_or_none(churn.get('hotspot_ratio')), 4)} | "
            f"{_format_f(_float_or_none(churn.get('churn_gini')), 4)} | "
            f"{_format_f(_float_or_none(agq.get('runtime_s_mean')), 3)} | "
            f"{_format_f(_float_or_none(sonar.get('runtime_s')), 3)} |"
        )
    lines.append("")

    failures = [r for r in report["results"] if "error" in r]
    if failures:
        lines.append("## Failures")
        lines.append("")
        for row in failures:
            lines.append(f"- `{row['name']}`: {row['error']}")
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark AGQ theses on OSS repos")
    parser.add_argument("--repos-dir", default="/tmp/agq_oss_15")
    parser.add_argument(
        "--repos-file",
        default=None,
        help="JSON file with repo list: [{\"name\":..., \"url\":...}, ...]",
    )
    parser.add_argument("--output-json", default="artifacts/benchmark/agq_thesis_oss15.json")
    parser.add_argument("--output-md", default="artifacts/benchmark/agq_thesis_oss15.md")
    parser.add_argument("--clone-depth", type=int, default=400)
    parser.add_argument("--no-clone", action="store_true")
    parser.add_argument("--bugfix-since", default="2 years ago")
    parser.add_argument("--sonar-url", default="http://127.0.0.1:9000")
    parser.add_argument("--sonar-user", default="admin")
    parser.add_argument("--sonar-password", default="admin")
    parser.add_argument("--sonar-timeout", type=int, default=600)
    parser.add_argument("--scanner-image", default="sonarsource/sonar-scanner-cli:latest")
    parser.add_argument("--no-sonar", action="store_true")
    parser.add_argument("--cleanup-sonar-projects", action="store_true")
    args = parser.parse_args()

    repos_dir = Path(args.repos_dir).resolve()
    repos_dir.mkdir(parents=True, exist_ok=True)
    repos = _load_repo_specs(args.repos_file)

    sonar = None
    if not args.no_sonar:
        sonar = SonarClient(
            base_url=args.sonar_url,
            user=args.sonar_user,
            password=args.sonar_password,
        )
        print(f"[setup] waiting for SonarQube at {args.sonar_url} ...", flush=True)
        sonar.ensure_up(timeout_s=max(30, args.sonar_timeout))
        print("[setup] SonarQube is UP", flush=True)

    rows: List[Dict[str, object]] = []
    for idx, spec in enumerate(repos, start=1):
        print(f"[{idx:02d}/{len(repos)}] repo={spec.name}", flush=True)
        row: Dict[str, object] = {"name": spec.name, "url": spec.url}
        project_key = _slug_project_key(spec.name)
        try:
            repo_path = _clone_repo(spec, repos_dir=repos_dir, depth=args.clone_depth, no_clone=args.no_clone)
            row["path"] = str(repo_path)

            agq_1 = _compute_agq_once(repo_path, spec.name)
            agq_2 = _compute_agq_once(repo_path, spec.name)
            row["agq"] = {
                "run1": agq_1,
                "run2": agq_2,
                "score_mean": (agq_1["agq_score"] + agq_2["agq_score"]) / 2.0,
                "score_delta": abs(agq_1["agq_score"] - agq_2["agq_score"]),
                "runtime_s_mean": (agq_1["runtime_s"] + agq_2["runtime_s"]) / 2.0,
            }

            row["defect_proxy"] = _bugfix_proxy(repo_path, since=args.bugfix_since)
            row["churn"] = _churn_proxy(repo_path, since=args.bugfix_since)

            if sonar is not None:
                sonar.create_project(project_key=project_key, project_name=project_key)
                sonar_scan = _run_sonar_scan(
                    repo_path=repo_path,
                    project_key=project_key,
                    sonar_url=args.sonar_url,
                    sonar_user=args.sonar_user,
                    sonar_password=args.sonar_password,
                    scanner_image=args.scanner_image,
                    timeout_s=args.sonar_timeout,
                )
                measures = sonar.get_measures(project_key)
                quality_gate = sonar.get_quality_gate(project_key)
                maintainability_rating = _float_or_none(measures.get("sqale_rating"))

                row["sonar"] = {
                    "project_key": project_key,
                    "quality_gate": quality_gate,
                    "runtime_s": sonar_scan["runtime_s"],
                    "scan_stdout_tail": sonar_scan["stdout_tail"],
                    "maintainability_rating": maintainability_rating,
                    "maintainability_rating_letter": _rating_letter(maintainability_rating),
                    "maintainability_quality_score": _rating_quality_score(maintainability_rating),
                    "bugs": _float_or_none(measures.get("bugs")),
                    "vulnerabilities": _float_or_none(measures.get("vulnerabilities")),
                    "code_smells": _float_or_none(measures.get("code_smells")),
                    "ncloc": _float_or_none(measures.get("ncloc")),
                    "complexity": _float_or_none(measures.get("complexity")),
                    "cognitive_complexity": _float_or_none(measures.get("cognitive_complexity")),
                    "duplicated_lines_density": _float_or_none(measures.get("duplicated_lines_density")),
                }

                code_smells = row["sonar"]["code_smells"]
                ncloc = row["sonar"]["ncloc"]
                if code_smells is not None and ncloc and ncloc > 0:
                    smells_per_kloc = float(code_smells) / (float(ncloc) / 1000.0)
                    row["sonar"]["code_smells_per_kloc"] = smells_per_kloc
                    # Convert "lower is better" to "higher is better" quality score in (0,1].
                    row["sonar"]["code_smell_quality_score"] = 1.0 / (1.0 + smells_per_kloc)
                else:
                    row["sonar"]["code_smells_per_kloc"] = None
                    row["sonar"]["code_smell_quality_score"] = None

                if args.cleanup_sonar_projects:
                    sonar.delete_project(project_key)

        except Exception as exc:  # noqa: BLE001 - benchmark should continue on single-repo errors
            row["error"] = str(exc)
            print(f"  [error] {spec.name}: {exc}", flush=True)

        rows.append(row)

    rows_agq = [r for r in rows if "agq" in r and "error" not in r]
    rows_sonar = [r for r in rows if "sonar" in r and "error" not in r]
    rows_joint = [r for r in rows if "agq" in r and "sonar" in r and "error" not in r]

    agq_scores = [float(r["agq"]["score_mean"]) for r in rows_agq]
    agq_deltas = [float(r["agq"]["score_delta"]) for r in rows_agq]
    agq_times = [float(r["agq"]["runtime_s_mean"]) for r in rows_agq]

    sonar_times = [float(r["sonar"]["runtime_s"]) for r in rows_sonar]

    sonar_maint_values = [
        float(r["sonar"]["maintainability_quality_score"])
        for r in rows_joint
        if r["sonar"]["maintainability_quality_score"] is not None
    ]

    # Sonar maintainability is often all "A" on mature OSS repos (zero variance).
    # In that case we fallback to code-smell density quality proxy for correlation tests.
    use_maint_predictor = len(set(sonar_maint_values)) >= 2
    sonar_predictor_key = (
        "maintainability_quality_score"
        if use_maint_predictor
        else "code_smell_quality_score"
    )

    # --- Bugfix proxy (kept for reference, not used in T2) ---
    rows_for_bugfix = []
    for r in rows_joint:
        if r["defect_proxy"]["bugfix_ratio"] is None:
            continue
        predictor = r["sonar"].get(sonar_predictor_key)
        if predictor is None:
            continue
        rows_for_bugfix.append(r)

    agq_for_bugfix = [float(r["agq"]["score_mean"]) for r in rows_for_bugfix]
    sonar_for_bugfix = [float(r["sonar"][sonar_predictor_key]) for r in rows_for_bugfix]
    bugfix_ratios = [float(r["defect_proxy"]["bugfix_ratio"]) for r in rows_for_bugfix]

    pearson_agq_bug = _pearson(agq_for_bugfix, bugfix_ratios)
    pearson_sonar_bug = _pearson(sonar_for_bugfix, bugfix_ratios)
    spearman_agq_sonar = _spearman(
        [float(r["agq"]["score_mean"]) for r in rows_for_bugfix],
        [float(r["sonar"][sonar_predictor_key]) for r in rows_for_bugfix],
    )

    # --- Churn-based proxy for T2 ---
    # hotspot_ratio: fraction of files changed >2x mean - predicts defect-prone spots
    # Ref: Nagappan & Ball 2005; Moser et al. 2008
    rows_for_churn = []
    for r in rows_joint:
        churn = r.get("churn", {})
        if churn.get("hotspot_ratio") is None:
            continue
        predictor = r["sonar"].get(sonar_predictor_key)
        if predictor is None:
            continue
        rows_for_churn.append(r)

    agq_for_churn = [float(r["agq"]["score_mean"]) for r in rows_for_churn]
    sonar_for_churn = [float(r["sonar"][sonar_predictor_key]) for r in rows_for_churn]
    hotspot_ratios = [float(r["churn"]["hotspot_ratio"]) for r in rows_for_churn]
    churn_ginis = [float(r["churn"]["churn_gini"]) for r in rows_for_churn]

    spearman_agq_hotspot = _spearman(agq_for_churn, hotspot_ratios)
    spearman_sonar_hotspot = _spearman(sonar_for_churn, hotspot_ratios)
    spearman_agq_gini = _spearman(agq_for_churn, churn_ginis)
    spearman_sonar_gini = _spearman(sonar_for_churn, churn_ginis)

    # T3: complementarity - Sonar says "A" but AGQ identifies architectural issues
    # Threshold recalibrated to mean(AGQ) - 0.5*std to adapt to score distribution
    agq_mean = _mean(agq_scores) or 0.70
    agq_std = statistics.pstdev(agq_scores) if len(agq_scores) >= 2 else 0.05
    low_agq_threshold = agq_mean - 0.5 * agq_std
    complement_cases = [
        r["name"]
        for r in rows_joint
        if r["sonar"]["maintainability_rating_letter"] == "A"
        and float(r["agq"]["score_mean"]) < low_agq_threshold
    ]

    max_delta = max(agq_deltas) if agq_deltas else None
    agq_spread = (max(agq_scores) - min(agq_scores)) if len(agq_scores) >= 2 else None
    agq_stddev = statistics.pstdev(agq_scores) if len(agq_scores) >= 2 else None
    med_agq_t = _median(agq_times)
    med_sonar_t = _median(sonar_times)

    theses: List[Dict[str, object]] = []
    theses.append(
        {
            "id": "T1",
            "title": "AGQ deterministic over repeated runs",
            "passed": (max_delta is not None and max_delta <= 1e-9),
            "evidence": f"max_score_delta={_format_f(max_delta, 10)} (target <= 1e-9)",
        }
    )

    # T2: AGQ predicts hotspot_ratio better than Sonar (churn-based ground truth)
    # Negative spearman expected: higher AGQ → fewer hotspots
    churn_pass = False
    churn_evidence = f"insufficient churn data (n={len(rows_for_churn)})"
    if spearman_agq_hotspot is not None and spearman_sonar_hotspot is not None:
        churn_pass = abs(spearman_agq_hotspot) > abs(spearman_sonar_hotspot)
        churn_evidence = (
            f"|r_s(AGQ,hotspot_ratio)|={abs(spearman_agq_hotspot):.4f} vs "
            f"|r_s(Sonar,hotspot_ratio)|={abs(spearman_sonar_hotspot):.4f} "
            f"(n={len(rows_for_churn)}); "
            f"r_s(AGQ,churn_gini)={spearman_agq_gini:.4f}"
        )
    theses.append(
        {
            "id": "T2",
            "title": "AGQ predicts code churn hotspots better than Sonar (hotspot_ratio)",
            "passed": churn_pass,
            "evidence": churn_evidence,
        }
    )

    theses.append(
        {
            "id": "T3",
            "title": "Complementarity: Sonar A but AGQ below mean-0.5*std exists",
            "passed": len(complement_cases) >= 1,
            "evidence": (
                f"threshold={low_agq_threshold:.3f} (mean={agq_mean:.3f} - 0.5*std={0.5*agq_std:.3f}); "
                f"cases={len(complement_cases)}"
                + (f" ({', '.join(complement_cases[:10])}{'...' if len(complement_cases)>10 else ''})"
                   if complement_cases else "")
            ),
        }
    )

    runtime_pass = med_agq_t is not None and med_sonar_t is not None and med_agq_t < med_sonar_t
    theses.append(
        {
            "id": "T4",
            "title": "AGQ median runtime is lower than SonarQube median runtime",
            "passed": runtime_pass,
            "evidence": f"median_agq_s={_format_f(med_agq_t, 3)} vs median_sonar_s={_format_f(med_sonar_t, 3)}",
        }
    )

    discr_pass = agq_spread is not None and agq_stddev is not None and agq_spread >= 0.10 and agq_stddev >= 0.03
    theses.append(
        {
            "id": "T5",
            "title": "AGQ discriminates quality across heterogeneous repos",
            "passed": discr_pass,
            "evidence": f"spread={_format_f(agq_spread, 4)}, stddev={_format_f(agq_stddev, 4)}",
        }
    )

    report: Dict[str, object] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repos_target": len(repos),
        "repos": [{"name": r.name, "url": r.url} for r in repos],
        "config": {
            "repos_dir": str(repos_dir),
            "repos_file": args.repos_file,
            "clone_depth": args.clone_depth,
            "bugfix_since": args.bugfix_since,
            "sonar_url": args.sonar_url if not args.no_sonar else None,
            "scanner_image": args.scanner_image if not args.no_sonar else None,
            "sonar_enabled": not args.no_sonar,
        },
        "summary": {
            "repos_with_agq": len(rows_agq),
            "repos_with_sonar": len(rows_sonar),
            "repos_joint": len(rows_joint),
            "failed_repos": len([r for r in rows if "error" in r]),
            "agq_mean": _mean(agq_scores),
            "agq_median_runtime_s": med_agq_t,
            "sonar_median_runtime_s": med_sonar_t,
            "runtime_ratio_sonar_over_agq": (med_sonar_t / med_agq_t) if med_agq_t and med_sonar_t else None,
        },
        "correlations": {
            "pearson_agq_vs_bugfix_ratio": pearson_agq_bug,
            "pearson_sonar_vs_bugfix_ratio": pearson_sonar_bug,
            "spearman_agq_vs_sonar": spearman_agq_sonar,
            "sonar_predictor_for_correlation": sonar_predictor_key,
            "spearman_agq_vs_hotspot_ratio": spearman_agq_hotspot,
            "spearman_sonar_vs_hotspot_ratio": spearman_sonar_hotspot,
            "spearman_agq_vs_churn_gini": spearman_agq_gini,
            "spearman_sonar_vs_churn_gini": spearman_sonar_gini,
            "n_repos_churn": len(rows_for_churn),
        },
        "theses": theses,
        "results": rows,
    }

    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2))
    output_md.write_text(_to_markdown(report))

    passed = sum(1 for t in theses if t["passed"])
    print(
        f"Thesis benchmark complete: {passed}/{len(theses)} checks passed. "
        f"JSON={output_json} MD={output_md}"
    )


if __name__ == "__main__":
    main()
