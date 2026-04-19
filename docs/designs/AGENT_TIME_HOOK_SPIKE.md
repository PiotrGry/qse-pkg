# Agent-time hook spike — feasibility memo

**Date:** 2026-04-19
**Branch:** fix/metrics-redesign
**Status:** survey complete, A2 prototype go/no-go pending
**Why:** Pilot Audit is PR-time. The real moat is catching drift at *generation time*, before the agent ever writes a file. This memo answers one question: which AI coding tools let a third-party CLI (`qse-gate`) intercept a proposed write, run dependency-graph analysis, and either block or feed the violation back so the model self-corrects?

## TL;DR

Four of five targets ship a usable hook. **Claude Code is the clear first target** — full pre-write access to proposed content, exit-2 block, structured feedback to the model. Windsurf Cascade is close second (blocks cleanly, but no feedback channel back to the agent). Aider re-prompts on non-zero lint/test exit (post-write but pre-accept, different pattern, still works). Cursor's 1.7 hooks miss the one we need. Continue.dev has no native hook.

## Platform scorecard

| Tool | Hook event | Sees proposed content? | Exit-2 blocks? | Feeds back to LLM? | Feasibility (1-5) |
|------|------------|:----------------------:|:--------------:|:------------------:|:-----------------:|
| **Claude Code** | `PreToolUse` (Write\|Edit) | ✓ full `content` / `new_string` on stdin JSON | ✓ | ✓ stderr + structured JSON decision | **5** |
| **Windsurf Cascade** | `pre_write_code` | ✓ `file_path` + `edits[]` (old/new_string) | ✓ | ✗ block-only; no structured feedback | **4** |
| **Aider** | `--lint-cmd` / `--test-cmd` | post-write, before accept | ✓ non-zero exit re-prompts LLM | ✓ stdout/stderr fed to model | **4** |
| **Cursor 1.7** | `afterFileEdit` only | ✗ fires *after* disk write | ✗ | ✗ | **2** |
| **Continue.dev** | slashCommands deprecated, MCP only | ✗ no pre-write hook | n/a | via MCP prompt injection only | **2** |

## Per-target detail

### Claude Code ✓ primary target

`PreToolUse` hook matches on `Edit|Write`, receives stdin JSON with `tool_input.content` (Write) or `tool_input.old_string / new_string` (Edit), plus `cwd` and `tool_use_id`. Exit code 2 blocks the write; stderr is shown to Claude which can self-correct. Alternatively, exit 0 with `{"hookSpecificOutput": {"permissionDecision": "deny", "permissionDecisionReason": "..."}}` gives structured rejection.

Hooks run in the user's shell with full permissions — `python3 -m qse.gate.runner` works directly. `if` field supports glob refinement (`Write(src/**/*.py)`). Default timeout 600s, keep it <1s to avoid UX spinner.

Registered in `.claude/settings.json` (committable per repo) or `~/.claude/settings.json` (global). This is the green path.

### Windsurf Cascade ✓ secondary target

Symmetric design to Claude Code. `pre_write_code` hook at `.windsurf/hooks.json` (workspace-level, committable), receives `file_path` + `edits` array, exit 2 blocks. Difference: stderr is shown to user when `show_output: true`, but **hook output cannot be fed back to Cascade as guidance** — block-only, no self-correction loop. Still useful as a hard gate.

System-, user-, and workspace-level merge. Enterprise plan exposes team-wide hook policy via cloud dashboard.

### Aider ✓ tertiary target, different pattern

`--lint-cmd` and `--test-cmd` fire *after* Aider writes the file, but if the command exits non-zero, Aider auto-re-prompts the LLM with stdout/stderr attached. Net effect: a post-write pre-accept loop. Our `qse-gate` run as `--lint-cmd="qse-gate . --config qse-gate.toml"` would give Aider a rejection signal plus the axiom-cited PR-comment-style reasoning, and Aider would push the LLM to fix it.

Downside: the bad write lands on disk first and is rolled back by Aider's re-prompt cycle. Works, but less surgical.

### Cursor ✗ not viable yet

