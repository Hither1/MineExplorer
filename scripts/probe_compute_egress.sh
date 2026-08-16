#!/usr/bin/env bash
# Can a ghx4 compute node reach the hosted model at all?
#
# The hosted G1 arm ran on the login node. Every cluster-side use of a hosted model --
# a gpt-5.6 benchmark run, or a hosted reference arm for PRO-LONG -- depends on compute
# nodes having the same egress, which is not a given on HPC systems and is cheaper to
# settle now than to discover inside a long benchmark job.
set -uo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
RUN_ROOT=${ART_DIR:-$ROOT_DIR/artifacts/manual-egress-probe}
CODEX_BIN=${CODEX_BIN:-/u/dzhang5/.nvm/versions/node/v22.16.0/bin/codex}
mkdir -p "$RUN_ROOT"

echo "== host: $(hostname -s)"
for target in https://api.openai.com/v1/models https://chatgpt.com; do
  code=$(curl -s -o /dev/null -m 15 -w '%{http_code}' "$target" 2>&1)
  echo "   $target -> HTTP $code (401/403 still proves reachability)"
done

echo "== can codex complete a turn from here?"
export CODEX_HOME=$RUN_ROOT/codex-home
mkdir -p "$CODEX_HOME"
ln -sfn "$HOME/.codex/auth.json" "$CODEX_HOME/auth.json"
WS=$RUN_ROOT/workspace
mkdir -p "$WS"; rm -f "$WS/hello.txt"

( cd "$WS" && timeout 300 "$CODEX_BIN" exec --json --skip-git-repo-check \
    --ignore-user-config --ignore-rules -m "${OPENAI_MODEL:-gpt-5.6-sol}" \
    -c 'model_reasoning_effort="low"' -s workspace-write \
    'Write a file named hello.txt in the current directory containing exactly OK. Then stop.' \
    < /dev/null ) > "$RUN_ROOT/probe.jsonl" 2> "$RUN_ROOT/probe.err"
echo "   exit=$? events=$(wc -l < "$RUN_ROOT/probe.jsonl")"
if [[ -f "$WS/hello.txt" ]]; then
  echo "   RESULT: compute node CAN drive the hosted model"
else
  echo "   RESULT: compute node CANNOT — first error follows"
  grep -o '"message":"[^"]*"' "$RUN_ROOT/probe.jsonl" | head -3
  head -3 "$RUN_ROOT/probe.err"
fi
