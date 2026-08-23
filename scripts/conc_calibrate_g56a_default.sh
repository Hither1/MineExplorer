#!/usr/bin/env bash
# Timeout-driven concurrency calibration for the g56a default arm (hosted).
# CONC=8 was measured unworkable (2026-08-23: with 20-frame windows full, 100% of
# calls hit the 240s ceiling); a single cell is known good (08-16 axis run, 400
# calls, 0 timeouts); the first calibration pass found 5-6 clean and 7 burning
# (30 timeouts in one 10-min window, spread across every active cell).
#
# Timeout deltas are counted PER FILE and only as increases: the launcher
# truncates a scene's old log when it relaunches it, and a raw aggregate count
# swallowed a real +30 inside a -72 truncation on the first pass.
# The cap climbs only after 6 consecutive clean windows (1h), drops 2 on a
# spike (>=10), and a burned level is never climbed back to (ratchet): capacity
# here is an account-level fact that varies slowly, and re-probing a level that
# just burned costs ~30 wasted 240s calls and as many no-op steps per probe.
set -uo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
CONC_FILE=${CONC_FILE:-outputs/g56a-conc-default.txt}
LOG=outputs/log-g56a-conc-default.txt
STATE=outputs/.conc-calib-state
MIN=2; MAX=8
mkdir -p "$STATE"
cap=$(cat "$CONC_FILE" 2>/dev/null | tr -d '[:space:]'); [[ "$cap" =~ ^[0-9]+$ ]] || cap=4
echo "$cap" > "$CONC_FILE"
clean=0
count_new() {  # sum of per-file increases since last tick
  local total=0 f cur prev key
  for f in outputs/log-g56a-default-codex-*.txt; do
    [[ -f "$f" ]] || continue
    cur=$(grep -c "timed out after 240" "$f" 2>/dev/null) || cur=0
    key="$STATE/$(basename "$f")"
    prev=$(cat "$key" 2>/dev/null); [[ "$prev" =~ ^[0-9]+$ ]] || prev=$cur
    (( cur > prev )) && total=$((total + cur - prev))
    echo "$cur" > "$key"
  done
  echo "$total"
}
count_new > /dev/null   # seed baselines without acting
while true; do
  sleep 600
  dto=$(count_new)
  cells=$(pgrep -u ruihan -f "eval_benchmar[k]" | while read -r p; do tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null; echo; done | grep -c "g56a-default-codex" || true)
  if (( dto >= 10 )); then
    clean=0; MAX=$((cap - 1)); (( MAX < MIN )) && MAX=$MIN
    cap=$((cap - 2)); (( cap < MIN )) && cap=$MIN
    echo "$cap" > "$CONC_FILE"
  elif (( dto > 0 )); then
    clean=0
    (( cap > MIN )) && { cap=$((cap-1)); echo "$cap" > "$CONC_FILE"; }
  else
    clean=$((clean+1))
    if (( clean >= 6 && cap < MAX && cells >= cap )); then
      cap=$((cap+1)); echo "$cap" > "$CONC_FILE"; clean=0
    fi
  fi
  echo "$(date '+%m-%d %H:%M:%S') tick cap=$cap max=$MAX cells=$cells new_timeouts=$dto clean_windows=$clean" >> "$LOG"
  n=0; for s in $(ls bench_4hop154/_split); do [[ -f "outputs/g56a-default-codex-$s/gpt-5.6-sol/4-hop/$s/result.json" ]] && n=$((n+1)); done
  (( n >= 154 )) && { echo "$(date '+%m-%d %H:%M:%S') arm complete ($n/154)" >> "$LOG"; exit 0; }
done
