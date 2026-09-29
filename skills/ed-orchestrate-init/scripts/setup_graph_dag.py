#!/usr/bin/env python3
"""Wire up the optional graph-engineered task-DAG pattern in a target project:
scaffolds the shared task-memory directory (task/batch-integration/UI-iteration/
plan/ADR/review templates, a per-area gotchas knowledge base, and a Map-of-Content
index), splices the orchestrator-workflow block into AGENTS.md, gitignores the
memory directory (it's local-machine scratch, not committed), registers it as an
Orca worktree-shared directory in orca.yaml, and — with --laya — installs the
Laya lane router at .orchestrate/bin/laya-route, and — with --engram — adds the
Engram persistent-memory section (orchestrator + worker rules) to the AGENTS.md block.

Usage:
  setup_graph_dag.py <memory-dir> [--agents-md AGENTS.md] [--gitignore .gitignore]
      [--orca-yaml orca.yaml] [--no-orca-yaml]
      [--laya] [--laya-bin .orchestrate/bin/laya-route] [--engram | --no-engram]

Idempotent: safe to re-run, and re-running is how an already-wired project picks
up newer templates and a refreshed AGENTS.md block. Never overwrites an existing
template, note, or laya-route file (the project owns and tunes its copies), never
duplicates a gitignore line, an AGENTS.md block, or an orca.yaml entry. The Laya
lane section of the AGENTS.md block is included whenever laya-route is installed,
whether by this run or an earlier one. The Engram section is kept on re-runs once
present (its heading is the marker); --no-engram removes it.
"""
import argparse
import datetime
import os
import re
import stat
import sys

BEGIN = "<!-- BEGIN:ed-orchestrate-graph-dag -->"
END = "<!-- END:ed-orchestrate-graph-dag -->"
SPLICE_RE = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.DOTALL)

LAYA_ASSET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "laya-route")

# Templates use @@MEM@@ (memory dir) and @@DATE@@ placeholders rather than
# str.format, so literal braces in the prose stay safe.

TASK_TEMPLATE = """---
id: TASK-000
title: Task Template
status: backlog # backlog | ready | in-progress | review | done
assigned_to: coder # any role name in this project's .orchestrate/agents.json
lane: graph # graph | fast | ui-iterate  (from laya-route, when installed)
tdd: first # first | defer  (helpers/utils/parsers/stores/guards are ALWAYS first)
routing_id: "" # laya-route decision id, for the outcome log
review: batch # batch | early  (early = risky/foundational: isolated review before dependents build on it)
context: # the ONLY knowledge files this task's agent reads at cold start
  - @@MEM@@/knowledge/gotchas/00-core.md
depends_on: []
blocks: []
governed_by: [] # links to ADRs, e.g. [[ADR-000-template]]
tags: [task, dag]
date_created: @@DATE@@
---

# [[TASK-000]]: Task Template

## Objective

One or two sentences: the exact behavior or deliverable.

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Unit tests scoped to the touched files pass (the full suite, e2e and review run
      once, at the batch-integration node — not here)

## Scope Fence

- **Allowed target files**: list the files/dirs this task may touch. When the task
  renames or reshapes a SHARED type/port/token/mock seed, every consumer
  (`git grep` imports, templates, specs, e2e) must sit in some node's fence.
- **Forbidden zones**: everything else. If the task needs more, stop and log a
  candidate follow-up task here instead of widening scope.

## Execution & Diffs Log
*(the executing sub-agent fills this in when done; a killed/abandoned worker's log is
purged by the orchestrator before any retry)*

- **Status Change**: `in-progress` -> `review`
- **Files Modified**:
- **Summary of Changes**:
- **Verification Evidence**: scoped unit test command + result
- **New Gotchas Discovered**: none, or the `gotchas/<area>.md` entry you appended
"""

