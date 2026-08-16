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

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PYTHON_BIN=${VLLM_PYTHON:-/work/nvme/bdrx/dzhang5/conda/envs/mineexplorer-vllm/bin/python}
MODEL_ID=${MODEL_ID:-Qwen/Qwen3.8-27B}
MODEL_REVISION=${MODEL_REVISION:-1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0}
SERVED_NAME=${SERVED_NAME:-$MODEL_ID}
# 30000-39999: disjoint from the Minecraft sandbox's 40000-59999, because a job runs
# both and a shared node runs several jobs.
PORT=${VLLM_PORT:-$(( 30000 + ${SLURM_JOB_ID:-$$} % 10000 ))}
MAX_LEN=${VLLM_MAX_MODEL_LEN:-131072}
GPU_FRAC=${VLLM_GPU_FRACTION:-0.90}
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
  --gpu-memory-utilization "$GPU_FRAC" \
  --trust-remote-code \
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
