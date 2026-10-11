# `agents.json` schema

Location (target project, repo-root-relative): `.orchestrate/agents.json`.
This is the canonical source of truth for the sub-agent roster — both
`ed-orchestrate` (delegation) and `ed-orchestrate-init` (generation) read/write this
exact schema. `ed-orchestrate-init` also renders a human-readable copy into the
target project's `AGENTS.md` — see
[agents-md-block-format.md](agents-md-block-format.md) — but that block is generated
output, not a second source of truth.

## Shape

```json
{
  "version": 1,
  "project": "optional freeform label",
  "roles": {
    "coder": {
      "description": "Implements features and fixes bugs against the current task spec.",
      "harness": "opencode",
      "model": "qwen3.6",
      "provider": "nan",
      "effort": null,
      "tools": { "bash": true, "read": true, "edit": true, "glob": true, "grep": true },
      "systemPromptSeed": "You are a software engineer subagent...",
      "worktreeStrategy": "new-child",
      "delegationMode": "handoff",
      "fallbacks": [
        { "provider": "opencode-go", "model": "deepseek-v4.1-flash" },
        { "harness": "claude", "model": "sonnet",  "provider": null, "effort": "medium" }
      ]
    },
    "planner": {
      "description": "Breaks goals into dependency-aware task lists.",
      "harness": "claude",
      "model": "opus",
      "provider": null,
      "effort": "high",
      "tools": null,
      "systemPromptSeed": null,
      "worktreeStrategy": "current",
      "delegationMode": "supervised"
    }
  },
  "defaults": {
    "role": "coder",
    "worktreeStrategy": "new-child",
    "delegationMode": "handoff"
  }
}
```

## Field reference

