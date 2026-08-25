#!/usr/bin/env bash
# The g56l campaign chain: hosted gpt-5.6-sol at effort LOW on the strict seven 4-hop
# scenes at 300 steps -- the three-arm head-to-head (worldmodel / prolong / default),
# sandboxed codex channel, milestone hint on (eval_benchmark default).
#
# Session policy is a controlled constant across all three arms: one codex session per
# turn. The default arm is per-turn by construction (CodexProvider); prolong and
# worldmodel get CODEX_SESSION_MAX_TURNS=1, which is also MCU-AgentBeats' operative
# default (run-arm.sh SESSION_TURNS=1). Measured basis: resumed sessions grow ~0.4 MB a
# turn (each turn attaches a frame and codex re-sends the whole thread), turn cost is
# 42s + 11.2s/MB below ~5 MB and steps to a flat ~600s past ~5.15-6.15 MB (MCU, three
# arms, 2026-08-25); our own wm-smoke2 on 0686 reproduced the wall at turn 16 with
# ~13-minute turns. At one turn per session the payload is constant and the wall is
# unreachable (MCU: 1,878 consecutive sessions, 53-71s median, no drift; our
# wm-probe-cs1: flat 51-66s). This deviates from g56a's prolong CS15 -- declared:
# g56l also moves effort none->low, so no cross-campaign averaging either way.
#
#   arm 1  worldmodel:codex  CONC=7, ceiling 1500s
#   arm 2  prolong:codex     CONC=7, ceiling 1500s
#   arm 3  default:codex     CONC=5, ceiling 240s (c4h policy), legacy/full/no-schema
#
# Sandbox: a219 (patched mc_server), clean-slate restart between arms; serving: none --
# the hosted account model.
#
#   setsid nohup bash scripts/chain_g56l.sh > outputs/log-g56l-chain.txt 2>&1 &
set -uo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
log() { echo "[chain] $(date '+%m-%d %H:%M:%S') $*"; }

python3 -c "import urllib.request as u;u.urlopen('http://192.168.2.12:8000/monitor/alive',timeout=8)" 2>/dev/null \
  || { log "ABORT: a219 sandbox not alive"; exit 1; }

SCENES="0306 0726 0182 0311 0482 0603 0763"
export SCENES SPLIT_ROOT=bench_4hop7/_split MODEL=gpt-5.6-sol MAX_STEPS=300 PREFIX=g56l
export CODEX_HOSTED=1 CODEX_MAX_OUTPUT_TOKENS=1024 CODEX_EFFORT=low
export CODEX_SESSION_MAX_TURNS=1
# Worldmodel knobs, spelled out even though each is the code default, so the launch
# record names the protocol: MCU-aligned dual-turn loop, induction every 60 steps,
# strategy bullets on, frames at the probe-verified 640x360.
export WM_INDUCTION_EVERY=60 WM_STRATEGY=1 WM_OBS_SIZE=640x360

count_results() { local arm=$1 n=0 s; for s in $SCENES; do
  [[ -f "outputs/g56l-$arm-$s/gpt-5.6-sol/4-hop/$s/result.json" ]] && n=$((n+1)); done; echo "$n"; }

restart_sandbox() {
  log "sandbox clean-slate restart on a219"
  ssh -o BatchMode=yes -o ConnectTimeout=8 ruihan@192.168.2.12 \
    bash /datapool/data3/storage/ruihan/.podman/restart-mc-a219.sh \
    && log "sandbox restarted" || log "sandbox restart FAILED -- next arm starts against the old instance"
}

log "arm 1 (worldmodel:codex hosted, effort low) starting; $(count_results worldmodel-codex)/7 already present"
ARMS="worldmodel:codex" CONC=7 SERVERS="hosted://account" \
  bash scripts/launch_4hop.sh > outputs/log-g56l-launcher-worldmodel.txt 2>&1
log "arm 1 finished; $(count_results worldmodel-codex)/7 results"

restart_sandbox

log "arm 2 (prolong:codex hosted, effort low) starting; $(count_results prolong-codex)/7 already present"
ARMS="prolong:codex" CONC=7 SERVERS="hosted://account" \
  bash scripts/launch_4hop.sh > outputs/log-g56l-launcher-prolong.txt 2>&1
log "arm 2 finished; $(count_results prolong-codex)/7 results"

restart_sandbox

log "arm 3 (default:codex hosted, effort low) starting; $(count_results default-codex)/7 already present"
ARMS="default:codex" CONC=5 SERVERS="hosted://account" \
  bash scripts/launch_4hop.sh > outputs/log-g56l-launcher-default.txt 2>&1
log "arm 3 finished; $(count_results default-codex)/7 results"
log "chain complete"
