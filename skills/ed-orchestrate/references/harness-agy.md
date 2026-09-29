# harness: agy (Antigravity)

Installed locally (`agy` binary confirmed present, verified via `agy --help`). No
confirmed native orca `--agent` id (see
[harness-model-support.md](harness-model-support.md)) — always use the raw-argv
`orca terminal create --command '...'` path for agy, not `worktree create --agent
agy` (which may not resolve to anything).

## Verified flags

- `-p` / `--print` / `--prompt` — run once, print response (headless mode; use this
  for delegation, not the interactive default).
- `--model <id>` — flat model-id string, provider is implicit in the id. **Always
  confirm the exact id with `agy models` before using one** — ids that look plausible
  are often wrong (e.g. `claude-opus-4-6` does NOT exist; the real id is
  `claude-opus-4-6-thinking`), and a bad id fails the launch with
  `invalid model selection`. **No separate `--provider` flag exists for agy** — do not
  ask for one in the interview, and leave `provider: null` for agy-harness roles in
  `agents.json`.
- `--effort low|medium|high` — reasoning effort. **Not accepted by every model**: ids
  that already encode the level (e.g. `gemini-3.7-flash-high`) reject it with
  `--effort is not supported for model ...`. For those, leave `effort: null` in
  `agents.json` and omit the flag.
- `--add-dir <path>` — **required for headless delegation.** agy does NOT inherit the
  shell's cwd: without it, `git` reports "not a git repository" and files inside the
  repo are refused even when the repo is listed in `trustedWorkspaces`. Always pass the
  repo root.
- `--mode accept-edits|plan`.
- `--output-format text|json|stream-json`.
- `--project <id>`, `--add-dir <path>`, `--conversation`/`--continue`/`-c`,
  `--sandbox`.
- `--dangerously-skip-permissions` — **required for headless (`-p`) delegation
  that reads or writes files.** Verified 2026-09-18 in a real project: print mode
  has no TTY to show the interactive permission prompt, so it silently denies
  every `read_file`/`write_file` call regardless of `trustedWorkspaces` /
  `permissions.allow`; with the flag, the same read succeeds. Put it in the role's
  `cliFlags` (`ed-orchestrate-init` suggests this for agy roles) — it is part of
  the role's invocation, **not** a way around `ed-orchestrate`'s own
  confirm-before-run step, which still happens (see `AGY.md` overlay). Even with
  the flag, the command allow-list below still applies.

## Unattended (headless) runs — permissions config

Verified empirically. Config lives at `~/.gemini/antigravity-cli/settings.json`.
**`~/.gemini/settings.json` is stale gemini-cli-era config and is NOT read** — editing
it has no effect; this is a common false lead after the gemini-cli → Antigravity
rename.

Gates, all must pass or headless `-p` dies with `permission check failed ...
user denied permission` (or ends with "jetski: no output produced"):

1. **Interactive-prompt gate** — lifted only by `--dangerously-skip-permissions`
   (see above); without it every file read/write is denied in print mode.
2. **Workspace** — `trustedWorkspaces: [<repo paths>]` plus `read_file(<path>)` /
   `write_file(<path>)` entries in `permissions.allow`. It only applies to the
   *active* workspace, so the run must also pass `--add-dir <repo>`. **Every new
   project needs its own entries — for the repo AND for the directory its Orca
   worktrees live in** (worktrees are separate paths). This is the recurring
   "worker can't write in a new project" failure; `ed-orchestrate-init` offers to
   add them (`scripts/ensure_harness_permissions.py agy`).
3. **Commands** — `permissions.allow: ["command(<binary>)", ...]` gates shell
   commands by their **first word**. Anything unlisted is denied, so env-var
   prefixes (`FOO=1 npx …` — first word `FOO=1`), `cd <dir> && …` (unless `cd` is
   listed), pipes, brace expansion and compound one-liners die. Put env prefixes
   inside an `npm run` script, prefer single commands, and allow-list the shell
   verbs review-type agents reach for: `wc`, `pwd`, `sort`, `uniq`, `diff`, `awk`,
   `jq`, `basename`, `dirname`, `tr`, `cut`, `cd`.

Paths outside the workspace are always refused (e.g. anything under `/tmp` unless
explicitly allow-listed) — so hand agy its inputs *inside* the repo, not in `/tmp`.

`agy agent` / `agy agents` (list available agents) exists but returned nothing on
this machine — no agent-definition subcommand or file format has been found for agy.
Treat `agy` as a raw-argv-only harness with no native per-project agent-definition
schema to auto-generate (unlike opencode).

## AGENTS.md auto-load

Both `agy` CLI and Antigravity IDE auto-load `AGENTS.md` / `GEMINI.md` by walking up
from cwd to repo root (gemini-cli, by contrast, loads only `GEMINI.md` unless the
project's `.gemini/settings.json` lists `AGENTS.md` under `context.fileName` —
`ed-orchestrate-init` always sets that, see `scripts/ensure_gemini_context.py`) — but strictly as free-form instruction prose. "Standalone
GEMINI.md/AGENTS.md files do not support frontmatter and are always active." This is
exactly the mechanism `ed-orchestrate`'s generated roster block relies on to reach
agy — see [agents-md-block-format.md](agents-md-block-format.md) — but it means agy
itself has no structured way to read `agents.json` directly; it only sees the
rendered prose table.

## Example raw-argv invocation

```
orca terminal create --worktree <id> --command 'agy -p "<task prompt>" --model <model> --add-dir <repo-root> --dangerously-skip-permissions' --json
```

`--add-dir <repo-root>` is mandatory, and `--dangerously-skip-permissions` comes
from the role's `cliFlags` (see above). Append `--effort <level>` only when
the chosen model actually accepts it — models whose id already encodes the level
reject the flag outright.
