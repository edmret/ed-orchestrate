# Laya routing — lanes for small changes (optional, needs graph-DAG)

The graph-DAG pattern ([graph-dag.md](graph-dag.md)) is the right shape for a
feature, but it's heavy for "make this header sticky": a planner pass, a task
node, an integration phase and two reviewers for a two-line CSS change. Laya
routing puts a cheap, deterministic router in front of the orchestrator so each
request lands in the lightest lane that is still safe.

Installed by `ed-orchestrate-init` (step 5g, "Laya router") as
`.orchestrate/bin/laya-route` — a stdlib-only Python script, runnable from any
harness's shell. The project owns its copy from then on (re-running init never
overwrites it).

## How it decides

```
laya-route --request-en "<English request>" [--files a,b | --git-diff [BASE]] [--task <id>]
→ {id, lane, tdd, context, answers, facts, reason, laya}
```

1. **Laya** — a local [Laya](http://localhost:8000) server (`laya-serve`,
   `LAYA_URL`, optional `LAYA_TOKEN`) is asked a set of **atomic yes/no
   questions** (visual only? pure logic? state/API? navigation? auth? forms?
   tests?). Measured: single-aspect questions scored 9–10/10 on real requests,
   while one broad "fast or graph?" question scored 6–7/10 with every miss
   unsafe (graph → fast). Never collapse them into one question.
2. **Path facts** — each file from `--files`/`--git-diff` is classified into a
   layer by path regex (navigation, state/API, test, logic, styles, template,
   component, config). **Path facts override Laya**: any navigation / state-API
   / config file, or ≥ 4 files, is `graph` no matter what Laya said.
3. **Deterministic combiner** — no LLM picks the lane. Laya down or timed out?
   Path facts decide alone, and anything uncertain defaults to `graph`. In the
   first measured batch Laya timed out on 5 of 13 requests and path facts
   routed all 5 correctly — so always pass `--files`/`--git-diff` when known.

## Lanes

