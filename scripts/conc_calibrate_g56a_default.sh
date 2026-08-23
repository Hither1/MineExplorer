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
MIN=2; MAX=6   # 6 measured clean for an hour on 08-23; 7 burned twice (30/33 timeouts per window)
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
    # The causal variable is concurrent CELLS, not the cap: the cap only gates
    # new launches, so after a burn the excess cells would otherwise keep
    # burning ~30 timeouts per window for the hours they take to drain
    # (measured 10:25-10:42). Ratchet below the burning cell count and trim
    # the youngest cells (least sunk work; their scenes rerun in the mop-up).
    clean=0; MAX=$((cells - 1)); (( MAX < MIN )) && MAX=$MIN
    cap=$MAX; (( cap < MIN )) && cap=$MIN
    echo "$cap" > "$CONC_FILE"
    while (( cells > MAX )); do
      young=$(for pid in $(pgrep -u ruihan -f "eval_benchmar[k]"); do
        cmd=$(tr "\0" " " < /proc/$pid/cmdline 2>/dev/null)
        [[ "$cmd" == *g56a-default-codex* ]] || continue
        et=$(ps -o etimes= -p "$pid" 2>/dev/null | tr -d " "); echo "${et:-0} $pid $cmd"
      done | sort -n | head -1)
      [[ -z "$young" ]] && break
      ypid=$(echo "$young" | awk "{print \$2}")
      yscene=$(echo "$young" | grep -oE "_split/[0-9]+" | cut -d/ -f2)
      kill "$ypid" 2>/dev/null
      echo "$(date '+%m-%d %H:%M:%S') trimmed cell $yscene (pid $ypid, youngest) to enforce cells<=$MAX" >> "$LOG"
      cells=$((cells-1)); sleep 2
    done
  elif (( dto >= 4 )); then
    # Sustained dirt (>=~7% of the window's calls): step down one.
    clean=0
    (( cap > MIN )) && { cap=$((cap-1)); echo "$cap" > "$CONC_FILE"; }
  else
    # dto 1-3 is the protocol's tolerated trickle (c4h defines a ceiling hit as
    # "one ceiling then a default action"). Climb is slow and earns back the
    # ratchet one level per 2h of fully-clean windows, ceiling 6: the morning's
    # "5-6 clean" was ramp-in optimism (cells at early steps carry few frames),
    # so capacity is a function of how many FULL-WINDOW cells run and the honest
    # steady-state sits near 4-5; asymmetric control (instant down, 2h up) probes
    # that boundary at ~one bad window per 2h worst case.
    clean=$((clean+1))
    if (( clean >= 12 && cap < 6 )); then
      cap=$((cap+1)); (( MAX < cap )) && MAX=$cap
      echo "$cap" > "$CONC_FILE"; clean=0
    fi
  fi
  echo "$(date '+%m-%d %H:%M:%S') tick cap=$cap max=$MAX cells=$cells new_timeouts=$dto clean_windows=$clean" >> "$LOG"
  n=0; for s in $(ls bench_4hop154/_split); do [[ -f "outputs/g56a-default-codex-$s/gpt-5.6-sol/4-hop/$s/result.json" ]] && n=$((n+1)); done
  (( n >= 154 )) && { echo "$(date '+%m-%d %H:%M:%S') arm complete ($n/154)" >> "$LOG"; exit 0; }
done
