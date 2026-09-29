# harness: opencode

Installed locally (`opencode` binary confirmed present, verified via `opencode
--help`/`opencode run --help`). No native `--model` on `orca worktree create` /
`orca orchestration worker-start` — model+provider must be baked into opencode's own
invocation.

## Per-project agent file schema (verified, real prior art)

`.opencode/agent/<name>.md` — identical format already in use in this user's
`new-proy` and `historiador` projects:

```markdown
---
description: <role.description>
mode: all
model: <provider>/<model>
tools:
  bash: true
  read: true
  edit: true
  glob: true
  grep: true
---
<role.systemPromptSeed>
```

`mode: all` (or `primary`) is required — `all` lets the same file serve both as a
top-level `opencode run --agent <name>` session and as a subagent. opencode's CLI
refuses to run a `subagent`-mode agent as a top-level session and silently
falls back to its own default agent/model instead, which would otherwise
discard the role's configured harness/model without any hard error. Confirmed
against `opencode run --agent <role>`: it prints `agent "<role>" is a
subagent, not a primary agent. Falling back to default agent` and the
delegation quietly runs on the wrong model.

`model:` is a `<provider>/<model>` string, e.g. `nan/qwen3.6`. `ed-orchestrate-init`
auto-generates this file for every `opencode`-harness role (see
`ed-orchestrate-init/references/opencode-agent-file-template.md`), asking before
overwriting an existing hand-maintained file of the same name.

## Project permissions — writes through the shared memory symlink

In an Orca worktree the shared task-memory dir (e.g. `.ai-memory`, shared via
`orca.yaml` `worktree.sharedDirectories`) is a symlink that resolves **outside**
the worktree. opencode classifies that as `external_directory`, and in
`opencode run` (no TTY to prompt) it auto-rejects the read/write — the worker
exits 0 having changed nothing, or can't write its task-node report. Fix, in
the project's `opencode.json`:

```json
{ "permission": { "external_directory": "allow" } }
```

`ed-orchestrate-init` writes this (`scripts/ensure_harness_permissions.py
opencode`) when any role or fallback runs on opencode.

## Operating notes (verified in real batches)

- **Stagger parallel `opencode run` starts by ≥ 30 s** — simultaneous starts
  contend on the shared SQLite session store and one dies with `database is
  locked`. A large `opencode.db` makes it likelier; prune between milestones.
- **Never kill a tool process inside a running session** (e.g. `pkill` its test
  run): the tool call never resolves and the session wedges silently. Message
  the agent, or close the terminal and relaunch with a resume brief.
- **`orca terminal wait --for exit` is unreliable for `opencode run`** — poll
  `orca terminal read --limit <n>` for the run's summary and the returning shell
  prompt instead.
- **Keep the prompt free of shell metacharacters.** Passed inline through
  `terminal create --command`, a `!` triggers zsh history expansion and the
  invocation never runs. Write the brief to a file and dispatch a pointer.

## Global provider config

`~/.config/opencode/opencode.json`, `provider.<name>.models` — this user has a
custom `nan` provider (OpenAI-compatible endpoint) with models `qwen3.6`, `gemma4`,
`deepseek-v4-flash`, `deepseek-v4-flash-0731`, `mimo-v2.5`, plus a local `ollama`
provider (`deepseek-r1:14b`, `gemma3:27b`, `glm-4.7-flash`, `qwen3:14b`).
`ed-orchestrate-init` reads this file to offer real `provider/model` choices during
the interview instead of asking the user to type one blind.

## CLI (raw-argv fallback, or when no agent file exists yet)

```
opencode run "<task prompt>" --agent <role-name> --model <provider>/<model>
```

Other relevant flags: `--format json` (scriptable output), `--auto` (auto-approve
permissions — do not use this to bypass `ed-orchestrate`'s own confirm-before-run
step), `--variant` (reasoning effort). Threaded via `orca terminal create --command`
for the handoff path, since `worktree create`/`worker-start` don't support opencode
model selection directly.
