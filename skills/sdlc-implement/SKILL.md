---
name: sdlc-implement
description: The Implement phase — build test-first (red → green → refactor) and execute the plan step by step, verifying each. Use during Implement, or when the user runs /sdlc-implement. Portable executor — prefer superpowers:test-driven-development + executing-plans on Claude when installed; this is the built-in equivalent for every other host.
allowed-tools: Bash
---

# sdlc-implement

**Executor resolution (host-aware):**
- **Claude Code + `superpowers` installed** → prefer **`superpowers:test-driven-development`** +
  **`superpowers:executing-plans`** (their richer versions; where subagents exist,
  `superpowers:subagent-driven-development`).
- **Otherwise** (Cursor / any host / no companion) → use this. Same discipline, portable.

Two things happen in this phase: **build test-first**, and **execute the plan step by step**.

## Test-first (TDD)
**No production code without a failing test first.** If you didn't watch the test fail, you don't know
it tests the right thing. Wrote code before the test? Delete it and re-derive from the test.

**Red → Green → Refactor**, one behavior at a time:
1. **RED** — write the smallest test for the next behavior. Run it. **Watch it fail for the right
   reason** (it asserts the behavior — not a typo or an import error).
2. **GREEN** — write the *minimal* code to pass. Run it. All green.
3. **REFACTOR** — clean up while staying green.

Skip TDD only for throwaway prototypes / generated code / config — and say so.

## Test behavior, not plumbing (anti-patterns to avoid)
- **Don't test the mock** — assert real behavior/output, not that a stub was called.
- **No test-only methods in production code** — tests exercise the real interface.
- **Don't mock what you don't understand** — a wrong mock passes a wrong test.
- **Don't leave integration as an afterthought** — cover the real seams, not just isolated units.

## Execute the plan, step by step
1. **Load** the plan and **review it critically** — raise any concern *before* starting (last cheap
   moment to catch a bad plan; it should already have passed `sdlc-plan-review`).
2. For **each step**: do exactly what it says (steps are bite-sized), **verify** it (run the check —
   see `sdlc-verify`), then move on. Track progress as you go.
3. **Park, don't force** on anything irreversible or blocked (matches the loop's park rule).

## In the loop
Every step's claim needs evidence (`sdlc-verify`); don't mark the goal done until its `done_when` is
verified. Prefer subagents for independent tasks where the host supports them.
