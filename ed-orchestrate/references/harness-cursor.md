# harness: cursor

Installed locally (`cursor` binary confirmed present). Supported natively via
`--model` on `orca orchestration worker-start` (supervised), per orca's documented
`--agent` enum. No separate provider concept documented. Confirm exact flag spelling
via `cursor --help` and the live `orca skills get orca-cli` output before relying on
a specific model id string, since those drift independently of this doc.
