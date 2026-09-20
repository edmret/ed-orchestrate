# harness: gemini

**Not installed on this machine — unverified.** Confirm flags via `gemini --help`
and the live `orca skills get orca-cli` output before relying on this doc.

`gemini` is a recognized id in orca's documented `--agent` enum, but no model/effort
flag support has been confirmed for it (unlike claude/codex/cursor). Treat as a
raw-argv-only harness (pass the full `gemini ...` invocation, including whatever its
own model flag turns out to be, via `orca terminal create --command`) until
confirmed otherwise on a machine that has `gemini` installed.