BATCH_TEMPLATE = """---
id: TASK-0xx-batch-integration
title: Batch integration — merge, full gate, review, fix-pass
status: backlog
assigned_to: integrator
review: batch
batch_base: "" # commit/branch the batch started from; review diffs `<batch_base>...HEAD`
context:
  - @@MEM@@/knowledge/gotchas/00-core.md
  - @@MEM@@/knowledge/gotchas/harness.md
depends_on: [] # every coder/tester node of the batch
blocks: []
governed_by: []
tags: [task, dag, integration]
date_created: @@DATE@@
---

# [[TASK-0xx-batch-integration]]

The ONE place per batch where the full suite, e2e and review run. The planner ends
every batch DAG with one of these; there are no per-task review nodes unless a node
is flagged `review: early`.

## Order (do not reorder)

1. `integrator`: merge the batch's child branches onto a clean base; resolve conflicts
   (escalate product-level conflicts, never force one).
2. `integrator`: full gate, stopping at the first red stage — typecheck, build, lint,
   format check, full unit suite, then e2e (only once typecheck + build are green).
3. Orchestrator dispatches `reviewer` ∥ `code-reviewer` ONCE over `git diff <batch_base>...HEAD`.
   Findings go to `@@MEM@@/reviews/REVIEW-<n>.md`.
4. Orchestrator triages: accepted findings → ONE `coder` fix-pass node; waived findings
   are listed below with the reason.
5. `integrator` re-runs the gate after the fix-pass; nodes move to `done`.
6. `integrator` records the Laya outcome for every routed node of the batch (if
   laya-route is installed): `laya-route outcome --id <routing_id> --value correct|wrong-lane|wrong-tdd|wrong-context`.

## Gate results

| Stage | Result | Evidence |
| --- | --- | --- |
| merge |  |  |
| typecheck + build |  |  |
| lint / format |  |  |
| unit (full) |  |  |
| e2e (full) |  |  |
| re-gate after fix-pass |  |  |

## Review triage

- **Accepted → fix-pass**:
- **Waived (with reason)**:
"""

ITER_TEMPLATE = """---
id: ITER-000
title: UI iteration ledger template
status: iterating # iterating | closed | debt-planned
lane: ui-iterate
routing_id: "" # laya-route decision id that opened this session
worktree: "" # the ONE worktree all iterations run in
branch: ""
debt_batch: "" # TASK-0xx-batch-integration created from this ledger at close
context:
  - @@MEM@@/knowledge/gotchas/00-core.md
tags: [iter, ui-iterate, ledger]
date_created: @@DATE@@
---

# [[ITER-000]]: UI iteration ledger template

One ledger per UI-iteration session: fast, small visual turns now, with the skipped
work recorded as debt and closed out by a normal graph batch at the end.

## Goal

What the UI should look/feel like when iterations end (one or two sentences, user's words).

## Rules for this session

- Template / styles / copy / layout: NO tests, NO e2e run, NO review. Check it in the
  running app.
- Helpers, utils, parsers, pure functions: TDD NOW, inside the iteration (never deferred).
- If a turn needs a new store, route, guard, API call or mock handler, or a shared
  library's public API: STOP and report — the orchestrator splits it into a graph task.
- The orchestrator commits after every turn (`wip(ui-iter): <turn summary>`), so each
  turn is revertible. The coder never runs git.

## Iterations
<!-- Coder appends one block per turn, newest LAST. Keep each block short. -->

### Turn 1 — <short title>
- **Asked**: what the user asked for this turn.
- **Changed**: files touched
- **Commit**: `<sha>` (orchestrator fills)
- **Debt** (each item becomes a closure task at close; tick nothing here):
  - [ ] unit: <component/behavior that now lacks a spec>
  - [ ] e2e: <flow/spec to add or update>
  - [ ] a11y: <contrast/focus/labels to verify>
  - [ ] i18n: <hard-coded strings to move to keys>
  - [ ] mock: <fake data the new UI needs>
  - [ ] cleanup: <hard-coded values, duplication, dead code left behind>

## Close-out (orchestrator fills at close)

- **Closed at**: <date>, after N turns.
- **Final diff**: `git diff <base>...<branch> --stat`
- **Debt summary**: deduplicated list across all turns (dropped items say why).
- **Debt-closure batch**: [[TASK-0xx-...]] … → [[TASK-0xx-batch-integration]] —
  every debt item maps to a node or an explicit waiver.
"""

PLAN_TEMPLATE = """---
id: PLAN-000
title: Plan Template
status: draft # draft | active | done
tags: [plan, dag]
date_created: @@DATE@@
---

Written by `planner` for one goal: the set of task nodes it produced and how
they depend on each other. Not itself executed — a map of the DAG below it,
so the orchestrator (and a human) can see the whole shape at a glance instead
of opening every task node.

## Goal

One paragraph: what this plan achieves and why.

## Task nodes

In dependency order. Parallel waves share a number; the batch always ends in ONE
integration node:

- Wave 1: [[TASK-001]] — one-line summary — depends_on: none
- Wave 1: [[TASK-002]] — one-line summary — depends_on: none
- Wave 2: [[TASK-003]] — one-line summary — depends_on: [[TASK-001]]
- Final: [[TASK-004-batch-integration]] — depends_on: all of the above

## Nodes flagged `review: early`

Risky/foundational nodes (auth, shared stores/interceptors, public library API, DI
tokens, cross-cutting infra) that get an isolated review before dependents build on them.

## Open questions / risks

Anything the planner flagged as ambiguous or risky rather than smoothing over.
"""

