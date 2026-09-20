# Interview flow — exact question script

Literal question objects for `ed-orchestrate-init/AGENTS.md` steps 1–4, including
step 3b. On Claude
Code these map straight to `AskUserQuestion` calls (question/header/options/
multiSelect); on opencode/agy hosts, render each as a numbered plain-text list
per that host's overlay.

## Step 1 — existing config detected

```
question: "This project already has .orchestrate/agents.json. What do you want to do?"
header: "Existing config"
multiSelect: false
options:
  - label: "Start fresh (Recommended if roster is outdated)"
    description: "Discard current roles and rebuild the roster from scratch."
  - label: "Edit existing"
    description: "Load current roles as the starting point; add, remove, or change individual roles."
  - label: "Add or edit a fallback harness"
    description: "Give one role an alternate harness binding (model/provider/effort). Skips to step 3b."
  - label: "Cancel"
    description: "Leave agents.json and AGENTS.md untouched."
```

## Step 2 — role picker

```
question: "Which sub-agent roles do you want in this project's roster?"
header: "Roles"
multiSelect: true
options: one per built-in role, each option's description quoted from that role's
  `description` in `ed-orchestrate/references/role-defaults.md` — don't restate
  them here, that file is the single source of truth:
  - label: "coder"
  - label: "planner"
  - label: "tester"
  - label: "reviewer"
  - label: "architect"
  - label: "code-reviewer"
  - label: "designer"
  - label: "qa-designer"
  - label: "curator"
  - label: "integrator"
```
("Other" is always available for one custom role name — v1 supports exactly one
extra custom role per init pass.)

## Step 3, call A — per role: harness / effort / mode / worktree

Ask all 4 in one call (fits the 1–4 question cap):

```
question 1: "Which harness should <role> run on?"
header: "Harness"
multiSelect: false
options:
  - label: "claude"
    description: "Claude Code — supports --model/--effort natively via orca."
  - label: "codex"
    description: "OpenAI Codex CLI — supports --model natively via orca."
  - label: "opencode"
    description: "opencode CLI — multi-provider (e.g. this machine's custom nan provider). Model/provider baked into a generated .opencode/agent/<role>.md."
  - label: "agy"
    description: "Antigravity CLI — model is a flat id (e.g. gemini-3.6-flash-high), no separate provider."
```
(If the user wants gemini/cursor/droid, they type it via "Other" — the option
list surfaces the 4 most common choices only, per the harness capability notes
in `ed-orchestrate/references/harness-model-support.md`.)

```
question 2: "Reasoning effort for <role>?"
header: "Effort"
multiSelect: false
options:
  - label: "none"
    description: "Don't set an effort flag (default for harnesses without one, e.g. opencode)."
  - label: "low"
  - label: "medium"
  - label: "high"
    description: "Best for planner/reviewer roles doing harder reasoning."
```

```
question 3: "Default delegation mode for <role>?"
header: "Mode"
multiSelect: false
options:
  - label: "Fire-and-forget (handoff)"
    description: "Kick off the work and stop supervising — report the worktree/terminal handle and move on."
  - label: "Supervised"
    description: "Wait for worker_done/escalation/question via orca orchestration's check --wait loop."
```

```
question 4: "Worktree strategy for <role>?"
header: "Worktree"
multiSelect: false
options:
  - label: "current"
    description: "Run in the current worktree, no new one created."
  - label: "new-child"
    description: "Create a new worktree as a child of the current one (Recommended for most roles)."
  - label: "new-top-level"
    description: "Create a new parentless worktree."
```

## Step 3, call B — per role: model

If harness is `opencode`: attempt to read `~/.config/opencode/opencode.json`; for
each `provider.<id>.models.<model>` entry found, offer `<id>/<model>` as an
option (cap at 3, pick a representative spread if there are more); always
include "Other" for a manual entry. On read failure, skip straight to a
free-text prompt instead of a structured question.

```
question: "Which model should <role> use on opencode?"
header: "Model"
multiSelect: false
options (example, actual list built from opencode.json):
  - label: "nan/qwen3.6"
  - label: "nan/gemma4"
  - label: "ollama/qwen3:14b"
```

