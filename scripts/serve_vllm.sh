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
# CUDA graphs over eager kernels, which is not the same choice as torch.compile.
# The first successful load died mid-"Dynamo bytecode transform" -- compilation
# spawns parallel workers and their host memory is what ran out -- and the response
# was --enforce-eager, carrying the reasoning that "one request at a time means CUDA
# graphs buy little". That has it backwards. Grace (ARM) cores pay a high per-kernel
# launch cost, and a 64-layer hybrid model decoding at batch size 1-2 is launch-bound
# precisely where graphs pay most: measured 12.5 tok/s per request under eager, with
# "Enforce eager set, disabling torch.compile and CUDAGraphs" in the server log.
#
# `mode=none` keeps the Dynamo/Inductor pass off, so the host-memory blowup cannot
# recur, while `cudagraph_mode=FULL_DECODE_ONLY` still captures graphs over the eager
# kernels. FULL_DECODE_ONLY is vLLM's own fallback for attention that cannot do
# piecewise graphs (vllm/config/compilation.py:1409), which is this architecture.
# VLLM_EAGER=1 restores --enforce-eager if a capture ever fails on a node; it is the
# escape hatch, not the default, because eager is what truncated the baseline arms.
EAGER=${VLLM_EAGER:-0}
# Cudagraphs on this architecture need this, and vLLM's default makes them impossible.
# Every decode sequence holds one Mamba cache block for its recurrent state, so graph
# capture refuses to run unless max_num_seqs fits in the blocks the KV budget bought:
# "max_num_seqs (1024) exceeds available Mamba cache blocks (610)" killed the first
# single-card attempt (job 2959383) at engine start, before any request existed.
#
# 32 rather than 610: at 131k per request the KV cache supports about 3.7 concurrent
# full-length sequences anyway, and the real load is a handful of evaluation jobs each
# with one or two requests in flight. A ceiling far above the demand only widens the set
# of batch sizes captured at startup. It is a floor on nothing -- requests queue rather
# than fail -- so the cost of being wrong is latency under a load we do not run.
MAX_NUM_SEQS=${VLLM_MAX_NUM_SEQS:-32}
# Two GPUs, not one. Tensor parallelism here buys latency, not capacity (27B in bf16
# is ~54 GB of a 120 GB GH200), and latency is what decides which arms finish: the
# non-PRO-LONG arms spend one full generation per step, so a slow decode truncates
# them at walltime while PRO-LONG, calling a sixth as often, finishes. A serving
# asymmetry that lands on one arm is not a neutral cost.
#
# TP is second in line behind graphs and depends on them: under eager, TP=2 adds two
# all-reduce launches per layer per token while shrinking the per-kernel work, so it
# is close to a wash. TP=4 divides every head count cleanly too, but 1N/4G queues too
# slowly on ghx4 to be worth the wait (dz, 2026-08-16).
TP=${VLLM_TP:-2}
# One per-request output cap for every arm, sized not to bind. VLLMProvider asks for
# 4096 on the direct path; the codex path cannot ask for anything -- it ignores
# max_tokens by design and codex 0.147 has no max-output-tokens key -- so the server is
# the only place the arms can be made to match.
#
# 16384 rather than 4096, because the cap has to clear what this model actually emits
# with thinking on. Tokenising every model-authored item across the finished Qwen3.8
# runs: p50 237, p90 1933, and 24 items over 4096, the largest a single 12,918-token
# message. A 4096 cap would have cut those mid-deliberation, and since the JSON comes
# *after* the prose, a truncated response yields no action at all. This still forecloses
# the runaway it was introduced for -- a repetition loop generating toward the 131k
# context end -- while leaving the longest observed response 20% of headroom.
#
# vLLM applies it as a hard ceiling, not a default: get_max_tokens() takes a min over the
# request's own value and this one, and --override-generation-config merges into the
# model's own generation config rather than replacing it (--generation-config defaults to
# "auto"; config/model.py:1608-1613), so the sampling below survives alongside it.
MAX_OUTPUT_TOKENS=${VLLM_MAX_OUTPUT_TOKENS:-16384}
# Sampling, set once on the server so both channels get the same one. The codex arms
# send no sampling parameters at all (captured off the wire: no temperature, no top_p),
# so without this they run on whatever the model ships while the direct-vLLM arm sends
# temperature=0.7 from eval_benchmark -- two arms of one matrix sampling differently.
# vLLM applies these defaults on the Responses path as well as the chat path
# (responses/serving.py:195,438), which is the path codex speaks.
#
# The values are Qwen3.8's own recipe for thinking mode, which is the mode this server
# runs and the mode the finished runs were taken in: "Thinking Mode: temperature=1.0,
# top_p=0.95, top_k=20, min_p=0.0, presence_penalty=0.0, repetition_penalty=1.0". They
# are also what the shipped generation_config.json carries, so this pins what was already
# in force rather than changing it -- the point being that it is now pinned for *both*
# channels instead of one, and recorded in the advert.
SAMPLING=${VLLM_SAMPLING:-'"temperature": 1.0, "top_p": 0.95, "top_k": 20, "min_p": 0.0, "repetition_penalty": 1.0'}
# Thinking on, pinned rather than inherited, and pinned to match the runs already taken.
#
# The alternative was measured and rejected. Pinning it off aligns with MineExplorer
# main's protocol, but Qwen3.8 defaults to thinking and its card warns that low reasoning
# effort in multi-turn agentic tasks "can lead to insufficient analysis, more failures,
# and repeated retries". That is what happened: with thinking off, the default arm looped
# on `echo ok` 87 times inside one call and burned the client timeout, where the same arm
# with thinking on never exceeded 3 tool calls across 46 calls. The damage was one-sided
# -- the PRO-LONG arm was unaffected -- and a comparison whose baseline our own serving
# choice crippled is worse than no comparison.
#
# Scope: this governs the direct-vLLM arm. The codex arms carry `reasoning.effort` on
# every request and vLLM synthesises enable_thinking from it, overriding this default, so
# they are pinned client-side instead (CODEX_LOCAL_EFFORT, mc_agent/llm_provider.py).
# Both are set to thinking-on so the two channels agree.
CHAT_TEMPLATE_KWARGS=${VLLM_CHAT_TEMPLATE_KWARGS:-'{"enable_thinking": true}'}
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

