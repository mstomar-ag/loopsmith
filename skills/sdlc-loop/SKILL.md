---
name: sdlc-loop
description: Run the autonomous park-and-continue SDLC loop over the .sdlc/goals backlog. Use when the user runs /sdlc-loop or asks to run goals autonomously / overnight / unattended.
allowed-tools: Bash(python3 *), Bash(gh issue view *)
---

# sdlc-loop

Drive the backlog autonomously. The Python helpers own state/budget + the backlog source; you run
each goal. The source is config-selected (`.sdlc/config.json` → `discovery.source`): **local goal
files** (default) or **GitHub issues** (`source: github`, needs an authenticated `gh`). You run the
loop the same way either way — the helper handles where goals come from and how status is recorded.

First, reset the per-run budget: `python3 "${CLAUDE_SKILL_DIR}/scripts/loop.py" start .sdlc`

Then repeat until the helper says stop:

1. `goal=$(python3 "${CLAUDE_SKILL_DIR}/scripts/loop.py" next .sdlc)`
2. If output is `DONE` (backlog empty) or `BUDGET` (a per-run budget hit: iterations always;
   wall-clock minutes / reported tokens when `config.json` sets them) → STOP. If the host surfaces
   token usage to you, report it between goals — `loop.py spend .sdlc <tokens>` — so
   `budget.max_tokens` can actually enforce; never guess a number (no report = no token cap).
3. Otherwise: first **recall prior art** — if the knowledge graph is enabled, run the `sdlc-context`
   pre-flight to pull a cited brief from the graph + past issues + conventions, so the goal starts
   informed by history instead of a flushed window (no-op when the KG is off).
   **Match the model to the goal** — run `python3 "${CLAUDE_SKILL_DIR}/../sdlc-model/scripts/predict.py"
   resolve "$goal" .sdlc`. If it prints a tier (`haiku`/`sonnet`/`opus`/`fable`), run this goal's phases
   inside a **subagent with that `model`** (the Task tool's model override — the session can't switch its
   own model); if it prints `off` (the default, or you're off-Claude), run the phases inline as usual.
   One tier for the whole goal. Then read the goal and
   run it through the full SDLC (research → plan → plan-review →
   implement → review) — each phase via its **executor** (the `superpowers`/`code-review` companion on
   Claude if installed, else LoopSmith's portable `sdlc-brainstorm`/`sdlc-plan`/`sdlc-implement`/
   `sdlc-review`/`sdlc-verify`; each skill's resolution header picks). `$goal` is a **file path** in local mode (read the file) or a **GitHub issue
   number** in github mode (`gh issue view "$goal"` to read it). **Park instead of forcing through**
   if you hit any of:
   - a hard checkpoint / a decision only the user can make,
   - an **irreversible or expensive action** (deploy, delete, overwrite, spend, migrate) — NEVER
     run one unattended,
   - a failure you cannot resolve.

   As you complete each phase, **record it** so the issue timeline is the audit trail:
   `python3 "${CLAUDE_SKILL_DIR}/scripts/loop.py" note .sdlc "$goal" "<phase>: <key findings / decisions>"`.
   For a decision/finding/fix worth keeping, record a 🔒 Critical Insight (the
   `.github/CRITICAL_INSIGHT_TEMPLATE.md` format) the same way. This comments the issue in github mode
   and appends to `.sdlc/journey/<goal>.md` in local mode; it's fail-open (never breaks the run).
4. Entering the **review** phase? Move the board card to QC:
   `python3 "${CLAUDE_SKILL_DIR}/scripts/loop.py" qc .sdlc "$goal"` (github-project board only — a no-op for local/issues).
5. **Retrospective (Learn)** — after Review, run the **`sdlc-retro`** executor (advisory): reflect on
   the structural + product debt the fix left behind and grade intent-vs-shipped. Autonomous mode →
   **write only the audit-trail notes**, and **park** any north-star / standing-rule proposal to the
   review queue for a human; never edit a standing doc unattended. Fail-open — it never breaks the run.
6. Record the outcome:
   `python3 "${CLAUDE_SKILL_DIR}/scripts/loop.py" record .sdlc "$goal" done` (or `parked "reason"`).
7. Loop.

**Self-improving (optional, gated):** when the backlog is empty (`next` → `DONE`) but the knowledge
graph is enabled and `kg.py gap list .sdlc` shows open gaps **and** budget remains, you may close the
loop instead of stopping: take the oldest gap, research it, write the finding to
`.sdlc/knowledge/analysis/`, refresh the graph (`/sdlc-kg`), then mark it filled —
`python3 "${CLAUDE_SKILL_DIR}/../sdlc-kg/scripts/kg.py" gap resolve "<the gap>" .sdlc`. **One gap per
spare iteration, only within budget, and park (never force)** anything that needs a human. This is how
the graph fills what it didn't know — turn it off by leaving the KG disabled.

At STOP, report: N done, M parked. If anything parked, point the user to the parked items —
`.sdlc/state/review-queue.md` in local mode, or the issues labelled `sdlc:parked` (the **Blocked**
column on the board) in github mode.
Parking is always correct over forcing an irreversible action to "finish" a goal.
