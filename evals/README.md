# Quality evals — catch drift on every change

LoopSmith's "output" is agent *behavior* (does it follow the spine, plan before editing, verify before
claiming done). Behavior is non-deterministic, so quality is guarded in two tiers. Run the whole thing
on every change; a drop below the committed baseline fails the build.

## Tier 1 — deterministic behavioral gate (free, runs in CI)

The intent hook (`hooks/sdlc_gate.sh`) is a deterministic proxy for *"the agent got the right discipline
signal"*: a code request must trigger the full spine, a read-only question may be answered directly.
`run.py` runs the hook over the behavioral corpus (`fixtures.json`), scores it, and **fails if the score
drops below `baseline.json`** — that drop is the drift signal. No LLM, no cost, identical every run.

```bash
python3 evals/run.py          # score the corpus, gate on drift vs baseline
```

Add a fixture (`{id, prompt, expect: code|ask|standard, tier2_rubric}`) whenever you add or change a
discipline signal. Raise the baseline only when you add harder fixtures — never lower it to green a red
build without justifying the regression.

## Tier 2 — LLM-judge behavioral evals (opt-in, needs API budget) — PARKED

The only way to measure *actual output quality*: run the agent on each fixture goal, then have an LLM
judge score the transcript against that fixture's `tier2_rubric` (did it plan before editing? did
plan-review catch the planted flaw? did review find the planted bug? did it park on the irreversible
action?). Track scores over time; a drop below baseline is a quality regression.

The runner and its **injectable `agent`/`judge` seam are already here and tested** (`run_tier2`,
`test_tier2_seam_hermetic`) — wiring a real LLM is a one-function change. It is **withheld on purpose**:
it costs money per run and needs a judge-model + rubric decision, so `--live` prints a parked notice
instead of spending. Turn it on once the budget is greenlit; run it nightly / pre-release, not per-PR
(cost + non-determinism).

```bash
python3 evals/run.py --live    # parked until a real judge is wired
```
