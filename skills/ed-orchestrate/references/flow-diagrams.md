# ed-orchestrate — flow diagrams

Visual companion to [../AGENTS.md](../AGENTS.md). Step numbers match that file; if the
procedure changes there, update these. Repo-wide diagrams (graph, Laya):
[docs/ARCHITECTURE.md](../../../docs/ARCHITECTURE.md).

## Full delegation flow (steps 0–8)

```mermaid
flowchart TD
    START(["User: delegate / hand off / supervise"]) --> S0{"0. .orchestrate/bin/laya-route<br/>exists?"}
    S0 -->|yes| R0["Route request: graph / fast / ui-iterate / ask<br/>(fast + ui-iterate skip planner)"]
    S0 -->|no| S1
    R0 --> S1

    S1["1. Read .orchestrate/agents.json<br/>validate_agents_json.py"]
    S1 -->|missing| M1["Old path .claude/ed-orchestrate/?<br/>offer move, else tell user to run<br/>ed-orchestrate-init. Never invent a roster."]
    S1 -->|invalid| M2["Show errors, stop"]
    S1 -->|ok| S2

    S2["2. Resolve role<br/>named > only one > infer from description > ask<br/>(reviewer vs code-reviewer ambiguity always asks)"]
    S2 --> S2a{"2a. Harness token in phrasing<br/>differs from primary?"}
    S2a -->|"no / same"| B1["Use primary binding"]
    S2a -->|yes| FB{"cross-harness fallback<br/>for that harness?"}
    FB -->|found| B2["Use fallback binding<br/>(its own cliFlags, not the role's)"]
    FB -->|missing| ASK["Ask: use primary / add fallback now<br/>(hands into init step 3b) / cancel"]
    ASK --> B1
    B1 --> S3
    B2 --> S3

    S3["3. Delegation mode<br/>hand off / give this to = handoff<br/>supervise / monitor / coordinate = supervised<br/>neutral = role.delegationMode"]
    S3 --> S4["4. Resolve orca executable<br/>(rule read live from orca-cli skill)"]
    S4 --> S5["5. orca skills get orca-cli<br/>+ orchestration when supervised"]
    S5 --> S6{"6. Resolved harness?"}
    S6 -->|"claude / codex / cursor"| H1["--model / --effort thread through<br/>worker-start or terminal create"]
    S6 -->|"opencode / agy / gemini / droid"| H2["harness-&lt;name&gt;.md path:<br/>generated agent file or raw argv"]
    H1 --> S7
    H2 --> S7
    S7["7. Build command: append binding cliFlags<br/>short pointer prompt, scoped tests, no git<br/>render in code block, host confirm, run"]
    S7 -->|"provider error (not task error)"| S2b["2b. Retry once with same-harness fallback<br/>in array order, say which ran"]
    S2b --> S7
    S7 --> S8{"8. Mode"}
    S8 -->|handoff| E1["Report worktree/terminal handle, stop"]
    S8 -->|supervised| E2["check --wait worker_done / escalation / question<br/>surface to user, release / retain / stop per live guide"]
```

## Where one delegation's inputs come from

```mermaid
flowchart LR
    CFG[(".orchestrate/agents.json")] -->|"role: harness, model, provider,<br/>effort, tools, worktreeStrategy,<br/>delegationMode, cliFlags"| RES["Resolved binding"]
    FALL["role.fallbacks[]"] -->|"cross-harness: explicit harness token<br/>same-harness: provider failure"| RES
    PHRASE["User phrasing"] -->|"role, harness token, verb"| RES
    LIVE["orca skills get orca-cli"] -->|"real CLI syntax"| CMD
    RES --> CMD["Command"]
    NODE["Task node pointer<br/>(graph mode)"] -->|"prompt"| CMD
    CMD --> W["Worker"]
```

## Handoff vs supervised

```mermaid
sequenceDiagram
    participant U as User
    participant O as Orchestrator
    participant ORCA as orca CLI
    participant W as Worker
    rect rgb(235,245,255)
    Note over U,W: handoff
    U->>O: "give this to coder"
    O->>ORCA: worktree / terminal create (pointer prompt)
    ORCA->>W: start
    O-->>U: handle, then stop (no polling)
    end
    rect rgb(255,245,230)
    Note over U,W: supervised
    U->>O: "supervise coder on X"
    O->>ORCA: worker-start
    ORCA->>W: start
    loop until worker_done
        O->>ORCA: orchestration check --wait (worker_done, escalation, question)
        ORCA-->>O: event
        O-->>U: surface escalation / question
    end
    W-->>O: worker_done
    O->>ORCA: worker-release / retain / stop
    O->>O: judge by files changed + task node log, not exit code
    end
```
