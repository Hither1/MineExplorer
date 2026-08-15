#!/usr/bin/env bash
# Run a command with a native ARM64 Minecraft sandbox alive on this node.
#
#   scripts/with_minecraft_arm64.sh -- scripts/run_qwen35_0313_0544.sh
#
# Starts scripts/start_minecraft_arm64.sh, waits for /monitor/alive, exports
# MC_SANDBOX_URL, runs the command, and tears the sandbox down on exit. Intended for a
# Slurm allocation: the sandbox renders on CPU while the evaluation uses the GPU.
set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
W=${MC_ARM64_ROOT:-/work/nvme/bdrx/dzhang5/mc-arm64}
PORT=${MC_SANDBOX_PORT:-8000}
READY_TIMEOUT=${MC_SANDBOX_READY_TIMEOUT:-300}
SANDBOX_LOG=${MC_SANDBOX_LOG:-${ART_DIR:-$W}/minecraft-sandbox.log}

if [[ ${1:-} == "--" ]]; then
  shift
fi
if [[ $# -eq 0 ]]; then
  echo "usage: $0 -- <command> [args...]" >&2
  exit 2
fi

mkdir -p "$(dirname "$SANDBOX_LOG")"
"$SCRIPT_DIR/start_minecraft_arm64.sh" > "$SANDBOX_LOG" 2>&1 &
SANDBOX_PID=$!

cleanup() {
  kill -TERM "$SANDBOX_PID" 2>/dev/null || true
  # The engine is launched by MineStudio as a detached JVM; stop it by its exact class.
  pkill -TERM -f 'net.minecraft.client.main.Main' 2>/dev/null || true
  pkill -TERM -f "Xvfb :${MC_XVFB_DISPLAY_NUM:-99}\\b" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

deadline=$((SECONDS + READY_TIMEOUT))
until curl -fsS "http://127.0.0.1:$PORT/monitor/alive" > /dev/null 2>&1; do
  if ! kill -0 "$SANDBOX_PID" 2>/dev/null; then
    echo "minecraft sandbox exited before becoming ready; log: $SANDBOX_LOG" >&2
    tail -40 "$SANDBOX_LOG" >&2
    exit 1
  fi
  if (( SECONDS > deadline )); then
    echo "minecraft sandbox not ready within ${READY_TIMEOUT}s; log: $SANDBOX_LOG" >&2
    tail -40 "$SANDBOX_LOG" >&2
    exit 1
  fi
  sleep 2
done

export MC_SANDBOX_URL="http://127.0.0.1:$PORT"
echo "minecraft sandbox ready: $MC_SANDBOX_URL (log: $SANDBOX_LOG)"

"$@"
rc=$?
echo "command exited with $rc; last sandbox log lines:"
tail -15 "$SANDBOX_LOG"
exit $rc
