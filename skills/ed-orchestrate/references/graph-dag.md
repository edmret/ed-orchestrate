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
   (see `role-defaults.md` — planner plans, never implements). It writes a
   plan overview (`<dir>/plans/PLAN-<n>.md` — the DAG's table of contents:
   goal, task list in dependency order, open risks) plus one markdown file per
   task node into `<dir>/tasks/` (commonly `.ai-memory/`, but any directory
   the project already uses for this works — `ed-orchestrate` doesn't mandate
   a path). `<dir>/INDEX.md` is the whole graph's entry point — start there.
2. **Each task node encodes its own graph edges** in YAML frontmatter:

   ```yaml
   ---
   id: TASK-000
   title: Short task title
   status: backlog # backlog | ready | in-progress | review | done
   assigned_to: coder # any role name in this project's roster
   lane: graph # graph | fast | ui-iterate (laya-routing.md, when installed)
   tdd: first # first | defer
   review: batch # batch | early — early = risky/foundational, isolated review
   context: [] # the ONLY knowledge files the agent reads at cold start
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
   **Cold-start budget**: the worker reads its node, the node's `governed_by`
   ADRs, `<dir>/knowledge/gotchas/00-core.md`, and ONLY the files in the node's
   `context:` — never `INDEX.md` (that's for planner/architect/curator) or the
   whole gotchas set "just in case".
5. **The batch ends in ONE integration node — and that's where review
   happens.** The planner ends every batch with a single
   `TASK-…-batch-integration` node (template scaffolded by init). Order:
   `integrator` merges the parallel branches and runs the full gate
   (typecheck + build, then lint, the full unit suite, then e2e) → the
   orchestrator dispatches `reviewer` ∥ `code-reviewer` **once** over the
   combined batch diff → triage (accepted → ONE `coder` fix-pass; waived →
   recorded with reason) → `integrator` re-gates → nodes `done`.
   - Coder/tester nodes verify with **unit tests scoped to their own files
     only**, never e2e, never the full suite; say so in every dispatch prompt,
     because sub-agents default to the full suite "to be safe".
   - **No per-task or per-wave review.** Waves move nodes to `review` and the
     next wave proceeds. Only nodes the planner flags `review: early` (auth,
     shared state, public API, DI tokens, cross-cutting infra) get an isolated
     review before dependents build on them. This cuts review cost from
     2 reviewers × N tasks to 2 per batch, without dropping the gate: a coder's
     own green tests are self-graded and never count as review.
   - **Workers never run git.** The orchestrator branches and commits each
     green wave (commits are rollback points); `integrator` merges.
6. **`curator` runs periodically, not per-task.** After a batch of nodes
   completes, delegate to `curator` to fold gotchas and outcomes from finished
   task reports into the per-area `knowledge/gotchas/<area>.md` files (keeping
   `00-core.md` ≤ 8 KB) and prune stale ones — a hygiene pass, not part of the
   critical path, but one that compounds when skipped.
7. **Small changes skip the graph.** With the Laya router installed
   ([laya-routing.md](laya-routing.md)), every request is routed first:
   `fast` (one coder, one node, no planner) and `ui-iterate` (one long-lived
   coder, a debt ledger closed by a debt-closure DAG at the end) keep small
   changes cheap while still ending in the same integration phase.

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
(`governed_by`, i.e. `<dir>/adrs/ADR-<n>.md`) if the project keeps one, not
inline in every task report; tactical gotchas belong in the
matching `<dir>/knowledge/gotchas/<area>.md` (appended newest first by whoever
hit the trap; `gotchas.md` is only the area index), and settled canonical approaches in
`<dir>/knowledge/patterns.md` — both consolidated by `curator`. `reviewer`/`code-reviewer` write their one-per-batch findings to
`<dir>/reviews/REVIEW-<n>.md`, linked from the batch-integration node.

## Escalation / scope fence

Give each task node an explicit allowed-files scope. If executing it would
require touching files outside that scope, the sub-agent should stop and
report a candidate follow-up task rather than widening its own scope — the
orchestrator (or `planner`, if re-invoked) decides whether to add a new node,
not the sub-agent unilaterally.

## Wiring it up via `ed-orchestrate-init`

`ed-orchestrate-init` step 5g offers to set this up automatically (and, if
already wired, silently refreshes it) by running `ed-orchestrate-init/scripts/setup_graph_dag.py
<dir>`, which idempotently:

- scaffolds `<dir>` with every template a role needs to actually produce
  DAG artifacts — `INDEX.md` (Map of Content), `tasks/TASK-template.md`,
  `tasks/TASK-batch-integration-template.md`, `tasks/ITER-template.md`,
  `plans/PLAN-template.md`, `adrs/ADR-template.md`,
  `reviews/REVIEW-template.md`, the `knowledge/gotchas.md` area index with
  seed `knowledge/gotchas/00-core.md` and `knowledge/gotchas/harness.md`
  (cross-harness operating traps already hit in earlier projects), and
  `knowledge/patterns.md` — never overwriting a file that already exists;
- with `--laya`, installs the Laya router at `.orchestrate/bin/laya-route`
  plus `<dir>/laya/README.md` ([laya-routing.md](laya-routing.md));
- splices a `<!-- BEGIN:ed-orchestrate-graph-dag -->` … `<!-- END -->` block
  into the target `AGENTS.md` — the "are you the orchestrator?" guard, worker
  rules, the orchestrator workflow above, and (when Laya is installed) the
  lanes — same idempotent splice guarantee as the
  roster block (`agents-md-block-format.md`) — re-running only replaces that
  span, never touches content outside it;
- with `--engram`, adds the Engram section (orchestrator + worker rules)
  ([engram-memory.md](engram-memory.md)) to that block;
- appends `<dir>` to `.gitignore` if not already present — the task graph is
  local-machine scratch, not committed. No trailing slash: in a worktree the
  dir is a symlink, which a `dir/` pattern doesn't match;
- registers `<dir>` under `orca.yaml`'s `worktree.sharedDirectories` (creating
  a minimal `orca.yaml` if none exists, or appending to an existing
  `sharedDirectories` list in place) so every Orca child worktree sees the
  same graph without a commit/pull cycle. If the file's shape can't be
  matched safely, the script warns instead of guessing.

Re-running `ed-orchestrate-init` on an already-wired project re-runs the
script: it refreshes the AGENTS.md block and adds any templates introduced
since (existing files untouched), so projects pick up workflow improvements
without a hand-port. A pre-split flat `knowledge/gotchas.md` is left as is,
with a note to have `curator` split it into area files.

`<dir>` itself is never fixed to `.ai-memory/` — that's just the default
suggestion; any project-chosen path works, since nothing else in this repo
hardcodes it.

### Why this needs `AGENTS.md` *and* `CLAUDE.md`

Step 5's `d2` (always run, not gated behind any question) splices a small
`@AGENTS.md` import into the target project's `CLAUDE.md` via
`ed-orchestrate-init/scripts/ensure_claude_md_import.py`. This isn't
graph-DAG-specific — it's what makes the roster block *and* this block
actually load every session. Claude Code only auto-reads `AGENTS.md` when no
`CLAUDE.md` exists on the path at all; any project with its own `CLAUDE.md`
(outside this skill's control) silently shadows both blocks, so without the
import a user would have to manually tell Claude to read `AGENTS.md` every
session — the graph would sit there unused.

## Relationship to `.orchestrate/agents.json`

The graph pattern is a delegation *discipline*, not a schema addition — it
doesn't change any `agents.json` field. `role.description`,
`systemPromptSeed`, and `worktreeStrategy` are exactly what already exists;
this reference only changes what the orchestrator hands each role and how it
decides dispatch order.
