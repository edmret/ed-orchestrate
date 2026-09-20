# ed-orchestrate-init — interview flow

Shared core, harness-agnostic. See your host overlay
([CLAUDE.md](CLAUDE.md) / [OPENCODE.md](OPENCODE.md) / [AGY.md](AGY.md)) for how
"ask a structured question" is implemented on that host — everything below is
written in host-neutral terms ("ask" = whatever that overlay says to do).

The exact question objects for steps 2–3b are spelled out verbatim in
[references/interview-flow.md](references/interview-flow.md) — follow that script
rather than re-deriving the questions each run. Default descriptions and system
prompt seeds for the built-in roles live in
`ed-orchestrate/references/role-defaults.md` — quote them, never re-invent them.

## 1. Detect existing config

Check for `.orchestrate/agents.json` in the current project. If it
exists, ask: **Start fresh** / **Edit existing** (load current roles as the
starting point for steps 2–3) / **Add or edit a fallback harness** (skip steps 2
and 3, go straight to step 3b) / **Cancel**.

If it doesn't exist, check the pre-rename path,
`.claude/ed-orchestrate/agents.json`, before treating the project as fresh — a
project with only the old file has a real roster and must not silently lose it.
If the old path exists, tell the user about the rename (the config is
host-neutral, read by opencode and Antigravity/agy too, so it no longer lives
under `.claude/`) and ask whether to move it to `.orchestrate/agents.json`. On
yes, move the file (creating `.orchestrate/` if needed; contents need no edits)
and continue as "existing config detected". On no, stop.

If this skill was invoked with an argument matching an existing role name
(case/slug-normalized), skip the branch above and step 2's role picker entirely —
go straight to that role's edit menu: **Edit primary config** (step 3 for that
role) / **Add or edit a fallback harness** (step 3b, already role-scoped) /
**Cancel**. An argument that matches no existing role falls through to the normal
detection, and is treated as a pre-filled custom-role name if the user reaches
the step 2 picker.

## 2. Pick roles

One multi-select question: `coder` (implementation), `planner` (task breakdown —
plans only, never implements), `tester` (test writing/verification), `reviewer`
(correctness/security review), `architect` (research and structural design),
`code-reviewer` (code-quality review), `designer` (UI/UX spec), `qa-designer`
(visual/UX fidelity check), `curator` (prunes/curates shared task and knowledge
notes), `integrator` (merges parallel task branches, resolves conflicts, runs
the full suite once per batch) — plus an "Other" free-text option for one
additional custom role name.

v1 limit: more than one extra custom role in a single pass isn't supported —
either run `ed-orchestrate-init` again afterward to add another, or hand-edit
`agents.json` (then validate it with `ed-orchestrate`'s validator before trusting
it).

## 3. Per role, gather fields

For each selected role:

- **Structured call A** (harness, effort, delegation mode, worktree strategy) —
  exact question text in `references/interview-flow.md`.
- **Structured call B** (model) — if the chosen harness is `opencode`, first try
  to read `~/.config/opencode/opencode.json` and offer up to 3 real
  `provider/model` pairs found in its `provider.*.models` blocks as options (plus
  Other); if the file can't be read, fall back to free text. Split the chosen
  `provider/model` string on the first `/` to populate `model` and `provider`
  separately — **never ask provider as its own question, it's derived from the
  opencode choice.** For every other harness, present 2–3 illustrative example
  model ids (from that harness's `references/harness-<name>.md` in the
  `ed-orchestrate` skill — note in the prompt that these are illustrative and may
  drift) plus Other for the exact id; `provider` stays `null`.
