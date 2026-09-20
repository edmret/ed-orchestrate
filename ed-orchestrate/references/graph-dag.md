# Graph-engineered delegation (optional pattern)

`ed-orchestrate` itself only delegates one task to one role per invocation —
it has no memory of previous delegations and holds no plan. For a single small
fix, that's enough: just call it again for the next step. For a multi-step
feature spanning several roles and possibly parallel work, running it in a
flat repeated loop ("hand off task 1 to coder, then task 2 to coder, then...")
degrades badly: each delegation starts cold, mistakes repeat, and the
orchestrator re-derives context it already had. This reference describes the
alternative — graph-engineered delegation — for projects that want it. It is
optional: nothing in `ed-orchestrate`'s core flow requires it, and a project
with no shared task-memory directory should just keep delegating one task at a
time.

## Shape

Instead of a loop, the orchestrator walks a Directed Acyclic Graph of task
nodes:

1. **`planner` produces the DAG once.** Delegate the whole goal to `planner`
   (see `role-defaults.md` — planner plans, never implements). It writes one
   markdown file per task node into this project's shared task-memory
   directory (commonly `.ai-memory/tasks/`, but any directory the project
   already uses for this works — `ed-orchestrate` doesn't mandate a path).
2. **Each task node encodes its own graph edges** in YAML frontmatter:

   ```yaml
   ---
   id: TASK-000
   title: Short task title
   status: backlog # backlog | ready | in-progress | review | done
   assigned_to: coder # any role name in this project's roster
   depends_on: [] # task ids that must be done first
   blocks: [] # task ids this one blocks
   governed_by: [] # links to relevant ADRs/decisions, if this project keeps them
   ---
   ```

3. **The orchestrator walks the graph**, not a fixed sequence: dispatch every
   `ready` node (all `depends_on` satisfied) whose assigned role is free,
   possibly several in parallel across separate worktrees
   (`worktreeStrategy: new-child` per role), and mark nodes `done` as their
   reports land.
4. **Dispatch with a pointer, not full context.** Pass the sub-agent only
   `"Execute <task node>. Governed by <its linked decisions>."` — the
   sub-agent reads the task node and its immediate linked context itself,
   rather than the orchestrator re-explaining the whole feature in the
   delegation prompt. This is the token-efficiency payoff of the graph over a
   loop: context is pulled on demand, not repeated per delegation.
5. **`integrator` is the fan-in node.** When parallel branches (parallel
   coder task nodes in separate worktrees) finish, delegate the merge to
   `integrator` rather than merging them yourself — it reconciles conflicts,
   checks semantic consistency, and runs the full test suite exactly once for
   the combined result (see `role-defaults.md`). Don't re-run the full suite
   per individual task node; that's `integrator`'s job, once per batch.
6. **`curator` runs periodically, not per-task.** After a batch of nodes
   completes, optionally delegate to `curator` to fold gotchas and outcomes
   from finished task reports into the project's shared knowledge notes and
   prune stale ones — a hygiene pass, not part of the critical path.

## Task node report

Whatever role executes a task node should report against the same shape the
node itself was written in, so the orchestrator (or `curator`) can read
outcomes mechanically rather than parsing prose:

```markdown
## Execution & Diffs Log
- **Status Change**: `in-progress` -> `review`
- **Files Modified**: list of paths
- **Summary of Changes**: what was implemented or fixed
- **Verification Evidence**: test command output or green test names
- **New Gotchas Discovered**: none, or a link into the shared knowledge notes
```

Structural rationale ("why this approach") belongs in a linked decision record
(`governed_by`) if the project keeps one, not inline in every task report;
tactical gotchas belong in the shared knowledge notes `curator` maintains.

## Escalation / scope fence

Give each task node an explicit allowed-files scope. If executing it would
require touching files outside that scope, the sub-agent should stop and
report a candidate follow-up task rather than widening its own scope — the
orchestrator (or `planner`, if re-invoked) decides whether to add a new node,
not the sub-agent unilaterally.

## Wiring it up via `ed-orchestrate-init`

`ed-orchestrate-init` step 5g offers to set this up automatically (skipped if
already wired) by running `ed-orchestrate-init/scripts/setup_graph_dag.py
<dir>`, which idempotently:

- creates `<dir>/tasks/TASK-template.md` (the frontmatter shape shown above)
  if it doesn't already exist — never overwrites a hand-edited template;
- splices a `<!-- BEGIN:ed-orchestrate-graph-dag -->` … `<!-- END -->` usage
  block into the target `AGENTS.md`, same idempotent splice guarantee as the
  roster block (`agents-md-block-format.md`) — re-running only replaces that
  span, never touches content outside it;
- appends `<dir>/` to `.gitignore` if not already present — the task graph is
  local-machine scratch, not committed;
- registers `<dir>` under `orca.yaml`'s `worktree.sharedDirectories` (creating
  a minimal `orca.yaml` if none exists, or appending to an existing
  `sharedDirectories` list in place) so every Orca child worktree sees the
  same graph without a commit/pull cycle. If the file's shape can't be
  matched safely, the script warns instead of guessing.

`<dir>` itself is never fixed to `.ai-memory/` — that's just the default
suggestion; any project-chosen path works, since nothing else in this repo
hardcodes it.

## Relationship to `.orchestrate/agents.json`

The graph pattern is a delegation *discipline*, not a schema addition — it
doesn't change any `agents.json` field. `role.description`,
`systemPromptSeed`, and `worktreeStrategy` are exactly what already exists;
this reference only changes what the orchestrator hands each role and how it
decides dispatch order.
