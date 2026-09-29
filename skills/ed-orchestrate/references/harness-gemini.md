# harness: gemini

**Not installed on this machine — unverified.** Confirm flags via `gemini --help`
and the live `orca skills get orca-cli` output before relying on this doc.

`gemini` is a recognized id in orca's documented `--agent` enum, but no model/effort
flag support has been confirmed for it (unlike claude/codex/cursor). Treat as a
raw-argv-only harness (pass the full `gemini ...` invocation, including whatever its
own model flag turns out to be, via `orca terminal create --command`) until
confirmed otherwise on a machine that has `gemini` installed.

## Project context files (applies to agy too)

gemini-cli reads only `GEMINI.md` by default, so the roster and graph-DAG blocks
`ed-orchestrate-init` splices into `AGENTS.md` would be invisible to it. Init
therefore always runs `ed-orchestrate-init/scripts/ensure_gemini_context.py`,
which:

- merges `"context": {"fileName": ["AGENTS.md", "GEMINI.md"]}` into the project's
  `.gemini/settings.json` (other keys, e.g. `mcpServers`, preserved);
- splices a thin pointer block into `.gemini/GEMINI.md` — "read AGENTS.md", the
  "are you the orchestrator?" guard, and agy headless notes — instead of a
  duplicated copy of the project's conventions that drifts from `AGENTS.md`.
