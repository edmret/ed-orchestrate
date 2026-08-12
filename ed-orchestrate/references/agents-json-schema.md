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
        { "harness": "claude", "model": "sonnet",  "provider": null, "effort": "medium" },
        { "harness": "codex",  "model": "gpt-5.5", "provider": null, "effort": "high" }
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
| `.fallbacks` | array of objects, or absent | no | optional alternate harness bindings, used only when the user names a different harness at delegation time (`ed-orchestrate/AGENTS.md` step 2a). Absent and `[]` are equivalent. Never asked during `ed-orchestrate-init`'s fresh-role flow — only via its step 3b |
| `.fallbacks[].harness` | same enum as `.harness` | yes, per entry | must differ from the role's primary `.harness`, and must be unique across the array (resolution looks entries up by harness) |
| `.fallbacks[].model` | string | yes, per entry | same semantics as `.model` |
| `.fallbacks[].provider` | string or `null` | yes, per entry | same semantics as `.provider` — meaningful only when that entry's `harness == "opencode"` |
| `.fallbacks[].effort` | same enum as `.effort`, or `null` | yes, per entry | same semantics as `.effort` |
| `.linearProject` | string, or absent | no | optional, meaningful only for the `manager` role; the Linear project/team key `manager` tracks issues under, asked once during `ed-orchestrate-init`'s manager-only prompt at step 3. Absent means `manager` still splits tasks but creates no Linear issues — see [role-defaults.md](role-defaults.md)'s `manager` section for how it's substituted into the materialized `systemPromptSeed` |
| `defaults.role` | string | no | must reference an existing key under `roles` |
| `defaults.worktreeStrategy` / `defaults.delegationMode` | same enums as above | no | fallback for a hand-edited role object missing that field (shouldn't happen via `ed-orchestrate-init`, since it always fills every field) |

A fallback entry carries **only** `harness`/`model`/`provider`/`effort`.
`worktreeStrategy`, `delegationMode`, `tools`, and `systemPromptSeed` stay role-level
and apply whichever binding resolves — primary or fallback.

## Optional field example: `manager`'s `linearProject`

```json
"manager": {
  "description": "Turns an existing task list into tracked work items — Linear issues when a project is configured, otherwise a plain checklist.",
  "harness": "claude",
  "model": "sonnet",
  "provider": null,
  "effort": "medium",
  "tools": null,
  "systemPromptSeed": "You are the manager sub-agent. ... Track these tasks as issues in the \"ENG\" Linear project via the orca-linear skill. ...",
  "worktreeStrategy": "current",
  "delegationMode": "supervised",
  "linearProject": "ENG"
}
```

Validate any file against this schema with
`ed-orchestrate/scripts/validate_agents_json.py <path>`.
