# ed-orchestrate-init — Claude Code overlay

Shared core: [AGENTS.md](AGENTS.md).

Use the real `AskUserQuestion` tool for every structured question in the flow
(steps 1, 2, 3's calls A/B and agy headless-flag question, 3b, 4, 5f/5g's
yes/no/explain questions, and 5h's agy-permissions question) — exactly as scripted in
[references/interview-flow.md](references/interview-flow.md): the given headers,
question text, options, and `multiSelect` flags. Use plain conversational turns
(not `AskUserQuestion`) for the free-text prompts: step 3's description /
accept-defaults exchange, step 5f's path-glob prompt, step 5g's memory-directory
prompt, step 5h's Orca-worktrees-dir prompt, step 5d3's delete-duplicate prompt, and the custom-role name if "Other" is chosen in step 2.