Cursor 1.7 shipped hooks (`cursor.com/docs/hooks`). The event list covers session, agent, shell, MCP, subagent, and `afterFileEdit` — but **no `beforeFileEdit` / `pre_write_code` equivalent**. The community has been asking for one (forum request thread exists). Without a pre-write hook, `qse-gate` would have to run post-edit and either revert via git (ugly) or just lint (no enforcement). Feasibility lifts to 4 if/when Cursor adds `beforeFileEdit`. Worth watching the changelog, not worth building against today.

### Continue.dev ✗ MCP-only, no real hook

Slash commands are deprecated in favour of prompt files. `config.ts` exists but has no pre-write lifecycle. MCP server registration is the only real extension point, and MCP is request/response from the LLM to our server — the LLM decides when to call us, not the runtime. We cannot force validation on every write. Skip.

## Recommendation: target Claude Code first

**Reasoning:**
1. **Most complete hook surface** — full content, block, structured feedback to model.
2. **Our own tooling already runs inside Claude Code** (this repo, gstack, /codex). Eating our own dog food.
3. **Smallest blast radius for a prototype** — `.claude/settings.json` in one repo, no extension publish, no IDE dependency.
4. **Clearest demo artefact** — "watch Claude try to write a forbidden import, get slapped by the axiom, rewrite it correctly, all without leaving the editor." Shoots straight at the grant panel's agent-time narrative.

**Secondary target after Claude Code MVP ships:** Windsurf Cascade, same architecture (hook script reading stdin JSON, calling `qse-gate`, exit 2). Shared hook script, two config files.

**Parking-lot:** Aider adapter once the Claude Code and Cascade paths are stable. Cursor watch — check changelog monthly for `beforeFileEdit`.

## Critical unknowns resolved by this spike

- ✓ **Does the hook see proposed content?** Yes (Claude Code, Cascade). No (Cursor).
- ✓ **Can the hook block?** Yes via exit 2 (Claude Code, Cascade, Aider).
- ✓ **Can the block feed back to the LLM for self-correction?** Yes (Claude Code, Aider). No (Cascade — block-only). No (Cursor — no pre-write hook).
- ✓ **Can we call `python3 -m qse.gate.runner` from the hook?** Yes, all targets.

## Remaining unknowns for the prototype (A2)

- How fast is `qse.gate.runner` on a single-file diff against a cached base graph? If >1s, users see a spinner. Need a `--stdin` fast path that rebuilds only the touched module's subgraph, not the whole repo.
- For `Edit` tool, we receive `old_string` / `new_string`, not final file content. We need to reconstruct the proposed file by reading current disk + applying the edit, or switch to a delta-only import analysis.
- Does blocking a write actually make Claude re-plan, or does it just escalate to user? Needs empirical test.
- Can the hook read the `qse-gate.toml` from the project root reliably? `$CLAUDE_PROJECT_DIR` is the right anchor.

## Next actions

1. **Go/no-go meeting** (with you, now) — confirm Claude Code as prototype target.
2. **A2 prototype** (next session, 4-6h): ship `.claude/hooks/qse-gate-hook.sh` + `qse/gate/stdin_runner.py` (fast-path subgraph analysis). Demo: try to add a forbidden import to `examples/sample-ai-drift-demo`, watch Claude Code block itself, watch the self-correction.
3. **Parallel track** (days): benchmark the hook latency on the real qse-pkg repo. Target <500ms.

## Sources

- [Claude Code hooks reference](https://code.claude.com/docs/en/hooks.md)
- [Claude Code hooks guide (examples)](https://code.claude.com/docs/en/hooks-guide.md)
- [Cursor hooks](https://cursor.com/docs/hooks)
- [Cursor forum — pre-edit hook request](https://forum.cursor.com/t/request-hooks-support-post-edit-pre-edit-etc/114716)
- [Windsurf Cascade hooks](https://docs.windsurf.com/windsurf/cascade/hooks)
- [Aider linting and testing](https://aider.chat/docs/usage/lint-test.html)
- [Continue.dev customization](https://docs.continue.dev/customize/overview)
- [Continue.dev MCP setup](https://docs.continue.dev/customize/deep-dives/mcp)
