# harness: agy (Antigravity)

Installed locally (`agy` binary confirmed present, verified via `agy --help`). No
confirmed native orca `--agent` id (see
[harness-model-support.md](harness-model-support.md)) — always use the raw-argv
`orca terminal create --command '...'` path for agy, not `worktree create --agent
agy` (which may not resolve to anything).

## Verified flags

- `-p` / `--print` / `--prompt` — run once, print response (headless mode; use this
  for delegation, not the interactive default).
- `--model <id>` — flat model-id string, provider is implicit in the id (e.g.
  `gemini-3.6-flash-high`, `claude-sonnet-4-6`, `gpt-oss-120b-medium`). **No separate
  `--provider` flag exists for agy** — do not ask for one in the interview, and leave
  `provider: null` for agy-harness roles in `agents.json`.
- `--effort low|medium|high` — reasoning effort.
- `--mode accept-edits|plan`.
- `--output-format text|json|stream-json`.
- `--project <id>`, `--add-dir <path>`, `--conversation`/`--continue`/`-c`,
  `--sandbox`.
- `--dangerously-skip-permissions` — exists, but `ed-orchestrate` must never pass
  this to route around its own confirm-before-run step (see `AGY.md` overlay).

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
orca terminal create --worktree <id> --command 'agy -p "<task prompt>" --model <model> --effort <effort>' --json
```