echo "starting vLLM: $MODEL_ID@$MODEL_REVISION on $HOST_FQDN:$PORT (max_len=$MAX_LEN" \
     "tp=$TP exec=$( [ "$EAGER" = 1 ] && echo eager || echo cudagraphs ) max_out=$MAX_OUTPUT_TOKENS" \
     "chat_template_kwargs=$CHAT_TEMPLATE_KWARGS)"
setsid "$PYTHON_BIN" -m vllm.entrypoints.openai.api_server \
  --model "$MODEL_ID" --revision "$MODEL_REVISION" \
  --served-model-name "$SERVED_NAME" \
  --host 0.0.0.0 --port "$PORT" \
  --max-model-len "$MAX_LEN" \
  --tensor-parallel-size "$TP" \
  --max-num-seqs "$MAX_NUM_SEQS" \
  --gpu-memory-utilization "$GPU_FRAC" \
  --trust-remote-code \
  --enable-auto-tool-choice --tool-call-parser "$TOOL_PARSER" \
  --override-generation-config "{\"max_new_tokens\": $MAX_OUTPUT_TOKENS, $SAMPLING}" \
  --default-chat-template-kwargs "$CHAT_TEMPLATE_KWARGS" \
  $( [ "$EAGER" = 1 ] && echo --enforce-eager || echo -cc.mode=none -cc.cudagraph_mode=FULL_DECODE_ONLY ) \
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

# The serving configuration travels with the advert, not just the URL. Two of these
# -- the output cap and the thinking pin -- change what the model produces, so a score
# is only comparable to another score served the same way, and "which server answered"
# has to be answerable months later from the run's own artifacts.
cat > "$DISCOVERY.tmp" <<JSON
{
  "url": "http://$HOST_FQDN:$PORT/v1",
  "host": "$HOST_FQDN",
  "port": $PORT,
  "model": "$SERVED_NAME",
  "revision": "$MODEL_REVISION",
  "max_model_len": $MAX_LEN,
  "max_output_tokens": $MAX_OUTPUT_TOKENS,
  "sampling": {$SAMPLING},
  "tensor_parallel_size": $TP,
  "execution": "$( [ "$EAGER" = 1 ] && echo eager || echo cudagraphs-full-decode-only )",
  "chat_template_kwargs": $CHAT_TEMPLATE_KWARGS,
  "job": "${SLURM_JOB_ID:-none}",
  "started_at": "$(date -Iseconds)"
}
JSON
mv "$DISCOVERY.tmp" "$DISCOVERY"
echo "vLLM ready and advertised: $DISCOVERY"
cat "$DISCOVERY"

# Stay alive for the allocation; evaluation jobs come and go against this process.
wait "$SERVER_PID"
