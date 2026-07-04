# TODO / parked

Deliberately deferred work, with enough context to pick it up cold.

## Tier-2 LLM-judge behavioral evals — parked (needs an API budget)

The quality pipeline's second tier (`evals/`): run the agent on each fixture goal, then have an LLM
judge score the transcript against that fixture's `tier2_rubric` (did it plan before editing? did
plan-review catch the planted flaw? did review find the planted bug? did it park on the irreversible
action?); track scores over time and fail on a drop below baseline.

- **Status:** the runner + its injectable `agent`/`judge` seam are already built and tested
  (`run_tier2`, `test_tier2_seam_hermetic`). `python3 evals/run.py --live` prints a parked notice and
  spends nothing.
- **Why parked:** it costs API tokens per run and needs a judge-model + rubric decision — a spend
  call, not one to make unattended.
- **To wire when greenlit:** implement the real `agent(prompt)` (run the agent headless on the fixture
  goal) and `judge(output, rubric)` (an LLM scoring 0..1 per rubric line) in `evals/run.py`, gate both
  behind `--live` + an API key, and run it nightly / pre-release — not per-PR (cost + non-determinism).
  See [`evals/README.md`](evals/README.md) for the two-tier design.

## Other deferred (see the roadmap for context)

- **research-radar Phase B/C** — findings → gap log → the loop fills them; opt-in guard-railed GitHub
  filing. Deferred until the dry-run digest (`/sdlc-radar`) proves useful.
- **Second-host adapters beyond Cursor** — the portable executors + `sdlc-init --cursor` prove the
  pattern; a Codex/other adapter can follow the same shape (a host rules file + `companions: off`).
