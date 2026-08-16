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
# An episode outliving its server is the same wasted node as no server at all, and it
# wastes it *after* hours of compute rather than before. Alive is not the property that
# matters -- alive long enough is. Refuse a server with less time left than the episode
# needs, and keep waiting for the successor instead.
MIN_REMAINING=${MODEL_SERVER_MIN_REMAINING:-0}

# Minutes of walltime left on a Slurm job, or empty when that cannot be determined --
# an unknown is not a failure, and a server reached outside Slurm has no walltime.
remaining_minutes() {
  local job=$1 left
  [[ -z $job || $job == none ]] && return 0
  left=$(squeue -h -j "$job" -o "%L" 2>/dev/null | tr -d ' ')
  [[ -z $left || $left == "INVALID" ]] && return 0
  python3 - "$left" <<'PY' 2>/dev/null
import sys
t = sys.argv[1]
days, _, rest = t.rpartition("-") if "-" in t else ("0", "", t)
parts = [int(p) for p in rest.split(":")]
while len(parts) < 3:
    parts.insert(0, 0)
h, m, s = parts
print(int(days or 0) * 1440 + h * 60 + m + (1 if s else 0))
PY
}

deadline=$((SECONDS + WAIT))
last_reason="no server advertised at $DISCOVERY"
while true; do
  if [[ -f $DISCOVERY ]] && read -r URL MODEL JOB < <(python3 -c '
import json, sys
d = json.load(open(sys.argv[1]))
print(d["url"], d["model"], d.get("job", "none"))
' "$DISCOVERY" 2>/dev/null); then
    # The file can outlive the server. Ask the server itself.
    if ! LIVE=$(curl -fsS --max-time 30 "$URL/models" 2>/dev/null); then
      last_reason="advertised server $URL is not answering (stale file from job $JOB?)"
    else
      LIVE_MODEL=$(printf '%s' "$LIVE" | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"][0]["id"])')
      if [[ "$LIVE_MODEL" != "$MODEL" ]]; then
        last_reason="server at $URL serves '$LIVE_MODEL', but $SLUG advertises '$MODEL'"
      elif [[ -n "$EXPECT_MODEL" && "$LIVE_MODEL" != "$EXPECT_MODEL" ]]; then
        # A different model is not something waiting will fix.
        echo "server at $URL serves '$LIVE_MODEL', but this run expects '$EXPECT_MODEL'" >&2
        exit 1
      else
        LEFT=$(remaining_minutes "$JOB")
        if [[ -n "$LEFT" && "$MIN_REMAINING" -gt 0 && "$LEFT" -lt "$MIN_REMAINING" ]]; then
          last_reason="server job $JOB has ${LEFT}min left, this run needs ${MIN_REMAINING}min"
        else
          echo "using $SLUG: $LIVE_MODEL at $URL (server job $JOB${LEFT:+, ${LEFT}min left})" >&2
          printf '%s\n' "$URL"
          exit 0
        fi
      fi
    fi
  else
    last_reason="no server advertised at $DISCOVERY"
  fi
  if (( SECONDS > deadline )); then
    echo "$last_reason (gave up after ${WAIT}s)" >&2
    exit 1
  fi
  sleep 10
done
