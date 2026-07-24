"""sdlc-doctor: a setup check-up. doctor.check() audits only what THIS project's config makes relevant
(github board -> gh auth+scope; KG -> builder; vision-first -> north-star) and returns each check with
the exact one-line fix. The command runner is injectable so these are hermetic (no real gh/graphify)."""
import json, pathlib, importlib.util, tempfile

D = pathlib.Path(__file__).resolve().parent.parent / "skills" / "sdlc-doctor" / "scripts" / "doctor.py"


def _doc():
    spec = importlib.util.spec_from_file_location("doctor", D)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def _sdlc(d, cfg):
    base = pathlib.Path(d) / ".sdlc"; base.mkdir(parents=True)
    (base / "config.json").write_text(json.dumps(cfg))
    return str(base)


def _runner(gh_auth="", builder=""):
    """Fake command runner: canned stdout for the probes, '' = command unavailable/failed."""
    def run(args):
        if args[:3] == ["gh", "auth", "status"]:
            return gh_auth
        if len(args) >= 2 and args[1] == "--version":   # <builder> --version
            return builder
        return ""
    return run


def _by_name(checks):
    return {c["name"]: c for c in checks}


def test_flags_missing_gh_project_scope():
    d = _doc()
    with tempfile.TemporaryDirectory() as t:
        base = _sdlc(t, {"discovery": {"source": "github", "github": {"project": {"enabled": True}}}})
        c = _by_name(d.check(base, run=_runner(gh_auth="Logged in. Token scopes: 'repo', 'workflow'")))
        assert c["gh auth"]["ok"] is True
        assert c["gh project scope"]["ok"] is False
        assert "gh auth refresh -s project" in c["gh project scope"]["fix"]


def test_passes_when_scope_present():
    d = _doc()
    with tempfile.TemporaryDirectory() as t:
        base = _sdlc(t, {"discovery": {"source": "github", "github": {"project": {"enabled": True}}}})
        c = _by_name(d.check(base, run=_runner(gh_auth="scopes: 'repo', 'project'")))
        assert c["gh project scope"]["ok"] is True


def test_flags_missing_kg_builder():
    d = _doc()
    with tempfile.TemporaryDirectory() as t:
        base = _sdlc(t, {"knowledge_graph": {"enabled": True, "builder": "graphify"}})
        c = _by_name(d.check(base, run=_runner(builder="")))         # graphify --version fails
        assert c["graphify installed"]["ok"] is False
        assert "pip install graphifyy" in c["graphify installed"]["fix"]


def test_skips_irrelevant_checks_for_local_zero_dep():
    d = _doc()
    with tempfile.TemporaryDirectory() as t:
        base = _sdlc(t, {"discovery": {"source": "local-goals"}})
        names = [c["name"] for c in d.check(base, run=_runner())]
        assert not any("gh" in n or "graphify" in n or "north-star" in n for n in names)
        assert "project layer" in names                              # always checked


def test_main_runs():
    d = _doc()
    with tempfile.TemporaryDirectory() as t:
        base = _sdlc(t, {"discovery": {"source": "local-goals"}})
        assert d.main(["doctor.py", "check", base]) == 0


def test_detects_companions_never_failing_on_absence():
    d = _doc()
    with tempfile.TemporaryDirectory() as t:
        base = _sdlc(t, {"discovery": {"source": "local-goals"}})
        def run(args):
            return "superpowers@claude-plugins-official" if args == ["claude", "plugin", "list"] else _runner()(args)
        checks = d.check(base, run=run)
        names = " | ".join(c["name"] for c in checks)
        assert "superpowers: present" in names            # detected installed
        assert "code-review: absent" in names             # detected missing
        assert all(c["ok"] for c in checks if "superpowers" in c["name"] or "code-review" in c["name"])


def test_features_dashboard_reports_states(tmp_path):
    import json, importlib.util, pathlib as _pl
    spec = importlib.util.spec_from_file_location(
        "doctor", _pl.Path(__file__).resolve().parent.parent / "skills" / "sdlc-doctor" / "scripts" / "doctor.py")
    d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
    base = tmp_path / ".sdlc"; base.mkdir()
    base.joinpath("config.json").write_text(json.dumps(
        {"model_selection": "auto", "verify": {"enforce": True}}))
    rows = {name: state for name, state, _ in d.features(str(base))}
    assert "AUTO" in rows["model+effort auto-selection"]
    assert rows["machine-checked done (verify.enforce)"].startswith("ON")
    assert "off" in rows["hard plan-gate (deny source edits w/o fresh plan)"]
    assert rows["backlog source"] == "local-goals"
