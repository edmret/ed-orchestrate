# Orca delegation patterns

Decision table mapping `(delegationMode, worktreeStrategy, harness)` to which orca
subsystem and flag *category* to use. Deliberately stops short of literal flag
spelling — that always comes from the live `orca skills get orca-cli` /
`orca skills get orchestration` fetch (`ed-orchestrate/AGENTS.md` step 5), never
from this file.

| Role config | What to do |
|---|---|
| `handoff` + `worktreeStrategy: new-top-level` | After `orca skills get orca-cli`: create a new parentless worktree with `--agent <harness>` and a prompt built from the task + role's `systemPromptSeed`, using whatever that live guide currently calls the "no parent" flag. |
| `handoff` + `worktreeStrategy: new-child` | Same, but as a child of the current worktree, per the guide's child-worktree flag. |
| `handoff` + `worktreeStrategy: current` | Skip worktree creation; target the current worktree per the guide's in-place terminal/command option. |
| `supervised` (any worktree strategy) | After `orca skills get orchestration`: `run-create` → `task-create` → `worker-start --agent <harness> [--model/--effort if harness ∈ {claude, codex, cursor}]` → `check --wait --types worker_done,escalation,question`. |
| harness ∈ `{claude, codex, cursor}` + `handoff` | Model/effort go on the harness's own CLI invocation inside `terminal create --command`, **not** on `worktree create` — that path has no `--model` flag. |
| harness ∈ `{opencode, agy, gemini, droid}` (any mode) | Model/provider must already be resolved before touching `orca` — see the matching `references/harness-<name>.md`. Never pass `--model` to `worktree create` / `worker-start` for these; per [harness-model-support.md](harness-model-support.md) it's documented as claude/codex/cursor-only. |

## Full handoff sequence (fire-and-forget)

Read the current syntax from the live guide, then follow this shape:

1. `orca worktree create --name <task-name> [worktree-strategy flag] --agent <harness> --prompt "<task brief>" --json`
2. If the harness needs a raw-argv invocation (opencode/agy/gemini/droid, or
   claude/codex/cursor with a specific model): `orca terminal create --worktree <id>
   --command '<full harness invocation>' --json`
3. `orca terminal wait --terminal <handle> --for tui-idle --timeout-ms <n> --json`
4. `orca terminal send --terminal <handle> --text "<task brief>" --enter --json`
   (only if the invocation itself didn't already carry the full prompt).
5. Report the worktree/terminal handle to the user and stop — no polling loop.

## Supervised sequence

1. `orca orchestration run-create --objective "<objective>" --json`
2. `orca orchestration task-create --spec "<worker task>" --json`
3. `orca orchestration worker-start --task <task_id> --worktree <strategy> --agent
   <harness> [--model <id> --effort <level>] --json`
4. `orca orchestration check --wait --types worker_done,escalation,question
   --timeout-ms <n> --json`
5. `orca orchestration worker-release --dispatch <dispatch_id> --json` (or
   `-retain` / `-stop` / `-abandon`, per what the live guide and the check result
   direct).
