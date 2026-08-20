#!/usr/bin/env bash
# Runs arms 2 and 3 of the q35a campaign after arm 1 finishes, unattended.
#
#   setsid nohup bash tasks/<task>/run_remaining_arms.sh > outputs/log-q35a-chain.txt 2>&1 &
#
# Arm 1 (prolong:codex) was launched by hand at 13:08 and has its own launcher; this waits
# for that launcher's completion line rather than for a PID, so it survives either process
# dying. Arms 2 and 3 are vllm-direct: no codex, no bwrap, no sandbox selftest per cell.
#
# CONC stays at 14, the only value verified against the a230 sandbox. Measured 2026-08-20
# 15:0x with 13-14 concurrent sessions: a230 load 397 on 255 cores, so there is no headroom
# to buy concurrency with, and an env.step timeout storm mid-campaign costs far more than
# the ~30% a higher CONC might return. Raising it is a decision to take with a fresh
# measurement, not a default.
set -uo pipefail
cd /datapool/data3/storage/ruihan/data_share/jh/Collab/MineExplorer

PREFIX=q35a
MODEL=Qwen3.5-27B
CONC=${CONC:-14}
MAX_STEPS=200
SPLIT_ROOT=bench_4hop154/_split
SERVERS="http://192.168.2.20:8001/v1 http://192.168.2.20:8002/v1 http://192.168.2.20:8003/v1"
SCENES="$(python scripts/screen_scenes.py --hops 4 | awk '$1 ~ /^[0-9]{4}$/ {printf "%s ", $1}')"
n_scenes=$(echo "$SCENES" | wc -w)
[[ "$n_scenes" -eq 154 ]] || { echo "[chain] expected 154 scenes, got $n_scenes -- refusing"; exit 2; }

say() { echo "[chain] $(date '+%m-%d %H:%M:%S') $*"; }

say "waiting for arm 1 (prolong) to finish"
until grep -q "all cells finished" outputs/log-q35a-launcher-prolong.txt 2>/dev/null; do
  sleep 120
done
say "arm 1 finished; $(find outputs -path '*q35a-prolong*' -name result.json | wc -l)/154 results"

for arm in hypothesis:vllm default:vllm; do
  agent=${arm%%:*}; channel=${arm##*:}
  log="outputs/log-${PREFIX}-launcher-${agent}.txt"
  # Sessions the previous arm failed to release show up as sandbox load the next arm pays
  # for; report the count so a leak is visible in this log rather than only in a230's load.
  say "sandbox sessions before $arm: $(python -c "
import urllib.request,json
try: print(len(json.loads(urllib.request.urlopen('http://192.168.2.22:8000/list_sessions',timeout=15).read())['sessions']))
except Exception as e: print('probe failed:',e)" 2>&1)"
  say "starting $arm -> $log"
  PREFIX=$PREFIX MODEL=$MODEL SPLIT_ROOT=$SPLIT_ROOT SERVERS="$SERVERS" \
  ARMS="$arm" SCENES="$SCENES" MAX_STEPS=$MAX_STEPS CONC=$CONC \
    bash scripts/launch_4hop.sh > "$log" 2>&1
  say "$arm done; $(find outputs -path "*${PREFIX}-${agent}-${channel}*" -name result.json | wc -l)/154 results"
done

say "all three arms complete"
python scripts/summarize_4hop.py --prefix "$PREFIX" --model "$MODEL" --md > "outputs/${PREFIX}-summary.md" 2>&1
say "summary written to outputs/${PREFIX}-summary.md"
