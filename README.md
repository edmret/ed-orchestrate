# ed-orchestrate

> 🚀 **A collection of skills to build cost-effective, hybrid multi-AI agent teams effortlessly.**
> 
> Mix and match paid subscriptions & frontier models (Claude, Codex, Gemini) with local open-source models (via OpenCode, Ollama, etc.) to assign specialized sub-agent roles. Combine top-tier reasoning where it matters with cost-efficient local execution for routine tasks—giving you infinite team combinations with maximum performance and minimal cost via Orca orchestration.

A pair of skills (for Claude Code, OpenCode, and Antigravity/AGY) for delegating coding sub-tasks to configurable sub-agent
roles (coder, planner, tester, reviewer, architect, code-reviewer,
designer, qa-designer, curator, integrator, or custom), each pinned to a **harness**
(claude, codex, opencode, agy/antigravity, cursor, gemini, droid), a **model**, and
(for opencode) a **provider**. Delegation itself runs through Orca's `orca-cli` /
`orchestration` skills — worktrees, terminals, supervised worker loops — not a new
mechanism.

- `ed-orchestrate/` — the delegate skill. Given a task and a role, resolves that
  role's harness/model/provider from the target project's
  `.orchestrate/agents.json` and runs the matching `orca` invocation.
- `ed-orchestrate-init/` — the interview skill. Asks the user which roles they
  want and which harness/model/provider each should use, then writes
  `.orchestrate/agents.json` and a generated roster block in the target
  project's `AGENTS.md` (and, for opencode roles, a native
  `.opencode/agent/<role>.md` file).

Both skills also work from opencode and Antigravity/agy via the `AGENTS.md`
auto-load convention those hosts share with Claude Code — see each skill's
`OPENCODE.md` / `AGY.md` overlay.

## Install

### For Antigravity / AGY CLI & Universal Skills (`~/.agents/skills`)

Antigravity discovers global skills from `~/.gemini/config/skills/`. Link Antigravity's config to `~/.agents/skills/` and symlink the repo skills:

```bash
# 1. Ensure Antigravity's global skills directory points to ~/.agents/skills
mkdir -p ~/.agents/skills
ln -s ~/.agents/skills ~/.gemini/config/skills

# 2. Symlink ed-orchestrate skills
ln -s /path/to/ed-orchestation/ed-orchestrate      ~/.agents/skills/ed-orchestrate
ln -s /path/to/ed-orchestation/ed-orchestrate-init ~/.agents/skills/ed-orchestrate-init
```

### For Claude Code

```bash
mkdir -p ~/.claude/skills
ln -s /path/to/ed-orchestation/ed-orchestrate      ~/.claude/skills/ed-orchestrate
ln -s /path/to/ed-orchestation/ed-orchestrate-init ~/.claude/skills/ed-orchestrate-init
```

`ed-orchestrate-init` requires `ed-orchestrate` installed alongside it — it reuses
`ed-orchestrate/scripts/validate_agents_json.py` as the canonical config validator.

## Usage

In a project you want to delegate work in, run `ed-orchestrate-init` once to build
a roster, then say things like "hand off writing tests to the tester role" or
"supervise the coder on implementing X" — see `ed-orchestrate/AGENTS.md` for the
full flow.
