#!/usr/bin/env bash
# The g56a campaign chain: hosted gpt-5.6-sol on the 154-scene 4-hop split at 200
# steps, sandboxed codex channel, qwen-protocol generation settings enforced
# client-side (CODEX_EFFORT=none = thinking off, CODEX_MAX_OUTPUT_TOKENS=1024).
# Smoke-verified 2026-08-21 (effort "none" on the wire, cap flag accepted).
#   arm 1  prolong:codex  CONC=10, ceiling 900s
#   -- sandbox clean-slate restart on a219 --
#   arm 2  default:codex  CONC=8, ceiling 120s (c4h policy), legacy layout
# Sandbox: a219 (patched mc_server); serving: none -- the hosted account model.
#
#   setsid nohup bash scripts/chain_g56a.sh > outputs/log-g56a-chain.txt 2>&1 &
set -uo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
log() { echo "[chain] $(date '+%m-%d %H:%M:%S') $*"; }

python3 -c "import urllib.request as u;u.urlopen('http://192.168.2.12:8000/monitor/alive',timeout=8)" 2>/dev/null \
  || { log "ABORT: a219 sandbox not alive"; exit 1; }

SCENES="$(ls bench_4hop154/_split | tr '\n' ' ')"
export SCENES SPLIT_ROOT=bench_4hop154/_split MODEL=gpt-5.6-sol MAX_STEPS=200 PREFIX=g56a
export CODEX_HOSTED=1 CODEX_MAX_OUTPUT_TOKENS=1024 CODEX_EFFORT=none

count_results() { local arm=$1 n=0 s; for s in $SCENES; do
  [[ -f "outputs/g56a-$arm-$s/gpt-5.6-sol/4-hop/$s/result.json" ]] && n=$((n+1)); done; echo "$n"; }

log "arm 1 (prolong:codex hosted) starting; $(count_results prolong-codex)/154 already present"
ARMS="prolong:codex" CONC=10 SERVERS="hosted://account" \
  bash scripts/launch_4hop.sh > outputs/log-g56a-launcher-prolong.txt 2>&1
log "arm 1 finished; $(count_results prolong-codex)/154 results"

log "sandbox clean-slate restart on a219"
ssh -o BatchMode=yes -o ConnectTimeout=8 ruihan@192.168.2.12 \
  bash /datapool/data3/storage/ruihan/.podman/restart-mc-a219.sh \
  && log "sandbox restarted" || log "sandbox restart FAILED -- arm 2 will start against the old instance"

log "arm 2 (default:codex hosted) starting; $(count_results default-codex)/154 already present"
ARMS="default:codex" CONC=8 SERVERS="hosted://account" \
  bash scripts/launch_4hop.sh > outputs/log-g56a-launcher-default.txt 2>&1
log "arm 2 finished; $(count_results default-codex)/154 results"
log "chain complete"
