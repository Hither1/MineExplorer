#!/usr/bin/env bash
# The strict 4-hop campaign on helixon: {agent x channel} arms x 7 scenes, one seed each,
# through scripts/run_cell.sh, at most $CONC cells at once against the a227 servers and
# the one podman Minecraft sandbox.
#
#   setsid nohup bash scripts/launch_4hop.sh > outputs/log-c4h-launcher.txt 2>&1 &
#
# One cell = one eval_benchmark process on a one-scene benchmark dir
# (bench_4hop7/_split/<scene>) writing to outputs/c4h-<agent>-<channel>-<scene>/, so
# cells never share an output tree or a codex episode home. `--resume` inside
# run_cell.sh makes a relaunch skip every cell whose result.json exists, which is how a
# crashed cell is rerun -- and how the campaign is completed arm by arm: the default ARMS
# lists all four, and a launch runs only what is missing.
#
# Servers: identical TP=2 vLLM servers on a227 (2026-08-18 23:38 relaunch: :8001 GPUs 2,3,
# :8002 GPUs 4,5, :8003 GPUs 6,7; thinking off / temp 0.7 / max_new_tokens 1024 / prefix
# caching on). Pending cells are dealt to the servers round-robin, so each server carries a
# mix of arms and no arm is confounded with a server. Which server a cell used is in its
# log ("Connected to vLLM server at" / "endpoint=").
#
# The first campaign (2026-08-18 14:31-17:11: default x vllm, prolong x codex) ran on two
# differently sized servers (TP=4 :8001, TP=2 :8002, no prefix caching), scenes alternating
# between them; see experiments/RESULTS_helixon_4hop.md.
set -uo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

SCENES=${SCENES:-"0306 0726 0182 0311 0482 0603 0763"}
# agent:channel pairs, in launch priority order (earlier arms start first).
ARMS=${ARMS:-"default:vllm prolong:codex hypothesis:vllm default:codex"}
CONC=${CONC:-14}
MAX_STEPS=${MAX_STEPS:-300}
PREFIX=${PREFIX:-c4h}
# Served model name = results subdirectory. The a227 servers alias both checkpoints,
# so a whole campaign moves between them with MODEL + PREFIX and nothing else.
MODEL=${MODEL:-Qwen3.8-27B}
SERVERS=${SERVERS:-"http://192.168.2.20:8001/v1 http://192.168.2.20:8002/v1 http://192.168.2.20:8003/v1"}
# Per-call ceiling on the codex channel. PRO-LONG turns take 40-120 s and never hit the
# 900 s default. The default/hypothesis agents through CodexProvider are different: with
# thinking off the model spends the call investigating its workspace -- `ls`, then
# `view_image` on the attached frames 20-70 times, PIL crops -- at ANY frame count (probe
# 2026-08-18 23:57, 4/8/12/16/20 frames, prefix caching on: 5 of 7 calls had not answered
# at 240 s; the two that did took 67 s and 193 s, after 6 and 36 requests). Only the
# ceiling ends such a step, so the ceiling is the arm's per-step cost -- one ceiling then a
# no-op (no retry, since 2026-08-18). 120 s keeps the campaign at ~10 h for 300 steps and
# admits the fast answers; it is a policy, and the results table says so.
PROLONG_CODEX_TIMEOUT=${PROLONG_CODEX_TIMEOUT:-900}
PROVIDER_CODEX_TIMEOUT=${PROVIDER_CODEX_TIMEOUT:-120}
read -r -a servers <<< "$SERVERS"

# Pending cells first, then deal servers: a finished cell must not consume a server slot.
cells=()
for arm in $ARMS; do
  agent=${arm%%:*}; channel=${arm##*:}
  for s in $SCENES; do
    tag="$PREFIX-$agent-$channel-$s"
    if [[ -f "outputs/$tag/$MODEL/4-hop/$s/result.json" ]]; then
      echo "[launcher] $(date '+%H:%M:%S') skip $tag (result.json exists)"
      continue
    fi
    cells+=("$agent $channel $s")
  done
done
echo "[launcher] $(date '+%H:%M:%S') ${#cells[@]} cells pending, conc=$CONC, servers=${#servers[@]}"

running=0
i=0
for cell in "${cells[@]}"; do
  set -- $cell
  agent=$1; channel=$2; scene=$3
  url=${servers[$(( i % ${#servers[@]} ))]}
  i=$((i + 1))
  tag="$PREFIX-$agent-$channel-$scene"
  while (( running >= CONC )); do
    wait -n || true
    running=$((running - 1))
  done
  timeout=$PROLONG_CODEX_TIMEOUT
  [[ "$channel" == "codex" && "$agent" != "prolong" ]] && timeout=$PROVIDER_CODEX_TIMEOUT
  echo "[launcher] $(date '+%H:%M:%S') start $tag -> $url (model $MODEL, codex ceiling ${timeout}s)"
  MODEL="$MODEL" VLLM_URL="$url" CODEX_TIMEOUT="$timeout" \
    bash scripts/run_cell.sh "$agent" "$channel" "bench_4hop7/_split/$scene" "$tag" "$MAX_STEPS" \
    > "outputs/log-$tag.txt" 2>&1 &
  running=$((running + 1))
  # Stagger: /create_env + reset on the shared sandbox is the contended step, and two
  # resets in the same second have been seen to collide on it.
  sleep 45
done
wait
echo "[launcher] $(date '+%H:%M:%S') all cells finished"
for arm in $ARMS; do
  agent=${arm%%:*}; channel=${arm##*:}
  for s in $SCENES; do
    tag="$PREFIX-$agent-$channel-$s"
    r="outputs/$tag/$MODEL/4-hop/$s/result.json"
    if [[ -f "$r" ]]; then
      python3 -c "import json,sys; j=json.load(open(sys.argv[1])); print(f\"{sys.argv[2]:30s} steps={j['total_steps']:3d} {j['termination_reason']:10s} milestones={j['milestones_completed']}/{j['milestones_trackable']} sandboxed={j.get('codex_sandboxed','-')}\")" "$r" "$tag"
    else
      echo "$tag: NO RESULT"
    fi
  done
done
