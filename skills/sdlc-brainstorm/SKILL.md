---
name: sdlc-brainstorm
description: The Goal phase — turn an idea into an approved design before any code: explore intent, requirements, and constraints; ask one question at a time; propose 2-3 approaches with trade-offs; restate as one concrete, checkable goal. Use at Goal, or when the user runs /sdlc-brainstorm. Portable executor — prefer superpowers:brainstorming on Claude when installed; this is the built-in equivalent for every other host.
---

# sdlc-brainstorm

**Executor resolution (host-aware):**
- **Claude Code + `superpowers` installed** → prefer **`superpowers:brainstorming`** (its richer
  version, including an interactive visual companion).
- **Otherwise** (Cursor / any host / no companion) → use this. Same discipline, portable (text-only —
  no visual server).

Turn the idea into an approved design **before any implementation.**

> **Hard gate:** do NOT write code, scaffold, or invoke an implementation skill until you've presented a
> design and the user has approved it — **every** project, however simple. "Too simple to need a design"
> is where unexamined assumptions waste the most work. The design can be a few sentences; present it and
> get approval anyway.

## The flow
1. **Explore context** — read the relevant files, docs, recent commits (and the north-star, if present).
2. **Scope check** — if the request spans multiple independent subsystems, flag it and **decompose**
   into sub-projects first; brainstorm the first one through this flow. Each gets its own goal → plan.
3. **Ask clarifying questions — one at a time** — purpose, constraints, success criteria. Prefer
   multiple-choice where you can.
4. **Propose 2-3 approaches** with trade-offs and **your recommendation** — never just one.
5. **Present the design** in sections scaled to complexity; get approval, revising until approved.
6. **Restate the outcome as one concrete, checkable goal** (a `done_when` a reviewer could verify) —
   the artifact the rest of the SDLC runs on.

## Hand off
The terminal step is **`sdlc-plan`** (write the implementation plan). Do not jump to any other
implementation action from here.
