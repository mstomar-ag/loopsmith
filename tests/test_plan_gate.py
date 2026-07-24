"""Tests for the OPT-IN hard plan-gate (hooks/plan_gate.sh). Default off = allows
everything silently; on = denies source edits without a fresh .sdlc/plans/*.md."""
import json, os, pathlib, subprocess, time

HOOK = pathlib.Path(__file__).resolve().parent.parent / "hooks" / "plan_gate.sh"


def _run(project_dir, file_path):
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project_dir)}
    proc = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"tool_input": {"file_path": file_path}}),
        capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def _project(tmp_path, enabled=True, fresh_hours=24):
    base = tmp_path / ".sdlc"
    base.mkdir()
    base.joinpath("config.json").write_text(json.dumps(
        {"gates": {"hard_plan_gate": {"enabled": enabled,
                                      "plan_freshness_hours": fresh_hours}}}))
    return tmp_path


def _deny_reason(out):
    return json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]


def test_default_off_allows_everything(tmp_path):
    # no .sdlc at all → silent allow
    assert _run(tmp_path, str(tmp_path / "app.py")) == ""
    # .sdlc present but flag off → silent allow
    _project(tmp_path, enabled=False)
    assert _run(tmp_path, str(tmp_path / "app.py")) == ""


def test_enabled_denies_source_edit_without_plan(tmp_path):
    _project(tmp_path)
    out = _run(tmp_path, str(tmp_path / "app.py"))
    assert "deny" in out and "no fresh plan" in _deny_reason(out)


def test_enabled_allows_docs_config_and_sdlc_layer(tmp_path):
    _project(tmp_path)
    for path in ("README.md", "config.json", "notes.txt",
                 str(tmp_path / ".sdlc" / "goals" / "g.md"),
                 str(tmp_path / "docs" / "spec.md")):
        assert _run(tmp_path, path) == ""


def test_fresh_plan_unblocks_source_edits(tmp_path):
    _project(tmp_path)
    plans = tmp_path / ".sdlc" / "plans"
    plans.mkdir()
    (plans / "0001-plan.md").write_text("# plan")
    assert _run(tmp_path, str(tmp_path / "app.py")) == ""


def test_stale_plan_still_denies(tmp_path):
    _project(tmp_path, fresh_hours=1)
    plans = tmp_path / ".sdlc" / "plans"
    plans.mkdir()
    plan = plans / "0001-plan.md"
    plan.write_text("# plan")
    two_hours_ago = time.time() - 7200
    os.utime(plan, (two_hours_ago, two_hours_ago))
    out = _run(tmp_path, str(tmp_path / "app.py"))
    assert "deny" in out


def test_override_sentinel_allows(tmp_path):
    _project(tmp_path)
    (tmp_path / ".sdlc" / ".allow-direct-edits").write_text("")
    assert _run(tmp_path, str(tmp_path / "app.py")) == ""


def test_malformed_stdin_fails_open(tmp_path):
    _project(tmp_path)
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)}
    proc = subprocess.run(["bash", str(HOOK)], input="garbage{{{",
                          capture_output=True, text=True, env=env)
    assert proc.returncode == 0 and proc.stdout.strip() == ""


def test_deny_output_is_valid_hook_json(tmp_path):
    _project(tmp_path)
    out = _run(tmp_path, str(tmp_path / "core.go"))
    payload = json.loads(out)["hookSpecificOutput"]
    assert payload["hookEventName"] == "PreToolUse"
    assert payload["permissionDecision"] == "deny"
