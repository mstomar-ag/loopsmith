"""Overnight supervisor: the exit classifier (pure) + the wrapper e2e with a fake
session command. No real sessions, no sleeping (scale=0), no network."""
import importlib.util, os, pathlib, subprocess, time

S = pathlib.Path(__file__).resolve().parent.parent / "skills" / "sdlc-loop" / "scripts"


def _mod():
    spec = importlib.util.spec_from_file_location("sc", S / "supervise_classify.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


class _FixedRng:
    def randint(self, lo, hi):
        return lo


def test_done_when_loop_reports_its_own_stop():
    m = _mod()
    for tail in ("stopped: backlog-empty", "LOOP STOP: backlog-empty\n3 done, 1 parked",
                 "Backlog is empty.", "DONE"):
        assert m.classify(tail, rng=_FixedRng())[0] == "done", tail


def test_stop_report_alone_is_NOT_done_budget_wins():
    # THE review-found bug: the "N done, M parked" report prints on EVERY stop —
    # a budget stop carrying it must classify relaunch, never done.
    m = _mod()
    action, _, _ = m.classify("LOOP STOP: budget\n0 done, 2 parked, 0 failed", rng=_FixedRng())
    assert action == "relaunch"
    action, _, _ = m.classify("2 done, 1 parked, 0 failed", rng=_FixedRng())
    assert action != "done"                     # report without a success marker = unknown


def test_budget_stop_relaunches_after_short_pause():
    m = _mod()
    # the true contract: `loop.py next` prints BUDGET on its own line
    action, secs, _ = m.classify("$ loop.py next .sdlc\nBUDGET\n0 done, 2 parked", rng=_FixedRng())
    assert action == "relaunch" and secs == 60


def test_limit_with_reset_time_sleeps_until_reset_plus_jitter():
    m = _mod()
    # now = 03:00 local; message says resets at 5:30 -> 2.5h + 120s jitter
    now = time.mktime((2026, 7, 24, 3, 0, 0, 0, 0, -1))
    action, secs, reason = m.classify(
        "You have hit your usage limit. Your limit resets at 5:30am.",
        now=now, rng=_FixedRng())
    assert action == "sleep"
    assert secs == int(2.5 * 3600) + 120
    assert "reset" in reason


def test_limit_reset_earlier_today_means_tomorrow():
    m = _mod()
    now = time.mktime((2026, 7, 24, 6, 0, 0, 0, 0, -1))   # 6:00; "resets at 5:30" = next day
    action, secs, _ = m.classify("usage limit reached — resets at 5:30", now=now, rng=_FixedRng())
    assert action == "sleep"
    assert secs == int(23.5 * 3600) + 120


def test_limit_without_time_backs_off_capped():
    m = _mod()
    waits = [m.classify("rate limit exceeded, try later", attempt=a, rng=_FixedRng())[1]
             for a in (0, 1, 2, 9)]
    assert waits == [1800, 3600, 3600, 3600]


def test_unknown_crash_escalates_capped():
    m = _mod()
    waits = [m.classify("Traceback (most recent call last): boom", attempt=a, rng=_FixedRng())[1]
             for a in (0, 1, 2, 3, 9)]
    assert waits == [300, 600, 1200, 3600, 3600]


def _run_supervisor(tmp_path, fake_script, max_runs="10"):
    base = tmp_path / ".sdlc"; (base / "state").mkdir(parents=True)
    fake = tmp_path / "fake-claude.sh"
    fake.write_text("#!/usr/bin/env bash\n" + fake_script)
    fake.chmod(0o755)
    env = {**os.environ,
           "LOOPSMITH_CLAUDE_CMD": str(fake),
           "LOOPSMITH_SUPERVISE_MAX_RUNS": max_runs,
           "LOOPSMITH_SUPERVISE_SLEEP_SCALE": "0"}
    return subprocess.run(["bash", str(S / "supervise.sh"), str(base)],
                          capture_output=True, text=True, env=env, timeout=60), base


def test_wrapper_exits_zero_on_backlog_empty(tmp_path):
    proc, base = _run_supervisor(
        tmp_path, 'echo "run complete"; echo "LOOP STOP: backlog-empty"\n')
    assert proc.returncode == 0
    assert "action=done" in (base / "state" / "supervisor.log").read_text()


def test_wrapper_relaunches_through_limit_then_finishes(tmp_path):
    # 1st session: limit (no parseable time -> backoff, scaled to 0s); 2nd: done.
    script = (
        'N="$(cat "$STATE_DIR/n" 2>/dev/null || echo 0)"; N=$((N+1)); echo "$N" > "$STATE_DIR/n"\n'
        'if [ "$N" -lt 2 ]; then echo "usage limit reached, try again later"; else echo "LOOP STOP: backlog-empty"; fi\n')
    base_dir = tmp_path / ".sdlc"
    script = script.replace("$STATE_DIR", str(tmp_path))
    proc, base = _run_supervisor(tmp_path, script)
    assert proc.returncode == 0
    log = (base / "state" / "supervisor.log").read_text()
    assert "action=backoff" in log and "action=done" in log


def test_wrapper_stop_file_halts_cleanly(tmp_path):
    base = tmp_path / ".sdlc"; (base / "state").mkdir(parents=True)
    (base / "state" / "supervisor.stop").write_text("")
    env = {**os.environ, "LOOPSMITH_CLAUDE_CMD": "false",
           "LOOPSMITH_SUPERVISE_SLEEP_SCALE": "0"}
    proc = subprocess.run(["bash", str(S / "supervise.sh"), str(base)],
                          capture_output=True, text=True, env=env, timeout=30)
    assert proc.returncode == 0 and "stop-file" in proc.stdout


def test_wrapper_max_runs_caps_a_crash_loop(tmp_path):
    proc, base = _run_supervisor(tmp_path, 'echo "segfault-ish nonsense"\n', max_runs="3")
    assert proc.returncode == 1
    assert "max runs (3) reached" in proc.stdout + (base / "state" / "supervisor.log").read_text()
