#!/usr/bin/env bash
# One cell of the 4-hop axis: <agent-mode> x <channel> on one scene.
#
#   scripts/run_cell.sh <agent-mode> <channel> <benchmark-dir> <tag> [max-steps]
#
#   agent-mode : default | hypothesis | prolong   (prolong is codex-only)
#   channel    : vllm | codex
#
# Serving contract, pinned here so a run records it rather than inheriting it:
# thinking OFF on both channels, 4096 output cap, temperature 0.7, 300 steps.
# The two channels are switched from opposite ends -- the server's
# --default-chat-template-kwargs governs vllm, CODEX_LOCAL_EFFORT governs codex --
# so both are set together or the channel axis stops being a control.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

AGENT_MODE=${1:?agent-mode}
CHANNEL=${2:?channel}
BENCH_DIR=${3:?benchmark-dir}
TAG=${4:?tag}
MAX_STEPS=${5:-300}

MODEL=Qwen3.8-27B
VLLM_URL=${VLLM_URL:-http://192.168.2.20:8001/v1}
OUT="outputs/$TAG"

set -a; . ./.env; set +a

# Per-cell CODEX_HOME. eval_benchmark reads $CODEX_HOME once, process-wide, so
# concurrent cells sharing one home would share codex's rollout store and its
# session state. The account credential is symlinked in rather than the whole
# home copied: linking ~/.codex wholesale drags in the account's MCP tool
# schemas, which cost 78k tokens per request and overflowed a context once.
export CODEX_HOME="$ROOT/$OUT/.codex-home"
mkdir -p "$CODEX_HOME" "$OUT"
[[ -f "$HOME/.codex/auth.json" && ! -e "$CODEX_HOME/auth.json" ]] && \
  ln -sfn "$HOME/.codex/auth.json" "$CODEX_HOME/auth.json"

export LOCAL_API_KEY=EMPTY
export CODEX_MODEL_CONTEXT_WINDOW=131072
export CODEX_LOCAL_EFFORT=none          # thinking off on the codex channel
export CODEX_TIMEOUT=${CODEX_TIMEOUT:-900}
export MC_RESET_TIMEOUT=${MC_RESET_TIMEOUT:-600}

ARGS=(--model "$MODEL" --benchmark-dir "$BENCH_DIR" --output-dir "$OUT"
      --max-steps "$MAX_STEPS" --temperature 0.7 --agent-mode "$AGENT_MODE" --resume)

case "$CHANNEL" in
  vllm)  ARGS+=(--use-vllm --vllm-url "$VLLM_URL") ;;
  codex) ARGS+=(--use-codex --codex-base-url "$VLLM_URL" --codex-effort low) ;;
  *) echo "channel must be vllm or codex, got '$CHANNEL'" >&2; exit 2 ;;
esac

echo "[cell] $TAG  agent=$AGENT_MODE channel=$CHANNEL steps=$MAX_STEPS bench=$BENCH_DIR"
exec .venv/bin/python eval_benchmark.py "${ARGS[@]}"
