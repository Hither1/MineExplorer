#!/usr/bin/env bash
set -euo pipefail

# MINEEXPLORER_ROOT when running from a snapshot copy, where this script's own
# location points at the run directory rather than the repo.
ROOT_DIR=${MINEEXPLORER_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
PYTHON_BIN=${PYTHON_BIN:-/work/nvme/bdrx/dzhang5/conda/envs/mineexplorer-qwen35-tf/bin/python}
HF_HOME=${HF_HOME:-/work/nvme/bdrx/dzhang5/huggingface}
MODEL_REVISION=${MODEL_REVISION:-1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0}
MODEL_ID=${MODEL_ID:-Qwen/Qwen3.8-27B}
# Derived from the job id: ghx4 nodes are shared, and a fixed port let two of our
# own jobs collide -- the loser exited while /health still answered from the
# winner's server, so the run scored against the wrong process.
# The shared vLLM server (scripts/serve_vllm.sh), resolved at run time. Each job used
# to start its own transformers-serve: 52 GB of weights per job and no paged KV cache.
MODEL_SERVER=${MODEL_SERVER:-qwen38-27b}
QWEN_API_URL=${QWEN_API_URL:-}
MAX_STEPS=${MAX_STEPS:-300}
LOADING_COMMAND_STEPS=${LOADING_COMMAND_STEPS:-20}
# Captured before the default is applied: `${TEMPERATURE+1}` is set only when the caller
# exported one, which is the difference between "asked for 0.7" and "did not ask", and the
# advert below defers to the first.
TEMPERATURE_SET=${TEMPERATURE+1}
TEMPERATURE=${TEMPERATURE:-0.7}
AGENT_MODE=${AGENT_MODE:-default}
MILESTONE_HINT=${MILESTONE_HINT:-0}
RUN_ROOT=${ART_DIR:-$ROOT_DIR/artifacts/manual-qwen35-0313-0544}
OUTPUT_DIR=${OUTPUT_DIR:-$RUN_ROOT/results}
TASK_VIEW=$RUN_ROOT/benchmark-view

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "missing task Python: $PYTHON_BIN" >&2
  echo "run scripts/setup_deltaai_qwen35.sh first" >&2
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
# 27B weights leave roughly 40 GiB for KV and activations on a 95 GiB GH200, and a
# PRO-LONG prompt grows every turn (the log, plus an attached frame). What runs out
# first is not capacity but fragmentation: one run died with 9 GiB reserved and
# unallocated while a 2.3 GiB allocation failed.
export PYTORCH_CUDA_ALLOC_CONF=${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}
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

# Take the temperature from the server's own advert rather than from this script.
#
# The server pins sampling for both channels with --override-generation-config, but that
# is a *default*, and VLLMProvider puts `temperature` in every request, where an explicit
# value wins. So the codex arms ran the server's recipe while this arm sent 0.7 on top of
# the server's top_p -- a mixture matching neither recipe, and a channel control differing
# from the cells it controls in the variable it exists to hold fixed. Reading the advert
# keeps the value in one place; restating it here is exactly what let the two drift.
#
# Same pattern as the codex runner taking CODEX_MODEL_CONTEXT_WINDOW from max_model_len.
# An explicit TEMPERATURE still wins, for a deliberate probe. Read before the endpoints
# are contacted, since it needs only the advert, which is also what makes it testable.
if [[ -z ${TEMPERATURE_SET:-} ]]; then
  DISCOVERY=${DISCOVERY_DIR:-$ROOT_DIR/artifacts/servers}/$MODEL_SERVER.json
  if T=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sampling"]["temperature"])' \
           "$DISCOVERY" 2>/dev/null); then
    TEMPERATURE=$T
    echo "temperature <- $DISCOVERY: $TEMPERATURE"
  else
    echo "warning: $DISCOVERY has no sampling.temperature; using $TEMPERATURE" >&2
  fi
fi

curl -fsS "${MC_SANDBOX_URL%/}/monitor/alive" > "$RUN_ROOT/minecraft-alive.json"

if [[ -z "$QWEN_API_URL" ]]; then
  QWEN_API_URL=$(bash "$ROOT_DIR/scripts/use_model_server.sh" "$MODEL_SERVER" "$MODEL_ID") || exit 1
fi
export AGENT_API_BASE=$QWEN_API_URL

curl -fsS "$QWEN_API_URL/models" > "$RUN_ROOT/qwen-models.json"
#

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
