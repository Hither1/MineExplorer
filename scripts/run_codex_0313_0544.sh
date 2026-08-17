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

# MINEEXPLORER_ROOT when running from a snapshot copy, where this script's own
# location points at the run directory rather than the repo.
ROOT_DIR=${MINEEXPLORER_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
PYTHON_BIN=${PYTHON_BIN:-/work/nvme/bdrx/dzhang5/conda/envs/mineexplorer-qwen35-tf/bin/python}
# The sandbox wrapper, not codex itself. It is a drop-in -- same argv, cwd is still the
# workspace -- and it is what keeps the agent off the scene metadata (whose milestone
# coordinates *are* the answer to a navigation task), off other runs' results, and off
# every network destination but the model API. CODEX_BIN=<the real codex> opts out
# deliberately, and the choice is recorded in each run's manifest.
CODEX_BIN=${CODEX_BIN:-$ROOT_DIR/prolong_mc/codex_sandbox.sh}
# The real binary the wrapper execs, and where the account credential lives.
CODEX_REAL_BIN=${CODEX_REAL_BIN:-/u/dzhang5/.nvm/versions/node/v22.16.0/bin/codex}
export CODEX_REAL_BIN
MODEL_ID=${MODEL_ID:-gpt-5.6-sol}
CODEX_EFFORT=${CODEX_EFFORT:-xhigh}
# MODEL_SERVER names a shared vLLM server (see scripts/serve_vllm.sh) to drive codex
# with instead of a hosted model. Unset means the hosted account model.
#
# This replaces a per-run `transformers serve` process. That started 52 GB of weights
# per job, had no paged KV cache -- a PRO-LONG episode died of allocator
# fragmentation, not capacity -- and needed a shim to tolerate the Codex CLI at all.
MODEL_SERVER=${MODEL_SERVER:-}
CODEX_BASE_URL=${CODEX_BASE_URL:-}
MAX_STEPS=${MAX_STEPS:-300}
LOADING_COMMAND_STEPS=${LOADING_COMMAND_STEPS:-20}
TEMPERATURE=${TEMPERATURE:-0.7}
AGENT_MODE=${AGENT_MODE:-default}
MILESTONE_HINT=${MILESTONE_HINT:-0}
# PRO-LONG's own ablations (arm C), read by --agent-mode prolong only. Empty means the
# unablated arm; PROLONG_LOG_WINDOW=0 is upstream's "latest state only".
PROLONG_LOG_WINDOW=${PROLONG_LOG_WINDOW:-}
PROLONG_STATELESS=${PROLONG_STATELESS:-0}
if [[ "$AGENT_MODE" != prolong && ( -n "$PROLONG_LOG_WINDOW" || "$PROLONG_STATELESS" == 1 ) ]]; then
  # Checked before anything is started, because the flags reach only ProlongAgent: a
  # mislabelled cell would otherwise run the unablated arm under an ablation's name and
  # be pooled with the arm it was launched to be the control for.
  echo "PROLONG_* ablations require AGENT_MODE=prolong (got '$AGENT_MODE')" >&2
  exit 2
fi
RUN_ROOT=${ART_DIR:-$ROOT_DIR/artifacts/manual-codex-0313-0544}
OUTPUT_DIR=${OUTPUT_DIR:-$RUN_ROOT/results}
TASK_VIEW=$RUN_ROOT/benchmark-view

if [[ -z ${MC_SANDBOX_URL:-} ]]; then
  echo "MC_SANDBOX_URL is required; wrap this with scripts/with_minecraft_arm64.sh" >&2
  exit 2
fi

# The master CODEX_HOME: it holds the credential and nothing else, and the wrapper binds
# only its auth.json, read-only, into a home it derives per episode. The global ~/.codex
# is never used -- it carries `model = "gpt-5.6-sol"`, project trust settings and an
# AGENTS.md that `--ignore-user-config` does NOT suppress, and its sessions/ would let
# one episode read another's conversation.
export CODEX_EVAL_HOME=${CODEX_EVAL_HOME:-$RUN_ROOT/codex-home}
mkdir -p "$CODEX_EVAL_HOME" "$RUN_ROOT" "$OUTPUT_DIR" "$TASK_VIEW"
# Hosted arm only. Linking the account credential used to also pull in the account's MCP
# app tools -- github, slack, gmail, drive, sites -- which added 275 KB of JSON schema to
# *every* request: 23 tools and 312 KB instead of 10 and 18 KB, about 78k tokens against
# 4.6k, enough to overflow a 65536-token context and fail 94% of one run's calls. That is
# now closed at the source by SAFE_CODEX_FLAGS (prolong_mc/codex_backend.py), which is a
# correctness fix as much as a cost one: those same tools are a route to the answers that
# no filesystem sandbox sits on. A locally served model authenticates with a dummy key and
# needs no credential at all.
if [[ -z "$MODEL_SERVER" ]]; then
  ln -sfn "$HOME/.codex/auth.json" "$CODEX_EVAL_HOME/auth.json"
else
  export CODEX_SANDBOX_NO_AUTH=1
fi
export CODEX_BIN MC_SANDBOX_URL PYTHONNOUSERSITE=1
# What the agent may reach through the sandbox's one exit. MC_SANDBOX_URL is deliberately
# absent: the runner steps the world, the agent only writes actions.json, and upstream
# draws the same line. A local model server is added below, once its URL is known.
export CODEX_SANDBOX_ALLOW=${CODEX_SANDBOX_ALLOW:-.chatgpt.com:443,.openai.com:443,chatgpt.com:443}
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

if [[ -n "$MODEL_SERVER" ]]; then
  export LOCAL_API_KEY=EMPTY
  # Resolving a URL is not the same as confirming what answers on it; the helper
  # asserts the live server serves the model this run claims to measure.
  CODEX_BASE_URL=$(bash "$ROOT_DIR/scripts/use_model_server.sh" "$MODEL_SERVER" "$MODEL_ID") || exit 1
  echo "codex -> $CODEX_BASE_URL"
  # The sandbox has no route out except the allowlist, so the served model has to be on
  # it or codex cannot reach the model at all.
  CODEX_SANDBOX_ALLOW="$CODEX_SANDBOX_ALLOW,$(printf '%s' "$CODEX_BASE_URL" | sed -E 's#^https?://##; s#/.*##')"
  export CODEX_SANDBOX_ALLOW
  echo "sandbox egress allowlist: $CODEX_SANDBOX_ALLOW"
  # Codex has no catalog entry for a locally served model, so it guesses the context
  # window. Take the number from the server's own advert rather than restating it
  # here: the two would drift, and the direction that hurts is codex believing there
  # is more room than the server will give it.
  DISCOVERY=${DISCOVERY_DIR:-$ROOT_DIR/artifacts/servers}/$MODEL_SERVER.json
  if CW=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["max_model_len"])' \
            "$DISCOVERY" 2>/dev/null); then
    export CODEX_MODEL_CONTEXT_WINDOW=$CW
    echo "codex context window <- $DISCOVERY: $CW"
  else
    echo "warning: $DISCOVERY has no max_model_len; codex keeps its built-in default" >&2
  fi
fi

# The sandbox's own assertions, through the wrapper this run will use. A bind that
# stopped binding, a home pointed back at a shared one, or a namespace that kept the
# host's network all produce runs that look exactly like isolated ones.
if [[ "$(basename "$CODEX_BIN")" == "codex_sandbox.sh" ]]; then
  "$PYTHON_BIN" -m prolong_mc.sandbox_selftest || {
    echo "sandbox selftest FAILED; not running" >&2; exit 1; }
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
if [[ -n "$PROLONG_LOG_WINDOW" ]]; then
  eval_args+=(--prolong-log-window "$PROLONG_LOG_WINDOW")
fi
if [[ "$PROLONG_STATELESS" == 1 ]]; then
  eval_args+=(--prolong-stateless)
fi

cd "$ROOT_DIR"
"$PYTHON_BIN" eval_benchmark.py "${eval_args[@]}"
