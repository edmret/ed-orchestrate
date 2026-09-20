# ed-orchestrate — Claude Code overlay

Shared core: [AGENTS.md](AGENTS.md).

- **Step 2 (role disambiguation)**: use the real `AskUserQuestion` tool — one
  question, options built from the candidate role names + descriptions.
- **Step 7 (confirm before running)**: the Bash tool's own permission prompt is the
  execution gate. Render the resolved command, then call Bash — the user approves or
  denies at that point. No extra chat confirmation step needed on top of it.
