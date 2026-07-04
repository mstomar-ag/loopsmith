# Executor parity — brainstorm (`sdlc-brainstorm` vs `superpowers:brainstorming`)

`sdlc-brainstorm` is LoopSmith's portable Goal-phase fallback; superpowers stays **preferred on Claude**.

| Dimension | superpowers:brainstorming | sdlc-brainstorm | Verdict |
|---|---|---|---|
| Hard gate — no code until the design is approved (every project) | ✓ | ✓ | **par** |
| "Too simple to need a design" anti-pattern | ✓ | ✓ | **par** |
| Explore project context first | ✓ | ✓ | **par** |
| Scope check / decompose multi-subsystem requests | ✓ | ✓ | **par** |
| Clarifying questions, one at a time | ✓ | ✓ | **par** |
| Propose 2-3 approaches + a recommendation | ✓ | ✓ | **par** |
| Present the design in sections; get approval | ✓ | ✓ | **par** |
| Terminal → hand to plan-writing | ✓ (`writing-plans`) | ✓ (`sdlc-plan`) | **par** |
| Written spec doc + spec self-review + user spec review | ✓ (`docs/.../<topic>-design.md`) | ~ restate as one checkable goal (`done_when`) → `sdlc-plan-review` | **lighter (by design)** |
| Interactive **visual** brainstorming companion (25 KB Node server) | ✓ | ✗ intentionally omitted | **Claude-only premium — not needed off-Claude** |

**Net:** **par** on the whole brainstorming discipline (gate, questions, approaches, design, approval).
Two deliberate differences: LoopSmith folds the "spec doc" into the **goal artifact + `sdlc-plan-review`**
rather than a separate design file, and the **visual companion is a Claude-only premium the portable
fallback skips**. No discipline is lost; superpowers stays richer on Claude.
