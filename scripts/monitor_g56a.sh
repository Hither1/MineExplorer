#!/usr/bin/env bash
# Two-host guard for the g56a campaign (hosted gpt-5.6-sol; clients on a218,
# Minecraft sandbox on a219). One line per 120s tick to outputs/log-g56a-monitor.txt.
#
# Exit 0: both arms 154/154. Exit 1 (danger, supervisor re-invoked):
#   a219: MemAvailable<80G | ruihan java>38 (up to 20 active + ~10 JVMs leaked by
#         the killed q38a cells, cleared at the between-arms restart) | sandbox dead
#         3 ticks | ssh dead 5 ticks
#         | load>245 x3 AND our a219 cpu>45 cores (pin breach)
#   a218: MemAvailable<50G | our a218 cpu>80 cores (client runaway)
#   API:  "failed/disconnected" lines grow by >40 in one tick (hosted outage/limits)
set -uo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
LOG=outputs/log-g56a-monitor.txt

# Codex trees sometimes outlive their cell (the user has seen finished tasks leave
# processes behind). A campaign codex process is identified by cwd under our
# outputs/; it is an orphan when no live eval_benchmark remains in its ancestor
# chain. Interactive codex sessions live elsewhere and are never touched.
reap_codex() {
  local n=0 pid cwd p st
  for pid in $(pgrep -u ruihan -f "code[x] exec|code[x]-linux|bwra[p]|sandbox_prox[y]"); do
    st=$(ps -o stat= -p "$pid" 2>/dev/null) || continue
    [[ "$st" == Z* ]] && continue
    cwd=$(readlink "/proc/$pid/cwd" 2>/dev/null) || continue
    [[ "$cwd" == "$ROOT"/outputs/* ]] || continue
    p=$pid
    local live=0
    for _ in 1 2 3 4 5 6 7 8; do
      p=$(ps -o ppid= -p "$p" 2>/dev/null | tr -d " ") || break
      [[ -z "$p" || "$p" -le 1 ]] && break
      if tr "\0" " " < "/proc/$p/cmdline" 2>/dev/null | grep -q "eval_benchmark"; then live=1; break; fi
    done
    (( live )) && continue
    kill "$pid" 2>/dev/null && n=$((n+1))
  done
  echo "$n"
}
A219=192.168.2.12
hi_load=0; alive_fail=0; ssh_fail=0; prev_fails=-1
while true; do
  ts=$(date '+%m-%d %H:%M:%S')
  stats=$(ssh -o BatchMode=yes -o ConnectTimeout=10 "ruihan@$A219" \
    'l=$(cut -d" " -f1 /proc/loadavg); m=$(awk "/MemAvailable/{printf \"%d\", \$2/1048576}" /proc/meminfo); j=$(pgrep -cu ruihan java || true); c=$(ps -o pcpu= -u ruihan | awk "{s+=\$1} END {printf \"%d\", s/100}"); echo "$l $m $j $c"' 2>/dev/null) || stats=""
  if [[ -z "$stats" ]]; then
    ssh_fail=$((ssh_fail+1)); echo "$ts SSH-FAIL a219 ($ssh_fail/5)" >> "$LOG"
    (( ssh_fail >= 5 )) && { echo "$ts DANGER: a219 unreachable" >> "$LOG"; exit 1; }
    sleep 120; continue
  fi
  ssh_fail=0
  read -r load9 mem9 java9 cpu9 <<< "$stats"
  load8=$(cut -d" " -f1 /proc/loadavg)
  mem8=$(awk '/MemAvailable/{printf "%d", $2/1048576}' /proc/meminfo)
  cpu8=$(ps -o pcpu= -u ruihan | awk '{s+=$1} END {printf "%d", s/100}')
  ncodex=$(pgrep -cu ruihan -f "code[x]-linux|code[x] exec" || true)
  if python3 -c "import urllib.request as u;u.urlopen('http://$A219:8000/monitor/alive',timeout=8)" 2>/dev/null; then
    alive=ok; alive_fail=0
  else
    alive=DOWN; alive_fail=$((alive_fail+1))
  fi
  np=0; nd=0
  for s in $(ls bench_4hop154/_split); do
    [[ -f "outputs/g56a-prolong-codex-$s/gpt-5.6-sol/4-hop/$s/result.json" ]] && np=$((np+1))
    [[ -f "outputs/g56a-default-codex-$s/gpt-5.6-sol/4-hop/$s/result.json" ]] && nd=$((nd+1))
  done
  fails=$(cat outputs/log-g56a-prolong-codex-*.txt outputs/log-g56a-default-codex-*.txt 2>/dev/null | grep -cE "produced no actions.json|Agent failed to provide|stream disconnected|429|rate.?limit" || true)
  dfail=0; (( prev_fails >= 0 )) && dfail=$((fails - prev_fails)); prev_fails=$fails
  reaped=$(reap_codex)
  echo "$ts a219(load=$load9 mem=${mem9}G java=$java9 our=${cpu9}c sandbox=$alive) a218(load=$load8 mem=${mem8}G our=${cpu8}c codex=$ncodex) apifails=+$dfail reaped=$reaped prolong=$np/154 default=$nd/154" >> "$LOG"
  if awk -v l="$load9" 'BEGIN{exit !(l>245)}'; then hi_load=$((hi_load+1)); else hi_load=0; fi
  if (( hi_load >= 3 )); then
    if (( cpu9 > 45 )); then echo "$ts DANGER: a219 load>245 x3 AND our cpu=${cpu9}c" >> "$LOG"; exit 1; fi
    echo "$ts WARN: a219 load>245 x3 but ours=${cpu9}c (other tenants)" >> "$LOG"; hi_load=0
  fi
  (( mem9 < 80 ))       && { echo "$ts DANGER: a219 memavail<80G" >> "$LOG"; exit 1; }
  (( alive_fail >= 3 )) && { echo "$ts DANGER: sandbox dead 3 ticks" >> "$LOG"; exit 1; }
  (( java9 > 38 ))      && { echo "$ts DANGER: a219 java=$java9 (JVM leak)" >> "$LOG"; exit 1; }
  (( mem8 < 50 ))       && { echo "$ts DANGER: a218 memavail<50G" >> "$LOG"; exit 1; }
  (( cpu8 > 80 ))       && { echo "$ts DANGER: a218 our cpu=${cpu8}c (client runaway)" >> "$LOG"; exit 1; }
  (( dfail > 40 ))      && { echo "$ts DANGER: api failure lines +$dfail in one tick" >> "$LOG"; exit 1; }
  (( np >= 154 && nd >= 154 )) && { echo "$ts campaign complete" >> "$LOG"; exit 0; }
  sleep 120
done
