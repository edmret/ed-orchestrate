# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A pair of Claude Code **skills** (not an app — no build, no runtime, no test suite).
They're distributed as plain markdown + a few standalone Python scripts, meant to be
symlinked into `~/.claude/skills/`:

```
ln -s ../../ed-orchestation/ed-orchestrate      ~/.claude/skills/ed-orchestrate
ln -s ../../ed-orchestation/ed-orchestrate-init ~/.claude/skills/ed-orchestrate-init
```

- **`ed-orchestrate`** — delegates a coding sub-task to a configured sub-agent role
  (coder/planner/tester/reviewer/custom). Reads the target project's
  `.orchestrate/agents.json`, resolves that role's harness/model/provider,
  and runs the matching `orca` invocation.
- **`ed-orchestrate-init`** — interviews the user to build that `agents.json` roster
  and splice a roster block into the target project's `AGENTS.md`.

`ed-orchestrate-init` depends on `ed-orchestrate` being installed alongside it — it
reuses `ed-orchestrate/scripts/validate_agents_json.py` as the single source of truth
for config validation rather than duplicating that logic.

## Running the scripts

No package manager, no deps beyond the stdlib. Run directly with `python3`:

```
python3 ed-orchestrate/scripts/validate_agents_json.py <path-to-agents.json>
python3 ed-orchestrate-init/scripts/render_agents_md_block.py <agents.json> [--project-name NAME] [--splice <AGENTS.md>]
python3 ed-orchestrate-init/scripts/render_opencode_agent_file.py <agents.json> <role-name> --out <path>
```

There's no test suite in this repo — validate changes to a script by running it
against a real or hand-crafted `agents.json` and checking exit code / stderr output.

## Architecture

### Discovery-stub pattern

Every skill directory follows the same layered structure, and it's intentional —
don't collapse it:

- **`SKILL.md`** — the file Claude Code loads for skill discovery. It's a thin stub:
  frontmatter (`name`, `description`, `argument-hint`) used for matching user intent,
  plus pointers to `AGENTS.md` and the host overlay. It intentionally contains almost
  no procedural content.
- **`AGENTS.md`** — the shared, host-agnostic procedure (the numbered steps of the
  actual flow). This is what other hosts (opencode, Antigravity/agy) load natively
  via their own `AGENTS.md` auto-load convention, so it must stay host-neutral.
- **`CLAUDE.md` / `OPENCODE.md` / `AGY.md`** — per-host overlays, each just a few
  lines noting where that host's mechanics differ from the shared `AGENTS.md` flow
  (e.g. how a "structured question" or a "confirm before running" gate is
  implemented on that host). Never duplicate the shared procedure into an overlay —
  overlays only state deltas.
- **`references/*.md`** — detail that would bloat the main flow if inlined (schema
  definitions, per-harness capability notes, the exact interview question script).
  `AGENTS.md` points into these rather than embedding them.

When editing a flow, change it once in `AGENTS.md`; only touch an overlay file if
the behavior genuinely differs per host.

### Never hardcode the `orca` CLI surface

`ed-orchestrate/AGENTS.md` explicitly forbids hardcoding `orca` subcommand syntax
anywhere in this repo. The real CLI surface is always fetched live at delegation
time via `orca skills get orca-cli` (and `orca skills get orchestration` for
supervised runs) so these skills can't drift from the binary that actually runs the
command. Preserve this — don't "helpfully" inline example `orca` invocations as if
they were canonical.

### `agents.json` is the roster's single source of truth

`ed-orchestrate-init` writes `.orchestrate/agents.json` in the *target*
project (not this repo) and derives the `AGENTS.md` roster block and, for
`opencode`-harness roles, a native `.opencode/agent/<role>.md` file, from it.
`ed-orchestrate/scripts/validate_agents_json.py` defines the schema in code — see
`ed-orchestrate/references/agents-json-schema.md` for the human-readable version.
Required per-role fields: `description`, `harness`, `model`, `provider`, `effort`,
`tools`, `systemPromptSeed`, `worktreeStrategy`, `delegationMode`. Optional:
`fallbacks` — alternate `harness`/`model`/`provider`/`effort` bindings used when a
delegation names a harness other than the role's primary one
(`ed-orchestrate/AGENTS.md` step 2a).

Built-in roles (`coder`/`planner`/`tester`/`reviewer`) get their default
`description` and `systemPromptSeed` from
`ed-orchestrate/references/role-defaults.md`, materialized verbatim into the project's
`agents.json` at init time. That file is the single source of truth for those
defaults — the interview's role-picker option text quotes it too.

Per `ed-orchestrate/references/harness-model-support.md`: `--model`/`--effort` only
thread through the live `orca` invocation for `claude`, `codex`, `cursor`. For
`opencode`, `agy`, `gemini`, `droid`, model selection instead goes through a
per-harness reference file or a generated agent file — never assume a uniform
`--model` flag works across harnesses.

The `AGENTS.md` roster block written into a target project is spliced idempotently
between `<!-- BEGIN:ed-orchestrate-roster -->` / `<!-- END:ed-orchestrate-roster -->`
markers (`ed-orchestrate-init/scripts/render_agents_md_block.py`) — content outside
that span must never be touched by regeneration.

### v1 scope limits (intentional, not gaps to "fix")

- `ed-orchestrate-init` supports adding at most one custom role beyond the four
  built-ins (`coder`, `planner`, `tester`, `reviewer`) per interview pass.
- Native per-harness agent-file generation is opencode-only; every other harness
  relies solely on `agents.json` + the AGENTS.md roster block.
