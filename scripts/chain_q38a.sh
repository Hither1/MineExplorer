#!/usr/bin/env bash
# The q38a campaign chain: Qwen3.8-27B on the 154-scene 4-hop split at 200 steps,
# mirroring q35a arm by arm so the two models pool cell-for-cell:
#   arm 1  prolong:codex          CONC=10, servers :8001-:8003 (q35a ran CONC=14;
#          lowered to 10 at the user's request -- protect a219 over speed)
#   -- sandbox clean-slate restart on a219 (leaked-JVM zeroing, as the q35a chain did)
#   arm 2  default:vllm append-only CONC=9, servers :8001-:8004 (q35a default-ao contract)
# Sandbox: a219 (192.168.2.12:8000), started by ~ruihan .podman/start-mc-a219.sh,
# core-pinned 192-223. a230, which served q35a, is down (no route) as of 2026-08-21.
#
#   setsid nohup bash scripts/chain_q38a.sh > outputs/log-q38a-chain.txt 2>&1 &
set -uo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
log() { echo "[chain] $(date '+%m-%d %H:%M:%S') $*"; }

SCENES="$(ls bench_4hop154/_split | tr '\n' ' ')"
export SCENES SPLIT_ROOT=bench_4hop154/_split MODEL=Qwen3.8-27B MAX_STEPS=200 PREFIX=q38a

count_results() { local arm=$1 n=0 s; for s in $SCENES; do
  [[ -f "outputs/q38a-$arm-$s/Qwen3.8-27B/4-hop/$s/result.json" ]] && n=$((n+1)); done; echo "$n"; }

log "arm 1 (prolong:codex) starting; $(count_results prolong-codex)/154 already present"
ARMS="prolong:codex" CONC=10 \
SERVERS="http://192.168.2.20:8001/v1 http://192.168.2.20:8002/v1 http://192.168.2.20:8003/v1" \
  bash scripts/launch_4hop.sh > outputs/log-q38a-launcher-prolong.txt 2>&1
log "arm 1 finished; $(count_results prolong-codex)/154 results"

log "sandbox clean-slate restart on a219"
ssh -o BatchMode=yes -o ConnectTimeout=8 ruihan@192.168.2.12 \
  bash /datapool/data3/storage/ruihan/.podman/restart-mc-a219.sh \
  && log "sandbox restarted" || log "sandbox restart FAILED -- arm 2 will start against the old instance"

log "arm 2 (default:vllm append-only) starting; $(count_results default-vllm-append-only)/154 already present"
ARMS="default:vllm" CONC=9 PROMPT_LAYOUT=append-only \
SERVERS="http://192.168.2.20:8001/v1 http://192.168.2.20:8002/v1 http://192.168.2.20:8003/v1 http://192.168.2.20:8004/v1" \
  bash scripts/launch_4hop.sh > outputs/log-q38a-launcher-default-ao.txt 2>&1
log "arm 2 finished; $(count_results default-vllm-append-only)/154 results"
log "chain complete"
