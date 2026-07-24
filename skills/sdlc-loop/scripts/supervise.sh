#!/usr/bin/env bash
# Overnight supervisor — OWNS the loop's lifetime so limit exhaustion never means
# permanent downtime, with ZERO polling: this process is blocked (0 CPU) while the
# session runs and asleep otherwise. On each session exit the classifier reads the
# output tail and picks: done -> exit · budget -> short pause + relaunch ·
# usage-limit -> sleep until the stated reset (+jitter) -> relaunch · unknown ->
# capped escalating backoff. Stop it any time: touch <sdlc>/state/supervisor.stop
# macOS laptop note: a sleeping MACHINE stops everything — run under `caffeinate -is`
# (or keep the device on AC with sleep off); OS one-shot wake timers are the
# hardened alternative for sleep-prone machines.
#   supervise.sh [sdlc_dir]      (default .sdlc)
# Env: LOOPSMITH_CLAUDE_CMD  — the session command (default: claude -p /sdlc-loop);
#      LOOPSMITH_SUPERVISE_MAX_RUNS — total session launches before giving up (48);
#      LOOPSMITH_SUPERVISE_SLEEP_SCALE — multiply waits (tests set 0; default 1).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SDLC_DIR="${1:-.sdlc}"
STATE="$SDLC_DIR/state"
LOG="$STATE/supervisor.log"; TAILF="$STATE/supervisor.tail"; STOPF="$STATE/supervisor.stop"
CMD="${LOOPSMITH_CLAUDE_CMD:-claude -p /sdlc-loop}"
MAX_RUNS="${LOOPSMITH_SUPERVISE_MAX_RUNS:-48}"
SCALE="${LOOPSMITH_SUPERVISE_SLEEP_SCALE:-1}"
mkdir -p "$STATE"
attempt=0; runs=0
while :; do
  [ -f "$STOPF" ] && { echo "supervisor: stop-file present — exiting" | tee -a "$LOG"; exit 0; }
  if [ "$runs" -ge "$MAX_RUNS" ]; then
    echo "supervisor: max runs ($MAX_RUNS) reached — exiting" | tee -a "$LOG"; exit 1
  fi
  runs=$((runs + 1))
  echo "supervisor: run #$runs — $(date)" >> "$LOG"
  # Per-run capture: classify THIS session's output only — a cumulative-log tail
  # could bleed a previous run's stop text into the verdict.
  RUNOUT="$STATE/supervisor.run.out"
  # shellcheck disable=SC2086 — CMD is deliberately word-split (a command line)
  $CMD > "$RUNOUT" 2>&1
  cat "$RUNOUT" >> "$LOG" 2>/dev/null || true
  tail -n 50 "$RUNOUT" > "$TAILF" 2>/dev/null || : > "$TAILF"
  verdict="$(python3 "$HERE/supervise_classify.py" "$TAILF" "$attempt" 2>/dev/null \
             || echo 'action=backoff sleep=1800 reason=classifier unavailable')"
  action="${verdict#action=}"; action="${action%% *}"
  secs="$(printf '%s' "$verdict" | sed -n 's/.*sleep=\([0-9]*\).*/\1/p')"
  echo "supervisor: $verdict" | tee -a "$LOG"
  case "$action" in
    done) exit 0 ;;
    relaunch) attempt=0 ;;
    sleep) attempt=0 ;;
    *) attempt=$((attempt + 1)) ;;
  esac
  sleep_for=$(( ${secs:-1800} * SCALE ))
  [ "$sleep_for" -gt 0 ] && sleep "$sleep_for"
done
