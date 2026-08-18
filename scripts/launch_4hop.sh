#!/usr/bin/env bash
# The strict 4-hop campaign on helixon: {prolong x codex, default x vllm} x 7 scenes,
# one seed each, through scripts/run_cell.sh, at most $CONC cells at once against the
# one shared a227 server and the one podman Minecraft sandbox.
#
#   setsid nohup bash scripts/launch_4hop.sh > outputs/log-c4h-launcher.txt 2>&1 &
#
# One cell = one eval_benchmark process on a one-scene benchmark dir
# (bench_4hop7/_split/<scene>) writing to outputs/c4h-<agent>-<channel>-<scene>/, so
# cells never share an output tree or a codex episode home. `--resume` inside
# run_cell.sh makes a relaunch skip every cell whose result.json exists, which is how a
# crashed cell is rerun: launch this file again.
#
# The queue is ordered long-first (the vllm cells take ~1 h at 300 steps, the prolong
# cells ~30 min), interleaved so both arms accumulate results at a similar rate.
set -uo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

SCENES=${SCENES:-"0306 0726 0182 0311 0482 0603 0763"}
CONC=${CONC:-8}
MAX_STEPS=${MAX_STEPS:-300}
PREFIX=${PREFIX:-c4h}
# Two identically configured servers on a227 (2026-08-18: TP=4 on GPUs 4-7 at :8001,
# TP=2 on GPUs 2,3 at :8002, both thinking off / temp 0.7 / max_new_tokens 1024).
# Scenes alternate between them, so each server carries BOTH arms of the scenes it
# gets and neither arm is confounded with a server. Which server a cell used is in
# its log ("Connected to vLLM server at" / "endpoint=").
SERVERS=${SERVERS:-"http://192.168.2.20:8001/v1 http://192.168.2.20:8002/v1"}
read -r -a servers <<< "$SERVERS"

cells=()
i=0
for s in $SCENES; do
  url=${servers[$(( i % ${#servers[@]} ))]}
  cells+=("default vllm $s $url")
  cells+=("prolong codex $s $url")
  i=$((i + 1))
done

running=0
declare -A pid_tag
for cell in "${cells[@]}"; do
  set -- $cell
  agent=$1; channel=$2; scene=$3; url=$4
  tag="$PREFIX-$agent-$channel-$scene"
  if [[ -f "outputs/$tag/Qwen3.8-27B/4-hop/$scene/result.json" ]]; then
    echo "[launcher] $(date '+%H:%M:%S') skip $tag (result.json exists)"
    continue
  fi
  while (( running >= CONC )); do
    wait -n || true
    running=$((running - 1))
  done
  echo "[launcher] $(date '+%H:%M:%S') start $tag -> $url"
  VLLM_URL="$url" bash scripts/run_cell.sh "$agent" "$channel" "bench_4hop7/_split/$scene" "$tag" "$MAX_STEPS" \
    > "outputs/log-$tag.txt" 2>&1 &
  pid_tag[$!]=$tag
  running=$((running + 1))
  # Stagger: /create_env + reset on the shared sandbox is the contended step, and two
  # resets in the same second have been seen to collide on it.
  sleep 45
done
wait
echo "[launcher] $(date '+%H:%M:%S') all cells finished"
for s in $SCENES; do
  for a in "default-vllm" "prolong-codex"; do
    r="outputs/$PREFIX-$a-$s/Qwen3.8-27B/4-hop/$s/result.json"
    if [[ -f "$r" ]]; then
      python3 -c "import json,sys; j=json.load(open(sys.argv[1])); print(f\"{sys.argv[2]:28s} steps={j['total_steps']:3d} {j['termination_reason']:10s} milestones={j['milestones_completed']}/{j['milestones_trackable']} sandboxed={j.get('codex_sandboxed','-')}\")" "$r" "$PREFIX-$a-$s"
    else
      echo "$PREFIX-$a-$s: NO RESULT"
    fi
  done
done