ADR_TEMPLATE = """---
id: ADR-000
title: ADR Template
status: proposed # proposed | accepted | superseded
supersedes: [] # e.g. [[ADR-000-old-name]]
tags: [adr]
date_created: @@DATE@@
---

## Context

What situation forces a decision here — the constraint, the problem, or the
question, not the answer yet.

## Decision

What was decided, stated plainly.

## Alternatives considered

What else was on the table and why it lost, briefly — enough that a later
reader doesn't re-propose it without knowing it was already rejected.

## Consequences

What this makes easier, what it makes harder, and what it locks in.
"""

REVIEW_TEMPLATE = """---
id: REVIEW-000
task: TASK-000 # usually the batch-integration node this review ran under
reviewer_role: reviewer # reviewer | code-reviewer
diff: "<batch_base>...HEAD"
tags: [review]
date_created: @@DATE@@
---

One review per batch, over the combined batch diff — not one per task. Read enough
to judge, then write the verdict and stop.

Findings only, most severe first — one entry per finding:

- **Severity**: blocker | major | minor
- **File/line**:
- **What's wrong**:
- **Concrete failure case**:
- **Suggested fix**:

If nothing worth flagging was found, say so plainly instead of inventing filler
findings.
"""

GOTCHAS_INDEX = """---
title: Gotchas (index)
type: knowledge
tags: [knowledge, gotchas]
date_created: @@DATE@@
---

# Gotchas — INDEX

Traps worth not rediscovering live in per-area files under `gotchas/`. This file is
only the map — **never append here**.

**Rule**: read `gotchas/00-core.md` plus ONLY the area files listed in your task
node's `context:` frontmatter. Append new traps, newest first, to the matching area
file (create it if the area is new, and add a row below). `curator` consolidates.

This vault records *traps*, not conventions. Conventions live in `AGENTS.md`.

## Area files

| File | Scope (read when) |
| --- | --- |
| gotchas/00-core.md | Cross-cutting rules every task needs (always; keep ≤ 8 KB) |
| gotchas/harness.md | Dispatching/operating sub-agents across harnesses (orchestrator, integrator) |
"""

GOTCHAS_CORE = """---
title: Gotchas — Core — rules every task needs
type: knowledge
tags: [knowledge, gotchas]
date_created: @@DATE@@
---

# Core — rules every task needs

Cross-cutting traps that shipped past green gates. Keep this file ≤ 8 KB; only rules
EVERY task needs belong here — everything else goes to an area file.

## Rules

- A zero exit code from a sub-agent proves nothing. Judge by ground truth — the files it
  should have changed (`git status --porcelain`) and its task node's Execution log.
- A task node must be self-contained within its own checkout: never cite a path outside
  the repo as required context — sandboxed harnesses auto-reject the read and the run
  unwinds silently.

## Entries (newest first)
"""

