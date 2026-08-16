#!/usr/bin/env bash
# One long-lived vLLM server that every evaluation run queries.
#
# Replaces the per-run `transformers serve` process. That design loaded 52 GB of
# weights once per job, ran without a paged KV cache -- a PRO-LONG episode eventually
# died of allocator fragmentation, not capacity -- and needed a shim to survive the
# Codex CLI's requests at all (`client_metadata` dropped, `developer` aliased to
# `system`, system messages merged). vLLM needs none of that: it implements the
# Responses API the CLI speaks, natively.
#
# The server publishes host and port to a discovery file so evaluation jobs, which
# land on other nodes, can find it and assert they are talking to the right model.
set -uo pipefail

# MINEEXPLORER_ROOT when running from a snapshot copy, where this script's own
# location points at the run directory rather than the repo.
ROOT_DIR=${MINEEXPLORER_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
PYTHON_BIN=${VLLM_PYTHON:-/work/nvme/bdrx/dzhang5/conda/envs/mineexplorer-vllm/bin/python}
MODEL_ID=${MODEL_ID:-Qwen/Qwen3.8-27B}
MODEL_REVISION=${MODEL_REVISION:-1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0}
SERVED_NAME=${SERVED_NAME:-$MODEL_ID}
# 30000-39999: disjoint from the Minecraft sandbox's 40000-59999, because a job runs
# both and a shared node runs several jobs.
PORT=${VLLM_PORT:-$(( 30000 + ${SLURM_JOB_ID:-$$} % 10000 ))}
MAX_LEN=${VLLM_MAX_MODEL_LEN:-131072}
GPU_FRAC=${VLLM_GPU_FRACTION:-0.90}
# Qwen3.8 emits XML tool calls -- <tool_call><function=name><parameter=p>value --
# not Hermes JSON, so `qwen3_xml` is the parser that turns them into structured
# tool_calls. Without it vLLM returns the raw text, codex sees no tool call at all,
# and the agent silently cannot act: a failure that looks like a bad model rather
# than a missing flag.
TOOL_PARSER=${VLLM_TOOL_PARSER:-qwen3_xml}
# Eager by default. torch.compile is where the first successful load died: the step
# was killed mid-"Dynamo bytecode transform" with the weights already resident, and
# compilation spawns parallel workers whose host memory is what ran out. This
# workload is one agent request at a time, so CUDA graphs buy little. Set
# VLLM_EAGER=0 to re-enable compilation once the stack has proven itself.
EAGER=${VLLM_EAGER:-1}
# One GPU holds the model comfortably -- 27B in bf16 is ~54 GB of a 120 GB GH200 --
# so tensor parallelism here buys latency, not capacity. It is worth buying: the
# per-step cost of the non-PRO-LONG arms is one full generation, and at TP=1 with
# eager execution the server decodes ~10-13 tokens/s per request, which is what puts
# a 150-step baseline episode past its walltime while PRO-LONG, making a sixth as
# many calls, finishes comfortably. A serving-speed asymmetry that lands on one arm
# is not a neutral cost.
TP=${VLLM_TP:-1}
SERVER_SLUG=${SERVER_SLUG:-qwen38-27b}
DISCOVERY_DIR=${DISCOVERY_DIR:-$ROOT_DIR/artifacts/servers}
DISCOVERY=$DISCOVERY_DIR/$SERVER_SLUG.json
READY_TIMEOUT=${VLLM_READY_TIMEOUT:-2400}
LOG=${ART_DIR:-$ROOT_DIR/artifacts}/vllm-server.log

export HF_HOME=${HF_HOME:-/work/nvme/bdrx/dzhang5/huggingface}
export PYTHONNOUSERSITE=1
export VLLM_LOGGING_LEVEL=${VLLM_LOGGING_LEVEL:-INFO}

mkdir -p "$DISCOVERY_DIR" "$(dirname "$LOG")"
HOST_FQDN=$(hostname -s)

# Import the model module before starting vLLM, under the same environment the
# server runs in. A dependency installed into the *user* site-packages is invisible
# under PYTHONNOUSERSITE=1, so it passes a casual login-node check and then fails on
# the node: einops did exactly that, twice, at a queue wait each time. Checking here
# turns a 60-second startup crash into an immediate, named failure -- and running the
# same line before submitting turns it into no queue wait at all.
if ! "$PYTHON_BIN" -c "import vllm.model_executor.models.qwen3_5" >/dev/null 2>&1; then
  echo "serving env cannot import the model module (deps missing under PYTHONNOUSERSITE=1):" >&2
  "$PYTHON_BIN" -c "import vllm.model_executor.models.qwen3_5" 2>&1 | tail -6 >&2
  exit 1
fi

cleanup() {
  # Remove our own advert only. A stale discovery file pointing at a dead node is
  # exactly how a run ends up scoring against nothing.
  if [[ -f $DISCOVERY ]] && grep -q "\"job\": \"${SLURM_JOB_ID:-none}\"" "$DISCOVERY" 2>/dev/null; then
    rm -f "$DISCOVERY"
  fi
  [[ -n ${SERVER_PGID:-} ]] && kill -TERM -- "-$SERVER_PGID" 2>/dev/null
  true
}
trap cleanup EXIT INT TERM

echo "starting vLLM: $MODEL_ID@$MODEL_REVISION on $HOST_FQDN:$PORT (max_len=$MAX_LEN)"
setsid "$PYTHON_BIN" -m vllm.entrypoints.openai.api_server \
  --model "$MODEL_ID" --revision "$MODEL_REVISION" \
  --served-model-name "$SERVED_NAME" \
  --host 0.0.0.0 --port "$PORT" \
  --max-model-len "$MAX_LEN" \
  --tensor-parallel-size "$TP" \
  --gpu-memory-utilization "$GPU_FRAC" \
  --trust-remote-code \
  --enable-auto-tool-choice --tool-call-parser "$TOOL_PARSER" \
  $( [ "$EAGER" = 1 ] && echo --enforce-eager ) \
  > "$LOG" 2>&1 &
SERVER_PID=$!
SERVER_PGID=$SERVER_PID

deadline=$((SECONDS + READY_TIMEOUT))
while true; do
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "vLLM exited before becoming ready; see $LOG" >&2
    tail -40 "$LOG" >&2
    exit 1
  fi
  if curl -fsS "http://127.0.0.1:$PORT/v1/models" > /dev/null 2>&1; then
    break
  fi
  if (( SECONDS > deadline )); then
    echo "vLLM not ready within ${READY_TIMEOUT}s; see $LOG" >&2
    tail -40 "$LOG" >&2
    exit 1
  fi
  sleep 10
done

# Assert the server is serving what we asked for before advertising it. A run that
# discovers the wrong model produces numbers under the wrong name, which is worse
# than a run that fails to start.
SERVED=$(curl -fsS "http://127.0.0.1:$PORT/v1/models" | "$PYTHON_BIN" -c \
  'import json,sys; print(json.load(sys.stdin)["data"][0]["id"])')
if [[ "$SERVED" != "$SERVED_NAME" ]]; then
  echo "server reports model '$SERVED', expected '$SERVED_NAME'" >&2
  exit 1
fi

cat > "$DISCOVERY.tmp" <<JSON
{
  "url": "http://$HOST_FQDN:$PORT/v1",
  "host": "$HOST_FQDN",
  "port": $PORT,
  "model": "$SERVED_NAME",
  "revision": "$MODEL_REVISION",
  "max_model_len": $MAX_LEN,
  "job": "${SLURM_JOB_ID:-none}",
  "started_at": "$(date -Iseconds)"
}
JSON
mv "$DISCOVERY.tmp" "$DISCOVERY"
echo "vLLM ready and advertised: $DISCOVERY"
cat "$DISCOVERY"

# Stay alive for the allocation; evaluation jobs come and go against this process.
wait "$SERVER_PID"
