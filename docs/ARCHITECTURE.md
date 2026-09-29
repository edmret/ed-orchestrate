# Architecture & diagrams

Visual guide to how `ed-orchestrate` / `ed-orchestrate-init` fit together, how the
task graph gets generated, and how the Laya router picks a lane. Text references
these diagrams summarize:
[graph-dag.md](../skills/ed-orchestrate/references/graph-dag.md),
[laya-routing.md](../skills/ed-orchestrate/references/laya-routing.md).

Contents

1. [Big picture](#1-big-picture)
2. [What `ed-orchestrate-init` generates](#2-what-ed-orchestrate-init-generates)
3. [How the graph is generated and walked](#3-how-the-graph-is-generated-and-walked)
4. [Task node lifecycle](#4-task-node-lifecycle)
5. [How Laya works](#5-how-laya-works)
6. [Lanes end to end](#6-lanes-end-to-end)
7. [The router learns: decision + outcome log](#7-the-router-learns-decision--outcome-log)
8. [Single delegation (`ed-orchestrate`)](#8-single-delegation-ed-orchestrate)

---

## 1. Big picture

Two skills, one config file. `init` writes it once; `ed-orchestrate` reads it on every
delegation. The graph and Laya are optional layers on top.

```mermaid
flowchart LR
    U([User]) -->|"set up roster"| INIT["ed-orchestrate-init<br/>(interview)"]
    INIT -->|writes| CFG[(".orchestrate/agents.json<br/>single source of truth")]
    INIT -->|splices roster block| AGM["AGENTS.md"]
    INIT -->|"optional: graph mode"| GRAPH["setup_graph_dag.py"]
    GRAPH -->|scaffolds| MEM[(".ai-memory/<br/>task graph + knowledge")]
    GRAPH -->|"optional --laya"| LAYA[".orchestrate/bin/laya-route"]
    GRAPH -->|splices graph-DAG block| AGM

    U -->|"delegate X to coder"| ORCH["ed-orchestrate<br/>(orchestrator session)"]
    ORCH -->|reads + validates| CFG
    ORCH -.->|"small change? route first"| LAYA
    ORCH -.->|"reads/writes nodes"| MEM
    ORCH -->|"orca CLI (fetched live)"| W["Worker: harness + model + provider<br/>claude / codex / opencode / agy / gemini / cursor / droid"]
    W -->|report| MEM
```

## 2. What `ed-orchestrate-init` generates

Step 5 of the init flow. Steps marked **always** run without asking because each one
fixes a silent failure on a fresh project.

```mermaid
flowchart TD
    A["Interview: roles, harness, model,<br/>provider, fallbacks"] --> B["5a/b Assemble + validate<br/>validate_agents_json.py"]
    B -->|invalid| A
    B -->|valid| C["5c Write .orchestrate/agents.json"]
    C --> D["5d Splice roster block into AGENTS.md<br/>render_agents_md_block.py"]
    D --> D2["5d2 ALWAYS: @AGENTS.md import in CLAUDE.md<br/>ensure_claude_md_import.py"]
    D2 --> D3["5d3 ALWAYS: gemini/agy load AGENTS.md<br/>ensure_gemini_context.py"]
    D3 --> E{"any opencode<br/>role?"}
    E -->|yes| E1["5e .opencode/agent/&lt;role&gt;.md<br/>render_opencode_agent_file.py"]
    E -->|no| F
    E1 --> F{"fresh init?"}
    F -->|yes, asked| F1["5f permissions.deny<br/>orchestrator can't self-code"]
    F -->|no| G
    F1 --> G{"graph mode?<br/>(asked; refreshed silently if wired)"}
    G -->|yes| G1["5g setup_graph_dag.py &lt;dir&gt; [--laya]"]
    G -->|no| H
    G1 --> H["5h ensure_harness_permissions.py<br/>opencode external_directory / agy trust"]
    H --> Z(["Summary to user"])
```

Why the always-on steps exist:

```mermaid
flowchart LR
    subgraph Problem["Without the fix"]
        P1["CLAUDE.md exists"] -->|shadows| P2["AGENTS.md never auto-loaded"]
        P3["gemini-cli reads only GEMINI.md"] -->|ignores| P2
        P4["opencode / agy worker writes<br/>via shared symlink"] -->|denied| P5["worker can't save its report"]
    end
    subgraph Fix["init fixes"]
        F1["@AGENTS.md import"] --> OK["every harness sees roster + graph rules"]
        F2["context.fileName + GEMINI.md pointer"] --> OK
        F3["external_directory: allow<br/>agy --dangerously-skip-permissions"] --> OK2["workers can write"]
    end
```

## 3. How the graph is generated and walked

### 3a. Generation: `setup_graph_dag.py <dir>`

Idempotent. Templates are only ever created, never overwritten. The AGENTS.md block is
regenerated on every re-run.

```mermaid
flowchart TD
    S["setup_graph_dag.py &lt;memory-dir&gt;"] --> T["Scaffold templates<br/>(skip if file exists)"]
    S --> B["Splice BEGIN/END ed-orchestrate-graph-dag<br/>block into AGENTS.md (replace span only)"]
    S --> G["Append &lt;dir&gt; to .gitignore<br/>(no trailing slash: worktree symlink)"]
    S --> O["Register &lt;dir&gt; in orca.yaml<br/>worktree.sharedDirectories"]
    S -->|"--laya"| L["Install .orchestrate/bin/laya-route<br/>+ &lt;dir&gt;/laya/README.md"]

    T --> TREE
    subgraph TREE["&lt;memory-dir&gt;/ (default .ai-memory/)"]
        direction TB
        I["INDEX.md — map of content"]
        subgraph tasks["tasks/"]
            t1["TASK-template.md"]
            t2["TASK-batch-integration-template.md"]
            t3["ITER-template.md"]
        end
        subgraph others["plans / adrs / reviews"]
            p1["plans/PLAN-template.md"]
            p2["adrs/ADR-template.md"]
            p3["reviews/REVIEW-template.md"]
        end
        subgraph know["knowledge/"]
            k1["gotchas.md (area index)"]
            k2["gotchas/00-core.md, harness.md (seeds)"]
            k3["patterns.md"]
        end
        lay["laya/decisions.jsonl (created at first route)"]
    end
```

### 3b. Walking: one batch

`planner` builds the DAG once; the orchestrator walks it. Review happens once per
batch, not per task.

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant O as Orchestrator
    participant P as planner
    participant C as coder / tester (parallel worktrees)
    participant I as integrator
    participant R as reviewer ∥ code-reviewer
    participant K as curator
    participant M as .ai-memory

    U->>O: feature request
    O->>P: "Plan goal G" (pointer, not full context)
    P->>M: PLAN-n.md + TASK-*.md (frontmatter edges) + batch-integration node
    loop every ready node (depends_on all done)
        O->>C: "Execute TASK-x. Governed by ADR-y."
        C->>M: read node + 00-core.md + node.context only
        C->>C: scoped unit tests only (no e2e, no full suite, no git)
        C->>M: Execution log, status -> review
        O->>O: branch + commit green wave (rollback point)
    end
    O->>I: batch-integration node
    I->>I: merge branches, typecheck+build, lint, full unit, e2e
    O->>R: review combined batch diff ONCE
    R->>M: REVIEW-n.md
    O->>O: triage: accept -> 1 coder fix-pass, or waive with reason
    O->>I: re-gate
    I->>M: nodes -> done, Laya outcome recorded
    O->>K: periodic hygiene pass
    K->>M: fold gotchas into knowledge/gotchas/&lt;area&gt;.md
```

Only nodes the planner flags `review: early` (auth, shared state, public API, DI
tokens, cross-cutting infra) get an isolated review before dependents build on them.

## 4. Task node lifecycle

```mermaid
stateDiagram-v2
    state "in-progress" as in_progress
    [*] --> backlog: planner emits node
    backlog --> ready: all depends_on done
    ready --> in_progress: orchestrator dispatches
    in_progress --> review: worker reports green scoped tests
    in_progress --> backlog: scope fence hit, follow-up task proposed
    review --> in_progress: early review or gate failed, fix-pass
    review --> done: integration + batch review passed
    done --> [*]
```

Edges live in each node's YAML frontmatter:

```mermaid
flowchart LR
    T0["TASK-001<br/>depends_on: []"] --> T2["TASK-003<br/>depends_on: 001, 002"]
    T1["TASK-002<br/>depends_on: []"] --> T2
    T2 --> INT["TASK-004-batch-integration<br/>assigned_to: integrator"]
    T3["TASK-005<br/>depends_on: []"] --> INT
    INT -.->|"reviewer ∥ code-reviewer once"| REV["REVIEW-1.md"]
```

## 5. How Laya works

`laya-route` is a stdlib-only script every harness can call from a shell. It fuses two
signals: **Laya** (a local model server answering atomic yes/no questions) and **path
facts** (regex over changed files). A deterministic combiner picks the lane — no LLM
makes the final call.

```mermaid
flowchart TD
    REQ["Request (English)<br/>+ --files or --git-diff"] --> SPLIT{" "}
    SPLIT --> LQ["Ask Laya 8 atomic questions<br/>POST /v1/systemone (noul scores 0..1)<br/>visual_only, pure_logic, state_or_api,<br/>navigation, auth_rbac, forms, e2e_mock, testing"]
    SPLIT --> PF["Classify each file into a layer<br/>navigation / state_api / test / logic /<br/>styles / template / component / config"]

    LQ -->|"timeout / down"| NOA["answers = None"]
    LQ -->|ok| ANS["answers"]

    PF --> GL{"graph layer touched<br/>(navigation, state_api, config)<br/>or ≥ 4 files?"}
    GL -->|"yes — path facts WIN"| GRAPH(["lane = graph"])
    GL -->|no| HAVE{"Laya answered?"}

    NOA --> HAVE
    ANS --> HAVE

    HAVE -->|no| FB{"files all visual?"}
    FB -->|yes| UI(["ui-iterate"])
    FB -->|"visual/logic/test only"| FAST(["fast"])
    FB -->|"otherwise"| GRAPH2(["graph — safe default"])

    HAVE -->|yes| HOT{"deciding question > 0.65?<br/>state_or_api / navigation / auth_rbac"}
    HOT -->|yes| GRAPH3(["graph"])
    HOT -->|no| UNS{"deciding question<br/>in 0.35–0.65?"}
    UNS -->|"yes, no files"| ASK(["ask user 1 question"])
    UNS -->|"yes, files exist"| SETTLE["path facts settle:<br/>non-trivial layer -> graph, else fast"]
    UNS -->|no| VIS{"pure_logic ≤ 0.5<br/>and files visual/none?"}
    VIS -->|yes| UI2(["ui-iterate"])
    VIS -->|no| FAST2(["fast"])
```

Output of every call, and how it feeds dispatch:

```mermaid
flowchart LR
    D["laya-route JSON<br/>{id, lane, tdd, context,<br/>answers, facts, reason, laya}"]
    D --> L["lane -> which workflow"]
    D --> T["tdd: first | defer<br/>logic/store/guard/parser = always first"]
    D --> C["context -> cold-start manifest<br/>00-core.md + only area files that exist"]
    D --> ID["id -> outcome join key"]
```

Design rules baked in (measured, see `laya-routing.md`):

- **Atomic questions only.** Single-aspect questions scored 9–10/10; one broad "fast or
  graph?" question scored 6–7/10 and every miss was unsafe (graph → fast).
- **Path facts override Laya.** Laya timed out on 5 of 13 early requests; path facts
  routed all 5 correctly. Always pass `--files` / `--git-diff` when known.
- **Uncertain means `graph`.** Failure mode is "too careful", never "too loose".
- **Lane + files pick context; Laya scores pick only the lane.** Stops a high
  state/API score on a UI tweak from dragging in graph-wide context.

## 6. Lanes end to end

```mermaid
flowchart TD
    R["laya-route decision"] --> L{lane}

    L -->|graph| G1["planner -> task DAG"] --> G2["waves of coder/tester nodes<br/>(TDD per node)"] --> G3["batch-integration node<br/>integrator gate + reviewer ∥ code-reviewer once"]

    L -->|fast| F1["ONE coder, ONE task node<br/>(no planner), TDD first, scoped unit tests"] --> F2["joins next batch's integration phase<br/>or a one-task integration"]

    L -->|ui-iterate| U1["ONE worktree, ONE long-lived coder<br/>+ ITER ledger"] --> U2["each tweak = new turn, same agent<br/>no tests / e2e / review per turn"] --> U3["orchestrator commits wip(ui-iter)<br/>coder logs Debt per turn"]

    L -->|ask| A1["ask user one question"] --> A2["re-route with --files"] --> R

    U3 --> U4{"turn needs store / route /<br/>guard / API change?"}
    U4 -->|yes| U5["stop, route that part separately<br/>-> graph task"]
    U4 -->|no| U2
    U3 -->|"user: close iterations"| U6["planner reads ledger"] --> U7["debt-closure DAG:<br/>tester nodes (specs), coder nodes (structural)<br/>every debt item = node or explicit waiver"] --> G3
```

| Lane | Cost | Guarantees |
| --- | --- | --- |
| `graph` | highest | full DAG, one batch integration + review |
| `fast` | low | TDD first, still ends in an integration phase |
| `ui-iterate` | lowest per turn | skipped work is logged as debt and *must* be closed at the end |
| `ask` | one question | re-routed with file facts |

## 7. The router learns: decision + outcome log

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant LR as laya-route
    participant LY as Laya server
    participant LOG as laya/decisions.jsonl
    participant I as integrator
    participant CU as curator

    O->>LR: --request-en "..." --files ...
    LR->>LY: 8 atomic questions
    LY-->>LR: scores (or timeout)
    LR->>LOG: {kind: decision, id, lane, tdd, context, answers, files, request}
    LR-->>O: lane + tdd + context + id
    Note over O,I: work happens in the chosen lane
    I->>LR: outcome --id ID --value correct | wrong-lane | wrong-tdd | wrong-context
    LR->>LOG: {kind: outcome, id, value, note}
    O->>LR: outcome (also when a fast/ui-iterate run had to escalate)
    CU->>LOG: review misses, tune PROJECT TUNING block
    Note over LOG: decision + outcome joined by id<br/>= Laya fine-tuning dataset
```

Tuning knobs live in the `PROJECT TUNING` block of the installed
`.orchestrate/bin/laya-route` (the project owns that copy; init never overwrites it):
`LAYER_RULES`, `GRAPH_LAYERS`, `QUESTIONS` / `DECIDING`, `TOPIC_CONTEXT` /
`LAYER_CONTEXT`.

## 8. Single delegation (`ed-orchestrate`)

What happens for one "give this to the tester" request, with or without the graph.

```mermaid
flowchart TD
    A["User: delegate task to role"] --> B{".orchestrate/agents.json<br/>exists?"}
    B -->|"no (old path?)"| B1["offer move, or tell user to run<br/>ed-orchestrate-init. Never invent a roster."]
    B -->|yes| C["validate_agents_json.py"]
    C -->|fail| C1["show errors, stop"]
    C -->|ok| D["Resolve role:<br/>named > only one > infer from description > ask"]
    D --> E{"delegation names a<br/>different harness?"}
    E -->|"yes"| E1["use matching cross-harness fallback binding"]
    E -->|no| E2["use primary binding<br/>(same-harness fallback if provider down)"]
    E1 --> F
    E2 --> F["Fetch live CLI surface:<br/>orca skills get orca-cli<br/>(never hardcoded in this repo)"]
    F --> G{"delegationMode"}
    G -->|handoff| G1["orca-cli handoff"]
    G -->|supervised| G2["orchestration skill:<br/>coordinator loop, worker_done wait"]
    G1 --> H["Confirm command, run, relay result"]
    G2 --> H
```

Model selection differs per harness — see
[harness-model-support.md](../skills/ed-orchestrate/references/harness-model-support.md):
`--model`/`--effort` thread through for `claude`, `codex`, `cursor`; `opencode`, `agy`,
`gemini`, `droid` use per-harness reference files or a generated agent file.
