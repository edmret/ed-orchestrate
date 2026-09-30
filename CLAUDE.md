# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A pair of Claude Code **skills** living under `skills/` (not an app — no build, no
runtime, no test suite). Plain markdown + a few standalone Python scripts. The
`skills/` layout (rather than skills at the repo root) is deliberate — it's what the
[skills.sh](https://www.skills.sh) `npx skills` CLI's discovery expects
(`skills/<name>/SKILL.md`), so this repo installs with `npx skills add
edmret/ed-multi-ai` from anywhere, in addition to the manual symlink method below.
See [README.md](README.md) for both install paths.

Manual install — symlink into `~/.agents/skills/` (for Antigravity/AGY CLI via
`~/.gemini/config/skills` symlink) and/or `~/.claude/skills/`:

```bash
# Antigravity / AGY CLI (via ~/.agents/skills -> ~/.gemini/config/skills)
ln -s ../../ed-orchestation/skills/ed-orchestrate      ~/.agents/skills/ed-orchestrate
ln -s ../../ed-orchestation/skills/ed-orchestrate-init ~/.agents/skills/ed-orchestrate-init

# Claude Code
ln -s ../../ed-orchestation/skills/ed-orchestrate      ~/.claude/skills/ed-orchestrate
ln -s ../../ed-orchestation/skills/ed-orchestrate-init ~/.claude/skills/ed-orchestrate-init
```

- **`ed-orchestrate`** — delegates a coding sub-task to a configured sub-agent role
  (coder/planner/tester/reviewer/architect/code-reviewer/designer/
  qa-designer/curator/integrator/custom). Reads the target project's
  `.orchestrate/agents.json`, resolves that role's harness/model/provider,
  and runs the matching `orca` invocation.
- **`ed-orchestrate-init`** — interviews the user to build that `agents.json` roster
  and splice a roster block into the target project's `AGENTS.md`.

`ed-orchestrate-init` depends on `ed-orchestrate` being installed alongside it — it
reuses `skills/ed-orchestrate/scripts/validate_agents_json.py` as the single source of truth
for config validation rather than duplicating that logic. Both `npx skills add` and
the manual symlinks above install them side by side, so this holds either way.

Mermaid diagrams of the init flow, graph generation/walk, Laya routing and lanes live
in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — update them when those flows change
(`setup_graph_dag.py`, `laya-route` `decide()`, `references/graph-dag.md`,
`references/laya-routing.md`).

## Running the scripts

No package manager, no deps beyond the stdlib. Run directly with `python3`
(paths below are relative to the repo root):

```
python3 skills/ed-orchestrate/scripts/validate_agents_json.py <path-to-agents.json>
python3 skills/ed-orchestrate-init/scripts/render_agents_md_block.py <agents.json> [--project-name NAME] [--splice <AGENTS.md>]
python3 skills/ed-orchestrate-init/scripts/render_opencode_agent_file.py <agents.json> <role-name> --out <path>
python3 skills/ed-orchestrate-init/scripts/setup_graph_dag.py <memory-dir> [--agents-md AGENTS.md] [--gitignore .gitignore] [--orca-yaml orca.yaml] [--no-orca-yaml] [--laya] [--laya-bin .orchestrate/bin/laya-route] [--engram | --no-engram]
python3 skills/ed-orchestrate-init/scripts/ensure_engram.py --harnesses claude,opencode,agy [--project NAME] [--config-dir .engram]
python3 skills/ed-orchestrate-init/scripts/smoke_check.py <memory-dir> --harnesses claude,opencode,codex [--print-task] [--reset]
python3 skills/ed-orchestrate-init/scripts/ensure_claude_md_import.py <CLAUDE.md path> [--import-path AGENTS.md]
python3 skills/ed-orchestrate-init/scripts/ensure_gemini_context.py [--gemini-dir .gemini] [--agents-md AGENTS.md]
python3 skills/ed-orchestrate-init/scripts/ensure_harness_permissions.py opencode [opencode.json]
python3 skills/ed-orchestrate-init/scripts/ensure_harness_permissions.py codex [.orchestrate/agents.json] [--memory-dir .ai-memory]
python3 skills/ed-orchestrate-init/scripts/ensure_harness_permissions.py agy [<agy settings.json>] --path <dir> [--from-git-worktrees] [--baseline-commands]
```

There's no test suite in this repo — validate changes to a script by running it
against a real or hand-crafted `agents.json` (or, for `setup_graph_dag.py`, a
scratch directory with a hand-crafted `AGENTS.md`/`.gitignore`/`orca.yaml`; for
the `ensure_*` scripts, scratch copies of the files they merge into — never the
real `~/.gemini/antigravity-cli/settings.json`) and checking exit code / stderr
output, and that re-running is a no-op. `skills/ed-orchestrate-init/assets/laya-route`
(the router template `setup_graph_dag.py --laya` installs) has no `.py`
extension — load it with `importlib.machinery.SourceFileLoader` to exercise
`decide()` with stubbed Laya answers, and point `LAYA_URL` at a closed port to
exercise the path-facts fallback.

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

`skills/ed-orchestrate/AGENTS.md` explicitly forbids hardcoding `orca` subcommand syntax
anywhere in this repo. The real CLI surface is always fetched live at delegation
time via `orca skills get orca-cli` (and `orca skills get orchestration` for
supervised runs) so these skills can't drift from the binary that actually runs the
command. Preserve this — don't "helpfully" inline example `orca` invocations as if
they were canonical.

### `agents.json` is the roster's single source of truth

`ed-orchestrate-init` writes `.orchestrate/agents.json` in the *target*
project (not this repo) and derives the `AGENTS.md` roster block and, for
`opencode`-harness roles, a native `.opencode/agent/<role>.md` file, from it.
`skills/ed-orchestrate/scripts/validate_agents_json.py` defines the schema in code — see
`skills/ed-orchestrate/references/agents-json-schema.md` for the human-readable version.
Required per-role fields: `description`, `harness`, `model`, `provider`, `effort`,
`tools`, `systemPromptSeed`, `worktreeStrategy`, `delegationMode`. Optional:
`fallbacks` — an array of alternate bindings, either same-harness (no `harness`
key: a provider/model retry pair for when the primary provider is unavailable)
or cross-harness (explicit `harness` key, used only when a delegation names that
harness — `skills/ed-orchestrate/AGENTS.md` steps 2a/2b); `cliFlags` — extra raw CLI
flags for that role's invocation.

Built-in roles (`coder`/`planner`/`tester`/`reviewer`/`architect`/
`code-reviewer`/`designer`/`qa-designer`/`curator`/`integrator`) get their
default `description` and `systemPromptSeed` from
`skills/ed-orchestrate/references/role-defaults.md`, materialized verbatim into the project's
`agents.json` at init time. That file is the single source of truth for those
defaults — the interview's role-picker option text quotes it too. `planner`
only plans (produces a task breakdown; never implements) — the persistent,
per-session coordinator is the orchestrator, not a role in this roster (see
`skills/ed-orchestrate/references/graph-dag.md`).

Per `skills/ed-orchestrate/references/harness-model-support.md`: `--model`/`--effort` only
thread through the live `orca` invocation for `claude`, `codex`, `cursor`. For
`opencode`, `agy`, `gemini`, `droid`, model selection instead goes through a
per-harness reference file or a generated agent file — never assume a uniform
`--model` flag works across harnesses.

The `AGENTS.md` roster block written into a target project is spliced idempotently
between `<!-- BEGIN:ed-orchestrate-roster -->` / `<!-- END:ed-orchestrate-roster -->`
markers (`skills/ed-orchestrate-init/scripts/render_agents_md_block.py`) — content outside
that span must never be touched by regeneration.

### `ed-orchestrate-init` always fixes the CLAUDE.md/AGENTS.md shadow bug

Claude Code auto-loads `AGENTS.md` at session start only when **no** `CLAUDE.md`
exists anywhere on the path from the working directory up. Any target project with
its own `CLAUDE.md` — common, and never in this skill's control — silently shadows
the `AGENTS.md` roster/graph-DAG blocks entirely, so nothing written there is ever
read automatically; a user would have to manually tell Claude to read `AGENTS.md`
every session. `ed-orchestrate-init` step 5's `d2` fixes this unconditionally (not
an opt-in question) by splicing a small `@AGENTS.md` import into the target
`CLAUDE.md` (`skills/ed-orchestrate-init/scripts/ensure_claude_md_import.py`,
creating the file if missing) — Claude Code resolves `@path` imports regardless of
the shadowing rule. Preserve this step; don't make it optional.

