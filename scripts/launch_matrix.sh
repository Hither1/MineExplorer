#!/usr/bin/env bash
# Launch the agent x channel matrix for one model, one cell per scene.
#
#   bash scripts/launch_matrix.sh              # submit
#   DRY=1 bash scripts/launch_matrix.sh        # print the commands only
#
# The matrix has two axes and they answer different questions. The agent axis --
# default, hypothesis, prolong -- is the one the project is about. The channel axis
# is the control: `codex` reaches the model through the Codex CLI, `vllm` speaks to
# the same server directly. Without the second axis a PRO-LONG win is unreadable,
# because PRO-LONG only exists on the codex side and every difference could be the
# channel rather than the memory architecture.
#
# There is no prolong/vllm cell: the mechanism is built on `codex exec resume`
# sessions, so outside the CLI the agent does not exist.
set -uo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

TAG=${TAG:-m2}
MODEL_ID=${MODEL_ID:-Qwen/Qwen3.8-27B}
SERVER=${SERVER:-qwen38-27b}
# One cap for every cell. Capping the arms differently was a real defect: the
# non-PRO-LONG arms call the model once per step and were given a lower cap to fit
# their walltime, which silently truncated the very arm they were being compared to.
MAX_STEPS=${MAX_STEPS:-300}
SCENES=${SCENES:-"0313 0802"}
# Matched to the server's own walltime, not chosen independently. The arms that call
# the model once per step need ~300 generations and a 6h limit cut two baseline seeds
# off at 1/2 while PRO-LONG finished, so the limit has to be set from the slowest arm --
# but an episode cannot outlive the server it queries either, so setting it longer than
# the server buys nothing. Raise both together.
WALL=${WALL:-08:00:00}
# Attach only to a server that can outlive the episode, and wait for the successor
# rather than start against one that is about to expire: a run that loses its server at
# hour six has burned the node and produced nothing. These travel in the job's own `env`
# prefix -- exporting them here would reach the launcher, not the job.
MIN_REMAINING=${MODEL_SERVER_MIN_REMAINING:-360}
SERVER_WAIT=${MODEL_SERVER_WAIT:-5400}
SEED_TAG=${SEED_TAG:-}
export SBATCH_EXCLUDE=${SBATCH_EXCLUDE:-$(bash "$ROOT_DIR/scripts/bad_nodes.sh")}

# agent:channel
CELLS=${CELLS:-"default:codex hypothesis:codex prolong:codex default:vllm hypothesis:vllm"}

for cell in $CELLS; do
  mode=${cell%%:*}
  chan=${cell##*:}
  case "$chan" in
    codex) runner=scripts/run_codex_0313_0544.sh ;;
    vllm)  runner=scripts/run_qwen35_0313_0544.sh ;;
    *) echo "unknown channel: $chan" >&2; exit 2 ;;
  esac
  for scene in $SCENES; do
    slug="$TAG-qwen38-$mode-$chan-$scene${SEED_TAG:+-$SEED_TAG}"
    purpose="Qwen3.8-27B $mode agent reached through $chan on $scene, hint protocol, cap $MAX_STEPS: the agent axis is the question and the channel axis is the control that keeps a PRO-LONG result from being a Codex-CLI result"
    cmd=(bash scripts/launch.sh -s "$slug" -t E1 -p "$purpose" -T "$WALL" -g 1 -c 16 -m 100G
         -- env MODEL_SERVER="$SERVER" MODEL_ID="$MODEL_ID" AGENT_MODE="$mode"
            MILESTONE_HINT=1 MAX_STEPS="$MAX_STEPS" SCENES="$scene" CODEX_EFFORT=low
            MODEL_SERVER_MIN_REMAINING="$MIN_REMAINING" MODEL_SERVER_WAIT="$SERVER_WAIT"
            bash scripts/snapshot_exec.sh scripts/with_minecraft_arm64.sh --
            bash scripts/snapshot_exec.sh "$runner")
    if [[ ${DRY:-0} == 1 ]]; then
      printf '%q ' "${cmd[@]}"; echo
    else
      "${cmd[@]}" 2>&1 | grep -E "^submitted|refused|error" || true
    fi
  done
done
