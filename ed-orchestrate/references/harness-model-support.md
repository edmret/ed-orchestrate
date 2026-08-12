# Harness model/provider support

Which harnesses accept a `--model` flag on `orca orchestration worker-start` (the
supervised path) vs. need model/provider baked into their own invocation instead.
This table is v1's understanding, verified against orca's documented `--agent` enum
and each harness's own `--help` output where installed — but always re-confirm via
`orca skills get orca-cli` / `orca skills get orchestration` at point of use per
`ed-orchestrate/AGENTS.md` step 5, since this doc can drift and that live fetch
can't.

| harness | `--model` on `worker-start`? | provider concept | how ed-orchestrate threads model/provider |
|---|---|---|---|
| `claude` | yes | no | `worker-start --model <id>` (supervised), or the harness's own `--model` flag inside `terminal create --command` (handoff) |
| `codex` | yes | no | same, plus `-c model_reasoning_effort=<effort>` for effort, threaded via raw argv in `terminal create --command` |
| `cursor` | yes | no | `worker-start --model <id>` |
| `opencode` | **no** | yes — `~/.config/opencode/opencode.json`'s `provider` block (this user has a custom `nan` provider plus local `ollama`) | prefer a pre-generated `.opencode/agent/<role>.md` (model baked into frontmatter, see [harness-opencode.md](harness-opencode.md)) and pass `--agent <role>`; else raw argv `opencode run "<prompt>" --agent <role> --model <provider>/<model>` via `terminal create --command` |
| `agy` | **no** (no confirmed native orca `--agent` id either — see below) | no separate `--provider` flag; the model string is self-contained, e.g. `gemini-3.6-flash-high`, `claude-sonnet-4-6` | raw argv `orca terminal create --command 'agy -p "<prompt>" --model <model> --effort <effort>'` — see [harness-agy.md](harness-agy.md) |
| `gemini` | unconfirmed — not installed on this machine | unconfirmed | raw-argv fallback until confirmed via `gemini --help` + a live `orca skills get` fetch on a machine that has it |
| `droid` | unconfirmed — not installed on this machine | unconfirmed | raw-argv fallback until confirmed |

## On `agy`'s orca `--agent` id

Orca's own documented `--agent` enum is `claude, codex, omp, pi, grok, opencode,
cursor, gemini, droid` — there is **no confirmed native `agy` id** in that list.
Rather than gate the whole agy path on that, `ed-orchestrate` always uses the
raw-argv `orca terminal create --command '...'` path for agy, which works
regardless of whether orca has a native short id for it (that path takes any literal
command string). Re-check at point of use whether a native id now exists — the live
`orca skills get orca-cli` fetch is the authority, not this file.

## Installed locally (confirmed)

`orca`, `opencode`, `agy`, `cursor`, `python3`. **Not installed on this machine**:
`codex`, `gemini`, `droid` — their reference docs are marked unverified rather than
asserting flags that were never actually run.
