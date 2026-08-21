#!/usr/bin/env bash
# g56a arm-2 takeover, v2. The accelerated arm 1 runs as a resume launcher plus
# orphaned first-launch cells, so the trigger must wait for the launcher AND
# every eval cell to finish -- restarting the sandbox any earlier would kill
# live sessions. Then: clean-slate sandbox restart (wide 176-223 pin from the
# edited restart script, clears every leaked JVM), seed the arm-2 cap, start
# the arm-2 controller, and run the default arm adaptively.
#
#   setsid nohup bash scripts/arm2_starter_g56a.sh > outputs/log-g56a-arm2.txt 2>&1 &
set -uo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd); cd "$ROOT"
log() { echo "[starter2] $(date '+%m-%d %H:%M:%S') $*"; }

while pgrep -u ruihan -f "launch_4hop.sh" >/dev/null \
   || pgrep -u ruihan -f "eval_benchmark" >/dev/null; do
  sleep 60
done
log "arm 1 fully drained (launcher and cells gone)"

n=0; for s in $(ls bench_4hop154/_split); do
  [[ -f "outputs/g56a-prolong-codex-$s/gpt-5.6-sol/4-hop/$s/result.json" ]] && n=$((n+1)); done
log "arm 1 results: $n/154"

log "clean-slate sandbox restart on a219 (wide pin)"
timeout 400 ssh -o BatchMode=yes -o ConnectTimeout=8 ruihan@192.168.2.12 \
  bash /datapool/data3/storage/ruihan/.podman/restart-mc-a219.sh \
  && log "sandbox restarted" || log "sandbox restart FAILED -- arm 2 against the old instance"

echo 8 > outputs/g56a-conc.txt
setsid nohup bash scripts/conc_controller_g56a.sh > /dev/null 2>&1 &
log "arm 2 (default:codex hosted, adaptive CONC seeded 8, bounds [6,16]) starting"
SCENES="$(ls bench_4hop154/_split | tr '\n' ' ')" SPLIT_ROOT=bench_4hop154/_split \
MODEL=gpt-5.6-sol MAX_STEPS=200 PREFIX=g56a \
CODEX_HOSTED=1 CODEX_MAX_OUTPUT_TOKENS=1024 CODEX_EFFORT=none \
ARMS="default:codex" CONC=8 CONC_FILE=outputs/g56a-conc.txt SERVERS="hosted://account" \
  bash scripts/launch_4hop.sh > outputs/log-g56a-launcher-default.txt 2>&1

n=0; for s in $(ls bench_4hop154/_split); do
  [[ -f "outputs/g56a-default-codex-$s/gpt-5.6-sol/4-hop/$s/result.json" ]] && n=$((n+1)); done
log "arm 2 finished: $n/154"
