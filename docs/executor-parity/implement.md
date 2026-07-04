# Executor parity — implement (`sdlc-implement` vs `superpowers:test-driven-development` + `executing-plans`)

`sdlc-implement` is LoopSmith's portable fallback for the Implement phase, used when `superpowers` isn't
present. superpowers stays **preferred on Claude**. This comparison keeps the fallback **at par or better**.

## vs `test-driven-development`
| Dimension | superpowers | sdlc-implement | Verdict |
|---|---|---|---|
| Iron Law — no production code without a failing test | ✓ | ✓ | **par** |
| Watch it fail *for the right reason* | ✓ | ✓ | **par** |
| Red → Green → Refactor cycle | ✓ (with graph) | ✓ (3 steps) | **par** |
| Minimal code to pass | ✓ | ✓ | **par** |
| When-to-use + exceptions | ✓ | ✓ | **par** |
| Anti-patterns | ✓ full 8 KB doc (5 patterns + gate functions) | ~ 4 condensed rules (mocks, test-only methods, mock-understanding, integration) | **slightly lighter** |

## vs `executing-plans`
| Dimension | superpowers | sdlc-implement | Verdict |
|---|---|---|---|
| Load + review the plan critically first | ✓ | ✓ | **par** |
| Step-by-step, verify each | ✓ | ✓ | **par** |
| Stop/ask on blockers | ✓ | ✓ (park-and-continue) | **par** |
| Subagent preference where available | ✓ | ✓ (noted) | **par** |
| Loop integration (verify each step via `sdlc-verify`; gate `done_when`) | ✗ (host-agnostic) | ✓ | **better** |

**Net:** **par** on the TDD + plan-execution disciplines, **better** on loop integration, **slightly
lighter** only on the exhaustive anti-pattern catalogue (5 gate-functions → 4 condensed rules). Every
load-bearing rule is preserved; superpowers remains the richer choice on Claude.
