"""Lock the README's pipeline documentation: it must name all 7 phases, document both optional
companion plugins, and make clear they're an optional enhancement backed by the portable executors —
not hard dependencies. Stable anchors only (phase names, plugin names, documented terms) — not prose
wording."""
import pathlib

README = (pathlib.Path(__file__).resolve().parent.parent / "README.md").read_text()


def test_documents_all_seven_phases():
    for phase in ("Goal", "Research", "Plan", "Plan-Review", "Implement", "Review", "Retrospective"):
        assert phase in README, f"README omits phase: {phase}"


def test_distinguishes_shipped_plan_review_from_companions():
    assert "sdlc-plan-review" in README                      # the gate this kit ships
    assert "superpowers" in README and "code-review" in README  # the optional companions


def test_documents_both_backlog_sources():
    assert "discovery" in README                      # the config knob that selects the source
    assert ".sdlc/goals/" in README                   # the local files source
    assert "GitHub issues" in README and "sdlc:goal" in README   # the github source + its label scheme


def test_documents_optional_knowledge_graph():
    assert "knowledge_graph" in README                       # the config toggle
    assert "graphify" in README                              # the default builder
    assert "off by default" in README or "opt-in" in README  # not on without consent
    assert ".sdlc/knowledge/" in README                      # the corpus (research + analysis)


def test_documents_companions_as_optional_with_portable_fallback():
    assert "optional" in README.lower()                       # companions are not required
    assert "claude-plugins-official" in README                # where to get them if you want them
    assert "portable" in README.lower()                       # the sdlc-* executors that run without them