Else (any other harness), offer 2–3 illustrative example ids (explicitly caveat
in the question text: "illustrative — check `<harness> --help`/`<harness>
models` for the current list") plus Other:

```
question: "Which model should <role> use on <harness>?"
header: "Model"
multiSelect: false
options (illustrative, harness-dependent):
  claude:  opus, sonnet, haiku
  codex:   gpt-5.5, gpt-5.5-mini
  agy:     gemini-3.6-flash-high, claude-sonnet-4-6, gpt-oss-120b-medium
```

For opencode, split the chosen `provider/model` string on the first `/` into
`model` and `provider` fields — never ask provider separately. For every other
harness, `provider` is always `null`.

## Step 3 — description and seed (free text, not a structured question)

Built-in role (`coder`, `planner`, `tester`, `reviewer`, `architect`,
`code-reviewer`, `designer`, `qa-designer`, `curator`, `integrator`) — show both defaults from
`ed-orchestrate/references/role-defaults.md` and offer accept-or-override:

> Defaults for `<role>`:
> - description: "<role-defaults.md description>"
> - seed prompt: "<role-defaults.md systemPromptSeed>"
>
> Accept both, or type a replacement one-line description. (The seed is written
> into `agents.json` either way — edit it there if you want it different.)

Custom role — no default exists, so ask as before:

> "One-line description for `<role>` (used in the AGENTS.md roster table, and
> for opencode roles becomes the generated agent file's `description:`)."

Custom roles get `systemPromptSeed: null`.

## Step 3b — add or edit a fallback

Role picker, asked only when the entry point didn't already scope to one role and
the roster has more than one role:

```
question: "Which role do you want to add or edit a fallback for?"
header: "Role"
multiSelect: false
options: one per existing role name, description = that role's current `description`.
```

Kind picker, always asked next:

```
question: "What kind of fallback for <role>?"
header: "Fallback kind"
multiSelect: false
options:
  - label: "Same-harness (provider retry)"
    description: "Stays on <role>'s primary harness; swaps provider and model — e.g. a resilience binding for when the primary provider is unavailable."
  - label: "Cross-harness override"
    description: "Runs on a different harness entirely, used only when the user names that harness at delegation time."
```

**Same-harness**: skip the harness picker below entirely, go straight to the
model question with the effective harness fixed to `<role>`'s primary harness.

**Cross-harness**: harness picker — options computed at ask-time as the schema's
harness enum minus the role's primary harness minus its existing cross-harness
fallback harnesses. If that set is empty, skip this question and offer
replace/remove of an existing fallback instead:

```
question: "Which harness should be a fallback for <role>?"
header: "Fallback harness"
multiSelect: false
options: one per harness in the computed set, reusing step 3 call A question 1's
  one-line descriptions where the harness appears there.
```

Model — reuse step 3 call B verbatim (both the opencode-read-config branch and
the illustrative-examples-plus-Other branch), substituting the effective harness
(role's primary for same-harness, or the harness just chosen for cross-harness).

Effort — reuse step 3 call A question 2 verbatim, with an added first option:

```
  - label: "Inherit from primary"
    description: "Don't set an effort override — use whichever effort the primary binding resolves to."
```

```
question: "Add this fallback for <role>?"
header: "Confirm fallback"
multiSelect: false
options:
  - label: "Yes, add it"
  - label: "Edit again"
    description: "Change the kind, harness, model, or effort before adding."
  - label: "Cancel"
    description: "Discard it; don't modify agents.json."
```

When an entry with the same effective `(harness, provider)` pair already
exists, the question text is "Replace the existing fallback for `<provider or
harness>` on `<role>`?" with the same three options.

## Step 4 — confirm

```
question: "Write this roster to .orchestrate/agents.json and AGENTS.md?"
header: "Confirm"
multiSelect: false
options:
  - label: "Yes, write it"
  - label: "Edit a specific role"
    description: "Pick a role, then edit its primary config (step 3) or its fallbacks (step 3b)."
  - label: "Cancel"
    description: "Discard the draft, write nothing."
```

## Step 5f — no-self-code enforcement (first-time init only)

Only asked on a fresh `.orchestrate/agents.json` and only if
`.claude/settings.json` has no existing `permissions.deny` entry:

```
question: "Enforce the orchestrator's no-self-coding boundary at the permission layer too (not just by convention)?"
header: "No self-code"
multiSelect: false
options:
  - label: "Yes"
    description: "Deny this project's orchestrator session Edit/Write on a path you choose (e.g. src/**) via .claude/settings.json."
  - label: "No"
    description: "Rely on AGENTS.md's role-boundary convention alone."
  - label: "Explain first"
    description: "Show what this does before deciding."
```

On yes, follow with a plain-text prompt: "Which path glob(s) should be denied
to the orchestrator (comma-separated)? Default: `src/**`."

## Step 5g — graph-engineered task delegation (skipped if already wired)

Only asked if the target `AGENTS.md` has no
`<!-- BEGIN:ed-orchestrate-graph-dag -->` block yet:

```
question: "Set up graph-engineered task delegation for this project?"
header: "Graph DAG"
multiSelect: false
options:
  - label: "Yes"
    description: "Planner emits a task DAG in a shared directory; the orchestrator dispatches by graph, not a flat loop. See ed-orchestrate/references/graph-dag.md."
  - label: "No"
    description: "Keep delegating one task at a time via ed-orchestrate, no shared task-memory directory."
  - label: "Explain first"
    description: "Show what this does before deciding."
```

On yes, follow with a plain-text prompt: "Which directory should hold the
shared task graph? Default: `.ai-memory`."
