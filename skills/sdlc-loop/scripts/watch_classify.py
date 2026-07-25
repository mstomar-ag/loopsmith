#!/usr/bin/env python3
"""Decide what, out of the whole team ledger, actually needs THIS person — and only say it once.

Pure: no I/O, no git, no clock. The shell wrapper does the fetching and the file writing, this
decides. Same split as the supervisor's classifier, and for the same reason — the interesting logic
is the judgement, and judgement you cannot unit-test will drift.

Two independent suppressions, because they catch different mistakes:

  * the **cursor** (`{actor: highest seq seen}`) stops re-reading history on every tick;
  * the **signature** (`kind:issue:state`) stops the same mention firing again when a colleague's
    file is rewritten, rebased, or replayed — the cursor alone would re-fire all of it.

A *state change* is deliberately not suppressed: `open` -> `deferred` on the same issue is news.
"""
import json
import pathlib

PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}
EMPTY_CURSOR = {"seen": {}, "signatures": []}


def load_cursor(path):
    try:
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(EMPTY_CURSOR)
    return {"seen": data.get("seen") or {}, "signatures": list(data.get("signatures") or [])}


def save_cursor(path, cursor):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cursor, indent=2, sort_keys=True), encoding="utf-8")


def _seq(entry):
    tail = str(entry.get("id", "")).rsplit(":", 1)[-1]
    return int(tail) if tail.isdigit() else 0


def signature(entry):
    return f"{entry.get('kind')}:{entry.get('issue') or entry.get('goal')}:{entry.get('state') or ''}"


def rank(entry):
    """Most urgent first; ties broken oldest-first so nothing starves behind a busy colleague."""
    return (PRIORITY_ORDER.get(entry.get("priority"), 9), entry.get("ts", ""))


def classify(entries, cursor, me):
    """-> (items needing me, updated cursor). Never returns my own entries: a loop must not be
    woken by its own writes."""
    baseline = dict(cursor.get("seen") or {})       # frozen: what earlier ticks already processed
    signatures = set(cursor.get("signatures") or [])
    seen, items = dict(baseline), []
    for entry in entries:
        actor, seq = entry.get("actor", ""), _seq(entry)
        seen[actor] = max(seen.get(actor, 0), seq)
        if actor == me or entry.get("to") != me:
            continue
        if seq <= baseline.get(actor, 0):
            continue                                # an earlier tick already surfaced this
        sig = signature(entry)
        if sig in signatures:
            continue                                # replayed after a rebase — same news, not new
        signatures.add(sig)
        items.append(entry)
    items.sort(key=rank)
    return items, {"seen": seen, "signatures": sorted(signatures)}


def render_inbox(items, me):
    """The file the loop reads between goals. Written for a reader with no context: who, what, how
    urgent, and the one command that answers it."""
    if not items:
        return ""
    lines = [f"# Inbox — {me}", "",
             f"{len(items)} item{'s' if len(items) != 1 else ''} from the team ledger need you.",
             "Answer each with `handoff.py ack .sdlc --issue <n> --state "
             "accepted|deferred|declined|resolved [--why ...]`.", ""]
    for entry in items:
        priority = entry.get("priority", "-")
        issue = entry.get("issue")
        lines += [
            f"## {priority} · from {entry.get('actor', '?')}"
            + (f" · issue #{issue}" if issue else ""),
            f"- **needs:** {entry.get('why') or entry.get('goal', '')}",
            f"- **area:** {entry.get('area', '-')}  ·  **raised:** {entry.get('ts', '-')}"
            + (f"  ·  **their goal:** {entry.get('goal')}" if entry.get("goal") else ""),
            "",
        ]
    return "\n".join(lines)


def summarise(items):
    if not items:
        return ""
    top = items[0]
    return (f"{len(items)} ledger item(s) need you — most urgent "
            f"{top.get('priority', '-')} from {top.get('actor', '?')}"
            + (f" (#{top['issue']})" if top.get("issue") else ""))
