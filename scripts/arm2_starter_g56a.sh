#!/usr/bin/env bash
# Takes over the dead chain's arm-2 role, upgraded with adaptive concurrency:
# waits for the arm-1 (prolong) launcher to exit, applies the staged CONC_FILE
# launcher patch (safe only once nothing executes launch_4hop.sh), restarts the
# a219 sandbox (clears active + leaked JVMs), then starts the default arm at an
# adaptive cap seeded to 8 with the controller adjusting it in [4,10].
set -uo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
log() { echo "[arm2] $(date '+%m-%d %H:%M:%S') $*"; }

while pgrep -u ruihan -f "launch_4ho[p].sh" >/dev/null; do sleep 60; done
n=0; for s in $(ls bench_4hop154/_split); do
  [[ -f "outputs/g56a-prolong-codex-$s/gpt-5.6-sol/4-hop/$s/result.json" ]] && n=$((n+1)); done
log "arm 1 launcher gone; prolong results $n/154"

if [[ -f scripts/launch_4hop.sh.new ]]; then
  mv scripts/launch_4hop.sh.new scripts/launch_4hop.sh
  chmod +x scripts/launch_4hop.sh
  log "applied CONC_FILE launcher patch"
fi

log "sandbox clean-slate restart on a219"
ssh -o BatchMode=yes -o ConnectTimeout=8 ruihan@192.168.2.12 \
  bash /datapool/data3/storage/ruihan/.podman/restart-mc-a219.sh \
  && log "sandbox restarted" || log "sandbox restart FAILED -- continuing against old instance"

echo 8 > outputs/g56a-conc.txt
setsid nohup bash scripts/conc_controller_g56a.sh > /dev/null 2>&1 &
log "controller started, cap seeded to 8"

SCENES="$(ls bench_4hop154/_split | tr '\n' ' ')"
export SCENES SPLIT_ROOT=bench_4hop154/_split MODEL=gpt-5.6-sol MAX_STEPS=200 PREFIX=g56a
export CODEX_HOSTED=1 CODEX_MAX_OUTPUT_TOKENS=1024 CODEX_EFFORT=none
log "arm 2 (default:codex hosted, adaptive CONC) starting"
ARMS="default:codex" CONC=8 CONC_FILE=outputs/g56a-conc.txt SERVERS="hosted://account" \
  bash scripts/launch_4hop.sh > outputs/log-g56a-launcher-default.txt 2>&1
n=0; for s in $(ls bench_4hop154/_split); do
  [[ -f "outputs/g56a-default-codex-$s/gpt-5.6-sol/4-hop/$s/result.json" ]] && n=$((n+1)); done
log "arm 2 finished; $n/154 results"
