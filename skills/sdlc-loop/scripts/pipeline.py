"""Bidirectional pipeline report card (zero-dep, deterministic, $0).

A project may declare its delivery pipeline in `.sdlc/pipeline.json` — ordered
stages, the artifacts each produces, and the checks that hold on each stage:

    {"stages": [
       {"name": "extract",   "produces": ["data/raw/*.json"],
        "checks": {"forward": [{"name": "raw is valid", "run": "sh checks/raw.sh"}]}},
       {"name": "transform", "produces": ["data/out/*.json"],
        "checks": {"forward": [...],
                   "reverse": [{"name": "every output row traces to a raw row",
                                "run": "sh checks/trace.sh"}]}}]}

Two directions per stage, one card for the whole pipeline:
- FORWARD  = survivorship — the stage produced what it promised and its forward
  checks hold ("nothing dropped").
- REVERSE  = provenance — the stage's declared reverse checks hold against its
  UPSTREAM stage ("nothing invented; upstream honored"). Reverse findings
  localize a fault to the edge between two stages instead of a downstream symptom.

Honesty rule: a lane with NO declared instrument reads ABSENT — never PASS.
Check contract: a check is any command; exit 0 = PASS, exit 2 = WARN, any other
exit = FAIL. Deterministic commands only — the card itself never calls a network
or an LLM, and it NEVER gates the run it examines (it reports; the loop decides).

    python3 pipeline.py card .sdlc [--json out.json] [--compare prior.json]

`--compare` diffs a prior card signal-by-signal: regressed / improved /
still-failing (still-failing across runs is the recurrence signal — systemic,
not incidental; feed it to the backlog, not to a one-off fix).
"""
import glob, json, pathlib, subprocess, sys

PASS, WARN, FAIL, ABSENT = "PASS", "WARN", "FAIL", "ABSENT"
_ORDER = {PASS: 0, ABSENT: 1, WARN: 2, FAIL: 3}
_CHECK_TIMEOUT_SECS = 300           # one hung check must not hang the card


def load_pipeline(sdlc_dir):
    p = pathlib.Path(sdlc_dir) / "pipeline.json"
    if not p.exists():
        return None
    spec = json.loads(p.read_text())
    return spec if isinstance(spec.get("stages"), list) else None


def _run_check(check, cwd):
    """(status, detail) for one declared check command."""
    try:
        proc = subprocess.run(check.get("run", ""), shell=True, cwd=cwd,
                              capture_output=True, text=True, timeout=_CHECK_TIMEOUT_SECS)
    except subprocess.TimeoutExpired:
        return FAIL, f"timed out after {_CHECK_TIMEOUT_SECS}s"
    status = PASS if proc.returncode == 0 else (WARN if proc.returncode == 2 else FAIL)
    tail = (proc.stdout + proc.stderr).strip().splitlines()
    return status, (tail[-1][:200] if tail else f"exit {proc.returncode}")


def build_card(sdlc_dir, repo_root=None):
    """The card as plain data. repo_root is where produces-globs and checks resolve
    (defaults to the parent of .sdlc — the project root)."""
    root = str(repo_root or pathlib.Path(sdlc_dir).resolve().parent)
    spec = load_pipeline(sdlc_dir)
    if spec is None:
        return None
    stages = []
    for i, stage in enumerate(spec["stages"]):
        signals = []
        produces = stage.get("produces") or []
        if produces:
            missing = [g for g in produces if not glob.glob(str(pathlib.Path(root) / g))]
            signals.append({"direction": "forward", "name": "declared artifacts present",
                            "status": FAIL if missing else PASS,
                            "detail": f"missing: {missing}" if missing else f"{len(produces)} glob(s) satisfied"})
        checks = stage.get("checks") or {}
        for direction in ("forward", "reverse"):
            declared = checks.get(direction) or []
            for check in declared:
                status, detail = _run_check(check, root)
                signals.append({"direction": direction, "name": check.get("name", check.get("run", "check")),
                                "status": status, "detail": detail})
            if not declared and not (direction == "forward" and produces):
                # Honest absence: an uninstrumented lane must never read as green.
                # (Stage 0 has no upstream, so its reverse lane is legitimately n/a.)
                if direction == "reverse" and i == 0:
                    continue
                signals.append({"direction": direction, "name": f"{direction} instrumentation",
                                "status": ABSENT, "detail": "no declared checks for this lane"})
        stages.append({"stage": stage.get("name", f"stage-{i}"), "signals": signals})
    return {"pipeline": spec.get("name", "pipeline"), "stages": stages,
            "gating": "none — diagnostic report; never gates the run it examines",
            "verdict": _verdict(stages)}