GOTCHAS_HARNESS = """---
title: Gotchas — Multi-harness / orchestration ops
area: harness
tags: [knowledge, gotchas]
date_created: @@DATE@@
---

Read when: dispatching/operating sub-agents across harnesses (orca/opencode/agy/claude),
or authoring task nodes and dispatch briefs. Seeded by ed-orchestrate-init from traps
hit in earlier projects; keep what applies, prune what doesn't.

## Rules

- **`orca terminal read` returns a ~120-line tail by default — pass `--limit <n>`.** A
  truncated tail makes a working worker look stalled, and `--for tui-idle` can report
  satisfied while a run continues. Killing a working agent is the common failure.
- **Never kill an agent's in-flight tool process** (e.g. `pkill` a test run inside its
  shell tool): opencode never resolves that tool call and the session wedges. Message the
  agent, or close the tab and relaunch with a resume brief.
- **Put dispatch briefs in a file, dispatch a pointer.** Inline prompts through
  `orca terminal create --command` break on shell metacharacters — any `!` triggers zsh
  history expansion (`event not found`) and the invocation never runs. Write the brief
  to a task node / review file and dispatch "Execute <path>. Report changes + gate results."
- **Launch with the prompt attached**, not create-then-send: the first keystrokes sent
  into a freshly launched TUI can be dropped, silently truncating the brief.
- **Stagger simultaneous `opencode run` starts by ≥ 30 s** — parallel starts contend on
  opencode's shared SQLite session store (`database is locked`).
- **opencode agent files need `mode: all` (or `primary`)**: `mode: subagent` makes
  `opencode run --agent <role>` fall back to the default agent with only a warning — the
  role's prompt and model silently never apply. Check the first lines of run output.
- **opencode + symlinked shared dirs**: in a worktree, the shared memory dir is a symlink
  that resolves OUTSIDE the worktree, so opencode treats it as `external_directory` and
  auto-rejects reads/writes in `run` mode unless the project's `opencode.json` sets
  `permission.external_directory: "allow"`.
- **agy headless (`-p`) denies every `read_file`/`write_file`** unless the run passes
  `--dangerously-skip-permissions` (put it in the role's `cliFlags`). Even then, each
  command's FIRST word must be on `permissions.allow` in
  `~/.gemini/antigravity-cli/settings.json`: env-var prefixes (`FOO=1 npx …`), `cd … &&`,
  pipes and brace expansion are denied. Prefer single commands and `npm run` scripts.
  New projects (and their Orca worktree dirs) also need `read_file(<path>)` /
  `write_file(<path>)` + `trustedWorkspaces` entries there.
- **A killed worker's task-node log poisons every retry**: the memory dir is shared into
  every worktree, so an abandoned worker's "status: review" claim is the first thing the
  next dispatch reads. Resetting the worktree is half a rollback — purge the node's
  Execution log in the same breath.
- **Some models end the turn right after reading context.** Every coder dispatch carries
  an explicit "DO NOT END YOUR TURN after reading context — implement the task" line.
- **Workers leave backgrounded test watchers alive at 100% CPU.** Tests run in the
  foreground with watch mode off; before a gate, check for leftover test processes.
- **Sub-agents default to the full suite "to be safe".** Every coder/tester dispatch says
  explicitly: scoped unit tests only, no e2e; full suite + e2e + review are the
  integration phase's job.

## Entries (newest first)
"""

PATTERNS_SEED = """# Patterns

Curated by `curator` — canonical approaches this project has settled on, so new
task nodes reuse them instead of reinventing a slightly different version each
time. One entry per pattern: what it's for, and a pointer to where it's
implemented or an [[ADR-000-template]] that decided it.

## Cross-cutting solutions for parallel work

Zero file overlap between parallel nodes does NOT mean zero divergence. Before
sharding one contract across parallel agents, the planner writes the ONE allowed
solution for each cross-cutting concern here and copies it into every node.

## Entries

<!-- curator appends entries below -->
"""

LAYA_README = """# Laya routing log

`decisions.jsonl` is append-only, written by `.orchestrate/bin/laya-route`.

- `kind: "decision"`: one per routing call (request, files, Laya answers, lane/tdd/context, reason).
- `kind: "outcome"`: appended later by
  `laya-route outcome --id <id> --value correct|wrong-lane|wrong-tdd|wrong-context [--note ...]`.
  The integrator records it at batch close. The orchestrator records it when a
  fast/ui-iterate session had to escalate to graph.

Joined by `id`, the decision and outcome pairs are the fine-tuning dataset for Laya,
and `curator` reviews them for routing misses to tune the script's PROJECT TUNING
tables. Never edit past lines.
"""

INDEX_TEMPLATE = """---
type: index
tags: [moc, ed-orchestrate, graph-engineering]
date_created: @@DATE@@
---

# @@MEM@@ — Map of Content

Entry point into this project's shared task graph and knowledge base, for
`planner` / `architect` / `curator`. Dispatched workers do NOT read this at cold
start — their task node's links are their map. One line per item, newest first
within each section — `curator` keeps this current.

## ADRs

- [[ADR-000-template]]

## Plans

- [[PLAN-000-template]]

## Tasks

- [[TASK-000-template]] · [[TASK-batch-integration-template]] · [[ITER-000-template]]

## Reviews

(none yet)

## Knowledge

- [[gotchas]] (index) → `gotchas/00-core.md`, `gotchas/harness.md`, area files
- [[patterns]]
"""


def _fill(template, mem, today):
    return template.replace("@@MEM@@", mem).replace("@@DATE@@", today)


ENGRAM_HEADING = "### Persistent memory (Engram)"


