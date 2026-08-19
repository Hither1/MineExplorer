#!/usr/bin/env bash
# One cell of the 4-hop axis: <agent-mode> x <channel> on one scene.
#
#   scripts/run_cell.sh <agent-mode> <channel> <benchmark-dir> <tag> [max-steps]
#
#   agent-mode : default | hypothesis | prolong   (prolong is codex-only)
#   channel    : vllm | codex
#
# Serving contract, pinned here so a run records it rather than inheriting it:
# thinking OFF on both channels, temperature 0.7, 300 steps. The output cap is the
# server's (`max_new_tokens` in its --override-generation-config; 1024 since the
# 2026-08-18 relaunch) -- it is the only setting that reaches both channels, since
# codex sends no max_output_tokens and vLLM takes the min for the direct arm.
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

# The served model name, which is also the results subdirectory
# (eval_benchmark.py: out_root = <output-dir>/<model>). The a227 servers alias both
# checkpoints, so this is the whole of what switches a campaign between them.
MODEL=${MODEL:-Qwen3.8-27B}
VLLM_URL=${VLLM_URL:-http://192.168.2.20:8001/v1}
OUT="outputs/$TAG"

set -a; . ./.env; set +a

mkdir -p "$OUT"

# The codex channel runs through prolong_mc/codex_sandbox.sh, not through the `codex`
# on PATH. Two reasons, both measured on 2026-08-18:
#   * the `codex` on PATH here is a bash wrapper that forces CODEX_HOME=~/.codex/runtime-home
#     and links the account's global AGENTS.md and ~40 personal skills into it, so a
#     per-cell CODEX_HOME set here was silently ignored and every codex turn carried
#     ~5-6k tokens of the user's own instructions ahead of the PRO-LONG system prompt;
#   * without the wrapper the agent can read anything this user can, including
#     bench_*/<scene>/multi-agent/metadata.json, which holds the milestone coordinates.
# The sandbox gives codex a per-episode home (<workspace>.codexhome) holding nothing but
# an empty skills marker, a read scope of the workspace only, and one route out: the
# allowlisting proxy, which must name the model server. The local arm authenticates
# with the dummy env key, so no account credential is bound in (CODEX_SANDBOX_NO_AUTH).
# result.json records `codex_sandboxed: true` off $CODEX_BIN, so a run taken this way
# cannot be pooled with the earlier unsandboxed ones without saying so.
export CODEX_BIN="$ROOT/prolong_mc/codex_sandbox.sh"
export CODEX_REAL_BIN=${CODEX_REAL_BIN:-$HOME/.nvm/versions/node/v22.18.0/bin/codex}
export CODEX_SANDBOX_NO_AUTH=1
export CODEX_SANDBOX_ALLOW=${CODEX_SANDBOX_ALLOW:-.chatgpt.com:443,.openai.com:443,chatgpt.com:443}
CODEX_SANDBOX_ALLOW="$CODEX_SANDBOX_ALLOW,$(printf '%s' "$VLLM_URL" | sed -E 's#^https?://##; s#/.*##')"
export CODEX_SANDBOX_ALLOW

# The default/hypothesis agents drive codex through CodexProvider: one fresh `codex exec`
# per step in a throwaway temp workspace. Left alone, the sandbox would derive a new
# <workspace>.codexhome under /tmp for every call and nothing would clean it, and the
# rollout -- the only record of what the model did inside the call (the --json event
# stream does not list view_image calls) -- would go with it. One home per cell keeps
# every step's rollout under the cell's own output tree. PRO-LONG keeps its per-workspace
# home (one resumable session per episode), so it is not touched.
if [[ "$CHANNEL" == "codex" && "$AGENT_MODE" != "prolong" ]]; then
  export CODEX_EPISODE_HOME="$ROOT/$OUT/codex_home"
fi

export LOCAL_API_KEY=EMPTY
export CODEX_MODEL_CONTEXT_WINDOW=131072
export CODEX_LOCAL_EFFORT=none          # thinking off on the codex channel
export CODEX_TIMEOUT=${CODEX_TIMEOUT:-900}
export MC_RESET_TIMEOUT=${MC_RESET_TIMEOUT:-600}

ARGS=(--model "$MODEL" --benchmark-dir "$BENCH_DIR" --output-dir "$OUT"
      --max-steps "$MAX_STEPS" --temperature 0.7 --agent-mode "$AGENT_MODE" --resume)

case "$CHANNEL" in
  vllm)  ARGS+=(--use-vllm --vllm-url "$VLLM_URL") ;;
  codex)
    ARGS+=(--use-codex --codex-base-url "$VLLM_URL" --codex-effort low)
    # The sandbox's own assertions, through the wrapper this cell will use, before a
    # single step is spent. Set SKIP_SANDBOX_SELFTEST=1 only for a deliberate probe.
    # (without the per-cell episode home: the selftest asserts the wrapper's own
    # per-workspace derivation, which an exported CODEX_EPISODE_HOME overrides)
    if [[ "${SKIP_SANDBOX_SELFTEST:-0}" != "1" ]]; then
      env -u CODEX_EPISODE_HOME .venv/bin/python -m prolong_mc.sandbox_selftest || {
        echo "sandbox selftest FAILED; not running" >&2; exit 1; }
    fi
    ;;
  *) echo "channel must be vllm or codex, got '$CHANNEL'" >&2; exit 2 ;;
esac

echo "[cell] $TAG  agent=$AGENT_MODE channel=$CHANNEL steps=$MAX_STEPS bench=$BENCH_DIR"
exec .venv/bin/python eval_benchmark.py "${ARGS[@]}"
