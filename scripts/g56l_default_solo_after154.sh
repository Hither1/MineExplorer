#!/usr/bin/env bash
# Rerun the g56l default:codex strict-7 arm SOLO, the moment g56l154 finishes.
#
# Why a rerun: the first arm-3 attempt ran 09:46-13:0x under a changing account load --
# ~38% ceiling-noops alone, ~85% (11/13) once the 154 campaign's 14 single-image streams
# joined at 12:00. A default column measured at three different contention levels is not
# one arm; the cells were stopped (ledger 20260826-130500) and the scenes rerun here
# with the account to themselves, which is also the configuration the c4h 240s policy
# was calibrated against. Partial dirs of the stopped attempt are parked as evidence in
# outputs/g56l-default-partial-20260826/.
#
#   setsid nohup bash scripts/g56l_default_solo_after154.sh > outputs/log-g56l-default-solo-watch.txt 2>&1 &
set -uo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
log() { echo "[default-solo] $(date '+%m-%d %H:%M:%S') $*"; }

log "waiting for g56l154 chain to complete"
while ! grep -q "chain complete" outputs/log-g56l154-chain.txt 2>/dev/null; do sleep 600; done
log "g56l154 complete; parking partial default dirs and restarting the sandbox"

mkdir -p outputs/g56l-default-partial-20260826
for d in outputs/g56l-default-codex-*; do
  [[ -d "$d" ]] || continue
  s=${d##*-}
  [[ -f "$d/gpt-5.6-sol/4-hop/$s/result.json" ]] && continue   # a finished cell stays
  mv "$d" "outputs/g56l-default-partial-20260826/" && log "parked $d"
done
for f in outputs/log-g56l-default-codex-*.txt; do
  [[ -f "$f" ]] && mv "$f" "outputs/g56l-default-partial-20260826/" 2>/dev/null
done

ssh -o BatchMode=yes -o ConnectTimeout=8 ruihan@192.168.2.12 \
  bash /datapool/data3/storage/ruihan/.podman/restart-mc-a219.sh \
  && log "sandbox restarted" || log "sandbox restart FAILED -- running against the old instance"

export SCENES="0306 0726 0182 0311 0482 0603 0763"
export SPLIT_ROOT=bench_4hop7/_split MODEL=gpt-5.6-sol MAX_STEPS=300 PREFIX=g56l
export CODEX_HOSTED=1 CODEX_MAX_OUTPUT_TOKENS=1024 CODEX_EFFORT=low CODEX_SESSION_MAX_TURNS=1
log "default:codex strict-7 solo starting (CONC=5)"
ARMS="default:codex" CONC=5 SERVERS="hosted://account" \
  bash scripts/launch_4hop.sh > outputs/log-g56l-launcher-default-solo.txt 2>&1
n=0; for s in $SCENES; do
  [[ -f "outputs/g56l-default-codex-$s/gpt-5.6-sol/4-hop/$s/result.json" ]] && n=$((n+1)); done
log "default solo arm finished; $n/7 results"
