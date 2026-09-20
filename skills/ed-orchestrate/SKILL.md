---
name: ed-orchestrate
description: >-
  Delegate a coding sub-task to a configured sub-agent role (coder, planner, tester,
  reviewer, architect, code-reviewer, designer, qa-designer, curator, integrator, or
  any custom role defined in this project's .orchestrate/agents.json) running on its
  own harness, model, and provider, via Orca's orca-cli/orchestration CLI. Use
  whenever the user says "delegate", "hand off", "handoff", "give this to <role>",
  "have the
  coder/tester/planner/reviewer/architect/code-reviewer/designer/qa-designer/curator/integrator
  do X",
  "spin up a sub-agent", "run this on opencode/codex/agy/gemini/cursor/droid", "supervise
  <role> on X", or names any role defined in this project's agents.json. If no
  .orchestrate/agents.json exists yet in this project, tell the user to run
  ed-orchestrate-init first — never invent a roster. Works from Claude Code (this file)
  and, via the AGENTS.md roster block, from opencode and Antigravity/agy.
argument-hint: "[task] [optional: role name] [optional: handoff|supervise]"
---

# ed-orchestrate

Discovery stub. Read [AGENTS.md](AGENTS.md) for the full delegate flow — role
resolution, handoff-vs-supervised branching, and the harness capability rules. Then
read the overlay for your host: [CLAUDE.md](CLAUDE.md) for Claude Code,
[OPENCODE.md](OPENCODE.md) for opencode, [AGY.md](AGY.md) for Antigravity/agy — each
is a few lines noting the one or two differences for that host (mainly: whether you
have `AskUserQuestion` and a Bash pre-approval gate).

Never hardcode `orca` subcommand syntax here or in any file below — always run
`orca skills get orca-cli` (and `orca skills get orchestration` for supervised runs)
per the orca-cli/orchestration skills' own resolution rules before constructing a
command. Those skills are themselves thin stubs for exactly this reason: the real CLI
surface is fetched live so it can never drift from the binary that runs your command.