def engram_section(m):
    return [
        "",
        ENGRAM_HEADING,
        "",
        f"`{m}/` is this project's live task state, shared into every worktree. **Engram**",
        "(MCP `mem_*` tools) is durable memory across sessions and projects; the project name",
        "is pinned by the tracked `.engram/config.json`, so every worktree and harness uses the",
        f"same one. `{m}/` stays the source of truth for task state; Engram holds distilled",
        "decisions and root causes so an agent can `mem_search` a topic instead of reading",
        "many files. If no `mem_*` tools are available in your harness, skip this section.",
        "",
        "**Orchestrator**",
        "- Before planning: `mem_search` with keywords from the request.",
        "- `mem_save` when an ADR is accepted, a batch closes with a non-obvious root cause,",
        "  the user states a preference or rejects an approach, or a convention settles.",
        f"- Save a pointer, not a copy: decision + why + the `{m}/` path (e.g. `[[ADR-003]]`).",
        "- After `curator` runs, save the rules/ADRs it promoted (it lists candidates).",
        "- Before finishing a session: `mem_session_summary`.",
        "",
        "**Workers (every dispatched role)**",
        "- At cold start, AFTER your node/ADRs/`00-core.md`: at most 1-2 targeted `mem_search`",
        "  queries on the node's topic instead of opening extra files \"just in case\".",
        "- `mem_save` only a non-obvious root cause or trap you hit (short, with the node id).",
        f"  A gotcha still goes to `{m}/knowledge/gotchas/<area>.md` first; Engram is not a",
        "  substitute. Never save task status, diffs or logs there.",
        "- Engram unavailable or erroring: continue without it. It is never a blocker.",
        "",
        "Never store secrets, tokens or customer data in Engram.",
    ]


