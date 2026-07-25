import json, pathlib, importlib.util, tempfile

S = pathlib.Path(__file__).resolve().parent.parent / "skills" / "sdlc-loop" / "scripts"


def _state():
    spec = importlib.util.spec_from_file_location("state", S / "state.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def _sdlc(d):
    base = pathlib.Path(d) / ".sdlc"; (base / "goals").mkdir(parents=True); (base / "state").mkdir()
    (base / "config.json").write_text(json.dumps({"budget": {"max_iterations": 3}}))
    (base / "state" / "STATE.md").write_text(
        "# Loop State\n\n<!-- Do not hand-edit during a run. -->\n\n"
        "iteration: 0\nrun_iteration: 0\nlast_run: none\n\n## Items\n<!-- x -->\n")
    (base / "state" / "review-queue.md").write_text("# Morning Review Queue\n")
    g = base / "goals" / "0001-x.md"; g.write_text("---\nid: 0001\nstatus: pending\n---\nbody\n")
    return str(base), str(g)


def test_complete_sets_done():
    st = _state()
    with tempfile.TemporaryDirectory() as d:
        base, g = _sdlc(d); st.complete(base, g)
        assert "status: done" in pathlib.Path(g).read_text()


def test_park_sets_parked_and_appends_queue():
    st = _state()
    with tempfile.TemporaryDirectory() as d:
        base, g = _sdlc(d); st.park(base, g, "hit a deploy gate")
        assert "status: parked" in pathlib.Path(g).read_text()
        q = (pathlib.Path(base) / "state" / "review-queue.md").read_text()
        assert "0001-x.md" in q and "hit a deploy gate" in q and q.startswith("# Morning Review Queue")


def test_save_cursor_is_structure_preserving():
    st = _state()
    with tempfile.TemporaryDirectory() as d:
        base, _ = _sdlc(d); st.save_cursor(base, 3, 1, "2 done")
        txt = (pathlib.Path(base) / "state" / "STATE.md").read_text()
        assert "iteration: 3" in txt and "run_iteration: 1" in txt
        assert "Do not hand-edit" in txt and "## Items" in txt        # guard + structure survive


def test_start_run_resets_run_iteration_only():
    st = _state()
    with tempfile.TemporaryDirectory() as d:
        base, _ = _sdlc(d); st.save_cursor(base, 5, 9, "x"); st.start_run(base)
        cur = st.load_cursor(base)
        assert cur["run_iteration"] == 0 and cur["iteration"] == 5   # cursor preserved


def test_set_line_value_with_backslash_is_literal():
    # the summary flows from a goal filename; backslash-escapes must stay literal,
    # not be treated as re.sub replacement backreferences (re.error / corruption).
    st = _state()
    out = st._set_line("last_run: none\n", "last_run", r"done g\1")
    assert "last_run: done g\\1" in out

def test_state_and_queue_scaffold_themselves_on_a_fresh_clone(tmp_path):
    """Regression: `.sdlc/state/` is gitignored by design, so a teammate cloning an ADOPTED repo has
    config + goals but no state files — and every entry point died on FileNotFoundError before their
    first goal. Found by a two-clone e2e; unit tests all pre-created the files."""
    s = _state()
    d = tmp_path / ".sdlc"
    (d / "goals").mkdir(parents=True)                    # note: no state/ directory at all
    goal = d / "goals" / "0001.md"
    goal.write_text("---\nstatus: pending\n---\nx\n")

    assert s.load_cursor(str(d)) == {"iteration": 0, "run_iteration": 0,
                                     "run_started_at": 0, "run_tokens": 0}
    s.start_run(str(d))
    s.save_cursor(str(d), 1, 1, "last: 0001.md -> done")
    assert s.load_cursor(str(d))["iteration"] == 1
    assert "# Loop State" in (d / "state" / "STATE.md").read_text()

    s.park(str(d), str(goal), "needs a decision")        # queue absent too
    queue = (d / "state" / "review-queue.md").read_text()
    assert "# Morning Review Queue" in queue and "- needs: human review" in queue