| Lane | Shape | Tests / review |
| --- | --- | --- |
| `graph` | planner → task DAG → waves → batch-integration node | TDD per node; full suite, e2e, reviewer ∥ code-reviewer once per batch |
| `fast` | ONE coder, ONE task node, no planner | TDD first, scoped unit tests; joins the next batch's integration phase (or a one-task integration) |
| `ui-iterate` | ONE worktree, ONE long-lived coder, an ITER ledger; each tweak is a new turn to the same agent | none per turn (logic still TDD'd); skipped work logged as **debt**, closed by a planner-built debt-closure DAG at the end |
| `ask` | Laya unsure, no files to settle it | ask the user one question, re-route with `--files` |

`tdd: first` is forced for helpers/utils/parsers/pure functions/stores/guards in
every lane; only template/styles/copy/layout may be `defer`.

`context` is the cold-start manifest: `gotchas/00-core.md` plus only the area
gotcha files the lane and touched layers call for (area files are emitted only
once they exist). The planner copies it into the task node's `context:`
frontmatter. Lane and files decide context; Laya scores only decide the lane —
so a `fast`/`ui-iterate` request doesn't inherit graph-wide context from a high
state/API score.

## The UI-iteration lane end to end

1. Orchestrator opens ONE worktree, ONE `coder`, and an ITER ledger from
   `<memory-dir>/tasks/ITER-template.md` (with `routing_id`, `context`).
2. Each user tweak is a new turn to that SAME agent (orca `terminal send` /
   `SendMessage`), not a new dispatch — warm context is the saving.
3. Per turn: UI change, checked in the running app; no tests, no e2e, no
   review. Orchestrator commits `wip(ui-iter): …` (workers never run git); the
   coder appends a Turn block with a **Debt** list (unit, e2e, a11y, i18n, mock,
   cleanup).
4. A turn that needs a new store/route/guard/API/public-API change stops; the
   orchestrator routes that part separately and opens a graph task.
5. **"Close iterations"** — the orchestrator fills the ledger's Close-out and
   dispatches `planner` with the ledger pointer. The planner produces a
   **debt-closure DAG** (tester nodes for specs, coder nodes for structural
   debt) ending in the usual batch-integration node. Every debt item maps to a
   node or an explicit waiver — this is how "do the missing parts at the end"
   is guaranteed rather than remembered.

## Model tiers (N coder models)

The `coder` role can declare **N models** in `agents.json` (`modelTiers`, ordered cheapest
first; the role's own model is the top tier, reserved name `strong` — see
[agents-json-schema.md](agents-json-schema.md)). `laya-route` then answers a second question
besides the lane: *which tier is enough for this task?* — so the scarce strong model is only
spent where needed. It reads the tier names/models from `agents.json`; it never hardcodes them.

**Cheap-first, evidence-driven.** A wrong cheap pick costs wall-clock and a re-dispatch; a wrong
strong pick burns scarce tokens — so start at the cheapest tier and escalate on evidence:

1. **Hard gates (deterministic, path facts)** → `strong`: capability-risky paths (stores, guards,
   generated API clients, build/CI config, auth, money math) or a wide fence (≥ 8 files).
   Path facts beat Laya.
2. **Laya atomic votes** → `strong` only when decisive (> 0.9 with a fence, > 0.65 without).
   A yes can only push *up*.
3. **Laya Choice vote** (one question, one option per tier) → **logged only** until fine-tuned
   (zero-shot it is too noisy; use probabilities, never the reported `confidence`).
4. Otherwise → the **cheapest** tier (first in `modelTiers`). Middle tiers are reached by the
   planner (it sees every tier's `useWhen` and may pick one for the node) or by the cascade.
5. Laya down **and** no files → `tierPolicy.start` (default `strong`, the safe choice).

**Cascade (sticky per task node).** A tier attempt must pass scoped unit tests + typecheck/lint
on touched files. After `tierPolicy.escalateAfter` failed attempts, a stall or a provider error,
or a reviewer reopen for correctness, move to the next tier up — same worktree, pass the failure
notes. `strong` is the end of the ladder. Review stays mandatory at every tier: cheaper models
write plausible-but-wrong code that only the review/probe step catches.

Router output adds `model_tier`, `tier_reason`, `tier_mode`, `models` (tier → `harness:provider/model`)
and `dispatch_model`. The planner copies `model_tier` into the node frontmatter; the orchestrator
dispatches the coder with that tier's binding (`ed-orchestrate/AGENTS.md` step 2c).

### Fine-tuning it — in what order, and when

Tuning "on time" means: **don't tune on a hunch, and don't wait for a perfect dataset.** Move
through phases only when the outcome log says so (`laya-route outcome --tier tier-ok|tier-too-low|tier-too-high --model-used … --attempts N`):

| Phase | `tierPolicy.mode` | Do | Move on when |
|---|---|---|---|
| 1. Shadow | `shadow` | Tier is computed + logged, dispatch stays `strong`. Log an outcome per batch; review the first ~20 decisions by hand. | `laya-route export --stats` says `tier_ready` (≥ 30 labelled) |
| 2. Tune the cheap rules | `shadow` | Edit `TIER_HARD_GATES` / `TIER_QUESTIONS` / `WIDE_FENCE` for *this* repo's paths. Fix every `tier-too-low` by adding a gate (free, deterministic, instant) before touching Laya. | `tier-too-low` stops being caused by path patterns |
| 3. Allow-list | `on` for a small allow-list of obvious-cheap kinds (copy/styling/i18n/docs/mock seeds) | Cascade on. Orchestrator still reads the diff of cheap output. | `tier-too-low` < ~15% over ≥ 20 nodes |
| 4. Default cheap | `on` | Cheap-first with hard gates. Keep a manual override list (state machines, a11y, anything with an oracle). | steady |
| 5. Fine-tune Laya | `on` | `laya-route export --stats` shows `lane_ready` / `tier_ready` (default 30 labelled rows each, `--min-lane/--min-tier`); `laya-route export` writes the joined `lane-*.jsonl` / `tier-*.jsonl` datasets (decision + outcome by `id`; aim for ~100+ labels before training), then let the Choice vote break ties. Also swap the classifier (`ask_laya()`) for a faster model/machine if latency hurts. | — |

Gotchas seen in practice: path gates cannot see complexity inside a *new* folder (everything
looks cheap) — keep a manual override; a plain label edit can score high on `state_or_api`
(hence the 0.9 bar with a fence); every model's own log is optimistic — verify from files.
Re-run phase 2 after any big repo restructure; `curator` can summarise the log for you.

## Outcome log — the router improves

Every decision is appended to `<memory-dir>/laya/decisions.jsonl`. At batch
close the `integrator` records
`laya-route outcome --id <routing_id> --value correct|wrong-lane|wrong-tdd|wrong-context [--note …]`;
the orchestrator does the same when a fast/ui-iterate session had to escalate.
Joined by `id`, decision + outcome pairs are Laya's fine-tuning dataset, and
`curator` reviews them for misses.

## Tuning for a project

Edit the `PROJECT TUNING` block at the top of the installed script:

- `LAYER_RULES` — path regexes for this repo's layout (first match wins; keep
  risky layers first). Add a layer for anything that must always be `graph`
  (e.g. a library's public API, schematics, generated clients) and list it in
  `GRAPH_LAYERS`.
- `QUESTIONS` / `DECIDING` — add a domain question only if it's single-aspect,
  and only put it in `DECIDING` once the outcome log shows it's reliable.
- `TOPIC_CONTEXT` / `LAYER_CONTEXT` — map answers and layers to this repo's
  gotcha area file names.