def render_agents_md_block(memory_dir, laya_bin=None, engram=False):
    today = datetime.date.today().isoformat()
    m = memory_dir.rstrip("/")
    out = [
        BEGIN,
        (
            "<!-- Generated by ed-orchestrate-init — do not hand-edit between these\n"
            "     markers; re-run ed-orchestrate-init instead.\n"
            f"     Last generated: {today}. -->"
        ),
        "",
        "## Graph-engineered task delegation (ed-orchestrate)",
        "",
        f"This project tracks multi-step work as a task DAG in `{m}/` (local-machine,",
        "gitignored, shared into every Orca worktree by symlink) instead of a flat",
        "delegation loop. Pattern: `ed-orchestrate/references/graph-dag.md`.",
        "",
        "### Are you the orchestrator?",
        "",
        "The orchestrator is whichever harness the human is talking to directly, started",
        "without a scoped role. It coordinates via `ed-orchestrate` and never writes",
        "application code. If you were dispatched with a scoped role — you received",
        '"Execute [[TASK-xxx]]…", a task-node or ITER-ledger pointer, or a prompt naming your',
        "role — you are **not** the orchestrator: the Orchestrator workflow below does not",
        "apply to you; follow your role's `systemPromptSeed` and the worker rules.",
        "",
        "### Worker rules (every dispatched role)",
        "",
        "- **Pre-flight, mandatory**: in a linked git worktree (`git rev-parse --git-dir` differs",
        f"  from `--git-common-dir`), `{m}` must be a symlink into the main checkout",
        f"  (`readlink {m}`). If it is absent or a real directory, STOP and report — never",
        "  create a local copy: it is discarded with the worktree, taking every task-node",
        "  update with it. Also never install dependencies in a worktree whose dependency",
        "  directory the project shares by symlink.",
        "- **Cold-start budget**: read your task node (or ITER ledger), its `governed_by` ADRs,",
        f"  `{m}/knowledge/gotchas/00-core.md`, and ONLY the files in the node's `context:`",
        f"  frontmatter. Not `{m}/INDEX.md` (that's for planner/architect/curator), not every",
        "  gotcha file.",
        "- **Workers never run git** — no branch, commit, reset, or merge. Branching and",
        "  committing are the orchestrator's; merging is `integrator`'s.",
        "- **Scoped verification**: `coder`/`tester` verify with UNIT tests scoped to the files",
        "  they touched (plus typecheck/lint on them). No e2e execution (authoring/type-checking",
        "  e2e specs is fine). A red OUTSIDE your scope is recorded in the node, not escalated.",
        "- **Scope Fence**: need a file outside the node's fence? Stop and log a candidate task.",
        "- **Report** in the node's Execution & Diffs Log; set `status: review`. Append a",
        f"  non-obvious trap, newest first, to the matching `{m}/knowledge/gotchas/<area>.md`",
        "  (never to the `gotchas.md` index).",
        "- **Unattended**: never block on an interactive question; if blocked, write the",
        "  question into the task node and stop. Read enough to judge, then conclude.",
        "",
        "### Orchestrator workflow",
        "",
    ]
    step = 1
    if laya_bin:
        out += [
            f"{step}. **Route first.** Every new request goes through `{laya_bin}` (see Lanes",
            "   below) before anything is dispatched.",
        ]
        step += 1
    out += [
        f"{step}. **Plan as a DAG.** For multi-step work delegate to `planner`: it writes",
        f"   `{m}/plans/PLAN-<n>.md` plus task nodes from `{m}/tasks/TASK-template.md`",
        "   (`depends_on`, `blocks`, `governed_by`, Scope Fence, `lane`, `tdd`, `context`,",
        "   `review`), ending in ONE node from `TASK-batch-integration-template.md`.",
        "   Dispatch every `ready` node whose role is free; parallel coders get `new-child`",
        "   worktrees.",
    ]
    step += 1
    out += [
        f"{step}. **Lean dispatch.** Pass a pointer, not context: \"Execute [[TASK-001]].",
        "   Governed by [[ADR-001]].\" Put any longer brief in a file and point at it. Every",
        "   coder/tester dispatch states: scoped unit tests only, no e2e, and \"do not end",
        "   your turn after reading context\".",
    ]
    step += 1
    out += [
        f"{step}. **Review runs ONCE per batch, at integration — not per task or wave.**",
        "   Coder/tester waves move nodes to `review` and the next wave proceeds. After",
        "   `integrator` merges the batch and its full gate is green, dispatch `reviewer` ∥",
        "   `code-reviewer` once over `git diff <batch_base>...HEAD`, triage (accepted →",
        "   ONE coder fix-pass; waived → recorded with reason), `integrator` re-gates, nodes",
        "   → `done`. Only nodes the planner flagged `review: early` (auth, shared",
        "   state/interceptors, public API, DI tokens, cross-cutting infra) get an isolated",
        "   review before dependents build on them. A coder's own green tests are",
        "   self-graded — they never replace this gate.",
    ]
    step += 1
    out += [
        f"{step}. **Full suite + e2e run exactly once per batch**, by `integrator` at the",
        "   batch-integration node (and again only as the re-gate after the fix-pass).",
        "   Typecheck + build must be green before e2e starts; stop at the first red stage.",
    ]
    step += 1
    out += [
        f"{step}. **Commit each green wave** (workers never do) — commits are rollback",
        "   points, independent of when review runs. Before sharding one contract across",
        f"   parallel nodes, write the ONE allowed solution in `{m}/knowledge/patterns.md`.",
    ]
    step += 1
    out += [
        f"{step}. **Learning loop.** After each batch/milestone delegate to `curator`: fold",
        "   task logs into the `gotchas/<area>.md` files (keep `00-core.md` ≤ 8 KB), prune",
        "   stale nodes, keep ADRs consistent"
        + (", and review the Laya outcome log for routing misses." if laya_bin else "."),
    ]
    step += 1
    out += [
        f"{step}. **UI-iteration lane** (\"ui iterate\""
        + (", or `lane: ui-iterate`" if laya_bin else "")
        + "): ONE worktree, ONE long-lived `coder`,",
        f"   one ledger from `{m}/tasks/ITER-template.md`. Each tweak is a new turn to the SAME",
        "   agent (warm context), no tests/e2e/review per turn; pure logic is still TDD'd",
        "   immediately. The orchestrator commits `wip(ui-iter): …` per turn; the coder logs",
        "   each turn's **Debt**. A turn needing a new store/route/guard/API/public-API change",
        "   STOPS and becomes a graph task. On \"close iterations\" the orchestrator fills",
        "   Close-out and dispatches `planner` with the ledger: it produces a debt-closure DAG",
        "   (tester nodes for specs, coder nodes for structural debt) ending in the usual",
        "   batch-integration node — every debt item maps to a node or an explicit waiver.",
    ]
    if laya_bin:
        out += [
            "",
            "### Lanes (Laya router)",
            "",
            f"`{laya_bin} --request-en \"<English request>\" [--files a,b | --git-diff] [--task <id>]`",
            "→ `{id, lane, tdd, context, reason}`. Stdlib Python, works from any harness; asks a",
            "local Laya (`LAYA_URL`, default `http://localhost:8000`) atomic yes/no questions and",
            "combines them deterministically. **Path facts override Laya** (routes/guards,",
            "stores/services/API/mocks, config, or ≥ 4 files → `graph`); if Laya is down, path",
            "facts decide and anything uncertain is `graph`. Always pass English and, when known,",
            "`--files`/`--git-diff`. Tuning: `ed-orchestrate/references/laya-routing.md`.",
            "",
            "- `graph` — the normal DAG above.",
            "- `fast` — ONE coder, ONE task node, no planner. TDD first, scoped unit tests, then",
            "  into the next batch's integration phase (or a one-task integration).",
            "- `ui-iterate` — the UI-iteration lane above.",
            "- `ask` — Laya unsure and no files settle it: ask the user one question, re-route",
            "  with `--files`.",
            "- **TDD is never deferred** for helpers, utils, parsers, pure functions, stores,",
            "  guards — in any lane. Only template/styles/copy/layout may defer.",
            f"- **Outcome log**: decisions land in `{m}/laya/decisions.jsonl`. At batch close",
            f"  `integrator` runs `{laya_bin} outcome --id <routing_id> --value",
            "  correct|wrong-lane|wrong-tdd|wrong-context`; the orchestrator does the same when a",
            "  fast/ui-iterate session escalated.",
        ]
    if engram:
        out += engram_section(m)
    out.append(END)
    return "\n".join(out) + "\n"


