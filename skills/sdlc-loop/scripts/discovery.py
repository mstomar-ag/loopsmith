"""Local-goals backlog discovery (the file source). Source selection lives in sources.py, which also
implements the GitHub-issues source; this module is the zero-dep local-files adapter."""
import pathlib, importlib.util

_HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("frontmatter", _HERE / "frontmatter.py")
frontmatter = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(frontmatter)

_TERMINAL = {"done", "parked", "failed"}
# proposed = detector-suggested, awaiting HUMAN promotion (edit status -> pending).
# Not terminal, but never auto-picked: proposing work is safe, running it is gated.
_SKIP = _TERMINAL | {"proposed"}


def next_pending(goals_dir):
    """First *.md goal (filename order) whose status is not done/parked/failed/proposed. None if none.
    Files without frontmatter (e.g. README.md) are not goals."""
    for path in sorted(pathlib.Path(goals_dir).glob("*.md")):
        status = frontmatter.get(path.read_text(), "status")
        if status is not None and status not in _SKIP:
            return str(path)
    return None
