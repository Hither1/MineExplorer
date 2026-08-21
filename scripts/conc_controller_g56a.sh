#!/usr/bin/env bash
# Adaptive concurrency for the g56a default arm. Writes the cap to
# outputs/g56a-conc.txt every 120s; launch_4hop.sh (CONC_FILE mode) re-reads it at
# each launch gate. Lowering never kills running cells -- new launches just wait.
#
#   down 2 (floor 4): a219 load1>230, or api-failure lines grew >10 this tick,
#                     or a219 java count > cap+14 (active + leaked headroom)
#   up 1 (ceil 10):   three consecutive ticks with a219 load<190 and zero new
#                     api failures
# Exits when the default arm reaches 154/154 or its launcher is gone.
set -uo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
F=outputs/g56a-conc.txt
LOG=outputs/log-g56a-conc.txt
A219=192.168.2.12
[[ -s "$F" ]] || echo 8 > "$F"
healthy=0; prev_fails=-1
log() { echo "$(date '+%m-%d %H:%M:%S') $*" >> "$LOG"; }
log "controller up, cap=$(cat $F)"
while true; do
  sleep 120
  nd=0
  for s in $(ls bench_4hop154/_split); do
    [[ -f "outputs/g56a-default-codex-$s/gpt-5.6-sol/4-hop/$s/result.json" ]] && nd=$((nd+1))
  done
  (( nd >= 154 )) && { log "arm complete, exiting"; exit 0; }
  stats=$(ssh -o BatchMode=yes -o ConnectTimeout=10 "ruihan@$A219" \
    'echo "$(cut -d" " -f1 /proc/loadavg) $(pgrep -cu ruihan java || true)"' 2>/dev/null) || { log "a219 ssh fail, holding"; continue; }
  read -r load9 java9 <<< "$stats"
  fails=$(cat outputs/log-g56a-default-codex-*.txt 2>/dev/null | grep -cE "produced no actions.json|Agent failed to provide|stream disconnected|429|rate.?limit" || true)
  dfail=0; (( prev_fails >= 0 )) && dfail=$((fails - prev_fails)); prev_fails=$fails
  cap=$(cat "$F" 2>/dev/null | tr -d '[:space:]'); [[ "$cap" =~ ^[0-9]+$ ]] || cap=8
  new=$cap
  if awk -v l="$load9" 'BEGIN{exit !(l>230)}' || (( dfail > 10 )) || (( java9 > cap + 14 )); then
    new=$(( cap > 6 ? cap - 2 : 4 )); healthy=0
  elif awk -v l="$load9" 'BEGIN{exit !(l<190)}' && (( dfail == 0 )); then
    healthy=$((healthy+1))
    (( healthy >= 3 && cap < 10 )) && { new=$((cap+1)); healthy=0; }
  else
    healthy=0
  fi
  if (( new != cap )); then echo "$new" > "$F"; log "cap $cap -> $new (load=$load9 java=$java9 dfail=$dfail)"; fi
done
