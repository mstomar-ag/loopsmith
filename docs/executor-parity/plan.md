# Executor parity — plan (`sdlc-plan` vs `superpowers:writing-plans`)

`sdlc-plan` is LoopSmith's portable fallback for the Plan phase; superpowers stays **preferred on
Claude**. Comparison so the fallback is **at par or better**.

| Dimension | superpowers:writing-plans | sdlc-plan | Verdict |
|---|---|---|---|
| Plan for a zero-context reader; spell everything out | ✓ | ✓ | **par** |
| DRY / YAGNI / TDD / frequent commits | ✓ | ✓ | **par** |
| Scope check (split multi-subsystem specs) | ✓ | ✓ | **par** |
| File structure — responsibilities, small focused files, follow patterns | ✓ | ✓ | **par** |
| Task right-sizing (own test cycle + reviewer gate; independently testable) | ✓ | ✓ | **par** |
| Bite-sized steps (write test → fail → minimal → pass → commit) | ✓ | ✓ | **par** |
| Definition of done | ~ implied | ✓ explicit, mapped to `done_when` + `sdlc-verify` | **better** |
| Hand-off to a plan-review gate | ~ external | ✓ `sdlc-plan-review` (never skipped) | **better** |
| Required plan-document-header template | ✓ fixed format | ~ not mandated | **slightly lighter** |

**Net:** **par** on the planning discipline, **better** on the definition-of-done + plan-review/verify
integration, **slightly lighter** only on the fixed plan-document-header template. Nothing load-bearing
is lost.
