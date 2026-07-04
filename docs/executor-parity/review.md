# Executor parity — review (`sdlc-review` vs the `code-review` plugin + `superpowers:requesting-code-review`)

`sdlc-review` is LoopSmith's portable Review executor — a thorough two-layer code-quality audit. On
Claude, the `code-review` plugin (`/code-review`) + `superpowers:requesting-code-review` stay
**preferred**. This keeps the fallback **at par or better**.

| Capability | code-review plugin + requesting-code-review | sdlc-review | Verdict |
|---|---|---|---|
| Diff review for correctness bugs | ✓ | ✓ | **par** |
| Findings with `file:line` + severity | ✓ | ✓ (Bug/Concern/Coverage/Missing/Good/Minor/Nit) | **par** |
| Cleanup / reuse / simplification pass | ✓ | ✓ (Structure / DRY / dead-code / consistency) | **par** |
| Request-a-review workflow | ✓ (`requesting-code-review`) | ✓ (this *is* the reviewer) | **par** |
| Evidence discipline (no invented numbers) | ✓ | ✓ (ties to `sdlc-verify`) | **par** |
| Quantitative KPI dashboard (ruff/mypy/cov + hotspots) | ~ not a dashboard | ✓ | **better** |
| Health-scan mode (whole-file audit, not just the diff) | ~ diff-focused | ✓ | **better** |
| Async-correctness + project-rule (north-star / CLAUDE.md) gates | ~ generic | ✓ explicit | **better** |
| Counter-review (grade an external Cursor/GPT/SonarQube review) | ✗ | ✓ | **better** |

**Net:** **par** on diff-review correctness + cleanup, and **better** on the KPI dashboard, health-scan
mode, project-rule gate, and counter-review (the fuller two-layer audit). On Claude the
code-review plugin remains available and preferred; off-Claude, `sdlc-review` is a strong, self-contained
reviewer — and its counter-review mode can even grade Cursor's own reviewer.
