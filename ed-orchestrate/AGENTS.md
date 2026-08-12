# ed-orchestrate — delegate flow

Shared core, harness-agnostic. Read the overlay for your host
([CLAUDE.md](CLAUDE.md) / [OPENCODE.md](OPENCODE.md) / [AGY.md](AGY.md)) for the one
or two host-specific differences (mainly step 7's confirmation mechanism).

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
3. Infer from task phrasing against each role's `description` field.
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
    fields for every step below. `worktreeStrategy`, `delegationMode`, `tools`, and
    `systemPromptSeed` are role-level and stay as they are.
  - **Not found** — don't guess. Ask one question (host overlay's mechanism): use the
    role's primary harness instead / add a fallback for the named harness now (hand into
    `ed-orchestrate-init`'s step 3b, pre-scoped to this role and harness, then resolve
    with the new entry and resume here) / cancel.

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

Always render the fully resolved command(s) in a fenced code block in your reply
*before* invoking Bash. See your host overlay for exactly what "confirm" means on
that host — it's the dry-run safety net, and there is no separate CLI flag for it.

## 8. Follow-through

- **handoff** — report the worktree/terminal handle back to the user and stop. Don't
  keep polling; that's what `orca-cli`'s own "give this to another agent" pattern
  means.
- **supervised** — run the `orca orchestration check --wait --types
  worker_done,escalation,question --timeout-ms <n>` loop per the live guide fetched in
  step 5, surface `worker_done`/`escalation` results to the user, and use
  `worker-release` / `worker-retain` / `worker-stop` / `worker-abandon` exactly as
  that live guide directs — never an invented flag.