| Field | Type | Required | Notes |
|---|---|---|---|
| `version` | int | yes | schema version, `1` for v1 |
| `project` | string | no | freeform label |
| `roles.<name>` | object, key `^[a-z][a-z0-9-]*$` | yes, ≥1 role | |
| `.description` | string | yes | used in the AGENTS.md roster table, as the opencode agent file's `description:`, and as part of the task prompt seed for any harness |
| `.harness` | enum: `claude \| codex \| opencode \| agy \| cursor \| gemini \| droid` | yes | product-facing name; mapping to orca's `--agent` id lives in [harness-model-support.md](harness-model-support.md), not duplicated here |
| `.model` | string | yes | harness-specific id string; for opencode this is the bare model id (provider is a separate field) |
| `.provider` | string or `null` | yes (nullable) | **meaningful only when `harness == "opencode"`** in v1; should be `null` for every other harness (the validator warns, not errors, on this — forward-compatible if another harness grows a provider concept) |
| `.effort` | `"low" \| "medium" \| "high"` or `null` | yes (nullable) | only applied for harnesses that support it (today: claude, codex, agy) |
| `.tools` | object of booleans, or `null` | yes (nullable) | opencode tool-permission map (`bash`/`read`/`edit`/`glob`/`grep`); ignored for other harnesses, kept for forward compatibility |
| `.systemPromptSeed` | string or `null` | yes (nullable) | becomes the opencode agent file body, or is prepended to the task prompt for other harnesses. For built-in roles `ed-orchestrate-init` materializes the default from [role-defaults.md](role-defaults.md) at init time; the value is then owned by the project, so editing `role-defaults.md` later never retroactively changes an existing roster |
| `.worktreeStrategy` | `"current" \| "new-child" \| "new-top-level"` | yes | |
| `.delegationMode` | `"handoff" \| "supervised"` | yes | default only — explicit user phrasing at delegation time always wins (see `ed-orchestrate/AGENTS.md` step 3) |
| `.cliFlags` | array of strings, or absent | no | extra raw CLI flags appended to this role's delegation invocation on its **primary** harness (and same-harness fallbacks). Main use: `["--dangerously-skip-permissions"]` for an `agy` role — headless agy denies every file read/write without it ([harness-agy.md](harness-agy.md)); `ed-orchestrate-init` proposes it for agy roles and the validator warns when an agy binding lacks it |
| `.fallbacks` | array of objects, or absent | no | alternate bindings. Absent and `[]` are equivalent. Never asked during `ed-orchestrate-init`'s fresh-role flow — only via its step 3b. Two shapes, distinguished by whether `harness` is present: |
| `.fallbacks[].harness` | same enum as `.harness`, or **absent** | no, per entry | **absent** → same-harness fallback: a resilience/retry binding used when the primary `(model, provider)` pair is unavailable — e.g. an alternate opencode provider hosting a compatible model variant (`ed-orchestrate/AGENTS.md` step 2b). **present** → cross-harness override, used only when the user explicitly names a different harness at delegation time (`ed-orchestrate/AGENTS.md` step 2a); must differ from the role's primary `.harness`. Each `(effective harness, provider)` pair — where effective harness is this field or, if absent, the role's primary harness — must be unique across the array |
| `.fallbacks[].model` | string | yes, per entry | same semantics as `.model` — for a same-harness fallback this is usually a different model id than the primary (the provider-specific variant that alternate provider actually hosts), not a byte-identical copy |
| `.fallbacks[].provider` | string or `null`, or absent (≡ `null`) | no, per entry | same semantics as `.provider` — meaningful only when the effective harness is `opencode` |
| `.fallbacks[].cliFlags` | array of strings, or absent | no, per entry | flags for this binding. **Absent** → a same-harness entry inherits the role's `.cliFlags`; a cross-harness entry gets **none** (the role's flags belong to its primary harness — e.g. an agy-only flag must not reach opencode). A cross-harness entry to `agy` therefore needs its own `["--dangerously-skip-permissions"]` |
| `.fallbacks[].effort` | same enum as `.effort`, or absent (≡ inherit primary `.effort`) | no, per entry | same semantics as `.effort` |
| `.modelTiers` | array of objects, or absent | no | **N cheaper model bindings below the role's own** (which is the reserved top tier, named `strong`), ordered cheapest first. A router (`laya-route`) picks a tier *name* per task; the orchestrator dispatches with that tier's model. Mainly for `coder`; allowed on any role. Distinct from `fallbacks`: tiers are chosen by **task difficulty** (routing), fallbacks by **availability** (provider failure) or **user override**. Absent ≡ `[]` ≡ no tiering |
| `.modelTiers[].name` | string `^[a-z][a-z0-9-]*$` | yes, per entry | unique within the array; `strong` is reserved (the role's own `harness`/`model`/`provider`). Conventional: `cheap`, `mid` |
| `.modelTiers[].model` | string | yes, per entry | same semantics as `.model` |
| `.modelTiers[].harness` | same enum as `.harness`, or **absent** | no, per entry | absent → same harness as the role. May differ (e.g. a cheap opencode tier under a claude `strong`) |
| `.modelTiers[].provider` / `.effort` | as `.provider` / `.effort` | no, per entry | provider only meaningful for effective harness `opencode`; `effort` absent ≡ inherit |
| `.modelTiers[].useWhen` | string, or absent | no, per entry | one line: the kind of task this tier is good enough for. Shown in the roster, quoted to the planner/router, and the thing you tune from outcomes |
| `.modelTiers[].cliFlags` | array of strings, or absent | no, per entry | same inheritance rule as `.fallbacks[].cliFlags` (same-harness inherits the role's; cross-harness gets none) |
| `.tierPolicy` | object, or absent | no | requires non-empty `.modelTiers` |
| `.tierPolicy.mode` | `"off" \| "shadow" \| "on"` | no (default `shadow`) | `shadow`: router computes + logs the tier, dispatch stays `strong`. `on`: dispatch follows the tier. `off`: ignore tiers |
| `.tierPolicy.start` | tier name or `"strong"` | no | tier to use when the router gives no answer (default `strong` — the safe choice) |
| `.tierPolicy.escalateAfter` | int ≥ 1 | no (default 2) | failed attempts on a tier before moving up to the next one (cascade ends at `strong`) |
| `defaults.role` | string | no | must reference an existing key under `roles` |
| `defaults.worktreeStrategy` / `defaults.delegationMode` | same enums as above | no | fallback for a hand-edited role object missing that field (shouldn't happen via `ed-orchestrate-init`, since it always fills every field) |

`worktreeStrategy`, `delegationMode`, `tools`, and `systemPromptSeed` stay
role-level and apply whichever binding resolves — primary, fallback or tier.
`cliFlags` is binding-scoped as described above.

## Model tiers example: coder with N models

```json
"coder": {
  "harness": "opencode", "model": "deepseek-v4-flash", "provider": "nan", "effort": null,
  "...": "...other required fields...",
  "modelTiers": [
    { "name": "cheap", "model": "qwen3.6", "provider": "nan",
      "useWhen": "labels, styling, markup, i18n, docs, copy of an existing pattern" },
    { "name": "mid", "model": "kimi-k2.6", "provider": "nan",
      "useWhen": "new component/service logic with a clear spec and tests" }
  ],
  "tierPolicy": { "mode": "shadow", "start": "strong", "escalateAfter": 2 }
}
```

Tier order is the escalation ladder: `cheap` → `mid` → `strong` (the role's own
binding, always last). Rollout, outcome logging and tuning:
[laya-routing.md](laya-routing.md#model-tiers-n-coder-models). Projects that
predate this field used `coder.fallbacks[0]` as the "cheap" tier by convention —
migrate by moving that entry into `modelTiers` with `"name": "cheap"`; the
validator does not require it, and the old convention keeps validating.

## Fallback example: same-harness provider retry

```json
"reviewer": {
  "description": "Reviews a diff for correctness, security, and regressions before merge.",
  "harness": "opencode",
  "model": "qwen3.8-flash",
  "provider": "nan",
  "effort": "high",
  "tools": { "bash": false, "read": true, "edit": false, "glob": true, "grep": true },
  "systemPromptSeed": null,
  "worktreeStrategy": "current",
  "delegationMode": "supervised",
  "fallbacks": [
    { "provider": "opencode-go", "model": "qwen3.8-flash-alt" }
  ]
}
```

Here `reviewer`'s `fallbacks[0]` has no `harness` key, so it's a same-harness
binding: if the primary `nan` provider is unavailable, retry on `opencode-go`
with that provider's model-id variant, still on `opencode`. Contrast with a
cross-harness override entry, which always names an explicit `harness` that
differs from the role's primary.

Validate any file against this schema with
`ed-orchestrate/scripts/validate_agents_json.py <path>`.
