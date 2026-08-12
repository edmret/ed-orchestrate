# ed-orchestrate — opencode overlay

Shared core: [AGENTS.md](AGENTS.md). Reached here via opencode's `AGENTS.md`
auto-load convention — there's no `SKILL.md` frontmatter parsing on this host, so
trigger matching happens by you reading the roster block prose in the target
project's own `AGENTS.md`, not this repo's frontmatter.

- **Step 2 (role disambiguation)**: you likely don't have a structured multiple-choice
  tool. Ask as a numbered plain-text list ("1) coder 2) tester — or name another
  role") and wait for the typed reply.
- **Step 7 (confirm before running)**: you likely don't have a Bash pre-approval
  gate. Print the exact resolved command and ask in plain text — "Run this? yes/no"
  — and wait for an explicit yes before executing. This confirmation *is* the
  dry-run switch; there is no separate flag for it.
