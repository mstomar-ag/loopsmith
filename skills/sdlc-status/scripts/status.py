"""Read-only backlog status: counts by goal status + run cursor + queue state. Zero-dep.
(A 3-line frontmatter read is duplicated from sdlc-loop's frontmatter.py on purpose — the two
skills are independently installable units; sharing a lib across them would over-couple them.)"""
import sys, pathlib, re

_FENCE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def _status_of(text):
    m = _FENCE.match(text)
    if not m:
        return None
    s = re.search(r"^status:\s*(\S+)", m.group(1), re.MULTILINE)
    return s.group(1).strip('"') if s else None        # parity with frontmatter.parse (strips quotes)


def summary(sdlc_dir):
    base = pathlib.Path(sdlc_dir)
    counts = {"pending": 0, "in_progress": 0, "done": 0, "parked": 0, "failed": 0, "proposed": 0}
    for p in sorted((base / "goals").glob("*.md")):
        s = _status_of(p.read_text())
        if s in counts:
            counts[s] += 1
    cur = base / "state" / "STATE.md"
    it = 0
    if cur.exists():
        m = re.search(r"^iteration:\s*(\d+)", cur.read_text(), re.MULTILINE)
        it = int(m.group(1)) if m else 0
    q = base / "state" / "review-queue.md"
    queue_nonempty = bool(q.exists() and re.search(r"^## ", q.read_text(), re.MULTILINE))
    return {**counts, "iteration": it, "queue_nonempty": queue_nonempty,
            "ledger_entries": _ledger_entries(base)}


def _ledger_entries(base):
    """Ledger lines across every author's file. Zero when the ledger is off or absent, which
    keeps the status line byte-identical for a repo that has not opted in."""
    total = 0
    entries = base / "ledger" / "entries"
    if not entries.exists():
        return 0
    for path in sorted(entries.glob("*.jsonl")):
        try:
            total += sum(1 for line in path.read_text().splitlines() if line.strip())
        except OSError:
            continue
    return total


def main(argv):
    s = summary(argv[1] if len(argv) > 1 else ".sdlc")
    line = (f"backlog: {s['proposed']} proposed, {s['pending']} pending, {s['in_progress']} in-progress, "
            f"{s['done']} done, {s['parked']} parked, {s['failed']} failed | "
            f"iteration {s['iteration']} | "
            f"review-queue: {'NEEDS ATTENTION' if s['queue_nonempty'] else 'empty'}")
    if s["ledger_entries"]:                    # silent when the ledger is off: same line as before
        line += f" | ledger: {s['ledger_entries']} entries"
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
