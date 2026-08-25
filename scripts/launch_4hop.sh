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
# Where the one-scene benchmark dirs live, one per $SCENES entry. Built by
# `screen_scenes.py --split-to`, which is also what defines which scenes those are:
# bench_4hop7/_split is the strict seven, bench_4hop154/_split every 4-milestone scene.
SPLIT_ROOT=${SPLIT_ROOT:-bench_4hop7/_split}
# agent:channel pairs, in launch priority order (earlier arms start first).
ARMS=${ARMS:-"default:vllm prolong:codex hypothesis:vllm default:codex"}
CONC=${CONC:-14}
# CONC_FILE (optional): a path whose integer content overrides CONC, re-read at every
# launch gate -- lets a controller raise/lower the cap mid-campaign. Absent/invalid
# content falls back to $CONC, so existing callers are byte-identical without it.
CONC_FILE=${CONC_FILE:-}
cur_conc() { local c=""; [[ -n "$CONC_FILE" ]] && c=$(cat "$CONC_FILE" 2>/dev/null | tr -d "[:space:]"); [[ "$c" =~ ^[0-9]+$ ]] && echo "$c" || echo "$CONC"; }
MAX_STEPS=${MAX_STEPS:-300}
PREFIX=${PREFIX:-c4h}
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
PROLONG_CODEX_TIMEOUT=${PROLONG_CODEX_TIMEOUT:-1500}
PROVIDER_CODEX_TIMEOUT=${PROVIDER_CODEX_TIMEOUT:-240}
# Request layout for the default/hypothesis agents (run_cell.sh -> --prompt-layout). Anything
# but legacy is a different arm, so it gets its own tag suffix and never resumes into, or is
# summarised with, a legacy cell.
PROMPT_LAYOUT=${PROMPT_LAYOUT:-legacy}
# Same for the response style (run_cell.sh -> --response-style): full is today's protocol.
RESPONSE_STYLE=${RESPONSE_STYLE:-full}
# Codex channel only (run_cell.sh -> --codex-output-schema): constrain the final message
# to the agent's reply schema. Own tag suffix, same rule as the two above.
CODEX_OUTPUT_SCHEMA=${CODEX_OUTPUT_SCHEMA:-0}
# The checkpoint the cells talk to. It is also a path segment: eval_benchmark.py writes
# <output-dir>/<model with "/" -> "_">/4-hop/<scene>/result.json, which is what the resume
# check and the closing table below read. Set MODEL to whatever $SERVERS actually serve.
# The a227 servers alias both checkpoints, so a whole campaign moves between them with
# MODEL + PREFIX and nothing else.
MODEL=${MODEL:-Qwen3.8-27B}
MODEL_DIR=${MODEL//\//_}
LAYOUT_SUFFIX=""
[[ "$PROMPT_LAYOUT" != "legacy" ]] && LAYOUT_SUFFIX="-$PROMPT_LAYOUT"
[[ "$RESPONSE_STYLE" != "full" ]] && LAYOUT_SUFFIX="$LAYOUT_SUFFIX-$RESPONSE_STYLE"
[[ "$CODEX_OUTPUT_SCHEMA" == "1" ]] && LAYOUT_SUFFIX="$LAYOUT_SUFFIX-schema"
# ...but none of the three reach --agent-mode prolong: run_cell.sh drops them there, because
# PRO-LONG writes its own prompt. So a prolong cell is the same arm whatever they are set to,
# and it must keep the bare tag -- otherwise a layout campaign would re-run the arm from
# scratch (4-54 min a cell) instead of resuming the prolong cells it already has, and would
# file them under a name saying they ran a layout they cannot run.
arm_suffix() { [[ "$1" == "prolong" || "$1" == "worldmodel" ]] && echo "" || echo "$LAYOUT_SUFFIX"; }
export PROMPT_LAYOUT RESPONSE_STYLE CODEX_OUTPUT_SCHEMA MODEL
read -r -a servers <<< "$SERVERS"

# Pending cells first, then deal servers: a finished cell must not consume a server slot.
cells=()
for arm in $ARMS; do
  agent=${arm%%:*}; channel=${arm##*:}
  for s in $SCENES; do
    tag="$PREFIX-$agent-$channel$(arm_suffix "$agent")-$s"
    if [[ -f "outputs/$tag/$MODEL_DIR/4-hop/$s/result.json" ]]; then
      echo "[launcher] $(date '+%H:%M:%S') skip $tag (result.json exists)"
      continue
    fi
    cells+=("$agent $channel $s")
  done
done
echo "[launcher] $(date '+%H:%M:%S') ${#cells[@]} cells pending, conc=$CONC, servers=${#servers[@]}, model=$MODEL, layout=$PROMPT_LAYOUT style=$RESPONSE_STYLE schema=$CODEX_OUTPUT_SCHEMA"

running=0
i=0
for cell in "${cells[@]}"; do
  set -- $cell
  agent=$1; channel=$2; scene=$3
  url=${servers[$(( i % ${#servers[@]} ))]}
  i=$((i + 1))
  tag="$PREFIX-$agent-$channel$(arm_suffix "$agent")-$scene"
  # Poll the real child count: bash 5.0 wait -n never returns children that were
  # already reaped-and-notified (a mass SIGKILL left the counter stuck at cap).
  while (( $(jobs -pr | wc -l) >= $(cur_conc) )); do
    sleep 5
  done
  timeout=$PROLONG_CODEX_TIMEOUT
  # worldmodel owns its prompt and queue like prolong does, and its induction turns are
  # its longest calls -- it takes the planning-arm ceiling, not the provider policy cap.
  [[ "$channel" == "codex" && "$agent" != "prolong" && "$agent" != "worldmodel" ]] \
    && timeout=$PROVIDER_CODEX_TIMEOUT
  echo "[launcher] $(date '+%H:%M:%S') start $tag -> $url (model $MODEL, codex ceiling ${timeout}s)"
  MODEL="$MODEL" VLLM_URL="$url" CODEX_TIMEOUT="$timeout" \
    bash scripts/run_cell.sh "$agent" "$channel" "$SPLIT_ROOT/$scene" "$tag" "$MAX_STEPS" \
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
    tag="$PREFIX-$agent-$channel$(arm_suffix "$agent")-$s"
    r="outputs/$tag/$MODEL_DIR/4-hop/$s/result.json"
    if [[ -f "$r" ]]; then
      python3 -c "import json,sys; j=json.load(open(sys.argv[1])); print(f\"{sys.argv[2]:30s} steps={j['total_steps']:3d} {j['termination_reason']:10s} milestones={j['milestones_completed']}/{j['milestones_trackable']} sandboxed={j.get('codex_sandboxed','-')}\")" "$r" "$tag"
    else
      echo "$tag: NO RESULT"
    fi
  done
done
