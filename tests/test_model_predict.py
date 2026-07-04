"""Model auto-selection predictor (sdlc-model/predict.py): a deterministic goal->tier heuristic.
Pins each tier, the upward conflict-resolution rule, and the default so a wording change that
silently down-tiers hard work fails here."""
import pathlib, importlib.util

P = pathlib.Path(__file__).resolve().parent.parent / "skills" / "sdlc-model" / "scripts" / "predict.py"


def _mod():
    spec = importlib.util.spec_from_file_location("predict", P)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def test_hard_goals_get_opus():
    p = _mod().predict
    for g in ("migrate the database schema", "redesign the auth architecture",
              "fix the race condition in the scheduler", "add payment processing"):
        assert p(g) == "opus", g


def test_trivial_goals_get_haiku():
    p = _mod().predict
    for g in ("fix a typo in the README", "rename the helper for clarity",
              "reformat the config", "remove dead code"):
        assert p(g) == "haiku", g


def test_creative_goals_get_fable():
    p = _mod().predict
    for g in ("draft the product vision", "write the launch blog narrative"):
        assert p(g) == "fable", g


def test_ordinary_code_defaults_to_sonnet():
    p = _mod().predict
    for g in ("add a retry to the http client", "wire the new CLI flag", ""):
        assert p(g) == "sonnet", g


def test_conflict_resolves_upward():
    # a trivial word next to a hard one must NOT down-tier: hard wins.
    assert _mod().predict("fix the typo in the security module") == "opus"


def test_no_false_trigger_on_substrings():
    p = _mod().predict
    assert p("update the revision history") == "sonnet"   # 'vision'/'story' are substrings — must not fire
    assert p("improve the provision logic") == "sonnet"


def test_main_reads_text_and_file(tmp_path):
    m = _mod()
    assert m.main(["predict.py", "migrate the tables"]) == 0
    f = tmp_path / "goal.md"; f.write_text("fix a typo")
    assert m.main(["predict.py", str(f)]) == 0
    assert m.main(["predict.py"]) == 2   # usage
