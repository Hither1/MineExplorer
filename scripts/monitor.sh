#!/usr/bin/env bash
set -euo pipefail

HARNESS_HOME=${RESEARCH_HARNESS_HOME:-$HOME/.research-harness}
MONITOR="$HARNESS_HOME/bin/harness-monitor"

if [[ ! -x "$MONITOR" ]]; then
  echo "research harness is not installed: missing $MONITOR" >&2
  exit 2
fi

exec "$MONITOR" "$@"
