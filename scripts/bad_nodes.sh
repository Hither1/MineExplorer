#!/usr/bin/env bash
# Print the comma-separated exclude list for SBATCH_EXCLUDE.
#   export SBATCH_EXCLUDE=$(bash scripts/bad_nodes.sh)
set -euo pipefail
DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
awk '!/^#/ && NF {print $1}' "$DIR/bad_nodes.txt" | paste -sd, -
