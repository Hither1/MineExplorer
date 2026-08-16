#!/usr/bin/env bash
# Resolve the shared vLLM server's URL, or fail loudly.
#
#   MODEL_URL=$(bash scripts/use_model_server.sh qwen35-27b) || exit 1
#
# Prints the base URL (".../v1") on stdout; everything else goes to stderr so the
# caller can capture it directly.
#
# Every check here exists because its absence has already cost a run: a readiness
# endpoint answering from a *different* job's server, a discovery file left behind by
# a dead node, a server quietly holding a different model than the one the run claims
# to measure. Resolving a URL is not the same as confirming what is on the other end.
set -uo pipefail

# MINEEXPLORER_ROOT when running from a snapshot copy, where this script's own
# location points at the run directory rather than the repo.
ROOT_DIR=${MINEEXPLORER_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
SLUG=${1:?usage: use_model_server.sh <server-slug> [expected-model]}
EXPECT_MODEL=${2:-}
DISCOVERY=${DISCOVERY_DIR:-$ROOT_DIR/artifacts/servers}/$SLUG.json
WAIT=${MODEL_SERVER_WAIT:-900}

deadline=$((SECONDS + WAIT))
while [[ ! -f $DISCOVERY ]]; do
  if (( SECONDS > deadline )); then
    echo "no server advertised at $DISCOVERY after ${WAIT}s" >&2
    exit 1
  fi
  sleep 10
done

read -r URL MODEL JOB < <(python3 -c '
import json, sys
d = json.load(open(sys.argv[1]))
print(d["url"], d["model"], d.get("job", "none"))
' "$DISCOVERY") || { echo "unreadable discovery file $DISCOVERY" >&2; exit 1; }

# The file can outlive the server. Ask the server itself.
if ! LIVE=$(curl -fsS --max-time 30 "$URL/models" 2>/dev/null); then
  echo "advertised server $URL is not answering (stale file from job $JOB?)" >&2
  exit 1
fi
LIVE_MODEL=$(printf '%s' "$LIVE" | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"][0]["id"])')
if [[ "$LIVE_MODEL" != "$MODEL" ]]; then
  echo "server at $URL serves '$LIVE_MODEL', but $SLUG advertises '$MODEL'" >&2
  exit 1
fi
if [[ -n "$EXPECT_MODEL" && "$LIVE_MODEL" != "$EXPECT_MODEL" ]]; then
  echo "server at $URL serves '$LIVE_MODEL', but this run expects '$EXPECT_MODEL'" >&2
  exit 1
fi

echo "using $SLUG: $LIVE_MODEL at $URL (server job $JOB)" >&2
printf '%s\n' "$URL"
