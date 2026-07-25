# Changelog

## Unreleased

### Coordination
- **Team ledger** (`ledger: {"enabled": true}`, default OFF): a committed, append-only record of what
  the loop did — `claimed` when it takes a goal, `done`/`parked`/`failed` when it finishes one — with
  a timestamp and an actor on every line. **One file per person** (`.sdlc/ledger/entries/<actor>.jsonl`):
  you only ever write your own, so concurrent appends can neither race on disk nor conflict in git;
  the team view is their union, computed on read. Kinds `claimed · done · parked · failed · handoff ·
  ack · release · note`; an entry with a `to` is addressed to that person. `ledger.py` renders
  `TEAM.md`, lists what is addressed to you, and summarises outstanding hand-offs; `/sdlc-status`
  reports the entry count and `/sdlc-doctor` reports the flag. Every write from the loop is fail-open
  — a ledger problem can never stop a run. Absent config = byte-compatible with 0.6.0.

- **Cross-area hand-off** — parking with a successor instead of parking into silence. A blocker in
  code someone else owns is not a decision for the user, but until now it parked like one: a
  gitignored queue entry, an unaddressed issue comment, and no code path in the kit had ever set an
  assignee. `handoff.py open` resolves the owner from the repo's own `.github/CODEOWNERS` (override
  per area with `ledger.owners`), opens an issue in their area **assigned to them and carrying the
  goal label** — so their own loop picks it up through the `assignee` filter, no new transport —
  records a `handoff` ledger entry addressed to them, and links it from the blocked issue. Then the
  goal parks as before. `handoff.py ack --state accepted|deferred|declined|resolved` is the answer;
  `deferred` deliberately does not settle it. Degrades honestly with no owner, no `gh`, or a local
  backlog: the ledger entry is still written.

- **Ledger transport + watcher** — a mention nobody reads is worth nothing, so the ledger now shares
  itself and tells you when it needs you. `sync.py init` makes `.sdlc/ledger/` a **git worktree** on a
  dedicated ops branch (default `sdlc-ledger`, created from the EMPTY tree so it carries no code):
  fetching and rebasing the ledger touches only that worktree, so a pull can never disturb your code
  checkout or drag you into a mid-task rebase, and the branch is never merged into the integration
  branch so it needs no review. `publish` fast-forwards your own entries file with a bounded
  fetch-rebase-retry — a race replays, never forces, and can't conflict because nobody shares a file.
  `watch.sh` ticks on `ledger.watch.interval_seconds` (default 900): pull → classify → write
  `.sdlc/state/inbox.md` → publish. **`loop.py next` surfaces that inbox on stderr before handing over
  the next goal** — the only honest delivery point, since nothing can inject a message into a running
  session and interrupting a goal mid-flight loses work; worst case is one goal of latency, and stdout
  stays exactly the goal the caller parses. Deduped twice: a per-author cursor, plus a
  `kind:issue:state` signature so a colleague's rebase can't replay old mentions (a state *change*
  still fires).

### Backlog
- **Per-owner discovery scope**: `discovery.github.assignee` (e.g. `"@me"`) makes the loop pick only
  issues assigned to that user, so several people can run the loop against one shared board/Project
  without grabbing each other's work. Absent/empty = no filter (every open goal issue is in scope) —
  byte-compatible with prior behavior. Applies to discovery only; the board backlog sync still seeds
  the whole team's issues.

## 0.6.0 — the trust-and-feedback release

The theme: everything the loop CLAIMS is now checkable, everything it produces feeds
back into it, and an unattended night no longer ends at the first limit or crash.
Every new capability ships opt-in and default-OFF (one bug-fix exception, noted);
absent config keys behave exactly as 0.5.0.

### Guardrails made real
- **Prompt gate is repo-scoped** *(the one default-ON change — bug-fix class)*: the
  UserPromptSubmit directive now speaks only in repos that adopted the spine
  (`.sdlc/` exists); everywhere else it is a silent no-op, so a machine-wide install
  never injects policy into unrelated projects. `LOOPSMITH_GATE_GLOBAL=1` restores
  the old always-on behavior.
- **Budgets enforce**: `budget.max_minutes` (wall-clock) and `budget.max_tokens`
  (host-reported via the new `loop.py spend` verb) now actually halt the run;
  previously only `max_iterations` did. Absent keys enforce nothing.
- **Opt-in hard plan-gate**: `gates.hard_plan_gate.enabled` mechanically DENIES a
  source edit unless a fresh plan exists under `.sdlc/plans/`
  (`touch .sdlc/.allow-direct-edits` for a deliberate bypass; fail-open throughout).

### Truthful outcomes
- **`failed` is not `parked`**: a goal the loop could not resolve gets its own
  terminal status, review-queue tag ("needs: a fix" vs "needs: human review"),
  counters, and `record failed` verb — the morning queue separates decide-this
  from fix-this.
- **Machine-checked done**: `loop.py verify` runs the goal's proving command
  (frontmatter `verify_command`, else `verify.command`) and records evidence; with
  `verify.enforce` on, `record done` is REFUSED without a fresh passing verify from
  this run.

### The feedback circle
- **Bidirectional pipeline report card**: declare stages once in `.sdlc/pipeline.json`
  and `pipeline.py card` renders every stage in BOTH directions — forward
  (survivorship: nothing dropped) and reverse (provenance: nothing invented) — with
  uninstrumented lanes reading honest-ABSENT, a typed verdict, and `--compare` for
  the regressed / improved / still-failing (recurrence) delta between runs.
- **Findings become work**: `pipeline.py propose` turns failing card signals into
  `proposed` goal files with the failing check pre-wired as their `verify_command`;
  the loop never runs one until a human promotes it to `pending`.

### Smarter, cheaper, visible
- **Per-step model + effort selection** (under the existing `model_selection: "auto"`
  gate): `resolve-step` returns `model=<tier> effort=<low|medium|high>` so mechanical
  steps inside a hard goal (tests, watchers, lint) run below the goal's ceiling;
  `resolve` output stays backward-compatible.
- **Feature dashboard**: `doctor.py features` (also appended to `/sdlc-doctor`
  output) reports every optional capability's LIVE state with its one-line enable.

### Unattended for real
- **Overnight supervisor**: `scripts/supervise.sh` owns the loop's lifetime with
  zero polling — blocked while a session runs; on exit it classifies the output
  (via the pure `supervise_classify.py`): loop finished → stop · budget → relaunch ·
  usage-limit → **sleep until the stated reset time (+ jitter), then relaunch** ·
  unknown → capped backoff. Kill-file stop; per-run output capture; laptop-sleep
  caveat documented.

57 new tests across the arc (281 total, coverage >85% held, Tier-1 eval baseline
unchanged). No runtime dependencies added.