def splice(existing_content, block):
    if BEGIN in existing_content and END in existing_content:
        new_content, _ = SPLICE_RE.subn(lambda _m: block.rstrip("\n"), existing_content, count=1)
        return new_content
    if not existing_content.strip():
        return block
    if existing_content.endswith("\n"):
        return existing_content + "\n" + block
    return existing_content + "\n\n" + block


def write_if_missing(path, content):
    if os.path.exists(path):
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def scaffold_memory_dir(memory_dir, laya):
    today = datetime.date.today().isoformat()
    mem = memory_dir.rstrip("/")
    j = lambda *p: os.path.join(memory_dir, *p)  # noqa: E731
    files = {
        j("INDEX.md"): INDEX_TEMPLATE,
        j("tasks", "TASK-template.md"): TASK_TEMPLATE,
        j("tasks", "TASK-batch-integration-template.md"): BATCH_TEMPLATE,
        j("tasks", "ITER-template.md"): ITER_TEMPLATE,
        j("plans", "PLAN-template.md"): PLAN_TEMPLATE,
        j("adrs", "ADR-template.md"): ADR_TEMPLATE,
        j("reviews", "REVIEW-template.md"): REVIEW_TEMPLATE,
        j("knowledge", "gotchas.md"): GOTCHAS_INDEX,
        j("knowledge", "gotchas", "00-core.md"): GOTCHAS_CORE,
        j("knowledge", "gotchas", "harness.md"): GOTCHAS_HARNESS,
        j("knowledge", "patterns.md"): PATTERNS_SEED,
    }
    if laya:
        files[j("laya", "README.md")] = LAYA_README
    os.makedirs(j("scratch"), exist_ok=True)
    return [(path, write_if_missing(path, _fill(content, mem, today))) for path, content in files.items()]


