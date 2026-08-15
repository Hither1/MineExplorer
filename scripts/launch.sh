#!/usr/bin/env bash
set -euo pipefail

HARNESS_HOME=${RESEARCH_HARNESS_HOME:-$HOME/.research-harness}
LAUNCHER="$HARNESS_HOME/bin/harness-launch"

if [[ ! -x "$LAUNCHER" ]]; then
  echo "research harness is not installed: missing $LAUNCHER" >&2
  exit 2
fi

exec "$LAUNCHER" "$@"
