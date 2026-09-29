# ed-orchestrate-init — flow diagrams

Visual companion to [../AGENTS.md](../AGENTS.md). Step numbers match that file; if the
procedure changes there, update these. Repo-wide diagrams (graph, Laya):
[docs/ARCHITECTURE.md](../../../docs/ARCHITECTURE.md).

## Interview (steps 1–4)

```mermaid
flowchart TD
    START(["/ed-orchestrate-init [role?]"]) --> ARG{"argument matches<br/>existing role?"}
    ARG -->|yes| RM["Role menu:<br/>edit primary / fallback / cancel"]
    RM -->|primary| S3
    RM -->|fallback| S3b
    ARG -->|no| S1{"1. .orchestrate/agents.json<br/>exists?"}
    S1 -->|"no, old .claude/ path"| MV["Offer move to .orchestrate/"] --> S1b
    S1 -->|no| S2
    S1 -->|yes| S1b{"Start fresh / Edit existing /<br/>Add-edit fallback / Cancel"}
    S1b -->|fresh| S2
    S1b -->|edit| S2
    S1b -->|fallback| S3b

    S2["2. Pick roles (multi-select)<br/>10 built-ins + max 1 custom"] --> S3
    subgraph LOOP["3. for each role"]
        S3["Call A: harness, effort,<br/>delegation mode, worktree strategy"] --> CB["Call B: model<br/>opencode: read opencode.json, split provider/model<br/>others: examples + Other, provider = null"]
        CB --> PR["Description + systemPromptSeed<br/>built-in: role-defaults.md verbatim<br/>custom: free text, seed null"]
        PR --> AG{"harness = agy?"}
        AG -->|yes| AF["Propose cliFlags:<br/>--dangerously-skip-permissions"]
        AG -->|no| NXT
        AF --> NXT["next role"]
    end
    NXT --> S4
    S4["4. Confirm: roster table<br/>Yes write / Edit a role / Cancel"]
    S4 -->|"edit role"| S3
    S4 -->|yes| S5(["5. Generate"])
```

## Fallback sub-flow (step 3b)

```mermaid
flowchart TD
    A["a. Which role<br/>(skip if scoped or single role)"] --> B{"b. Kind"}
    B -->|"same-harness"| E
    B -->|"cross-harness"| C["c/d. Harnesses left =<br/>enum - primary - existing fallbacks"]
    C -->|"set empty"| X["Offer replace / remove instead"]
    C --> E["e. Model (call B verbatim)<br/>omit harness key if same-harness<br/>agy: ask headless flag -> entry's own cliFlags"]
    E --> F["f. Effort incl. 'inherit from primary'"]
    F --> G{"g. add / edit again / cancel<br/>(same harness+provider exists: replace?)"}
    G -->|"edit again"| B
    G -->|add| H["h. Append to role.fallbacks<br/>validate, write agents.json, re-splice roster<br/>NOT regenerating opencode agent file"]
    H --> I["i. Print fallback list"]
```

## Generate (step 5) with artifacts

```mermaid
flowchart TD
    G0["5a/b assemble + validate<br/>(reuses ed-orchestrate validator)"] -->|fail| FIX["fix draft, never write invalid"] --> G0
    G0 --> W1[".orchestrate/agents.json"]
    W1 --> W2["5d AGENTS.md roster block<br/>BEGIN/END ed-orchestrate-roster"]
    W2 --> W3["5d2 CLAUDE.md @AGENTS.md import<br/>ALWAYS"]
    W3 --> W4["5d3 .gemini/settings.json + GEMINI.md pointer<br/>ALWAYS"]
    W4 --> Q1{"opencode role?"}
    Q1 -->|yes| W5[".opencode/agent/role.md<br/>ask before overwriting existing"]
    Q1 -->|no| Q2
    W5 --> Q2{"fresh init and no<br/>permissions.deny yet?"}
    Q2 -->|"ask: yes"| W6["deny Edit/Write on src glob<br/>settings.json, or settings.local.json<br/>if a claude worker can edit"]
    Q2 -->|"no / skip"| Q3
    W6 --> Q3{"5g graph wired?"}
    Q3 -->|"already wired"| W7["silently re-run setup_graph_dag.py<br/>ask Laya only if router missing"]
    Q3 -->|"not wired: ask"| W8["memory dir (default .ai-memory)<br/>then Laya yes / no / explain"]
    Q3 -->|"declined"| Q4
    W7 --> Q4
    W8 --> Q4
    Q4{"5h opencode binding?"} -->|yes| W9["opencode.json<br/>external_directory: allow<br/>ALWAYS"]
    Q4 -->|no| Q5
    W9 --> Q5{"agy binding?"}
    Q5 -->|"ask: yes"| W10["~/.gemini/antigravity-cli/settings.json<br/>user-global: repo + worktrees dir"]
    Q5 -->|no| SUM
    W10 --> SUM(["Summary: files, roster, warnings,<br/>graph / Laya / deny status"])
```

## Idempotency: what re-runs may touch

```mermaid
flowchart LR
    subgraph Regenerated["Regenerated on every run"]
        R1["roster block in AGENTS.md"]
        R2["graph-DAG block in AGENTS.md"]
        R3["claude-import block in CLAUDE.md"]
    end
    subgraph AddOnly["Created only if missing"]
        A1["memory-dir templates"]
        A2[".orchestrate/bin/laya-route<br/>(project-tuned copy)"]
        A3[".gitignore / orca.yaml entries"]
    end
    subgraph Never["Never touched"]
        N1["content outside BEGIN/END markers"]
        N2["existing template files"]
        N3["hand-maintained .opencode/agent files<br/>without asking"]
    end
```
