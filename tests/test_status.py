import pathlib, importlib.util, tempfile

S = pathlib.Path(__file__).resolve().parent.parent / "skills" / "sdlc-status" / "scripts"


def _status():
    spec = importlib.util.spec_from_file_location("status", S / "status.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def test_summary_counts_by_status():
    with tempfile.TemporaryDirectory() as d:
        base = pathlib.Path(d) / ".sdlc"; (base / "goals").mkdir(parents=True); (base / "state").mkdir()
        (base / "state" / "STATE.md").write_text("iteration: 4\n")
        for n, s in [("0001", "done"), ("0002", "parked"), ("0003", "pending")]:
            (base / "goals" / f"{n}.md").write_text(f"---\nid: {n}\nstatus: {s}\n---\nx\n")
        out = _status().summary(str(base))
        assert out["done"] == 1 and out["parked"] == 1 and out["pending"] == 1 and out["iteration"] == 4


def test_summary_counts_quoted_status():   # parity with frontmatter.parse (strips quotes)
    with tempfile.TemporaryDirectory() as d:
        base = pathlib.Path(d) / ".sdlc"; (base / "goals").mkdir(parents=True); (base / "state").mkdir()
        (base / "goals" / "0001.md").write_text('---\nid: 0001\nstatus: "done"\n---\nx\n')
        assert _status().summary(str(base))["done"] == 1


def _bare(d):
    base = pathlib.Path(d) / ".sdlc"; (base / "goals").mkdir(parents=True); (base / "state").mkdir()
    return base


def test_ledger_count_is_zero_and_silent_when_absent(capsys):
    with tempfile.TemporaryDirectory() as d:
        base = _bare(d)
        assert _status().summary(str(base))["ledger_entries"] == 0
        _status().main(["status.py", str(base)])
        assert "ledger:" not in capsys.readouterr().out      # same line as before, for a repo without one


def test_ledger_count_unions_every_author_and_shows_in_the_line(capsys):
    with tempfile.TemporaryDirectory() as d:
        base = _bare(d)
        entries = base / "ledger" / "entries"; entries.mkdir(parents=True)
        (entries / "amy.jsonl").write_text('{"kind":"done"}\n\n{"kind":"parked"}\n')
        (entries / "bo.jsonl").write_text('{"kind":"note"}\n')
        assert _status().summary(str(base))["ledger_entries"] == 3     # blank line not counted
        _status().main(["status.py", str(base)])
        assert "ledger: 3 entries" in capsys.readouterr().out
