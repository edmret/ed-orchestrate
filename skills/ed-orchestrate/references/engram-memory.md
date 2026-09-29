# Engram persistent memory (optional, orchestrator-only, needs graph-DAG)

Two memories, two jobs:

| | `.ai-memory/` | Engram (`mem_*` MCP tools / engram plugin) |
| --- | --- | --- |
| Scope | this project's live task graph, ADRs, gotchas | durable recall across sessions and projects, per user |
| Used by | every worker role, every harness, via the worktree symlink | the orchestrator session only |
| Holds | state: nodes, logs, reviews, curated gotchas | distilled decisions, root causes, preferences, session summaries |
| Lifetime | working state, curated over time, local to the machine | survives checkout removal and new sessions |

Workers never depend on Engram: not every harness has the MCP, and a worker that
needs it would break the "any model, any harness" guarantee. They use `.ai-memory/`
alone. The orchestrator is the bridge.

## What init adds

`ed-orchestrate-init` step 5g asks (default Recommended when Engram is detected) and
runs `setup_graph_dag.py <dir> --engram`, which adds a
`### Persistent memory (Engram)` section to the graph-DAG block in `AGENTS.md`:

- **Search first**: `mem_search` with keywords from the request before planning.
- **Save at decision points**: `mem_save` when an ADR is accepted, a batch closes with a
  non-obvious gotcha/root cause, the user states a preference, or a convention settles.
- **Pointer, not copy**: one-paragraph decision + why + the `.ai-memory/` path
  (`[[ADR-003]]`). Node logs and gotcha files remain the source of truth for state.
- **After `curator`**: curator may run on a harness without Engram, so it lists
  promotion candidates in its report and the orchestrator saves them.
- **Session end**: `mem_session_summary`.
- Never store secrets or customer data. If no `mem_*` tools exist, the section is inert.

The section survives every re-run of init (its heading is the marker); `--no-engram`
removes it. Nothing else changes: no new files, no new dependency, no `agents.json`
field.

## Install Engram (once per machine)

Not part of this repo. Install it as a Claude Code plugin or MCP server per its own
docs; init only detects it (`command -v engram`, or `engram` in `~/.claude.json`
`mcpServers` / `~/.claude/settings.json` `enabledPlugins`).