def install_laya(laya_bin, memory_dir):
    if os.path.exists(laya_bin):
        return "exists"
    with open(LAYA_ASSET, "r", encoding="utf-8") as f:
        src = f.read()
    src, n = re.subn(r'^MEMORY_DIR = ".*?"', lambda _m: f'MEMORY_DIR = "{memory_dir.rstrip("/")}"', src, count=1, flags=re.M)
    if n != 1:
        raise SystemExit("laya-route asset has no MEMORY_DIR line to rewrite")
    os.makedirs(os.path.dirname(laya_bin) or ".", exist_ok=True)
    with open(laya_bin, "w", encoding="utf-8") as f:
        f.write(src)
    mode = os.stat(laya_bin).st_mode
    os.chmod(laya_bin, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return "installed"


def ensure_gitignore(gitignore_path, memory_dir):
    # No trailing slash: in Orca worktrees the dir is a SYMLINK, and a `dir/`
    # pattern doesn't match a symlink — the worktree would see it as untracked.
    ignore_line = memory_dir.rstrip("/")
    existing = ""
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as f:
            existing = f.read()
    present = {line.strip() for line in existing.splitlines()}
    # A legacy `dir/` line alone still has the symlink bug, so it doesn't count.
    if ignore_line in present or f"/{ignore_line}" in present:
        return False
    addition = ("" if existing.endswith("\n") or not existing else "\n") + (
        "\n" if existing.strip() else ""
    ) + (
        "# ed-orchestrate graph-DAG shared task memory (local-machine only). No trailing\n"
        "# slash: Orca shares it into worktrees as a symlink, which `dir/` doesn't match.\n"
        f"{ignore_line}\n"
    )
    with open(gitignore_path, "w", encoding="utf-8") as f:
        f.write(existing + addition)
    return True


SHARED_DIRS_RE = re.compile(r"(sharedDirectories:\s*\n(?:\s*(?:#.*|-\s*.+)\n)*)", re.MULTILINE)


def ensure_orca_yaml(orca_yaml_path, memory_dir):
    """Best-effort, regex-based (no YAML dependency) idempotent insert into an
    existing `sharedDirectories:` list, or a minimal new file if none exists.
    Never rewrites unrelated content; on any ambiguity, does nothing and
    returns a message telling the caller to add the line by hand."""
    entry = memory_dir.rstrip("/")
    if not os.path.exists(orca_yaml_path):
        content = (
            "# Orca workspace configuration — directories symlinked into every\n"
            "# Orca-created worktree so they see the same state as the main checkout.\n"
            "worktree:\n"
            "  sharedDirectories:\n"
            "    - node_modules\n"
            "    - .orchestrate\n"
            "    - .opencode/agent\n"
            f"    - {entry}\n"
        )
        with open(orca_yaml_path, "w", encoding="utf-8") as f:
            f.write(content)
        return "created"

    with open(orca_yaml_path, "r", encoding="utf-8") as f:
        content = f.read()

    if re.search(rf"^\s*-\s*{re.escape(entry)}\s*$", content, re.MULTILINE):
        return "already-present"

    match = SHARED_DIRS_RE.search(content)
    if not match:
        return "manual"

    block = match.group(1)
    # Match the indent of the list items already there.
    item_match = re.search(r"^(\s*)-\s*", block, re.MULTILINE)
    indent = item_match.group(1) if item_match else "    "
    new_block = block.rstrip("\n") + f"\n{indent}- {entry}\n"
    content = content[: match.start(1)] + new_block + content[match.end(1) :]
    with open(orca_yaml_path, "w", encoding="utf-8") as f:
        f.write(content)
    return "appended"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("memory_dir")
    parser.add_argument("--agents-md", default="AGENTS.md")
    parser.add_argument("--gitignore", default=".gitignore")
    parser.add_argument("--orca-yaml", default="orca.yaml")
    parser.add_argument("--no-orca-yaml", action="store_true")
    parser.add_argument("--laya", action="store_true", help="install the Laya lane router")
    parser.add_argument("--laya-bin", default=".orchestrate/bin/laya-route")
    engram_grp = parser.add_mutually_exclusive_group()
    engram_grp.add_argument("--engram", action="store_true",
                            help="add the Engram persistent-memory section (orchestrator + workers)")
    engram_grp.add_argument("--no-engram", action="store_true", help="remove that section")
    args = parser.parse_args()

    if args.laya:
        result = install_laya(args.laya_bin, args.memory_dir)
        print(
            f"Installed Laya router: {args.laya_bin}"
            if result == "installed"
            else f"Already exists (project-tuned copy, left as is): {args.laya_bin}"
        )
    laya_active = os.path.exists(args.laya_bin)

    legacy_gotchas = os.path.join(args.memory_dir, "knowledge", "gotchas.md")
    legacy = os.path.exists(legacy_gotchas) and not os.path.isdir(
        os.path.join(args.memory_dir, "knowledge", "gotchas")
    )

    for path, created in scaffold_memory_dir(args.memory_dir, laya_active):
        print(f"{'Created' if created else 'Already exists'}: {path}")

    if legacy:
        print(
            f"NOTE: {legacy_gotchas} predates the per-area split and was left untouched. "
            "Delegate `curator` to move its entries into knowledge/gotchas/<area>.md "
            "(00-core.md for rules every task needs) and reduce it to an index.",
            file=sys.stderr,
        )

    try:
        with open(args.agents_md, "r", encoding="utf-8") as f:
            existing = f.read()
    except FileNotFoundError:
        existing = ""
    # Engram is kept on refresh once present (heading is the marker); --no-engram drops it.
    old_block = SPLICE_RE.search(existing)
    had_engram = bool(old_block and ENGRAM_HEADING in old_block.group(0))
    engram_active = args.engram or (had_engram and not args.no_engram)
    new_content = splice(
        existing,
        render_agents_md_block(
            args.memory_dir, args.laya_bin if laya_active else None, engram_active
        ),
    )
    with open(args.agents_md, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(
        f"Spliced ed-orchestrate-graph-dag block into {args.agents_md}"
        + (" (with Engram section)" if engram_active else "")
    )

    changed = ensure_gitignore(args.gitignore, args.memory_dir)
    print(f"{'Updated' if changed else 'Already ignored'}: {args.gitignore}")

    if not args.no_orca_yaml:
        result = ensure_orca_yaml(args.orca_yaml, args.memory_dir)
        if result == "manual":
            print(
                f"WARN: could not confidently locate sharedDirectories in {args.orca_yaml}; "
                f"add `- {args.memory_dir.rstrip('/')}` under worktree.sharedDirectories by hand.",
                file=sys.stderr,
            )
        else:
            print(f"orca.yaml: {result}")


if __name__ == "__main__":
    main()