def _verdict(stages):
    failing = [s["stage"] for s in stages
               if any(x["status"] == FAIL for x in s["signals"])]
    blocked = [{"stage": s["stage"], "direction": x["direction"], "reason": x["detail"]}
               for s in stages for x in s["signals"] if x["status"] == ABSENT]
    actions = ([{"action": "declare_checks", "stage": b["stage"], "direction": b["direction"]}
                for b in blocked]
               + [{"action": "fix_stage", "stage": name} for name in failing])
    worst = PASS
    for s in stages:
        for x in s["signals"]:
            if _ORDER[x["status"]] > _ORDER[worst]:
                worst = x["status"]
    return {"overall": worst,
            "done_when": "no FAIL signals and no ABSENT lanes across all stages",
            "clean": worst in (PASS, WARN) and not blocked,
            "failing_stages": failing, "blocked_lanes": blocked, "next_actions": actions}


def compare_cards(prior, current):
    """Signal-level diff of two card payloads: regressed / improved / still_failing.
    still_failing (FAIL in both) is the recurrence signal — a systemic issue, not an
    incident. Measured in cards, not wall-clock."""
    def index(card):
        return {(s["stage"], x["direction"], x["name"]): x["status"]
                for s in card.get("stages", []) for x in s.get("signals", [])}
    prior_ix, current_ix = index(prior), index(current)
    delta = {"regressed": [], "improved": [], "still_failing": []}
    for key, now in sorted(current_ix.items()):
        before = prior_ix.get(key)
        if before is None:
            continue                       # newly-instrumented lane: no epoch verdict yet
        row = {"stage": key[0], "direction": key[1], "signal": key[2],
               "before": before, "now": now}
        if now == FAIL and before == FAIL:
            delta["still_failing"].append(row)
        elif _ORDER.get(now, 1) > _ORDER.get(before, 1):
            delta["regressed"].append(row)
        elif _ORDER.get(now, 1) < _ORDER.get(before, 1):
            delta["improved"].append(row)
    delta["recurrence_count"] = len(delta["still_failing"])
    return delta


def render(card, delta=None):
    icon = {PASS: "+", WARN: "!", FAIL: "x", ABSENT: "·"}
    lines = [f"# Pipeline report card — {card['pipeline']}", card["gating"], ""]
    for s in card["stages"]:
        worst = PASS
        for x in s["signals"]:
            if _ORDER[x["status"]] > _ORDER[worst]:
                worst = x["status"]
        lines.append(f"## {s['stage']}  [{worst}]")
        for x in s["signals"]:
            lines.append(f"  {icon[x['status']]} {x['direction']:<7} {x['name']}: "
                         f"{x['status']} — {x['detail']}")
        lines.append("")
    v = card["verdict"]
    lines.append(f"verdict: {v['overall']} · failing={v['failing_stages'] or 'none'} · "
                 f"blocked lanes={len(v['blocked_lanes'])}")
    if delta is not None:
        lines.append(f"delta: regressed={len(delta['regressed'])} improved={len(delta['improved'])} "
                     f"still-failing (recurrence)={delta['recurrence_count']}")
        for row in delta["regressed"]:
            lines.append(f"  REGRESSED [{row['stage']}/{row['direction']}] {row['signal']}: "
                         f"{row['before']} -> {row['now']}")
        for row in delta["still_failing"]:
            lines.append(f"  STILL FAILING [{row['stage']}/{row['direction']}] {row['signal']}")
    return "\n".join(lines)


def main(argv):
    if len(argv) >= 3 and argv[1] == "card":
        card = build_card(argv[2])
        if card is None:
            print("NO-PIPELINE (declare .sdlc/pipeline.json to use the report card)", file=sys.stderr)
            return 3
        delta = None
        if "--compare" in argv:
            prior_path = pathlib.Path(argv[argv.index("--compare") + 1])
            if not prior_path.exists():
                print(f"SKIP: {prior_path} not found", file=sys.stderr)
                return 3
            delta = compare_cards(json.loads(prior_path.read_text()), card)
            card["delta"] = delta
        print(render(card, delta))
        if "--json" in argv:
            out = pathlib.Path(argv[argv.index("--json") + 1])
            out.write_text(json.dumps(card, indent=2))
            print(f"wrote {out}")
        return 0 if not card["verdict"]["failing_stages"] else 1
    print("usage: pipeline.py card <sdlc_dir> [--json out.json] [--compare prior.json]",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
