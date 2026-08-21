#!/usr/bin/env bash
# a219 guard for the q38a campaign. Every 120s: a219 load / free mem / sandbox JVM
# count, sandbox liveness over HTTP, and per-arm result counts. Appends one line per
# tick to outputs/log-q38a-monitor.txt.
#
# Exits 0 when both arms have 154/154 results (campaign done).
# Exits 1 on a danger condition, so a supervising session is re-invoked to intervene:
#   - a219 load1 > 235 on two consecutive ticks (node near saturation)
#   - a219 MemAvailable < 80 GB
#   - sandbox /monitor/alive failing for 3 consecutive ticks (~6 min; a between-arms
#     restart takes ~2 min and does not trip this)
#   - ruihan-owned java processes > 25 (JVM leak beyond CONC+headroom)
#   - ssh to a219 failing for 5 consecutive ticks (node unreachable)
set -uo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
LOG=outputs/log-q38a-monitor.txt
A219=192.168.2.12
hi_load=0; alive_fail=0; ssh_fail=0
while true; do
  ts=$(date '+%m-%d %H:%M:%S')
  stats=$(ssh -o BatchMode=yes -o ConnectTimeout=10 "ruihan@$A219" \
    'l=$(cut -d" " -f1 /proc/loadavg); m=$(awk "/MemAvailable/{printf \"%d\", \$2/1048576}" /proc/meminfo); j=$(pgrep -cu ruihan java || true); echo "$l $m $j"' 2>/dev/null) || stats=""
  if [[ -z "$stats" ]]; then
    ssh_fail=$((ssh_fail+1)); echo "$ts SSH-FAIL ($ssh_fail/5)" >> "$LOG"
    (( ssh_fail >= 5 )) && { echo "$ts DANGER: a219 unreachable" >> "$LOG"; exit 1; }
    sleep 120; continue
  fi
  ssh_fail=0
  read -r load1 memg java <<< "$stats"
  if python3 -c "import urllib.request as u;u.urlopen('http://$A219:8000/monitor/alive',timeout=8)" 2>/dev/null; then
    alive=ok; alive_fail=0
  else
    alive=DOWN; alive_fail=$((alive_fail+1))
  fi
  np=0; nd=0
  for s in $(ls bench_4hop154/_split); do
    [[ -f "outputs/q38a-prolong-codex-$s/Qwen3.8-27B/4-hop/$s/result.json" ]] && np=$((np+1))
    [[ -f "outputs/q38a-default-vllm-append-only-$s/Qwen3.8-27B/4-hop/$s/result.json" ]] && nd=$((nd+1))
  done
  echo "$ts load=$load1 memavail=${memg}G java=$java sandbox=$alive prolong=$np/154 default=$nd/154" >> "$LOG"
  awk -v l="$load1" 'BEGIN{exit !(l>235)}' && hi_load=$((hi_load+1)) || hi_load=0
  (( hi_load >= 2 ))      && { echo "$ts DANGER: load>235 twice" >> "$LOG"; exit 1; }
  (( memg < 80 ))          && { echo "$ts DANGER: memavail<80G" >> "$LOG"; exit 1; }
  (( alive_fail >= 3 ))    && { echo "$ts DANGER: sandbox dead 3 ticks" >> "$LOG"; exit 1; }
  (( java > 25 ))          && { echo "$ts DANGER: java=$java (JVM leak)" >> "$LOG"; exit 1; }
  (( np >= 154 && nd >= 154 )) && { echo "$ts campaign complete" >> "$LOG"; exit 0; }
  sleep 120
done
