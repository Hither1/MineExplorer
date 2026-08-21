#!/usr/bin/env bash
# a219 guard for the q38a campaign. Every 120s: a219 load / free mem / sandbox JVM
# count, sandbox liveness over HTTP, and per-arm result counts. Appends one line per
# tick to outputs/log-q38a-monitor.txt.
#
# Exits 0 when both arms have 154/154 results (campaign done).
# Exits 1 on a danger condition, so a supervising session is re-invoked to intervene:
#   - a219 load1 > 245 on three consecutive ticks AND our own CPU footprint above
#     45 cores (pin breach / runaway of ours). Other tenants routinely push the node
#     past 245 by themselves (gaoguanfei hit 272 on 08-21); that alone is logged as
#     WARN but is not actionable by us -- our sandbox is hard-capped by taskset.
#   - a219 MemAvailable < 80 GB
#   - sandbox /monitor/alive failing for 3 consecutive ticks (~6 min; a between-arms
#     restart takes ~2 min and does not trip this)
#   - ruihan-owned java processes > 18 (leak past CONC=10 + headroom)
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
    'l=$(cut -d" " -f1 /proc/loadavg); m=$(awk "/MemAvailable/{printf \"%d\", \$2/1048576}" /proc/meminfo); j=$(pgrep -cu ruihan java || true); c=$(ps -o pcpu= -u ruihan | awk "{s+=\$1} END {printf \"%d\", s/100}"); echo "$l $m $j $c"' 2>/dev/null) || stats=""
  if [[ -z "$stats" ]]; then
    ssh_fail=$((ssh_fail+1)); echo "$ts SSH-FAIL ($ssh_fail/5)" >> "$LOG"
    (( ssh_fail >= 5 )) && { echo "$ts DANGER: a219 unreachable" >> "$LOG"; exit 1; }
    sleep 120; continue
  fi
  ssh_fail=0
  read -r load1 memg java ourcores <<< "$stats"
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
  echo "$ts load=$load1 memavail=${memg}G java=$java ourcores=$ourcores sandbox=$alive prolong=$np/154 default=$nd/154" >> "$LOG"
  if awk -v l="$load1" 'BEGIN{exit !(l>245)}'; then hi_load=$((hi_load+1)); else hi_load=0; fi
  if (( hi_load >= 3 )); then
    if (( ourcores > 45 )); then
      echo "$ts DANGER: load>245 x3 AND our cpu=${ourcores} cores (pin breach?)" >> "$LOG"; exit 1
    fi
    echo "$ts WARN: load>245 x3 but ours=${ourcores} cores (other tenants); not exiting" >> "$LOG"; hi_load=0
  fi
  (( memg < 80 ))          && { echo "$ts DANGER: memavail<80G" >> "$LOG"; exit 1; }
  (( alive_fail >= 3 ))    && { echo "$ts DANGER: sandbox dead 3 ticks" >> "$LOG"; exit 1; }
  (( java > 18 ))          && { echo "$ts DANGER: java=$java (JVM leak past CONC+headroom)" >> "$LOG"; exit 1; }
  (( np >= 154 && nd >= 154 )) && { echo "$ts campaign complete" >> "$LOG"; exit 0; }
  sleep 120
done
