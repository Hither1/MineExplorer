#!/usr/bin/env bash
# A second hypothesis launcher, 3 slots, walking the 154-scene order BACKWARDS.
#
# Why. Measured on four stable windows at 00:15, hypothesis completes 0.29-0.35 cells/min
# against default's 0.40-0.47, so it projects to 06:43-08:05 against a 06:15 stop while
# default has ~85 min of slack. The cause is not a fault -- 1.01 model calls/step, same as
# default's 1.00, no timeouts, no truncation -- it is that the DAG + plan makes each request
# ~48 % more expensive to prefill. Nothing to fix; the fix is scheduling.
#
# Why not restart the launcher with a higher CONC: launch_4hop.sh decides what to skip ONCE,
# at start, from `[[ -f result.json ]]`. A restart would queue the 9 cells currently in flight
# again and run them twice. Adding a launcher over the reversed order avoids that: the two
# walk the list from opposite ends and only meet as the arm finishes, and where they do meet
# eval_benchmark.py's own --resume check (run_cell.sh passes it, and it is evaluated when the
# cell starts, not when the launcher starts) skips the scene that already landed.
#
# 3 slots, not more: the cluster is at its throughput knee (12 -> 18 in flight bought +12 %),
# so this is a redistribution of a fixed pie toward the arm that needs it, not new capacity.
# a230 is nowhere near its limit (load 67 on 255 cores at 18 sessions), so the sandbox side
# has room for 21.
set -uo pipefail
cd /datapool/data3/storage/ruihan/data_share/jh/Collab/MineExplorer
REV="$(python scripts/screen_scenes.py --hops 4 | awk '$1 ~ /^[0-9]{4}$/ {print $1}' | tac | tr '\n' ' ')"
n=$(echo "$REV" | wc -w)
[[ "$n" -eq 154 ]] || { echo "[boost] screen returned $n, refusing"; exit 2; }
echo "[boost] $(date '+%H:%M:%S') starting, reversed order head: $(echo $REV | cut -d' ' -f1-6)"
PREFIX=q35a MODEL=Qwen3.5-27B SPLIT_ROOT=bench_4hop154/_split \
SERVERS="http://192.168.2.20:8001/v1 http://192.168.2.20:8002/v1 http://192.168.2.20:8003/v1 http://192.168.2.20:8004/v1" \
PROMPT_LAYOUT=append-only RESPONSE_STYLE=full \
ARMS="hypothesis:vllm" SCENES="$REV" MAX_STEPS=200 CONC=3 \
  bash scripts/launch_4hop.sh
