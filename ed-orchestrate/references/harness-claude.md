# harness: claude

Supported natively via `--model`/`--effort` on `orca orchestration worker-start`
(supervised) or the harness's own `--model` flag inside `orca terminal create
--command` (handoff) — see [orca-delegation-patterns.md](orca-delegation-patterns.md).
Always confirm exact flag spelling via the live `orca skills get orca-cli` fetch.

## Alternative: native in-process subagent (no orca)

Claude Code has its own per-project subagent format, independent of orca-mediated
delegation: `.claude/agents/<name>.md`, with frontmatter `name`, `description`,
`tools: <comma-separated list>`, `model: <short alias>` (e.g. `haiku`, `sonnet`,
`opus`), and the file body as the system prompt. This is invoked via the Agent tool
(`subagent_type: <name>`) and runs in-process — no new worktree or terminal, no
`orca` involved at all.

This is real prior art already used in this user's other projects (e.g.
`.claude/agents/coder-agent.md`), and one of those files even shells out to
`opencode run --provider nan --model qwen3.6 --task "$TASK_PROMPT"` directly from its
prompt body — a simpler, non-worktree-isolated way to bridge Claude → opencode that
predates orca-mediated delegation.

`ed-orchestrate` does not generate or manage `.claude/agents/*.md` files in v1 (only
`.opencode/agent/*.md` is auto-generated, see
[harness-opencode.md](harness-opencode.md)) — this is noted here as background for
when a `claude`-harness role might reasonably use this lighter mechanism instead of
an orca worktree, not as something the skill automates.
