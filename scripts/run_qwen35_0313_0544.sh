#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PYTHON_BIN=${PYTHON_BIN:-/work/nvme/bdrx/dzhang5/conda/envs/mineexplorer-qwen35-tf/bin/python}
TRANSFORMERS_BIN=${TRANSFORMERS_BIN:-$(dirname "$PYTHON_BIN")/transformers}
HF_HOME=${HF_HOME:-/work/nvme/bdrx/dzhang5/huggingface}
MODEL_REVISION=${MODEL_REVISION:-fc05daec18b0a78c049392ed2e771dde82bdf654}
MODEL_ID=${MODEL_ID:-Qwen/Qwen3.5-27B@$MODEL_REVISION}
# Derived from the job id: ghx4 nodes are shared, and a fixed port let two of our
# own jobs collide -- the loser exited while /health still answered from the
# winner's server, so the run scored against the wrong process.
QWEN_PORT=${QWEN_PORT:-$(( 20000 + ${SLURM_JOB_ID:-$$} % 20000 ))}
QWEN_API_URL=${QWEN_API_URL:-http://127.0.0.1:$QWEN_PORT/v1}
QWEN_API_URL=${QWEN_API_URL%/}
QWEN_SERVER_URL=${QWEN_API_URL%/v1}
START_QWEN_SERVER=${START_QWEN_SERVER:-1}
MAX_STEPS=${MAX_STEPS:-300}
LOADING_COMMAND_STEPS=${LOADING_COMMAND_STEPS:-20}
TEMPERATURE=${TEMPERATURE:-0.7}
AGENT_MODE=${AGENT_MODE:-default}
MILESTONE_HINT=${MILESTONE_HINT:-0}
RUN_ROOT=${ART_DIR:-$ROOT_DIR/artifacts/manual-qwen35-0313-0544}
OUTPUT_DIR=${OUTPUT_DIR:-$RUN_ROOT/results}
TASK_VIEW=$RUN_ROOT/benchmark-view
SERVER_LOG=$RUN_ROOT/qwen-server.log
SERVER_PID=""
SERVER_PGID=""

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "missing task Python: $PYTHON_BIN" >&2
  echo "run scripts/setup_deltaai_qwen35.sh first" >&2
  exit 2
fi
if [[ ! -x "$TRANSFORMERS_BIN" ]]; then
  echo "missing Transformers CLI: $TRANSFORMERS_BIN" >&2
  exit 2
fi
if [[ -z ${MC_SANDBOX_URL:-} ]]; then
  cat >&2 <<'EOF'
MC_SANDBOX_URL is required. DeltaAI is aarch64, while the released
davidzhth/mineexplorer:0.0.1 image is linux/amd64 only. Point this variable
at a reachable x86_64 Minecraft sandbox service. The service can be prepared
with scripts/start_minecraft_docker.sh; do not start that image on the GH200
node.
EOF
  exit 2
fi

export HF_HOME MC_SANDBOX_URL PYTHONNOUSERSITE=1
export AGENT_API_KEY=${AGENT_API_KEY:-EMPTY}
export AGENT_API_BASE=${AGENT_API_BASE:-$QWEN_API_URL}

mkdir -p "$RUN_ROOT" "$OUTPUT_DIR" "$TASK_VIEW"
for scene in ${SCENES:-0313 0544}; do
  if [[ ! -d "$ROOT_DIR/benchmark/$scene" ]]; then
    echo "unknown scene: benchmark/$scene" >&2
    exit 2
  fi
  ln -sfn "$ROOT_DIR/benchmark/$scene" "$TASK_VIEW/$scene"
done

cleanup() {
  if [[ -n "$SERVER_PGID" ]] && kill -0 -- "-$SERVER_PGID" 2>/dev/null; then
    kill -TERM -- "-$SERVER_PGID" 2>/dev/null || true
    for _ in $(seq 1 20); do
      if ! kill -0 -- "-$SERVER_PGID" 2>/dev/null; then
        break
      fi
      sleep 0.5
    done
    if kill -0 -- "-$SERVER_PGID" 2>/dev/null; then
      kill -KILL -- "-$SERVER_PGID" 2>/dev/null || true
    fi
  fi
  if [[ -n "$SERVER_PID" ]]; then
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

curl -fsS "${MC_SANDBOX_URL%/}/monitor/alive" > "$RUN_ROOT/minecraft-alive.json"

if [[ "$START_QWEN_SERVER" == 1 ]]; then
  # Transformers may spawn a serving child. Give the service its own process
  # group so cleanup releases every descendant and the Slurm step can exit.
  setsid "$TRANSFORMERS_BIN" serve \
    "$MODEL_ID" \
    --host 127.0.0.1 \
    --port "$QWEN_PORT" \
    --device cuda:0 \
    --dtype auto \
    --reasoning off \
    --log-level info \
    > "$SERVER_LOG" 2>&1 &
  SERVER_PID=$!
  SERVER_PGID=$SERVER_PID

  for _ in $(seq 1 360); do
    if curl -fsS "$QWEN_SERVER_URL/health" > "$RUN_ROOT/qwen-health.json" 2>/dev/null; then
      break
    fi
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
      echo "Qwen server exited before becoming ready; see $SERVER_LOG" >&2
      exit 1
    fi
    sleep 5
  done
fi

curl -fsS "$QWEN_API_URL/models" > "$RUN_ROOT/qwen-models.json"

eval_args=(
  --model "$MODEL_ID"
  --benchmark-dir "$TASK_VIEW"
  --output-dir "$OUTPUT_DIR"
  --loading-command-steps "$LOADING_COMMAND_STEPS"
  --max-steps "$MAX_STEPS"
  --num-workers 1
  --use-vllm
  --vllm-url "$QWEN_API_URL"
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
