#!/usr/bin/env bash
# Adaptive concurrency for the g56a default arm. Writes the cap to
# outputs/g56a-conc.txt every 120s; launch_4hop.sh (CONC_FILE mode) re-reads it at
# each launch gate. Lowering never kills running cells -- new launches just wait.
#
#   down 2 (floor 6): a219 OUR cpu>40c (48-core pin), or api-failure lines grew
#                     >10 this tick, or a219 java count > cap+14, or memavail<80G.
#                     Box load is other tenants' business, never a brake signal.
#   up 1 (ceil 16):   two consecutive ticks with a219 our cpu<30c and zero new
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
    'echo "$(cut -d" " -f1 /proc/loadavg) $(pgrep -cu ruihan java || true) $(free -g | awk "/Mem:/{print \$7}") $(ps -u ruihan -o pcpu= | awk "{s+=\$1} END{printf \"%d\", s/100}")"' 2>/dev/null) || { log "a219 ssh fail, holding"; continue; }
  read -r load9 java9 mem9 cpu9 <<< "$stats"
  fails=$(cat outputs/log-g56a-default-codex-*.txt 2>/dev/null | grep -cE "produced no actions.json|Agent failed to provide|stream disconnected|429|rate.?limit" || true)
  dfail=0; (( prev_fails >= 0 )) && dfail=$((fails - prev_fails)); prev_fails=$fails
  cap=$(cat "$F" 2>/dev/null | tr -d '[:space:]'); [[ "$cap" =~ ^[0-9]+$ ]] || cap=8
  new=$cap
  if (( cpu9 > 40 )) || (( dfail > 10 )) || (( java9 > cap + 14 )) || (( mem9 < 80 )); then
    new=$(( cap - 2 )); (( new < 6 )) && new=6; healthy=0
  elif (( cpu9 < 30 )) && (( dfail == 0 )); then
    healthy=$((healthy+1))
    (( healthy >= 2 && cap < 16 )) && { new=$((cap+1)); healthy=0; }
  else
    healthy=0
  fi
  if (( new != cap )); then echo "$new" > "$F"; fi
  log "tick cap=$new done=$nd ourcpu=${cpu9}c java=$java9 mem=${mem9}G load=$load9 dfail=$dfail"
done
