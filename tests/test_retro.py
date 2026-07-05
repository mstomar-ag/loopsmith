"""sdlc-retro: the Retrospective/learning executor. Pins that the skill is well-formed, does its three
things (structural + product reflection, intent-vs-shipped, three-store harvest routed to LoopSmith's
OWN stores), stays advisory (proposes/parks standing changes), is wired into BOTH orchestrators'
Retrospective phase, and leaks nothing from the source repo it was genericized from."""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
RETRO = ROOT / "skills" / "sdlc-retro" / "SKILL.md"


def _t():
    return RETRO.read_text()


def test_skill_exists_with_frontmatter():
    assert RETRO.exists()
    t = _t()
    assert "name: sdlc-retro" in t
    assert "description:" in t and "allowed-tools:" in t


def test_does_the_three_things():
    t = _t().lower()
    assert "structural reflection" in t and "product reflection" in t
    assert "intent-vs-shipped" in t
    assert "achieved" in t and "partial" in t and "diverged" in t     # the intent grade


def test_three_stores_are_loopsmiths_own():
    t = _t()
    assert ".sdlc/context/north-star.md" in t                          # north-star store
    assert ".sdlc/project.md" in t and "CLAUDE.md" in t                # standing-rule store
    assert ".sdlc/journey" in t or "loop.py" in t                      # audit-trail store


def test_advisory_and_fail_open():
    t = _t().lower()
    assert "advisory" in t and "park" in t                             # proposes; parks standing changes
    assert "never" in t and ("auto-write" in t or "unattended" in t)   # no unattended standing writes
    assert "fail-open" in t


def test_wired_into_both_orchestrators_retrospective_phase():
    for orch in ("sdlc-goal", "sdlc-loop"):
        t = (ROOT / "skills" / orch / "SKILL.md").read_text()
        assert "sdlc-retro" in t, f"{orch} does not run sdlc-retro"
        assert "Retrospective" in t, f"{orch} has no Retrospective phase step"


def test_no_source_repo_leakage():
    banned = ("docs/context", "Ported from", "OnShot", "onshot", "storytelling",
              "episode", "lipsync", "screenplay", "media-orch")
    t = _t()
    for b in banned:
        assert b not in t, f"sdlc-retro leaked '{b}'"
