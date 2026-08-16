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
MAX_STEPS=${MAX_STEPS:-300}
LOADING_COMMAND_STEPS=${LOADING_COMMAND_STEPS:-20}
TEMPERATURE=${TEMPERATURE:-0.7}
AGENT_MODE=${AGENT_MODE:-default}
MILESTONE_HINT=${MILESTONE_HINT:-0}
RUN_ROOT=${ART_DIR:-$ROOT_DIR/artifacts/manual-codex-0313-0544}
OUTPUT_DIR=${OUTPUT_DIR:-$RUN_ROOT/results}
TASK_VIEW=$RUN_ROOT/benchmark-view

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

eval_args=(
  --model "$MODEL_ID"
  --benchmark-dir "$TASK_VIEW"
  --output-dir "$OUTPUT_DIR"
  --loading-command-steps "$LOADING_COMMAND_STEPS"
  --max-steps "$MAX_STEPS"
  --num-workers 1
  --use-codex
  --codex-effort "$CODEX_EFFORT"
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
