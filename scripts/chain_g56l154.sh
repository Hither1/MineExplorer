#!/usr/bin/env bash
# The g56l154 campaign: worldmodel and prolong over ALL 154 4-hop scenes at the g56l
# settings (hosted gpt-5.6-sol, CODEX_EFFORT=low, one codex session per turn, output cap
# 1024, milestone hint on, 300 steps, 1 seed), the two arms IN PARALLEL per the user's
# order (2026-08-26 ~11:50, "跑154个4hop任务的default, prolong和worldmodel ... 并行跑").
#
# What differs from g56l strict-7 and why:
#   - worldmodel runs the POST-FIX code (4c03041: drop collection, search doctrine,
#     goal-kind fence, recent-events line). Declared: g56l arm 1 was pre-fix.
#   - default:codex is NOT in this chain. Measured on g56l arm 3 (12:00, CONC=5): ~38%
#     of calls die at the 240s ceiling and the rest take 60-240s, ~2.4 min/step, ~12-14 h
#     per 300-step episode -- 154 scenes is weeks at any concurrency. The g56l strict-7
#     default arm keeps running beside this campaign and completes the three-arm table;
#     extending default to 154 is a morning decision, not a launchable fact.
#   - CONC 7+7 single-image calls on the account while the default arm holds its five
#     20-image calls; a219 carries ~19 concurrent cells (c4h ran 14 routinely). If the
#     default arm's ceiling rate rises after 12:00, that is this load -- declared in
#     RUN_LEDGER.
#
#   setsid nohup bash scripts/chain_g56l154.sh > outputs/log-g56l154-chain.txt 2>&1 &
set -uo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
log() { echo "[chain154] $(date '+%m-%d %H:%M:%S') $*"; }

python3 -c "import urllib.request as u;u.urlopen('http://192.168.2.12:8000/monitor/alive',timeout=8)" 2>/dev/null \
  || { log "ABORT: a219 sandbox not alive"; exit 1; }

SCENES="$(ls bench_4hop154/_split | tr '\n' ' ')"
export SCENES SPLIT_ROOT=bench_4hop154/_split MODEL=gpt-5.6-sol MAX_STEPS=300 PREFIX=g56l154
export CODEX_HOSTED=1 CODEX_MAX_OUTPUT_TOKENS=1024 CODEX_EFFORT=low
export CODEX_SESSION_MAX_TURNS=1
export WM_INDUCTION_EVERY=60 WM_STRATEGY=1 WM_OBS_SIZE=640x360

count_results() { local arm=$1 n=0 s; for s in $SCENES; do
  [[ -f "outputs/g56l154-$arm-$s/gpt-5.6-sol/4-hop/$s/result.json" ]] && n=$((n+1)); done; echo "$n"; }

# Overridable since the 12:34-16:24 incident: at 7+7 (19 cells with the default arm)
# the mc_server starved -- step/reset calls past its 60-120s client timeouts turned
# ~300 scenes into error results while both launchers marched on. 6+6 is the highest
# level with a healthy precedent (12 cells, morning of 08-26).
WM_CONC=${WM_CONC:-7}
PL_CONC=${PL_CONC:-7}
log "worldmodel:codex x154 starting (CONC=$WM_CONC); $(count_results worldmodel-codex)/154 already present"
ARMS="worldmodel:codex" CONC=$WM_CONC SERVERS="hosted://account" \
  bash scripts/launch_4hop.sh > outputs/log-g56l154-launcher-worldmodel.txt 2>&1 &
WM_PID=$!

# Offset the second launcher so the two 45s launch staggers do not land create_env
# resets in the same second (measured collision mode on the shared sandbox).
sleep 25

log "prolong:codex x154 starting (CONC=$PL_CONC); $(count_results prolong-codex)/154 already present"
ARMS="prolong:codex" CONC=$PL_CONC SERVERS="hosted://account" \
  bash scripts/launch_4hop.sh > outputs/log-g56l154-launcher-prolong.txt 2>&1 &
PL_PID=$!

wait "$WM_PID"; log "worldmodel arm finished; $(count_results worldmodel-codex)/154 results"
wait "$PL_PID";  log "prolong arm finished; $(count_results prolong-codex)/154 results"
log "chain complete: wm=$(count_results worldmodel-codex)/154 prolong=$(count_results prolong-codex)/154"
