# ed-orchestrate — delegate flow

Shared core, harness-agnostic. Read the overlay for your host
([CLAUDE.md](CLAUDE.md) / [OPENCODE.md](OPENCODE.md) / [AGY.md](AGY.md)) for the one
or two host-specific differences (mainly step 7's confirmation mechanism).

This skill delegates one task to one role per invocation — it doesn't itself
hold a multi-step plan. If you (the orchestrator — see
[references/no-self-code.md](references/no-self-code.md) for what that means)
are walking a larger task graph across several delegations, see
[references/graph-dag.md](references/graph-dag.md) for the recommended
graph-engineered pattern (a `planner`-produced task DAG, scoped task-node
pointers instead of full context per delegation, and an `integrator` merge
gate) instead of a flat repeated-delegation loop.

## 0. Route first (only if the project has a router)

If `.orchestrate/bin/laya-route` exists, the orchestrator routes each new
request with it before choosing a role — `fast` and `ui-iterate` lanes skip the
planner entirely for small changes. See
[references/laya-routing.md](references/laya-routing.md). No router → skip this.

## 1. Preconditions

Read `.orchestrate/agents.json` in the current project (repo-root-relative).

If it doesn't exist, check the pre-rename path, `.claude/ed-orchestrate/agents.json`:

- **Old path also missing** — stop and tell the user to run `ed-orchestrate-init` first;
  never invent a roster or guess at harness/model values.
- **Old path exists** — tell the user this project's config is at the old location, that
  `ed-orchestrate` now expects `.orchestrate/agents.json` (a flat, host-neutral path,
  since opencode and Antigravity/agy read this same config, not just Claude Code), and
  ask (host overlay's structured-question mechanism) whether to move it. On yes, move the
  file — creating `.orchestrate/` if needed — and continue against the new path; the JSON
  embeds no path of its own, so its contents need no edits. On no, stop and tell them to
  move it manually or re-run `ed-orchestrate-init`, which always writes the new path.

Validate the resolved file:

```
python3 <this-skill-dir>/scripts/validate_agents_json.py .orchestrate/agents.json
```

If validation fails, show the errors and stop rather than guessing a fix.

## 2. Resolve the role

In priority order:
1. The user named a role explicitly (case/slug-normalize, e.g. "the Tester" → `tester`).
2. Exactly one role exists in `agents.json` → use it.
3. Infer from task phrasing against each role's `description` field. If the phrasing
   plausibly matches more than one role equally well — most likely `reviewer` vs
   `code-reviewer`, since both are diff-review gates by design — don't guess between
   them; treat it as still ambiguous and fall through to step 4.
4. Still ambiguous → ask one question (see host overlay for the mechanism) rather than
   guessing.

## 2a. Resolve harness override

Scan the task phrasing for an explicit harness token — case-insensitive match against
`{claude, codex, opencode, agy, cursor, gemini, droid}`, typically after
"on"/"using"/"via"/"with" ("run this on opencode", "using codex"). Same phrase-based
disambiguation style step 3 uses for delegation mode; don't invent a new mechanism.

- **No token, or the token matches the role's primary `harness`** — nothing to resolve.
  Proceed with the role's primary harness/model/provider/effort.
- **Token differs from the primary harness** — look for an entry in `role.fallbacks`
  whose `harness` matches:
  - **Found** — that entry's `harness`/`model`/`provider`/`effort` replace the primary
    fields for every step below, and its own `cliFlags` (none if absent) replace the
    role's — the role's flags belong to its primary harness. `worktreeStrategy`,
    `delegationMode`, `tools`, and `systemPromptSeed` are role-level and stay as they
    are.
  - **Not found** — don't guess. Ask one question (host overlay's mechanism): use the
    role's primary harness instead / add a fallback for the named harness now (hand into
    `ed-orchestrate-init`'s step 3b, pre-scoped to this role and harness, then resolve
    with the new entry and resume here) / cancel.

## 2b. Same-harness provider fallback

