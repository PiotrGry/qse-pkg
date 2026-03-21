#!/usr/bin/env python3
"""Pin commit SHAs for benchmark repositories.

For each repo in the benchmark JSON, resolves the current HEAD commit SHA
via `git ls-remote` and adds it to the JSON. This ensures reproducibility:
cloning at a pinned SHA guarantees identical analysis results.

Usage:
    python3 scripts/pin_commits.py scripts/repos_oss80_benchmark.json
    python3 scripts/pin_commits.py --all   # pin all *80* benchmark lists
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def resolve_head_sha(url: str, timeout: int = 15) -> str | None:
    """Get HEAD commit SHA from remote repo without cloning."""
    try:
        result = subprocess.run(
            ["git", "ls-remote", url, "HEAD"],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split()[0]
    except subprocess.TimeoutExpired:
        pass
    return None


def pin_commits(json_path: Path) -> dict:
    """Add commit SHAs to repo list JSON. Returns stats."""
    with open(json_path) as f:
        repos = json.load(f)

    pinned, failed, skipped = 0, 0, 0
    for repo in repos:
        if repo.get("commit"):
            skipped += 1
            continue
        sha = resolve_head_sha(repo["url"])
        if sha:
            repo["commit"] = sha
            pinned += 1
            print(f"  {repo['name']}: {sha[:12]}")
        else:
            failed += 1
            print(f"  {repo['name']}: FAILED")

    with open(json_path, "w") as f:
        json.dump(repos, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return {"pinned": pinned, "failed": failed, "skipped": skipped, "total": len(repos)}


def main():
    parser = argparse.ArgumentParser(description="Pin commit SHAs for benchmark repos")
    parser.add_argument("files", nargs="*", help="JSON files to pin")
    parser.add_argument("--all", action="store_true", help="Pin all *80* benchmark lists")
    args = parser.parse_args()

    scripts_dir = Path(__file__).parent

    if args.all:
        files = sorted(scripts_dir.glob("repos_*80_benchmark.json"))
    elif args.files:
        files = [Path(f) for f in args.files]
    else:
        parser.print_help()
        sys.exit(1)

    for f in files:
        print(f"\n=== {f.name} ===")
        stats = pin_commits(f)
        print(f"  Done: {stats['pinned']} pinned, {stats['skipped']} already pinned, {stats['failed']} failed / {stats['total']} total")


if __name__ == "__main__":
    main()
