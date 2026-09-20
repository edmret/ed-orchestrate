# ed-orchestrate-init — opencode overlay

Shared core: [AGENTS.md](AGENTS.md). Reached via opencode's `AGENTS.md`
auto-load convention, not `SKILL.md` frontmatter parsing.

No structured multi-choice tool assumed on this host. For every question marked
"structured" in [references/interview-flow.md](references/interview-flow.md),
ask it as a numbered plain-text list in the chat (e.g. "1) claude 2) codex
3) opencode 4) agy — or type another harness name") and wait for the user's
typed reply before continuing. Everything downstream — schema, file generation,
the AGENTS.md splice — is identical to the Claude Code flow.
