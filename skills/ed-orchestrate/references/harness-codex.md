# harness: codex

**Not installed on this machine — unverified.** Confirm flags via `codex --help` and
the live `orca skills get orca-cli` output before relying on this doc.

Per orca's documented `--agent` enum, `codex` is a recognized harness id. Supported
natively via `--model` on `orca orchestration worker-start` (supervised). For
reasoning effort specifically, orca's docs describe threading Codex's own
`-c model_reasoning_effort="<level>"` as raw argv inside `orca terminal create
--command 'codex --model <id> -c model_reasoning_effort="<level>"'` for the handoff
path, since `worktree create` has no effort flag of its own.

Treat as a raw-argv-capable harness until confirmed otherwise on a machine that has
`codex` installed.
