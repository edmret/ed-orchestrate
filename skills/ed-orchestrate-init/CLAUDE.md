# ed-orchestrate-init — Claude Code overlay

Shared core: [AGENTS.md](AGENTS.md).

Use the real `AskUserQuestion` tool for every structured question in the flow
(steps 1, 2, 3's calls A/B, 3b, 4, and 5f/5g's yes/no/explain questions) — exactly as scripted in
[references/interview-flow.md](references/interview-flow.md): the given headers,
question text, options, and `multiSelect` flags. Use plain conversational turns
(not `AskUserQuestion`) for the free-text prompts: step 3's description /
accept-defaults exchange, step 5f's path-glob prompt, step 5g's memory-directory
prompt, and the custom-role name if "Other" is chosen in step 2.
