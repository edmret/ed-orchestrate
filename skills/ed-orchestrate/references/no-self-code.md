# The orchestrator doesn't self-code (optional convention)

**The orchestrator** is not a role in `agents.json` — it's positional:
whichever harness a human is talking to directly, that was *not* itself
dispatched with a scoped role, is the orchestrator for that session. It reads
the roster, resolves roles, and calls `ed-orchestrate` to delegate; it does not
implement application code itself. `planner`, by contrast, is a role: it plans
(produces task breakdowns, or a DAG per `graph-dag.md`) but never implements
either.

Prompt convention alone ("the orchestrator shouldn't self-code") is easy to
drift from under pressure — a stuck delegation, a "just this one line" fix.
Projects that want this boundary enforced at the tool-permission layer, not
just by instruction, can add a deny rule to `.claude/settings.json` at the
target project's root:

```json
{
  "permissions": {
    "deny": ["Edit(src/**)", "Write(src/**)"]
  }
}
```

Adjust the glob(s) to whatever this project's actual source directories are —
`src/**` is illustrative, not a required path. This denies Edit/Write on those
paths for whichever Claude Code session is running as the orchestrator in that
project, regardless of what any prompt says.

**It also binds every Claude Code session in a child worktree.** `.claude/settings.json`
is git-tracked, so each Orca worktree checks out the same deny rule. Workers on
other harnesses (opencode, agy, codex, …) don't read it and are unaffected — but a
`claude`-harness role that must write those paths (`coder`, `tester`,
`integrator`, …) is blocked just like the orchestrator. If the roster has one, put
the rule in the primary checkout's gitignored `.claude/settings.local.json`
instead, and run those claude roles in their own worktree (`new-child` /
`new-top-level`) — see [harness-claude.md](harness-claude.md). The tradeoff: the
local file isn't shared with teammates or other machines, so each checkout sets
it up by hand (make sure `.claude/settings.local.json` is gitignored).

This is optional and not applied by `ed-orchestrate-init` automatically — it's
a per-project choice, since some projects want the orchestrator able to make
small direct edits (e.g. tests, config) and only delegate substantial
implementation work. If a project wants this enforced, add the deny rule to
`.claude/settings.json` by hand, or ask `ed-orchestrate-init` to do it for you
at setup time.