If the invocation constructed in step 6/7 fails for a reason attributable to the
provider (auth/rate-limit/unavailable error from the harness or provider, not a
task-content error), and `role.fallbacks` has an entry with no `harness` key
(i.e. bound to the same harness as the primary), retry once using that entry's
`model`/`provider` (and `effort` if it overrides the primary). If more than one
such entry exists, try them in array order. Report which binding actually ran if
a fallback was used — never silently swap providers without saying so. If none
succeed, stop and surface the failure; don't fall through to a cross-harness
fallback here — that's only ever chosen explicitly via step 2a.

## 3. Resolve delegation mode

Same verb-based disambiguation the `orca-cli`/`orchestration` skills already use:

- "hand off" / "handoff" / "give this to" / "another worktree" / neutral phrasing →
  `handoff`.
- "supervise" / "wait for" / "monitor" / "coordinate" → `supervised`.

If the user's phrasing is neutral and gives no signal either way, fall back to the
role's `delegationMode` default in `agents.json`.

## 4. Resolve the orca executable

Use the exact resolution rule documented in the `orca-cli` skill's own "resolve the
CLI for this session" section (`ORCA_CLI_COMMAND` env var → `orca-dev` if
`ORCA_DEV_REPO_ROOT` is set → `orca-ide` on Linux outside an Orca terminal → `orca`).
Don't copy that logic here — read it live so it can't drift.

## 5. Load the live guide

Always: `orca skills get orca-cli`.
Additionally, when mode is `supervised`: `orca skills get orchestration`.

## 6. Branch on harness capability

Branch on the harness **resolved in step 2a** — the role's primary harness unless a
fallback matched — not on `role.harness` directly. See
[references/harness-model-support.md](references/harness-model-support.md) for the full
table. Summary:

- **claude, codex, cursor** — `--model` / `--effort` thread straight through the
  live-fetched `worker-start` (supervised) or `terminal create --command` (handoff)
  syntax.
- **opencode, agy, gemini, droid** — do **not** rely on a `--model` flag on
  `orca worktree create` / `orca orchestration worker-start`; it is documented as
  claude/codex/cursor-only. Use the matching `references/harness-<name>.md` path
  instead (a pre-generated per-harness agent file, or a raw-argv harness invocation
  passed to `orca terminal create --command`).

See [references/orca-delegation-patterns.md](references/orca-delegation-patterns.md)
for the decision table mapping `(delegationMode, worktreeStrategy, harness)` to which
orca subsystem to use.

## 7. Construct → show → confirm → run

Append the resolved binding's `cliFlags` verbatim to the constructed command —
`role.cliFlags` for the primary or a same-harness fallback (unless that entry sets
its own), the fallback entry's own `cliFlags` for a cross-harness one. They're
opaque extra flags for that binding (e.g. headless agy's
`--dangerously-skip-permissions`); never invent or drop them.

Keep the task prompt a short pointer — "Execute [[TASK-NNN]]. Governed by
[[ADR-NNN]]." or "Execute the brief in `<path>`." — and put anything longer in a
file first. Inline prompts passed through `terminal create --command` break on
shell metacharacters (a `!` triggers zsh history expansion and the command never
runs). For `coder`/`tester`, the prompt also states: scoped unit tests only, no
e2e, no git, and do not end the turn after reading context — sub-agents otherwise
default to the full suite. When dispatching several opencode workers at once,
stagger their starts by ≥ 30 s (`references/harness-opencode.md`).

Always render the fully resolved command(s) in a fenced code block in your reply
*before* invoking Bash. See your host overlay for exactly what "confirm" means on
that host — it's the dry-run safety net, and there is no separate CLI flag for it.

## 8. Follow-through

- **handoff** — report the worktree/terminal handle back to the user and stop. Don't
  keep polling; that's what `orca-cli`'s own "give this to another agent" pattern
  means.
- Judge a worker by ground truth — the files it should have changed and its task
  node's log — never by exit code or terminal-tail length (`orca terminal read`
  returns ~120 lines unless you pass `--limit`). Never kill a worker's in-flight
  tool process; message it or relaunch with a resume brief.
- **supervised** — run the `orca orchestration check --wait --types
  worker_done,escalation,question --timeout-ms <n>` loop per the live guide fetched in
  step 5, surface `worker_done`/`escalation` results to the user, and use
  `worker-release` / `worker-retain` / `worker-stop` / `worker-abandon` exactly as
  that live guide directs — never an invented flag.