### `ed-orchestrate-init` also fixes Gemini loading and worker write permissions

Same class of silent failure as the shadow bug, same always-on treatment:
`ensure_gemini_context.py` (step 5d3) makes gemini-cli/agy load `AGENTS.md` via
`.gemini/settings.json` `context.fileName` plus a thin `.gemini/GEMINI.md` pointer;
`ensure_harness_permissions.py` (step 5h) sets opencode's
`permission.external_directory: "allow"` (worktree-shared dirs are symlinks that
resolve outside the worktree) and — asked, since the file is user-global — adds
agy's per-project `read_file`/`write_file`/`trustedWorkspaces` entries. Headless
agy also needs `--dangerously-skip-permissions`, carried as binding-scoped
`cliFlags` (a cross-harness fallback does not inherit the role's flags); the
validator warns when an agy binding lacks it.

### Graph-DAG block carries the workflow; Laya is its optional front door

`setup_graph_dag.py`'s AGENTS.md block is where the orchestrator workflow lives
(orchestrator guard, worker rules, once-per-batch integration + review, lanes) —
it's regenerated on every init re-run, so workflow changes land there, not in
per-project hand edits. Templates are only ever created, never overwritten:
the project owns and tunes its copies, including the installed `laya-route`.

### v1 scope limits (intentional, not gaps to "fix")

- `ed-orchestrate-init` supports adding at most one custom role beyond the ten
  built-ins (`coder`, `planner`, `tester`, `reviewer`, `architect`,
  `code-reviewer`, `designer`, `qa-designer`, `curator`, `integrator`) per
  interview pass.
- Native per-harness agent-file generation is opencode-only; every other harness
  relies solely on `agents.json` + the AGENTS.md roster block.