- **Prose exchange** (plain text, not a structured question) — description and
  system prompt seed. For a **built-in** role (`coder`, `planner`, `tester`,
  `reviewer`, `architect`, `code-reviewer`, `designer`, `qa-designer`,
  `curator`, `integrator`), show that role's default `description` and
  `systemPromptSeed` from `ed-orchestrate/references/role-defaults.md` and let
  the user accept both or type a replacement description; on accept, materialize
  both defaults verbatim into `agents.json`, and on override use the typed
  description with the default seed. For a **custom** role, ask for a one-line
  description as free text (used in the AGENTS.md roster table, and for
  opencode roles as the generated agent file's `description:`), take the reply
  verbatim, and set `systemPromptSeed: null` — there is no default for custom
  roles.

## 3b. Add or edit a fallback

Entry points: step 1's "Add or edit a fallback harness" option, step 1's
role-name-argument menu, or step 4's "Edit a specific role" sub-choice. Exact
question objects in `references/interview-flow.md`. Two fallback kinds share
this flow — a same-harness provider/model retry binding (`harness` field
absent in the stored entry) and a cross-harness override (`harness` field
present, used only when the user names a different harness at delegation time,
`ed-orchestrate/AGENTS.md` step 2a).

a. Ask which role — skip if already role-scoped by the entry point, or if the
   roster has exactly one role.
b. Ask which kind: **same-harness fallback** (stays on `<role>`'s primary
   harness, swaps provider/model — e.g. a resilience binding for when the
   primary provider is unavailable) or **cross-harness fallback** (runs on a
   different harness entirely, chosen at delegation time).
c. **Same-harness**: skip straight to (e) — the harness is implicitly the
   role's primary; no harness question. **Cross-harness**: compute the
   harnesses still available for this role — every harness in the schema enum
   minus the role's primary harness minus its existing cross-harness fallback
   harnesses. If that set is empty, say so and offer to replace or remove an
   existing fallback instead of adding one. Ask which harness the fallback
   should use, options built from that set.
d. (Cross-harness only) note the chosen harness for (e)/(f).
e. **Reuse step 3's structured call B verbatim** for the model, targeting the
   effective harness (role's primary for same-harness, or the harness chosen in
   (c)/(d) for cross-harness) — including the opencode `provider/model` split.
   Write the result into the fallback entry, not the role's top-level fields.
   Omit the `harness` key entirely for a same-harness entry; set it for a
   cross-harness entry.
f. **Reuse step 3's call A effort question verbatim**, scoped to this fallback,
   with an added "inherit from primary" option (omit the field, don't write a
   value) alongside low/medium/high. Don't re-ask harness (already resolved),
   delegation mode, or worktree strategy — those are role-level and this flow
   never changes them.
g. Show the resolved entry alongside the role's current fallbacks. Ask: add it /
   edit again (loop to (b)) / cancel. When an entry with the same effective
   `(harness, provider)` pair already exists, the question is "replace the
   existing fallback for `<provider or harness>`?" instead.
h. On confirm, append the entry to `role.fallbacks` (creating the array if
   absent) or replace the matching entry. Validate the whole file before
   writing, exactly as step 5b does, then write `.orchestrate/agents.json` and
   re-splice the roster block per step 5c/5d. Do **not** regenerate
   `.opencode/agent/<role>.md` — it derives from primary fields only, which
   this flow never touches.
i. Print the role's updated fallback list.

## 4. Confirm

Render the full drafted roster as a markdown table in the chat. One final
structured question: **Yes, write it** / **Edit a specific role** / **Cancel**.
"Edit a specific role" asks which role, then offers **Edit primary config** (loop
back to step 3 for that role) or **Add or edit a fallback harness** (step 3b,
already role-scoped).

## 5. Generate

a. Assemble the in-memory `agents.json` object per
   `ed-orchestrate/references/agents-json-schema.md`.
b. Validate before writing anything:
   ```
   python3 ~/.claude/skills/ed-orchestrate/scripts/validate_agents_json.py <path-to-drafted-file-or-tmp>
   ```
   If it fails, fix the draft and re-validate — never write an invalid file.
c. Write `.orchestrate/agents.json` (create `.orchestrate/`
   if missing), 2-space indent, stable key order.
d. Splice the roster block into the target project's `AGENTS.md`:
   ```
   python3 scripts/render_agents_md_block.py .orchestrate/agents.json --splice AGENTS.md
   ```
   (Creates `AGENTS.md` if it doesn't exist.) See
   `ed-orchestrate/references/agents-md-block-format.md` for the exact format and
   the idempotent splice guarantee.
e. For every role with `harness == "opencode"`: check whether
   `.opencode/agent/<role>.md` already exists. If so, ask before overwriting —
   don't clobber a hand-maintained file (this project convention already exists
   in some of this user's other projects). Then:
   ```
   python3 scripts/render_opencode_agent_file.py .orchestrate/agents.json <role> --out .opencode/agent/<role>.md
   ```
f. Only on a **Start fresh** run creating `.orchestrate/agents.json` for the
   first time (never on an edit-existing/fallback-only pass) — ask (host
   overlay's structured-question mechanism) whether to also enforce the
   orchestrator's no-self-code boundary at the permission layer, per
   `ed-orchestrate/references/no-self-code.md`: **Yes** / **No** /
   **Explain first**. On yes, ask which path glob(s) to deny Edit/Write on
   (free text, default suggestion: the project's obvious source directory,
   e.g. `src/**`), then merge a `permissions.deny` entry for
   `Edit(<glob>)`/`Write(<glob>)` into the target project's
   `.claude/settings.json` (create the file if missing; if it already has a
   `permissions.deny` array, append rather than replace). On "Explain first",
   show the reference doc's summary, then re-ask. Skip this question entirely
   (don't ask) if `.claude/settings.json` already has any `permissions.deny`
   entry — treat that as the project having already made this choice.
g. Skip this step if the target `AGENTS.md` already contains
   `<!-- BEGIN:ed-orchestrate-graph-dag -->` — already wired, nothing to ask.
   Otherwise ask (host overlay's structured-question mechanism) whether to set
   up graph-engineered task delegation, per
   `ed-orchestrate/references/graph-dag.md`: **Yes** / **No** /
   **Explain first**. On "Explain first", show the reference doc's summary,
   then re-ask. On yes, ask for the shared task-memory directory (free text,
   default suggestion `.ai-memory`), then run:
   ```
   python3 scripts/setup_graph_dag.py <dir> --agents-md AGENTS.md --gitignore .gitignore --orca-yaml orca.yaml
   ```
   This creates `<dir>/tasks/TASK-template.md` if missing, splices a
   `<!-- BEGIN:ed-orchestrate-graph-dag -->` usage block into `AGENTS.md`
   (idempotent, same splice guarantee as the roster block — never touches
   content outside its own markers), gitignores `<dir>/` (it's local-machine
   scratch, never committed), and registers `<dir>` under `orca.yaml`'s
   `worktree.sharedDirectories` so every Orca worktree sees the same graph
   (creates a minimal `orca.yaml` if none exists; appends to an existing
   `sharedDirectories` list in place, or warns to add it by hand if the file's
   shape can't be matched safely — never guesses at unrelated YAML). If the
   project doesn't use Orca worktrees at all, still offer this — the shared
   directory and AGENTS.md block are useful on their own; only the
   `orca.yaml` step is Orca-specific (skip it with `--no-orca-yaml` if the
   user says this project isn't Orca-managed).
h. Print a final summary — files written, the roster table, and whether
   graph-DAG mode and the no-self-code deny rule were set up — and remind the
   user they can re-run `ed-orchestrate-init` anytime to add/edit/remove
   roles or reconfigure either.

**v1 scope note (fallbacks)**: `render_opencode_agent_file.py` reads a role's
primary fields only and refuses any role whose primary harness isn't `opencode`.
A role with an `opencode` *fallback* but a different primary harness therefore
generates no `.opencode/agent/<role>.md` — that binding is used at delegation
time via the raw-argv path in `ed-orchestrate/references/harness-opencode.md`.

**v1 scope note**: native per-harness config file generation is **opencode-only**
— it's the only harness with a documented per-project agent-definition schema
relevant to orca-mediated delegation (Claude Code's own `.claude/agents/*.md`
format exists too, see `ed-orchestrate/references/harness-claude.md`, but this
skill doesn't generate those files in v1). Every other harness relies solely on
`agents.json` + the AGENTS.md roster block; `ed-orchestrate` bakes model/effort
into the raw CLI invocation at delegation time instead (see
`ed-orchestrate/references/harness-model-support.md`).
