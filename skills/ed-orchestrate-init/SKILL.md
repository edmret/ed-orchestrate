---
name: ed-orchestrate-init
description: >-
  Interview the user to configure ed-orchestrate's sub-agent roster for THIS
  project — which roles exist (coder, planner, tester, reviewer, architect,
  code-reviewer, designer, qa-designer, curator, integrator, or custom), and
  per role which harness (claude, codex, opencode, agy/antigravity, gemini,
  cursor, droid), model, and (for opencode) provider to use. Writes
  .orchestrate/agents.json and updates the delimited
  ed-orchestrate-roster block in this project's AGENTS.md; optionally scaffolds
  graph-DAG task memory (task/ADR/plan/review/UI-iteration templates) and the
  Laya lane router, and wires CLAUDE.md/GEMINI.md and harness write permissions
  so every harness reads the setup and can write. Use whenever the user
  says "set up ed-orchestrate", "configure sub-agents", "ed-orchestrate-init",
  "init ed-orchestrate", "add a sub-agent role", "edit the <role> role", "change
  which model the <role> uses", "add a fallback harness for <role>", or wants to
  (re)configure who does what in this project's delegation roster, or says
  "set up laya routing", "refresh the orchestration templates", or "workers
  can't write" in a new project. Passing a role
  name as the argument jumps straight to editing that role's primary config or
  its fallback harness bindings. Prefer this over hand-editing agents.json when the user is choosing
  roles/harnesses/models interactively; re-running it is safe and idempotent.
argument-hint: "[optional: role name to add or edit]"
---

# ed-orchestrate-init

Discovery stub. Requires the sibling `ed-orchestrate` skill installed at
`~/.claude/skills/ed-orchestrate` (same repo — install both; see that repo's
README). This skill reuses `ed-orchestrate`'s
`scripts/validate_agents_json.py` as the canonical config validator rather than
duplicating validation logic.

Read [AGENTS.md](AGENTS.md) for the interview flow,
[references/interview-flow.md](references/interview-flow.md) for the exact
question sequence, and the overlay for your host ([CLAUDE.md](CLAUDE.md),
[OPENCODE.md](OPENCODE.md), [AGY.md](AGY.md)) for how questions get asked there.
