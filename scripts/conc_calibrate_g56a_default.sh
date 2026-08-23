#!/usr/bin/env bash
# Timeout-driven concurrency calibration for the g56a default arm (hosted).
# CONC=8 was measured unworkable (2026-08-23: with 20-frame windows full, 100% of
# calls hit the 240s ceiling and every step no-opped); a single cell is known
# good (the 08-16 axis run, 400 calls, 0 timeouts). This walks the cap between
# those bounds on live evidence: any new provider timeout in a 10-minute window
# lowers the cap, two consecutive clean windows raise it. Writes the cap to
# $CONC_FILE for launch_4hop.sh's cur_conc().
set -uo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
CONC_FILE=${CONC_FILE:-outputs/g56a-conc-default.txt}
LOG=outputs/log-g56a-conc-default.txt
MIN=2; MAX=8
cap=$(cat "$CONC_FILE" 2>/dev/null | tr -d '[:space:]'); [[ "$cap" =~ ^[0-9]+$ ]] || cap=4
echo "$cap" > "$CONC_FILE"
prev_to=-1; clean=0
while true; do
  to=$(grep -c "timed out after 240" outputs/log-g56a-default-codex-*.txt 2>/dev/null | awk -F: '{s+=$2} END {print s+0}')
  cells=$(pgrep -u ruihan -f "eval_benchmar[k]" | while read -r p; do tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null; echo; done | grep -c "g56a-default-codex" || true)
  dto=0; (( prev_to >= 0 )) && dto=$((to - prev_to)); prev_to=$to
  if (( dto > 0 )); then
    clean=0
    (( cap > MIN )) && { cap=$((cap-1)); echo "$cap" > "$CONC_FILE"; }
  else
    clean=$((clean+1))
    if (( clean >= 2 && cap < MAX && cells >= cap )); then
      cap=$((cap+1)); echo "$cap" > "$CONC_FILE"; clean=0
    fi
  fi
  echo "$(date '+%m-%d %H:%M:%S') tick cap=$cap cells=$cells new_timeouts=$dto clean_windows=$clean" >> "$LOG"
  n=0; for s in $(ls bench_4hop154/_split); do [[ -f "outputs/g56a-default-codex-$s/gpt-5.6-sol/4-hop/$s/result.json" ]] && n=$((n+1)); done
  (( n >= 154 )) && { echo "$(date '+%m-%d %H:%M:%S') arm complete ($n/154)" >> "$LOG"; exit 0; }
  sleep 600
done
