#!/usr/bin/env bash
# Deliver a three-arm table on ONE common scene set before 07:00, 2026-08-21.
#
# The full 154-scene plan cannot make that deadline: arm 2 needs ~9 h more and arm 3 ~7 h,
# against ~8 h available. So the deliverable changes from "three arms x 154 scenes" to
# "three arms x the same K scenes", K set by what the hardware can actually finish. Arm 1
# already has all 154, so it covers any K for free.
#
# K is not chosen by cherry-picking: arm 2 is walking `screen_scenes.py --hops 4` output
# order, and arm 3 is given exactly the scenes arm 2 finished. The subset is therefore a
# prefix of a fixed, reproducible ordering (sorted by spawn-free milestones asc, depth desc,
# distance desc) -- systematic, not random, and biased toward the harder/cleaner end of the
# 154. That has to be said in the write-up; it does not bias the comparison BETWEEN arms,
# which all see the identical set.
#
#   setsid nohup bash tasks/<task>/deadline_controller.sh > outputs/log-q35a-deadline.txt 2>&1 &
set -uo pipefail
cd /datapool/data3/storage/ruihan/data_share/jh/Collab/MineExplorer

PREFIX=q35a; MODEL=Qwen3.5-27B; CONC=14; MAX_STEPS=200
SPLIT_ROOT=bench_4hop154/_split
SERVERS="http://192.168.2.20:8001/v1 http://192.168.2.20:8002/v1 http://192.168.2.20:8003/v1"

STOP_ARM2_AT=56          # results; the ~14 cells then in flight bring the set to ~70
ARM2_HARD_STOP="01:15"   # ...or this clock time, whichever comes first
ARM3_HARD_STOP="06:15"   # kill arm 3's launcher here so there is time to summarise by 07:00
K_CAP=90                 # never hand arm 3 more than this many scenes

say() { echo "[deadline] $(date '+%m-%d %H:%M:%S') $*"; }
n_arm2() { find outputs -path '*q35a-hypothesis-vllm*' -name result.json 2>/dev/null | wc -l; }
past()  { [[ "$(date +%H%M)" -ge "${1/:/}" && "$(date +%H)" -lt 12 ]]; }

# --- 1. let arm 2 run to the stop point ------------------------------------------------
say "arm 2 at $(n_arm2)/154; stopping its launcher at $STOP_ARM2_AT results or $ARM2_HARD_STOP"
while :; do
  n=$(n_arm2)
  [[ "$n" -ge "$STOP_ARM2_AT" ]] && { say "arm 2 reached $n results"; break; }
  past "$ARM2_HARD_STOP" && { say "hard stop $ARM2_HARD_STOP reached at $n results"; break; }
  sleep 60
done

# --- 2. stop the launcher, never the cells ---------------------------------------------
# Only the launcher: the cells in flight are worth their remaining minutes and will land on
# their own. Match on the exact command line rather than a pattern that could catch a cell.
for pid in $(pgrep -f '^bash scripts/launch_4hop\.sh$'); do
  say "killing arm 2 launcher pid $pid"; kill "$pid" 2>/dev/null
done
sleep 5
say "launcher(s) left: $(pgrep -cf '^bash scripts/launch_4hop\.sh$')"

# --- 3. drain the cells that were already running --------------------------------------
say "draining arm 2's in-flight cells"
while pgrep -f 'run_cell.sh hypothesis vllm' >/dev/null 2>&1; do
  past "$ARM3_HARD_STOP" && { say "drain exceeded the arm-3 deadline; proceeding anyway"; break; }
  sleep 60
done
say "arm 2 stopped with $(n_arm2)/154 results"

# --- 4. arm 3 gets exactly the scenes arm 2 finished ------------------------------------
S=$(for r in outputs/${PREFIX}-hypothesis-vllm-*/*/4-hop/*/result.json; do
      [[ -f "$r" ]] && basename "$(dirname "$r")"; done | sort -u | head -n "$K_CAP" | tr '\n' ' ')
K=$(echo "$S" | wc -w)
[[ "$K" -ge 20 ]] || { say "only $K common scenes -- too few to be worth arm 3; stopping"; exit 3; }
say "arm 3 will run the same $K scenes"
echo "$S" > outputs/${PREFIX}-common-scenes.txt

PREFIX=$PREFIX MODEL=$MODEL SPLIT_ROOT=$SPLIT_ROOT SERVERS="$SERVERS" \
ARMS="default:vllm" SCENES="$S" MAX_STEPS=$MAX_STEPS CONC=$CONC \
  bash scripts/launch_4hop.sh > outputs/log-${PREFIX}-launcher-default.txt 2>&1 &
ARM3=$!
say "arm 3 launched (pid $ARM3)"

# --- 5. watchdog: stop arm 3 in time to write the table ---------------------------------
while kill -0 "$ARM3" 2>/dev/null; do
  past "$ARM3_HARD_STOP" && {
    say "arm-3 deadline $ARM3_HARD_STOP reached; stopping its launcher"
    for pid in $(pgrep -f '^bash scripts/launch_4hop\.sh$'); do kill "$pid" 2>/dev/null; done
    break; }
  sleep 60
done
say "arm 3 has $(find outputs -path '*q35a-default-vllm*' -name result.json 2>/dev/null | wc -l)/$K results"
python scripts/summarize_4hop.py --prefix "$PREFIX" --model "$MODEL" --md > outputs/${PREFIX}-summary.md 2>&1
say "summary written to outputs/${PREFIX}-summary.md"
