#!/usr/bin/env bash
# Agent-time architectural gate for Claude Code.
# Reads PreToolUse JSON on stdin, delegates to qse.gate.hook_runner.
# Exit 2 blocks the write and shows stderr to Claude for self-correction.

set -u

# Resolve project root regardless of where the hook was spawned.
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$PROJECT_DIR" || exit 0

exec python3 -m qse.gate.hook_runner
