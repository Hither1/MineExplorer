#!/usr/bin/env bash
# G1: can the Codex CLI drive a model through a tool-using turn and produce the
# actions.json that PRO-LONG's runner consumes?
#
# Everything downstream of the PRO-LONG port depends on this, so it is deliberately
# the smallest thing that can answer it: no Minecraft, no PRO-LONG runner, just the
# CLI, a model, and PRO-LONG's own actions.json parser as the oracle.
#
# GATE_BACKEND=local  (default) local Qwen3.5-27B behind the transformers-serve shim.
# GATE_BACKEND=openai      hosted gpt-5.6-sol, no GPU and no local server.
#
# The two arms share the prompts, the flags and the oracle byte for byte, so a
# split verdict separates "the harness cannot work here" from "this model cannot
# drive it" -- the one distinction the local arm alone can never make.
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PYTHON_BIN=${PYTHON_BIN:-/work/nvme/bdrx/dzhang5/conda/envs/mineexplorer-qwen35-tf/bin/python}
TRANSFORMERS_BIN=${TRANSFORMERS_BIN:-$(dirname "$PYTHON_BIN")/transformers}
HF_HOME=${HF_HOME:-/work/nvme/bdrx/dzhang5/huggingface}
MODEL_REVISION=${MODEL_REVISION:-fc05daec18b0a78c049392ed2e771dde82bdf654}
MODEL_ID=${MODEL_ID:-Qwen/Qwen3.5-27B@$MODEL_REVISION}
# GATE_BACKEND, not BACKEND: the research harness exports BACKEND itself (it held the
# launcher's own path), so a run script that reads BACKEND silently gets the harness's
# value. This gate took the hosted branch that way while claiming to test a local model.
GATE_BACKEND=${GATE_BACKEND:-local}
OPENAI_MODEL=${OPENAI_MODEL:-gpt-5.6-sol}
OPENAI_EFFORT=${OPENAI_EFFORT:-xhigh}
# Derived from the job id, not fixed: ghx4 nodes are shared, so two of our own jobs
# landing on one node both tried to bind 30000. The loser exited while /health still
# answered -- from the winner's server, which has no shim -- and the whole run 422'd
# against a stranger's process while looking healthy.
QWEN_PORT=${QWEN_PORT:-$(( 20000 + ${SLURM_JOB_ID:-$$} % 20000 ))}
QWEN_API_URL=http://127.0.0.1:$QWEN_PORT/v1
CODEX_BIN=${CODEX_BIN:-/u/dzhang5/.nvm/versions/node/v22.16.0/bin/codex}
PROLONG_DIR=${PROLONG_DIR:?set PROLONG_DIR to the PRO-LONG checkout}
RUN_ROOT=${ART_DIR:-$ROOT_DIR/artifacts/manual-prolong-g1-$GATE_BACKEND}
WS=$RUN_ROOT/workspace
SERVER_LOG=$RUN_ROOT/qwen-server.log
SERVER_PID=""
SERVER_PGID=""

# A throwaway CODEX_HOME is not hygiene, it is the experiment's control: the user's
# real home carries auth.json plus `model = "gpt-5.6-sol"`, and any leak of those
# would silently answer this gate with a hosted model instead of the local one.
export CODEX_HOME=$RUN_ROOT/codex-home
export LOCAL_API_KEY=EMPTY
export HF_HOME PYTHONNOUSERSITE=1

mkdir -p "$WS" "$CODEX_HOME"
rm -f "$WS"/actions.json "$WS"/last_message.txt "$WS"/hello.txt

