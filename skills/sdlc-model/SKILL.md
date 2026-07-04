---
name: sdlc-model
description: Predict the model tier a goal deserves (haiku/sonnet/opus/fable) so a goal's phases run at a tier matched to the work. Use when the user runs /sdlc-model or asks which model to use for a goal.
allowed-tools: Bash(python3 *)
---

# sdlc-model

Match the model to the work. A one-line rename doesn't need Opus; a schema migration shouldn't run on
Haiku. This predicts the tier **once from the goal** — then the goal's phases run at that tier (the
design: "the rest of the steps will be executed with that model").

## Recommend a tier for a goal

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/predict.py" "<goal text>"     # or a .sdlc/goals/NNNN-*.md path
```

Prints one of `haiku | sonnet | opus | fable`:

| Tier | When | Signals |
|------|------|---------|
| **opus** | hard / risky / high blast-radius | migrate, architecture, security, auth, concurrency, performance, breaking change, payments |
| **fable** | creative / writing-heavy | vision, narrative, storytelling, blog, marketing copy |
| **haiku** | trivial / mechanical | typo, rename, whitespace, reformat, docstring, dead code |
| **sonnet** | everything else (default) | ordinary implementation |

Deterministic (regex over the goal text — no LLM, no cost, no drift). Conflicts resolve **upward**:
"fix the typo in the security module" → `opus`, because under-powering a hard goal costs more than
over-powering a trivial one.

## Automatic selection in the loop (config-gated)

`.sdlc/config.json` → `model_selection`:
- `"off"` (default) — phases run at the session's model, unchanged.
- `"auto"` — the loop predicts the tier from each goal and runs that goal's phases at it.

**Why phases, not the session:** the main session cannot switch its own model mid-run, but a phase run
as a **subagent** can take a `model` override. So under `auto`, `/sdlc-loop` and `/sdlc-goal` dispatch
each phase as a subagent at the predicted tier. (Absent that host capability, the recommendation above
still guides — turn `model_selection` to `off` and it's a no-op.)
