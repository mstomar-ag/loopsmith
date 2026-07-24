"""Tests for the bidirectional pipeline report card (pipeline.py) and the
machine done_when (loop.py verify + verify.enforce). All deterministic, $0."""
import json, pathlib, importlib.util, subprocess, sys, tempfile

S = pathlib.Path(__file__).resolve().parent.parent / "skills" / "sdlc-loop" / "scripts"


def _mod(name):
    spec = importlib.util.spec_from_file_location(name, S / f"{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def _project(d, stages):
    root = pathlib.Path(d)
    base = root / ".sdlc"
    (base / "goals").mkdir(parents=True); (base / "state").mkdir()
    (base / "config.json").write_text(json.dumps({"budget": {"max_iterations": 10}}))
    (base / "state" / "STATE.md").write_text("iteration: 0\nrun_iteration: 0\nlast_run: none\n")
    (base / "state" / "review-queue.md").write_text("# Q\n")
    (base / "pipeline.json").write_text(json.dumps({"name": "demo", "stages": stages}))
    return str(base)


def test_card_reports_both_directions_with_honest_absence():
    with tempfile.TemporaryDirectory() as d:
        (pathlib.Path(d) / "raw.txt").write_text("x")
        base = _project(d, [
            {"name": "extract", "produces": ["raw.txt"],
             "checks": {"forward": [{"name": "raw ok", "run": "true"}]}},
            {"name": "transform",
             "checks": {"reverse": [{"name": "rows trace back", "run": "true"}]}},
            {"name": "publish"},          # no checks at all → honest ABSENT lanes
        ])
        card = _mod("pipeline").build_card(base)
        stages = {s["stage"]: s["signals"] for s in card["stages"]}
        assert any(x["status"] == "PASS" and x["direction"] == "forward"
                   for x in stages["extract"])
        assert any(x["status"] == "PASS" and x["direction"] == "reverse"
                   for x in stages["transform"])
        publish = stages["publish"]
        assert {x["direction"] for x in publish if x["status"] == "ABSENT"} == {"forward", "reverse"}
        assert card["verdict"]["clean"] is False          # blocked lanes forbid a clean verdict
        assert {"action": "declare_checks", "stage": "publish", "direction": "reverse"} \
            in card["verdict"]["next_actions"]


def test_failing_check_and_missing_artifact_localize_to_their_stage():
    with tempfile.TemporaryDirectory() as d:
        base = _project(d, [
            {"name": "extract", "produces": ["nope-*.txt"]},                  # missing artifact
            {"name": "transform", "checks": {"reverse": [{"name": "trace", "run": "false"}]}},
        ])
        card = _mod("pipeline").build_card(base)
        assert card["verdict"]["failing_stages"] == ["extract", "transform"]
        assert card["verdict"]["overall"] == "FAIL"


def test_warn_exit_code_2_is_warn_not_fail():
    with tempfile.TemporaryDirectory() as d:
        base = _project(d, [
            {"name": "s", "checks": {"forward": [{"name": "advisory", "run": "exit 2"}]}},
        ])
        card = _mod("pipeline").build_card(base)
        assert card["stages"][0]["signals"][0]["status"] == "WARN"
        assert card["verdict"]["failing_stages"] == []


def test_compare_finds_recurrence_and_improvement():
    with tempfile.TemporaryDirectory() as d:
        base = _project(d, [
            {"name": "s", "checks": {"forward": [{"name": "gate", "run": "false"}]}},
        ])
        pl = _mod("pipeline")
        prior = pl.build_card(base)
        delta_same = pl.compare_cards(prior, pl.build_card(base))
        assert delta_same["recurrence_count"] == 1 and not delta_same["improved"]
        (pathlib.Path(base) / "pipeline.json").write_text(json.dumps(
            {"name": "demo", "stages": [
                {"name": "s", "checks": {"forward": [{"name": "gate", "run": "true"}]}}]}))
        delta_fixed = pl.compare_cards(prior, pl.build_card(base))
        assert delta_fixed["improved"] and delta_fixed["recurrence_count"] == 0


def test_no_pipeline_json_exits_3():
    with tempfile.TemporaryDirectory() as d:
        base = _project(d, [])
        (pathlib.Path(base) / "pipeline.json").unlink()
        proc = subprocess.run([sys.executable, str(S / "pipeline.py"), "card", base],
                              capture_output=True, text=True)
        assert proc.returncode == 3 and "NO-PIPELINE" in proc.stderr


# --- machine done_when: loop.py verify + verify.enforce ---

def _goal_backlog(d, verify_command=None, enforce=False):
    base = pathlib.Path(d) / ".sdlc"
    (base / "goals").mkdir(parents=True); (base / "state").mkdir()
    cfg = {"budget": {"max_iterations": 10},
           "verify": {"command": "", "enforce": enforce}}
    (base / "config.json").write_text(json.dumps(cfg))
    (base / "state" / "STATE.md").write_text("iteration: 0\nrun_iteration: 0\nlast_run: none\n")
    (base / "state" / "review-queue.md").write_text("# Q\n")
    fm = "---\nid: 0001\nstatus: pending\n"
    if verify_command:
        fm += f'verify_command: {verify_command}\n'
    (base / "goals" / "0001.md").write_text(fm + "---\nx\n")
    return str(base), str(base / "goals" / "0001.md")


def _loop_cli(*args):
    return subprocess.run([sys.executable, str(S / "loop.py"), *args],
                          capture_output=True, text=True)


def test_verify_verb_records_passing_evidence():
    with tempfile.TemporaryDirectory() as d:
        base, goal = _goal_backlog(d, verify_command="true")
        proc = _loop_cli("verify", base, goal)
        assert proc.returncode == 0 and "VERIFIED" in proc.stdout
        ev = json.loads((pathlib.Path(base) / "state" / "verify" / "0001.json").read_text())
        assert ev["exit"] == 0


def test_verify_verb_no_command_is_honest_exit_3():
    with tempfile.TemporaryDirectory() as d:
        base, goal = _goal_backlog(d)
        proc = _loop_cli("verify", base, goal)
        assert proc.returncode == 3 and "NO-COMMAND" in proc.stderr


def test_enforce_refuses_done_without_fresh_evidence_then_accepts():
    with tempfile.TemporaryDirectory() as d:
        base, goal = _goal_backlog(d, verify_command="true", enforce=True)
        _loop_cli("start", base)
        refused = _loop_cli("record", base, goal, "done")
        assert refused.returncode == 4 and "REFUSED" in refused.stderr
        assert "status: pending" in pathlib.Path(goal).read_text()   # nothing recorded
        assert _loop_cli("verify", base, goal).returncode == 0
        accepted = _loop_cli("record", base, goal, "done")
        assert accepted.returncode == 0
        assert "status: done" in pathlib.Path(goal).read_text()


def test_enforce_refuses_failed_verify_evidence():
    with tempfile.TemporaryDirectory() as d:
        base, goal = _goal_backlog(d, verify_command="false", enforce=True)
        _loop_cli("start", base)
        assert _loop_cli("verify", base, goal).returncode == 1
        refused = _loop_cli("record", base, goal, "done")
        assert refused.returncode == 4 and "FAILED" in refused.stderr


def test_enforce_off_keeps_prior_behavior():
    with tempfile.TemporaryDirectory() as d:
        base, goal = _goal_backlog(d)                    # enforce=False default
        assert _loop_cli("record", base, goal, "done").returncode == 0
        assert "status: done" in pathlib.Path(goal).read_text()


def test_enforce_never_blocks_parked_or_failed():
    with tempfile.TemporaryDirectory() as d:
        base, goal = _goal_backlog(d, enforce=True)
        assert _loop_cli("record", base, goal, "parked", "needs a call").returncode == 0
        assert "status: parked" in pathlib.Path(goal).read_text()


# --- in-process coverage of the CLI paths (subprocess runs don't count) ---

def test_verify_goal_and_refusal_in_process():
    with tempfile.TemporaryDirectory() as d:
        base, goal = _goal_backlog(d, verify_command="true", enforce=True)
        lp = _mod("loop")
        lp.state.start_run(base)
        assert lp._done_refusal(base, goal) == "no verify evidence for this goal"
        assert lp.verify_goal(base, goal) == 0
        assert lp._done_refusal(base, goal) is None
        # stale evidence (predates the run) refuses again
        lp.state.start_run(base)
        import time as _t; _t.sleep(1.1)     # STATE stamps whole seconds
        lp.state.start_run(base)
        assert lp._done_refusal(base, goal) == "verify evidence predates this run"


def test_verify_goal_failing_command_and_config_fallback():
    with tempfile.TemporaryDirectory() as d:
        base, goal = _goal_backlog(d, enforce=False)
        cfg = pathlib.Path(base) / "config.json"
        cfg.write_text(json.dumps({"budget": {"max_iterations": 10},
                                   "verify": {"command": "false", "enforce": False}}))
        lp = _mod("loop")
        assert lp.verify_goal(base, goal) == 1           # config-level command, failing
        assert lp._done_refusal(base, goal).startswith("last verify FAILED")


def test_loop_main_verbs_in_process(capsys):
    with tempfile.TemporaryDirectory() as d:
        base, goal = _goal_backlog(d, verify_command="true", enforce=True)
        lp = _mod("loop")
        assert lp.main(["loop.py", "start", base]) == 0
        assert lp.main(["loop.py", "record", base, goal, "done"]) == 4      # refused, no evidence
        assert lp.main(["loop.py", "verify", base, goal]) == 0
        assert lp.main(["loop.py", "record", base, goal, "done"]) == 0      # evidence fresh
        assert lp.main(["loop.py", "spend", base, "42"]) == 0
        assert lp.main(["loop.py", "bogus"]) == 2
        capsys.readouterr()


def test_pipeline_main_json_and_compare_in_process(tmp_path, capsys):
    with tempfile.TemporaryDirectory() as d:
        base = _project(d, [
            {"name": "s", "checks": {"forward": [{"name": "gate", "run": "false"}]}},
        ])
        pl = _mod("pipeline")
        prior_json = tmp_path / "prior.json"
        assert pl.main(["pipeline.py", "card", base, "--json", str(prior_json)]) == 1
        out = capsys.readouterr().out
        assert "Pipeline report card" in out and "verdict: FAIL" in out
        assert pl.main(["pipeline.py", "card", base, "--compare", str(prior_json)]) == 1
        out = capsys.readouterr().out
        assert "STILL FAILING" in out and "recurrence" in out
        assert pl.main(["pipeline.py", "card", base, "--compare", str(tmp_path / "nope.json")]) == 3
        assert pl.main(["pipeline.py"]) == 2
        capsys.readouterr()


def test_pipeline_render_regressed_row_and_invalid_spec():
    with tempfile.TemporaryDirectory() as d:
        base = _project(d, [
            {"name": "s", "checks": {"forward": [{"name": "gate", "run": "true"}]}},
        ])
        pl = _mod("pipeline")
        good = pl.build_card(base)
        (pathlib.Path(base) / "pipeline.json").write_text(json.dumps(
            {"name": "demo", "stages": [
                {"name": "s", "checks": {"forward": [{"name": "gate", "run": "false"}]}}]}))
        bad = pl.build_card(base)
        delta = pl.compare_cards(good, bad)
        assert delta["regressed"] and "REGRESSED" in pl.render(bad, delta)
        (pathlib.Path(base) / "pipeline.json").write_text(json.dumps({"stages": "not-a-list"}))
        assert pl.load_pipeline(base) is None


def test_check_timeout_reads_fail():
    with tempfile.TemporaryDirectory() as d:
        base = _project(d, [{"name": "s", "checks": {"forward": [{"name": "hang", "run": "sleep 2"}]}}])
        pl = _mod("pipeline")
        pl._CHECK_TIMEOUT_SECS = 0.2
        card = pl.build_card(base)
        sig = card["stages"][0]["signals"][0]
        assert sig["status"] == "FAIL" and "timed out" in sig["detail"]
