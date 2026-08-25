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
# Hosted codex (CODEX_HOSTED=1) authenticates with the master eval home's account,
# so the dummy-key switch stays off there; local serving keeps it on.
[[ "${CODEX_HOSTED:-0}" == "1" ]] || export CODEX_SANDBOX_NO_AUTH=1
export CODEX_SANDBOX_ALLOW=${CODEX_SANDBOX_ALLOW:-.chatgpt.com:443,.openai.com:443,chatgpt.com:443}
if [[ "${CODEX_HOSTED:-0}" != "1" ]]; then
  CODEX_SANDBOX_ALLOW="$CODEX_SANDBOX_ALLOW,$(printf '%s' "$VLLM_URL" | sed -E 's#^https?://##; s#/.*##')"
fi
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

# Outer isolation layer, ported from MCU-AgentBeats: a per-arm stub home so that any
# codex call that does fall back to the PATH wrapper (CODEX_BIN unset in a subprocess,
# an ad-hoc probe run from this environment) lands in an isolated home with empty
# AGENTS.md/skills stubs and its own sqlite thread store, instead of the account
# runtime-home. The sandboxed calls above bypass the wrapper and are not affected;
# this closes the paths around them. See scripts/codex-home.sh for the four measured
# failure modes it prevents.
eval "$(scripts/codex-home.sh "$AGENT_MODE-$CHANNEL")"

export LOCAL_API_KEY=EMPTY
export CODEX_MODEL_CONTEXT_WINDOW=131072
export CODEX_LOCAL_EFFORT=none          # thinking off on the codex channel
export CODEX_TIMEOUT=${CODEX_TIMEOUT:-900}
# Hosted resumed sessions (prolong) legitimately run 800-1100s per call once the
# session is ~25 turns deep -- the resume payload regrows every turn. 900 kills
# calls that were about to land and the retry pays the same latency again, so
# raise only that case; the stateless default-agent calls keep their tight cap.
if [[ "${CODEX_HOSTED:-0}" == "1" && "$CODEX_TIMEOUT" == "900" ]]; then
  export CODEX_TIMEOUT=1500
fi
export MC_RESET_TIMEOUT=${MC_RESET_TIMEOUT:-600}

# PROMPT_LAYOUT (legacy | static-first | append-only) is how the default/hypothesis agents lay
# out each request for the server's prefix cache -- see PROMPT_LAYOUTS in mc_agent/context.py.
# legacy is today's prompt byte for byte; anything else is a different arm, so give it its
# own tag. result.json records the value either way.
PROMPT_LAYOUT=${PROMPT_LAYOUT:-legacy}
# RESPONSE_STYLE (full | compact) is what those agents ask the model to write back -- see
# RESPONSE_STYLES there. full is today's protocol; compact is one line, memory / hypotheses /
# plan only when they change. Same rule: not full = a different arm, own tag, recorded.
RESPONSE_STYLE=${RESPONSE_STYLE:-full}
# CODEX_OUTPUT_SCHEMA=1 constrains the codex channel's final message to the agent's reply
# schema (`codex exec --output-schema`); it is the only channel that can answer with
# unparsable text. Codex channel + default/hypothesis only, and a different arm.
CODEX_OUTPUT_SCHEMA=${CODEX_OUTPUT_SCHEMA:-0}

ARGS=(--model "$MODEL" --benchmark-dir "$BENCH_DIR" --output-dir "$OUT"
      --max-steps "$MAX_STEPS" --temperature 0.7 --agent-mode "$AGENT_MODE" --resume)

# All three knobs above describe the default/hypothesis agents' request. PRO-LONG writes its
# own prompt (prolong_mc: its own AGENTS.md workflow and one resumed conversation), so
# eval_benchmark.py rejects all three for --agent-mode prolong rather than accept a flag it
# would silently ignore. Pass them only to the agents they reach, so one campaign can put the
# direct arms on a faster layout while the prolong arm runs its own protocol unchanged --
# which is also why launch_4hop.sh gives a prolong cell no layout suffix.
if [[ "$AGENT_MODE" != "prolong" ]]; then
  ARGS+=(--prompt-layout "$PROMPT_LAYOUT" --response-style "$RESPONSE_STYLE")
fi

case "$CHANNEL" in
  vllm)  ARGS+=(--use-vllm --vllm-url "$VLLM_URL") ;;
  codex)
    if [[ "${CODEX_HOSTED:-0}" == "1" ]]; then
      # Hosted account model: no base_url (codex talks to its own provider), and the
      # effort is the wire value itself -- "none" is the qwen protocol's thinking-off.
      ARGS+=(--use-codex --codex-effort "${CODEX_EFFORT:-none}")
    else
      ARGS+=(--use-codex --codex-base-url "$VLLM_URL" --codex-effort low)
    fi
    [[ "$CODEX_OUTPUT_SCHEMA" == "1" && "$AGENT_MODE" != "prolong" ]] && ARGS+=(--codex-output-schema)
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

knobs="layout=$PROMPT_LAYOUT style=$RESPONSE_STYLE schema=$CODEX_OUTPUT_SCHEMA"
[[ "$AGENT_MODE" == "prolong" ]] && knobs="layout/style/schema=n/a (PRO-LONG writes its own prompt)"
echo "[cell] $TAG  agent=$AGENT_MODE channel=$CHANNEL $knobs steps=$MAX_STEPS bench=$BENCH_DIR"
exec .venv/bin/python eval_benchmark.py "${ARGS[@]}"
