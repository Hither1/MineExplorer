#!/usr/bin/env bash
# Run the MineExplorer benchmark with a hosted model driven through the Codex CLI.
#
# Same agent, same scenes, same MilestoneChecker as scripts/run_qwen35_0313_0544.sh --
# only the provider differs, so the milestone counts are directly comparable to the
# Qwen3.5-27B numbers. No local model server and no GPU inference: the GPU allocation
# exists only because the Minecraft sandbox needs a node and DeltaAI will not schedule
# a GPU-less job.
#
# Caveat to carry into any comparison: Codex wraps each call in its own agent
# scaffolding (system prompt, tools, reasoning config), so this measures the model
# *through the Codex harness*, not as a plain VLM the way the vLLM path does.
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PYTHON_BIN=${PYTHON_BIN:-/work/nvme/bdrx/dzhang5/conda/envs/mineexplorer-qwen35-tf/bin/python}
CODEX_BIN=${CODEX_BIN:-/u/dzhang5/.nvm/versions/node/v22.16.0/bin/codex}
MODEL_ID=${MODEL_ID:-gpt-5.6-sol}
CODEX_EFFORT=${CODEX_EFFORT:-xhigh}
# LOCAL_MODEL=1 starts the transformers-serve shim and points codex at it, so the
# same harness can be driven by Qwen3.5-27B instead of a hosted model.
LOCAL_MODEL=${LOCAL_MODEL:-0}
# Derived from the job id, not fixed: ghx4 nodes are shared, so two of our own jobs
# landing on one node both tried to bind 30000. The loser exited while /health still
# answered -- from the winner's server, which has no shim -- and the whole run 422'd
# against a stranger's process while looking healthy.
QWEN_PORT=${QWEN_PORT:-$(( 20000 + ${SLURM_JOB_ID:-$$} % 20000 ))}
CODEX_BASE_URL=${CODEX_BASE_URL:-}
SERVER_PID=""
SERVER_PGID=""
MAX_STEPS=${MAX_STEPS:-300}
LOADING_COMMAND_STEPS=${LOADING_COMMAND_STEPS:-20}
TEMPERATURE=${TEMPERATURE:-0.7}
AGENT_MODE=${AGENT_MODE:-default}
MILESTONE_HINT=${MILESTONE_HINT:-0}
RUN_ROOT=${ART_DIR:-$ROOT_DIR/artifacts/manual-codex-0313-0544}
OUTPUT_DIR=${OUTPUT_DIR:-$RUN_ROOT/results}
TASK_VIEW=$RUN_ROOT/benchmark-view
SERVER_LOG=$RUN_ROOT/qwen-server.log

if [[ -z ${MC_SANDBOX_URL:-} ]]; then
  echo "MC_SANDBOX_URL is required; wrap this with scripts/with_minecraft_arm64.sh" >&2
  exit 2
fi

# Throwaway CODEX_HOME with only the credential linked in: the real one carries
# `model = "gpt-5.6-sol"` and project trust settings we do not want silently applied,
# and PRO-LONG refuses to mount the global ~/.codex for the same reason.
export CODEX_HOME=$RUN_ROOT/codex-home
mkdir -p "$CODEX_HOME" "$RUN_ROOT" "$OUTPUT_DIR" "$TASK_VIEW"
ln -sfn "$HOME/.codex/auth.json" "$CODEX_HOME/auth.json"
export CODEX_BIN MC_SANDBOX_URL PYTHONNOUSERSITE=1
# eval_benchmark.py:33-37 hard-fails at import unless both of these are set, before
# any provider is chosen. The Codex path reads neither; these just get past the check.
export AGENT_API_KEY=${AGENT_API_KEY:-EMPTY}
export AGENT_API_BASE=${AGENT_API_BASE:-http://unused.invalid/v1}

for scene in ${SCENES:-0313 0544}; do
  if [[ ! -d "$ROOT_DIR/benchmark/$scene" ]]; then
    echo "unknown scene: benchmark/$scene" >&2
    exit 2
  fi
  ln -sfn "$ROOT_DIR/benchmark/$scene" "$TASK_VIEW/$scene"
done

curl -fsS "${MC_SANDBOX_URL%/}/monitor/alive" > "$RUN_ROOT/minecraft-alive.json"

cleanup() {
  if [[ -n "$SERVER_PGID" ]] && kill -0 -- "-$SERVER_PGID" 2>/dev/null; then
    kill -TERM -- "-$SERVER_PGID" 2>/dev/null || true
    for _ in $(seq 1 20); do kill -0 -- "-$SERVER_PGID" 2>/dev/null || break; sleep 0.5; done
    kill -KILL -- "-$SERVER_PGID" 2>/dev/null || true
  fi
  [[ -n "$SERVER_PID" ]] && wait "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if [[ "$LOCAL_MODEL" == 1 ]]; then
  export LOCAL_API_KEY=EMPTY
  export HF_HOME=${HF_HOME:-/work/nvme/bdrx/dzhang5/huggingface}
  setsid "$PYTHON_BIN" "$ROOT_DIR/scripts/serve_qwen_for_codex.py" serve "$MODEL_ID" \
    --host 127.0.0.1 --port "$QWEN_PORT" --device cuda:0 --dtype auto \
    --reasoning off --log-level info > "$SERVER_LOG" 2>&1 &
  SERVER_PID=$!
  SERVER_PGID=$SERVER_PID
  for _ in $(seq 1 360); do
    curl -fsS "http://127.0.0.1:$QWEN_PORT/health" >/dev/null 2>&1 && break
    kill -0 "$SERVER_PID" 2>/dev/null || { echo "model server died; see $SERVER_LOG" >&2; exit 1; }
    sleep 5
  done
  # A healthy /health is not proof the server is ours; confirm we are still running
  # and that nothing else claimed the port first.
  if ! kill -0 "$SERVER_PID" 2>/dev/null || grep -q "address already in use" "$SERVER_LOG"; then
    echo "our model server is not the one answering on $QWEN_PORT; see $SERVER_LOG" >&2
    exit 1
  fi
  CODEX_BASE_URL=${CODEX_BASE_URL:-http://127.0.0.1:$QWEN_PORT/v1}
  echo "local model server ready; codex -> $CODEX_BASE_URL"
fi

eval_args=(
  --model "$MODEL_ID"
  --benchmark-dir "$TASK_VIEW"
  --output-dir "$OUTPUT_DIR"
  --loading-command-steps "$LOADING_COMMAND_STEPS"
  --max-steps "$MAX_STEPS"
  --num-workers 1
  --use-codex
  --codex-effort "$CODEX_EFFORT"
  --codex-base-url "$CODEX_BASE_URL"
  --temperature "$TEMPERATURE"
  --agent-mode "$AGENT_MODE"
  --resume
)
if [[ "$MILESTONE_HINT" == 1 ]]; then
  eval_args+=(--milestone-hint)
else
  eval_args+=(--no-milestone-hint)
fi

cd "$ROOT_DIR"
"$PYTHON_BIN" eval_benchmark.py "${eval_args[@]}"
