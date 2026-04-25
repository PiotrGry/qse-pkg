"""Generate a static HTML benchmark page from agq_240_*.json.

Output: docs/benchmark/index.html — single file, no deps, embeddable.
Shows per-language distributions of architectural metrics so users can
compare their own repo against the 240-repo OSS panel.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
BENCH_DIR = REPO_ROOT / "artifacts" / "benchmark"
OUT = REPO_ROOT / "docs" / "benchmark" / "index.html"


def load_lang(lang: str) -> list[dict]:
    path = BENCH_DIR / f"agq_240_{lang}80.json"
    data = json.loads(path.read_text())
    return [r for r in data["results"] if r.get("agq", {}).get("nodes", 0) > 30]


def percentiles(values: list[float], pcts: tuple[int, ...]) -> dict[int, float]:
    s = sorted(values)
    out = {}
    for p in pcts:
        idx = min(int(len(s) * p / 100), len(s) - 1)
        out[p] = s[idx]
    return out


def lang_stats(results: list[dict]) -> dict:
    agqs       = [r["agq"]["agq_score"] for r in results]
    one_minus_acy = [1 - r["agq"]["acyclicity"] for r in results]
    en         = [r["agq"]["edges"] / r["agq"]["nodes"] for r in results
                  if r["agq"]["nodes"] > 0]
    cohesion   = [r["agq"]["cohesion"] for r in results]
    return {
        "n":             len(results),
        "agq_mean":      statistics.mean(agqs),
        "agq_std":       statistics.pstdev(agqs),
        "agq_pcts":      percentiles(agqs, (10, 25, 50, 75, 90)),
        "cyclic_mean":   statistics.mean(one_minus_acy) * 100,
        "cyclic_pcts":   {k: v * 100 for k, v in percentiles(one_minus_acy, (50, 75, 90)).items()},
        "en_mean":       statistics.mean(en),
        "en_pcts":       percentiles(en, (25, 50, 75, 90)),
        "cohesion_mean": statistics.mean(cohesion),
        "cohesion_pcts": percentiles(cohesion, (10, 25, 50, 75, 90)),
        "top5":          sorted(results, key=lambda r: -r["agq"]["agq_score"])[:5],
        "bottom5":       sorted(results, key=lambda r: r["agq"]["agq_score"])[:5],
    }


def render() -> str:
    langs = ["python", "java", "go"]
    stats = {l: lang_stats(load_lang(l)) for l in langs}

    rows = []
    for lang in langs:
        s = stats[lang]
        rows.append(
            f"<tr><td><b>{lang.title()}</b></td>"
            f"<td>{s['n']}</td>"
            f"<td>{s['agq_mean']:.3f} ± {s['agq_std']:.3f}</td>"
            f"<td>{s['agq_pcts'][50]:.3f}</td>"
            f"<td>{s['agq_pcts'][25]:.3f}–{s['agq_pcts'][75]:.3f}</td>"
            f"<td>{s['cyclic_mean']:.1f}% ({s['cyclic_pcts'][90]:.1f}% p90)</td>"
            f"<td>{s['en_mean']:.2f}</td>"
            f"<td>{s['cohesion_mean']:.3f}</td>"
            f"</tr>"
        )

    def mk_repo_table(rows, label):
        items = "".join(
            f"<tr><td><a href='{r['url']}'>{r['name']}</a></td>"
            f"<td>{r['agq']['agq_score']:.3f}</td>"
            f"<td>{r['agq']['nodes']}</td>"
            f"<td>{1 - r['agq']['acyclicity']:.1%}</td>"
            f"</tr>"
            for r in rows
        )
        return (f"<h4>{label}</h4>"
                f"<table><thead><tr><th>Repo</th><th>AGQ</th><th>nodes</th>"
                f"<th>cycle %</th></tr></thead><tbody>{items}</tbody></table>")

    examples_html = ""
    for lang in langs:
        s = stats[lang]
        examples_html += f"<details><summary><b>{lang.title()} examples</b></summary>"
        examples_html += mk_repo_table(s["top5"], "Top 5 by AGQ")
        examples_html += mk_repo_table(s["bottom5"], "Bottom 5 by AGQ")
        examples_html += "</details>"

    return TEMPLATE.format(
        rows="".join(rows),
        examples=examples_html,
        py_p25=stats["python"]["agq_pcts"][25],
        py_p75=stats["python"]["agq_pcts"][75],
        java_p25=stats["java"]["agq_pcts"][25],
        java_p75=stats["java"]["agq_pcts"][75],
        go_p25=stats["go"]["agq_pcts"][25],
        go_p75=stats["go"]["agq_pcts"][75],
    )


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>QSE Architectural Benchmark — 240 OSS repos</title>
<meta name="description" content="Cross-language structural metric distributions for 240 popular OSS repositories. Where does your repo land?">
<style>
:root {{ --fg: #1d1d1f; --muted: #6e6e73; --border: #d2d2d7; --accent: #0071e3;
         --bg: #fbfbfd; }}
* {{ box-sizing: border-box; }}
body {{ font-family: -apple-system, system-ui, "Segoe UI", sans-serif;
        max-width: 1100px; margin: 2em auto; padding: 0 1.5em; color: var(--fg);
        line-height: 1.55; background: var(--bg); }}
h1 {{ font-size: 2.2em; font-weight: 600; letter-spacing: -0.02em; margin-top: 0; }}
h2 {{ font-weight: 600; margin-top: 2.5em; }}
h3 {{ font-weight: 600; }}
h4 {{ font-weight: 500; color: var(--muted); margin-top: 1.5em; margin-bottom: 0.5em; }}
.lead {{ font-size: 1.15em; color: var(--muted); }}
.banner {{ padding: 1.5em; background: #fff; border: 1px solid var(--border);
           border-radius: 12px; margin: 2em 0; }}
.banner code {{ font-size: 0.95em; }}
table {{ border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 0.95em; }}
th, td {{ padding: 0.7em 1em; border-bottom: 1px solid var(--border); text-align: left; }}
th {{ background: #f5f5f7; font-weight: 600; }}
code {{ background: #f0f0f0; padding: 0.1em 0.4em; border-radius: 4px;
        font-size: 0.9em; }}
details {{ margin: 1em 0; padding: 0.8em 1.2em; background: #fff;
           border: 1px solid var(--border); border-radius: 8px; }}
summary {{ cursor: pointer; font-weight: 500; }}
.note {{ background: #fff7e6; border-left: 4px solid #ff9500; padding: 1em 1.5em;
         border-radius: 4px; margin: 1.5em 0; font-size: 0.95em; }}
.cmd {{ background: #1d1d1f; color: #f5f5f7; padding: 1em 1.5em;
        border-radius: 8px; font-family: ui-monospace, monospace;
        font-size: 0.9em; overflow-x: auto; }}
footer {{ margin-top: 4em; padding-top: 2em; border-top: 1px solid var(--border);
          color: var(--muted); font-size: 0.9em; }}
a {{ color: var(--accent); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>

<h1>QSE Architectural Benchmark</h1>
<p class="lead">Cross-language structural metric distributions for 240 OSS repositories.
Where does your repo land?</p>

<div class="banner">
<p><b>How to compare your repo:</b></p>
<div class="cmd">pip install git+https://github.com/PiotrGry/qse-pkg.git
qse agq path/to/your/repo</div>
<p>Compare your AGQ score against the percentile bands below. Higher AGQ usually means flatter,
more layered structure — but absolute values are not predictive of bug rates.
For actionable signal, use <code>qse gate-diff</code> in CI.</p>
</div>

<h2>Distributions by language</h2>
<table>
<thead>
<tr>
  <th>Language</th>
  <th>n</th>
  <th>AGQ mean ± σ</th>
  <th>median</th>
  <th>p25–p75</th>
  <th>cycle %</th>
  <th>E/N</th>
  <th>cohesion</th>
</tr>
</thead>
<tbody>
{rows}
</tbody>
</table>

<p>Read this table as <i>structural fingerprint per language</i>:</p>
<ul>
<li><b>Python (n=76):</b> p25–p75 AGQ {py_p25:.3f}–{py_p75:.3f}. Most repos are cycle-free.</li>
<li><b>Java (n=75):</b> p25–p75 AGQ {java_p25:.3f}–{java_p75:.3f}. Higher cycle tolerance — frameworks frequently cyclic.</li>
<li><b>Go (n=78):</b> p25–p75 AGQ {go_p25:.3f}–{go_p75:.3f}. Cycle-free by language convention.</li>
</ul>

<h2>Examples</h2>
{examples}

<h2>What the metrics mean</h2>
<p><b>AGQ score</b> — composite of modularity, acyclicity, stability, cohesion. Range [0, 1].
Higher is structurally cleaner, but does not predict bug rates in current evidence
(see <a href="https://github.com/PiotrGry/qse-pkg/blob/main/docs/QSE_CLAIMS_AND_EVIDENCE.md">claims audit</a>).</p>

<p><b>Cycle %</b> — fraction of nodes inside a strongly-connected component &gt; 1.
Zero in healthy DAG. Java tolerates more (frameworks); Go cultural convention is zero.</p>

<p><b>E/N</b> — edges per node, a basic coupling density indicator.</p>

<p><b>Cohesion</b> — based on LCOM4. The only AGQ component that consistently aligns
with quality intuition in current data (negatively correlates with complexity_per_kloc,
r=−0.45, p=0.014, n=29).</p>

<div class="note">
<p><b>Honest disclaimer:</b> these distributions describe <i>where popular OSS code lives</i>,
not <i>what is good</i>. Use them as orientation: if your repo's AGQ is at p10 of its language,
it doesn't mean your code is bad — it means it's structurally unusual relative to OSS.
Investigate <i>why</i>, not <i>what number to chase</i>.</p>
<p>For pre-commit / CI use, prefer the delta-based <code>qse gate-diff</code>.
Absolute thresholds at this scale are calibration aids, not quality predictions.</p>
</div>

<h2>Use in CI</h2>
<div class="cmd"># Pre-commit
repos:
  - repo: https://github.com/PiotrGry/qse-pkg
    rev: v0.1.0
    hooks:
      - id: qse-gate

# GitHub Actions
- run: pip install git+https://github.com/PiotrGry/qse-pkg.git
- run: qse gate-diff --base origin/main --head HEAD --language python</div>

<footer>
<p>Generated by <code>scripts/generate_benchmark_page.py</code> from
<code>artifacts/benchmark/agq_240_{{python,java,go}}80.json</code> (Apr 2026).</p>
<p>Source: <a href="https://github.com/PiotrGry/qse-pkg">github.com/PiotrGry/qse-pkg</a></p>
</footer>

</body>
</html>
"""


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    html = render()
    OUT.write_text(html)
    print(f"Wrote {OUT.relative_to(REPO_ROOT)} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
