"""Exit-classifier for the overnight supervisor (zero-dep, pure, hermetically testable).

Reads the TAIL of a finished loop session's output and decides what the supervisor
does next. Four verdicts:
  done     — the loop's own success stop ("backlog-empty" / its stop report): exit.
  relaunch — a per-run budget stop: budgets reset per invocation BY DESIGN, so
             relaunch after a short fixed pause (the pause + the supervisor's
             max-runs cap prevent a hot ping-pong on a non-progressing backlog).
  sleep    — usage-limit exhaustion WITH a parseable reset time: sleep until
             reset + jitter, then relaunch (the 12:00 -> 3:00 -> 5:30 scenario).
  backoff  — usage-limit without a parseable time, or an unknown crash: capped
             escalating waits (cheap retries, never a hot loop, no permanent stop
             until the supervisor's max-runs cap).

The classifier never talks to any API and adds zero LLM calls — it reads text.
"""
import random, re, sys, time

_DONE = re.compile(r"backlog[- ]empty|backlog is empty|\d+ done, \d+ parked", re.I)
_BUDGET = re.compile(r"\bBUDGET\b|stopped.{0,12}budget|budget (cap|stop|hit|reached)", re.I)
_LIMIT = re.compile(r"(usage|rate).{0,3}limit|limit (reached|exhausted|hit)|out of (usage|quota)|"
                    r"hit your.{0,12}limit|quota exceeded", re.I)
_RESET_AT = re.compile(r"reset[s]?\s*(?:at\s*)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", re.I)

_BUDGET_PAUSE = 60
_LIMIT_FALLBACK = [1800, 3600, 3600, 3600]      # unparseable limit: retry cheaply, capped waits
_CRASH_BACKOFF = [300, 600, 1200, 3600]         # unknown crash: escalate, cap at 1h
_JITTER = (120, 300)                            # never thunder exactly on the reset minute


def _seconds_until(hour, minute, ampm, now):
    """Seconds from `now` (epoch) to the NEXT local occurrence of hour:minute."""
    lt = time.localtime(now)
    h = hour % 12 + (12 if (ampm or "").lower() == "pm" else 0) if ampm else hour
    target = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, h, minute, 0,
                          lt.tm_wday, lt.tm_yday, -1))
    if target <= now:
        target += 24 * 3600
    return int(target - now)


def classify(tail_text, attempt=0, now=None, rng=None):
    """(action, sleep_seconds, reason). `now`/`rng` are injectable for tests."""
    now = time.time() if now is None else now
    jitter = (rng or random).randint(*_JITTER)
    text = tail_text or ""
    if _DONE.search(text):
        return ("done", 0, "the loop reported its own success stop")
    if _LIMIT.search(text):
        m = _RESET_AT.search(text)
        if m:
            secs = _seconds_until(int(m.group(1)), int(m.group(2) or 0), m.group(3), now)
            return ("sleep", secs + jitter, f"usage limit — resuming after the stated reset (+{jitter}s jitter)")
        wait = _LIMIT_FALLBACK[min(attempt, len(_LIMIT_FALLBACK) - 1)]
        return ("backoff", wait, "usage limit with no parseable reset time — capped retry")
    if _BUDGET.search(text):
        return ("relaunch", _BUDGET_PAUSE, "per-run budget stop — budgets reset on relaunch by design")
    wait = _CRASH_BACKOFF[min(attempt, len(_CRASH_BACKOFF) - 1)]
    return ("backoff", wait, "unclassified exit — escalating backoff")


def main(argv):
    if len(argv) < 2:
        print("usage: supervise_classify.py <tail-file> [attempt]", file=sys.stderr)
        return 2
    try:
        text = open(argv[1], encoding="utf-8", errors="ignore").read()
    except OSError:
        text = ""
    action, secs, reason = classify(text, int(argv[2]) if len(argv) > 2 else 0)
    print(f"action={action} sleep={secs} reason={reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
