#!/usr/bin/env bash
# Run a command with a native ARM64 Minecraft sandbox alive on this node.
#
#   scripts/with_minecraft_arm64.sh -- scripts/run_qwen35_0313_0544.sh
#
# Starts scripts/start_minecraft_arm64.sh, waits for /monitor/alive, exports
# MC_SANDBOX_URL, runs the command, and tears the sandbox down on exit. Intended for a
# Slurm allocation: the sandbox renders on CPU while the evaluation uses the GPU.
#
# ghx4 nodes are shared, so nothing here may be a fixed per-node resource. Two of our
# own jobs landing on one node used to collide twice over:
#
#   * Both wanted Xvfb on :99. The loser logged "Xvfb failed to start on :99" and its
#     sandbox exited -- but /monitor/alive still answered on port 8000, from the
#     winner's server, so the readiness check passed and the run scored against
#     another job's Minecraft world until that job reset it out from under us
#     ("session '...' not found", hundreds of times, step counter climbing).
#   * cleanup ran `pkill -f net.minecraft.client.main.Main`, which kills every
#     Minecraft JVM on the node, including one belonging to a job still running.
#
# Port and display are therefore derived from the job id, and teardown is scoped to
# processes this script actually started.
set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
W=${MC_ARM64_ROOT:-/work/nvme/bdrx/dzhang5/mc-arm64}
JOB=${SLURM_JOB_ID:-$$}
# Disjoint from the model server's 20000-39999 range, or a job would collide with
# itself.
PORT=${MC_SANDBOX_PORT:-$(( 40000 + JOB % 20000 ))}
DISPLAY_NUM=${MC_XVFB_DISPLAY_NUM:-$(( 100 + JOB % 800 ))}
READY_TIMEOUT=${MC_SANDBOX_READY_TIMEOUT:-300}
SANDBOX_LOG=${MC_SANDBOX_LOG:-${ART_DIR:-$W}/minecraft-sandbox.log}
export MC_SANDBOX_PORT=$PORT MC_XVFB_DISPLAY_NUM=$DISPLAY_NUM

if [[ ${1:-} == "--" ]]; then
  shift
fi
if [[ $# -eq 0 ]]; then
  echo "usage: $0 -- <command> [args...]" >&2
  exit 2
fi

mkdir -p "$(dirname "$SANDBOX_LOG")"
# Own process group: teardown can then target exactly what this script started.
setsid "$SCRIPT_DIR/start_minecraft_arm64.sh" > "$SANDBOX_LOG" 2>&1 &
SANDBOX_PID=$!
SANDBOX_PGID=$SANDBOX_PID

cleanup() {
  kill -TERM -- "-$SANDBOX_PGID" 2>/dev/null || true
  # MineStudio launches the engine as a detached JVM, so it can outlive the group.
  # Match it by the display it renders to -- read from the process's own environment
  # -- never by class name alone, which would take a co-scheduled job's engine with it.
  for pid in $(pgrep -f 'net.minecraft.client.main.Main' 2>/dev/null); do
    if tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null | grep -qx "DISPLAY=:$DISPLAY_NUM"; then
      kill -TERM "$pid" 2>/dev/null || true
    fi
  done
  pkill -TERM -f "Xvfb :${DISPLAY_NUM}\\b" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

deadline=$((SECONDS + READY_TIMEOUT))
while true; do
  # Liveness before readiness: a dead child plus a healthy endpoint means the endpoint
  # is somebody else's. That combination used to read as success.
  if ! kill -0 "$SANDBOX_PID" 2>/dev/null; then
    echo "minecraft sandbox exited before becoming ready; log: $SANDBOX_LOG" >&2
    tail -40 "$SANDBOX_LOG" >&2
    exit 1
  fi
  if curl -fsS "http://127.0.0.1:$PORT/monitor/alive" > /dev/null 2>&1; then
    break
  fi
  if (( SECONDS > deadline )); then
    echo "minecraft sandbox not ready within ${READY_TIMEOUT}s; log: $SANDBOX_LOG" >&2
    tail -40 "$SANDBOX_LOG" >&2
    exit 1
  fi
  sleep 2
done

if grep -qE "Xvfb failed to start|address already in use|Address already in use" "$SANDBOX_LOG"; then
  echo "the sandbox answering on $PORT is not the one this job started; log: $SANDBOX_LOG" >&2
  tail -20 "$SANDBOX_LOG" >&2
  exit 1
fi

export MC_SANDBOX_URL="http://127.0.0.1:$PORT"
echo "minecraft sandbox ready: $MC_SANDBOX_URL (display :$DISPLAY_NUM, log: $SANDBOX_LOG)"

"$@"
rc=$?
echo "command exited with $rc; last sandbox log lines:"
tail -15 "$SANDBOX_LOG"
exit $rc
