#!/usr/bin/env bash
# Adaptive concurrency for the g56a arm-1 (prolong) resume launcher. Writes the
# cap to outputs/g56a-conc-arm1.txt; the adaptive launch_4hop.sh re-reads it
# before every cell launch. Bounds [6,20] inside the sandbox's 32-core pin
# (10 leaked q38a JVMs idle there too, so cap 20 = 30 JVMs ~ 20-27 cores).
# Down 2 on OUR pressure only -- other tenants' load is not ours to brake for:
#   a219 java > 60 (killed cells leak their server JVMs until the between-arms restart) | a219 our cpu > 27c (pin saturation) | a219 memavail < 80G
#   a218 our cpu > 80c | new api-failure lines > 10 per 120s tick
# Up 1 after 2 consecutive healthy ticks. Exits at 154 arm-1 results, or when
# both the launcher and all cells are gone.
set -uo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd); cd "$ROOT"
CAP_FILE=outputs/g56a-conc-arm1.txt
LOG=outputs/log-g56a-conc-arm1.txt
A219=192.168.2.12
MIN=6 MAX=20
cap=$(cat "$CAP_FILE" 2>/dev/null || true); [[ "$cap" =~ ^[0-9]+$ ]] || cap=8
healthy=0 prev_fails=-1
while true; do
  ts=$(date '+%m-%d %H:%M:%S')
  done_n=0
  for s in $(ls bench_4hop154/_split); do
    [[ -f "outputs/g56a-prolong-codex-$s/gpt-5.6-sol/4-hop/$s/result.json" ]] && done_n=$((done_n+1))
  done
  (( done_n >= 154 )) && { echo "$ts arm1 complete (154/154); controller exit" >> "$LOG"; exit 0; }
  cells=$(pgrep -u ruihan -cf "eval_benchmark" || true)
  launchers=$(pgrep -u ruihan -cf "launch_4hop.sh" || true)
  if (( launchers == 0 && cells == 0 )); then
    echo "$ts launcher and cells both gone at $done_n/154; controller exit" >> "$LOG"; exit 0
  fi
  fails=$(cat outputs/log-g56a-prolong-codex-*.txt 2>/dev/null | grep -cE "timed out after|stream disconnected|error sending request" || true)
  d=0; (( prev_fails >= 0 )) && d=$((fails - prev_fails)); prev_fails=$fails
  stats=$(timeout 25 ssh -o BatchMode=yes -o ConnectTimeout=10 "ruihan@$A219" \
    'echo "$(pgrep -c java 2>/dev/null || echo 0) $(free -g | awk "/Mem:/{print \$7}") $(ps -u ruihan -o pcpu= | awk "{s+=\$1} END{printf \"%d\", s/100}")"' 2>/dev/null) || stats=""
  a218cpu=$(ps -u ruihan -o pcpu= | awk '{s+=$1} END{printf "%d", s/100}')
  java=999; mem=999; ourcpu=0
  [[ -n "$stats" ]] && read -r java mem ourcpu <<< "$stats"
  danger=""
  (( java > 60 )) && danger="$danger java=$java"
  (( ourcpu > 27 )) && danger="$danger a219cpu=${ourcpu}c"
  [[ -n "$stats" ]] && (( mem < 80 )) && danger="$danger mem=${mem}G"
  (( a218cpu > 80 )) && danger="$danger a218cpu=${a218cpu}c"
  (( d > 10 )) && danger="$danger dfail=$d"
  new=$cap
  if [[ -n "$danger" ]]; then
    healthy=0; new=$((cap-2)); (( new < MIN )) && new=$MIN
  else
    healthy=$((healthy+1))
    if (( healthy >= 2 && cap < MAX )); then new=$((cap+1)); healthy=0; fi
  fi
  [[ "$new" != "$cap" ]] && echo "$ts cap $cap -> $new (danger='${danger# }')" >> "$LOG"
  cap=$new; echo "$cap" > "$CAP_FILE"
  echo "$ts tick cap=$cap cells=$cells done=$done_n java=$java a219cpu=${ourcpu}c a218cpu=${a218cpu}c dfail=$d" >> "$LOG"
  sleep 120
done
