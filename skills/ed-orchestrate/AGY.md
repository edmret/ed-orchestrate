# ed-orchestrate — Antigravity/agy overlay

Shared core: [AGENTS.md](AGENTS.md). Reached here via the same `AGENTS.md` auto-load
convention agy/Antigravity IDE already use for plain-prose project instructions —
there's no frontmatter parsing on this host either.

- **Step 2 (role disambiguation)**: no structured multiple-choice tool assumed. Ask
  as a numbered plain-text list and wait for the typed reply.
- **Step 7 (confirm before running)**: no Bash pre-approval gate assumed. Print the
  exact resolved command and ask in plain text — "Run this? yes/no" — and wait for
  an explicit yes before executing. The typed confirmation is the intended gate, not
  an obstacle to route around: never add `--dangerously-skip-permissions` (or any
  harness's equivalent) on your own to skip it. A role's configured `cliFlags` — e.g.
  the flag headless agy needs to read/write files at all
  (`references/harness-agy.md`) — are part of the shown command and are fine.
