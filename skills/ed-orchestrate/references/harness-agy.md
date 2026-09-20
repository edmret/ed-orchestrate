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
- `--dangerously-skip-permissions` — exists, but `ed-orchestrate` must never pass
  this to route around its own confirm-before-run step (see `AGY.md` overlay). It is
  also unnecessary: the settings-file allow-list below achieves unattended runs
  without disabling the guard, and that guard has caught real agent mistakes
  (hallucinated out-of-repo paths).

## Unattended (headless) runs — permissions config

Verified empirically. Config lives at `~/.gemini/antigravity-cli/settings.json`.
**`~/.gemini/settings.json` is stale gemini-cli-era config and is NOT read** — editing
it has no effect; this is a common false lead after the gemini-cli → Antigravity
rename.

Two independent gates, both must pass or headless `-p` dies with
`permission check failed ... user denied permission`:

1. **Workspace** — `trustedWorkspaces: [<repo paths>]` governs file read/write inside
   a workspace. It only applies to the *active* workspace, so it does nothing unless
   the run also passes `--add-dir <repo>` (see above). With both in place,
   `read_file`/`write_file` inside the repo need no allow-list entry.
2. **Commands** — `permissions.allow: ["command(<binary>)", ...]` gates shell commands
   by binary name. Anything unlisted is denied. The **entire command line** is
   evaluated, so a compound like `pwd && ls -la ..` is refused when `ls` is allowed but
   `pwd` is not. Beyond build/VCS tools, include the shell verbs review-type agents
   reach for: `wc`, `pwd`, `sort`, `uniq`, `diff`, `awk`, `jq`, `basename`, `dirname`,
   `tr`, `cut`.

Paths outside the workspace are always refused (e.g. anything under `/tmp` unless
explicitly allow-listed) — so hand agy its inputs *inside* the repo, not in `/tmp`.

`agy agent` / `agy agents` (list available agents) exists but returned nothing on
this machine — no agent-definition subcommand or file format has been found for agy.
Treat `agy` as a raw-argv-only harness with no native per-project agent-definition
schema to auto-generate (unlike opencode).

## AGENTS.md auto-load

Both `agy` CLI and Antigravity IDE auto-load `AGENTS.md` / `GEMINI.md` by walking up
from cwd to repo root — but strictly as free-form instruction prose. "Standalone
GEMINI.md/AGENTS.md files do not support frontmatter and are always active." This is
exactly the mechanism `ed-orchestrate`'s generated roster block relies on to reach
agy — see [agents-md-block-format.md](agents-md-block-format.md) — but it means agy
itself has no structured way to read `agents.json` directly; it only sees the
rendered prose table.

## Example raw-argv invocation

```
orca terminal create --worktree <id> --command 'agy -p "<task prompt>" --model <model> --add-dir <repo-root>' --json
```

`--add-dir <repo-root>` is mandatory (see above). Append `--effort <level>` only when
the chosen model actually accepts it — models whose id already encodes the level
reject the flag outright.