cleanup() {
  if [[ -n "$SERVER_PGID" ]] && kill -0 -- "-$SERVER_PGID" 2>/dev/null; then
    kill -TERM -- "-$SERVER_PGID" 2>/dev/null || true
    for _ in $(seq 1 20); do
      kill -0 -- "-$SERVER_PGID" 2>/dev/null || break
      sleep 0.5
    done
    kill -KILL -- "-$SERVER_PGID" 2>/dev/null || true
  fi
  [[ -n "$SERVER_PID" ]] && wait "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if [[ "$GATE_BACKEND" == local ]]; then
# Not `transformers serve` directly: Codex sends `client_metadata`, which the stock
# server 422s on. The shim drops unknown fields and logs each one.
setsid "$PYTHON_BIN" "$ROOT_DIR/scripts/serve_qwen_for_codex.py" serve "$MODEL_ID" \
  --host 127.0.0.1 --port "$QWEN_PORT" --device cuda:0 --dtype auto \
  --reasoning off --log-level info > "$SERVER_LOG" 2>&1 &
SERVER_PID=$!
SERVER_PGID=$SERVER_PID

for _ in $(seq 1 360); do
  curl -fsS "http://127.0.0.1:$QWEN_PORT/health" >/dev/null 2>&1 && break
  kill -0 "$SERVER_PID" 2>/dev/null || { echo "server died; see $SERVER_LOG" >&2; exit 1; }
  sleep 5
done
if ! kill -0 "$SERVER_PID" 2>/dev/null || grep -q "address already in use" "$SERVER_LOG"; then
  echo "our model server is not the one answering on $QWEN_PORT; see $SERVER_LOG" >&2
  exit 1
fi
curl -fsS "$QWEN_API_URL/models" > "$RUN_ROOT/qwen-models.json"
echo "== server up: $(cat "$RUN_ROOT/qwen-models.json" | head -c 200)"

# Codex puts -m straight into the request's `model` field, and the server compares it
# for exact equality against force_model (utils.py:1120-1127) -- so it must be MODEL_ID
# verbatim, revision included. /v1/models is no help: it lists every cached model in
# unstable order, and reading data[0] once picked the 4B and got the request rejected.
SERVED_MODEL=$MODEL_ID
echo "== serving as: $SERVED_MODEL"
else
  # The hosted arm needs the account credential but must not inherit config.toml's
  # model/effort -- those stay on the command line so both arms are configured the
  # same way and the only difference is which model answers.
  ln -sfn "$HOME/.codex/auth.json" "$CODEX_HOME/auth.json"
  SERVED_MODEL=$OPENAI_MODEL
  echo "== hosted backend: $SERVED_MODEL (effort=$OPENAI_EFFORT)"
fi

# Same flags PRO-LONG uses, plus the provider redirect. --ignore-user-config means
# config.toml cannot carry the provider, so it has to come through -c.
codex_common=(
  --json --skip-git-repo-check --ignore-user-config --ignore-rules
  -m "$SERVED_MODEL"
)
if [[ "$GATE_BACKEND" == local ]]; then
codex_common+=(
  -c model_provider=local
  -c 'model_providers.local.name="qwen-local"'
  -c "model_providers.local.base_url=\"$QWEN_API_URL\""
  # codex 0.147 dropped wire_api="chat"; only the Responses API is left, which
  # transformers serve does implement (cli/serving/response.py) -- note it ignores
  # previous_response_id, so any continuity has to come from the client side.
  -c 'model_providers.local.wire_api="responses"'
  -c 'model_providers.local.env_key="LOCAL_API_KEY"'
  -c 'model_reasoning_effort="low"'
)
else
codex_common+=( -c "model_reasoning_effort=\"$OPENAI_EFFORT\"" )
fi
codex_common+=(
  # workspace-write, not danger-full-access: bubblewrap confines writes to the
  # workspace and denies the agent's own commands any network, so it cannot reach
  # the Minecraft sandbox while codex itself still reaches the model.
  -s workspace-write
)

run_codex() {  # name, timeout, prompt
  local name=$1 tmo=$2 prompt=$3
  echo "== $name"
  local t0=$SECONDS
  set +e
  # </dev/null or codex treats the batch job's stdin as an appended <stdin> block.
  ( cd "$WS" && timeout "$tmo" "$CODEX_BIN" exec "${codex_common[@]}" \
      -o "$WS/last_message.txt" "$prompt" < /dev/null ) \
      > "$RUN_ROOT/$name.jsonl" 2> "$RUN_ROOT/$name.err"
  local rc=$?
  set -e
  echo "   exit=$rc elapsed=$((SECONDS - t0))s events=$(wc -l < "$RUN_ROOT/$name.jsonl")"
  [[ -s "$RUN_ROOT/$name.err" ]] && { echo "   stderr:"; head -5 "$RUN_ROOT/$name.err"; }
  return 0
}

# T1 — does a tool-using turn complete at all against this endpoint?
run_codex t1_smoke 900 'Write a file named hello.txt in the current directory containing exactly OK. Then stop.'
if [[ -f "$WS/hello.txt" ]]; then echo "   T1 PASS: $(cat "$WS/hello.txt")"; else echo "   T1 FAIL: no hello.txt"; fi

# T2 — the shape PRO-LONG actually needs: read a log, then emit actions.json.
cat > "$WS/logs.txt" <<'LOG'
================================================================================
Action 0 | INITIAL STATE | Score: 0

[STATE] pos=(-3009.5, 71.0, -5572.5) pitch=0 yaw=150 moved=0.00
================================================================================
Action 1 | Score: 0

Tool Call: {"forward": 1}
[STATE] pos=(-3009.5, 71.0, -5572.5) pitch=0 yaw=150 moved=0.00
================================================================================
Action 2 | Score: 0

Tool Call: {"forward": 1}
[STATE] pos=(-3009.5, 71.0, -5572.5) pitch=0 yaw=150 moved=0.00
LOG

run_codex t2_actions 900 'Read logs.txt in the current directory. Report how many actions have been taken so far and whether the player position changed. Then write actions.json containing a JSON object of the form {"actions": [...]} with 2 to 4 entries, each entry an object like {"action": {"forward": 1, "camera": [0, 30]}, "repeat": 5}. Write the file, then stop.'

"$PYTHON_BIN" - "$PROLONG_DIR" "$WS/actions.json" <<'PY'
import json, sys, pathlib
sys.path.insert(0, sys.argv[1])
p = pathlib.Path(sys.argv[2])
if not p.exists():
    print("   T2 FAIL: no actions.json"); sys.exit(0)
raw = p.read_text()
print(f"   actions.json ({len(raw)} bytes): {raw[:200]}")
try:
    obj = json.loads(raw)
except json.JSONDecodeError as e:
    print(f"   T2 FAIL: malformed JSON: {e}"); sys.exit(0)
entries = obj.get("actions") if isinstance(obj, dict) else obj
if isinstance(entries, list) and entries:
    print(f"   T2 PASS: {len(entries)} entries, first={entries[0]}")
else:
    print(f"   T2 FAIL: no usable 'actions' list (got {type(entries).__name__})")
PY

echo "== token usage (from --json events)"
"$PYTHON_BIN" - "$RUN_ROOT" <<'PY'
import json, pathlib, sys
for f in sorted(pathlib.Path(sys.argv[1]).glob("t*.jsonl")):
    kinds, usage = {}, None
    for line in f.read_text(errors="replace").splitlines():
        try: ev = json.loads(line)
        except Exception: continue
        k = ev.get("type") or ev.get("msg", {}).get("type", "?")
        kinds[k] = kinds.get(k, 0) + 1
        u = json.dumps(ev)
        if '"total_token_usage"' in u or '"token_count"' in u: usage = ev
    print(f"   {f.name}: {kinds}")
    if usage: print(f"     usage: {json.dumps(usage)[:300]}")
PY

if [[ "$GATE_BACKEND" == local ]]; then
  echo "== server-side view of the requests codex actually made"
  grep -iE "POST /v1|responses|error|Traceback|unsupported" "$SERVER_LOG" | tail -15
fi

echo "== G1 done -> $RUN_ROOT"
