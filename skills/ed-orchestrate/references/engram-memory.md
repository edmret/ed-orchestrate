# Engram persistent memory (optional, needs graph-DAG)

Two memories, two jobs:

| | `.ai-memory/` | Engram (`mem_*` MCP tools) |
| --- | --- | --- |
| Scope | this project's live task graph, ADRs, gotchas | durable recall across sessions and projects, per user |
| Holds | state: nodes, logs, reviews, curated gotchas | distilled decisions, root causes, preferences, session summaries |
| Shared via | worktree symlink (`orca.yaml` `sharedDirectories`) | MCP server, per harness |
| Lifetime | working state, local to the checkout's machine | survives checkout removal and new sessions |

**Why add it:** an agent can `mem_search` a topic (a few hundred tokens) instead of
opening several gotcha/ADR files "just in case" — fewer tokens per dispatch, and the
knowledge follows you across projects. `.ai-memory/` stays the source of truth for task
state; Engram never holds status, diffs or logs.

## Every harness needs it, or those workers are out

Engram is configured **per harness, user-global** (not per project). A worker on a
harness without it simply can't search, so init checks the whole roster:

```
python3 ed-orchestrate-init/scripts/ensure_engram.py --harnesses claude,opencode,agy [--project NAME]
```

| ed-orchestrate harness | `engram setup` agent | Detected as installed when |
| --- | --- | --- |
| `claude` | `claude-code` | `engram` in `~/.claude/settings.json` `enabledPlugins`, or `~/.claude.json` `mcpServers` |
| `opencode` | `opencode` | `mcp.engram` in `~/.config/opencode/opencode.json` |
| `agy` | `antigravity-cli` | `mcp(engram/…)` entries in `~/.gemini/antigravity-cli/settings.json` `permissions.allow` |
| `gemini` | `gemini-cli` | `mcpServers.engram` in `~/.gemini/settings.json` |
| `codex` | `codex` | `engram` in `~/.codex/config.toml` |
| `cursor` | `cursor` | `mcpServers.engram` in `~/.cursor/mcp.json` |
| `droid` | none | manual: MCP server running `engram mcp --tools=agent` |

The script is read-only for those files: it reports `ok` / `MISSING` / `manual` and the
fix. Init then asks before running `engram setup <agent>` (it edits user-global config),
or prints the commands for you to run (`! engram setup opencode`). Install the binary
first (e.g. `brew install engram`). Headless agy also needs the `mcp(engram/mem_*)`
allow entries — `engram setup antigravity-cli` adds them.

A worker whose harness has no Engram skips the Engram rules and works from
`.ai-memory/` alone — never a blocker.

## One project across all worktrees

Engram files memories under a project name. Left to cwd detection, every Orca worktree
directory could become its own project and fragment the memory. Init pins one name:
`ensure_engram.py --project <name>` writes `.engram/config.json`
(`{"project_name": "<name>"}`). **Commit that file** — a tracked file exists in every
worktree, and a worktree of such a repo saves to the pinned project (verified). Don't
commit the rest of `.engram/` (sync chunks) unless you use `engram sync` deliberately.

## What init adds to AGENTS.md

`setup_graph_dag.py <dir> --engram` adds a `### Persistent memory (Engram)` section to
the graph-DAG block (its heading is the marker: kept on re-runs, `--no-engram` removes):

- **Orchestrator**: `mem_search` before planning; `mem_save` on accepted ADR, batch
  root cause, user preference, settled convention (a pointer to the `.ai-memory/` path,
  not a copy); save what `curator` promoted; `mem_session_summary` at the end.
- **Workers**: after their node/ADRs/`00-core.md`, at most 1–2 targeted `mem_search`
  queries; `mem_save` only a non-obvious root cause (short, with the node id) — the
  gotcha still goes to `gotchas/<area>.md` first.
- Never secrets or customer data; Engram errors never block work.
