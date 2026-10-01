# harness: codex

Verified on codex-cli 0.159.1 (macOS). Re-check flags with `codex --help` and the live
`orca skills get orca-cli` output if your version differs.

Per orca's documented `--agent` enum, `codex` is a recognized harness id. Supported
natively via `--model` on `orca orchestration worker-start` (supervised). For
reasoning effort specifically, orca's docs describe threading Codex's own
`-c model_reasoning_effort="<level>"` as raw argv inside `orca terminal create
--command 'codex --model <id> -c model_reasoning_effort="<level>"'` for the handoff
path, since `worktree create` has no effort flag of its own.

## Instructions file: `AGENTS.md` is enough

Codex loads `AGENTS.md` natively (plus a user-global `~/.codex/AGENTS.md`); no
`CODEX.md`/bridge file is needed, unlike Claude Code (`CLAUDE.md` shadows it) and
gemini/agy (read only `GEMINI.md`). The binary also supports `AGENTS.override.md` and
`project_doc_fallback_filenames` in `~/.codex/config.toml`, unused here.

**Size cap**: Codex reads at most `project_doc_max_bytes` of project docs — the binary
carries the constant `32768`, so the default is presumably 32 KiB (not confirmed from
docs). A large `AGENTS.md` (roster + graph block + Engram + project rules) can exceed
that and the tail may be ignored. `ed-orchestrate-init` warns when it writes an
`AGENTS.md` over 30 000 bytes. Fixes: move project-specific prose out of `AGENTS.md`
(e.g. into `CLAUDE.md` / linked docs), or raise `project_doc_max_bytes`.

## Project permissions — writes through the shared memory symlink

Verified with `codex exec -s workspace-write` in a linked git worktree whose
`.ai-memory` is a symlink into the main checkout:

- no extra flag → `zsh:1: operation not permitted: .ai-memory/probe.txt` (the worker
  reports FAILED, or changes nothing). A write under the system temp dir succeeded
  without the flag (apparently exempt), so test under your home directory, not `/tmp`.
- `--add-dir <absolute real path of main/.ai-memory>` → write succeeds.
- `--add-dir .ai-memory` (the symlink path) → rejected: `symlinked writable roots are
  not supported`. The target must be the **resolved** path.

So the role's `cliFlags` carry `--add-dir "$(readlink -f .ai-memory)"` — `cliFlags` are
appended verbatim to the shell command, and the substitution is evaluated in the
worktree the command runs in, so it is machine-independent. `ed-orchestrate-init`
step 5h writes it (`scripts/ensure_harness_permissions.py codex`), and the validator
warns when a codex binding lacks `--add-dir`. A cross-harness codex fallback does not
inherit the role's flags; the script writes each binding's own.

`codex exec` defaults to a read-only sandbox: a writing role (`coder`, `tester`,
`integrator`) also needs `-s workspace-write` (or the equivalent config) in the
invocation. Verified only for `codex exec`; interactive `codex` accepts `--add-dir`
too but that path was not tested.

## Engram

`engram setup codex` configures it (`~/.codex/config.toml` gets an `engram` MCP entry).
`ensure_engram.py` reports it as missing until then.
