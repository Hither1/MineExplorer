#!/usr/bin/env bash
# Native aarch64 replacement for the published image's start_mc_server.sh.
# Starts Xvfb, then serves the same FastAPI contract on $MC_SANDBOX_PORT.
set -euo pipefail

W=${MC_ARM64_ROOT:-/work/nvme/bdrx/dzhang5/mc-arm64}
PY=${MC_SANDBOX_PYTHON:-/work/nvme/bdrx/dzhang5/conda/envs/mineexplorer-sandbox-arm64/bin/python}
PORT=${MC_SANDBOX_PORT:-8000}
DISP=":${MC_XVFB_DISPLAY_NUM:-99}"

[ -f "$W/engine/build/libs/mcprec-6.13.jar" ] || { echo "engine jar missing under $W/engine" >&2; exit 2; }
[ -f "$W/server/mc_server.py" ] || { echo "mc_server.py missing under $W/server" >&2; exit 2; }

Xvfb "$DISP" -screen 0 1280x720x24 +extension GLX +render -nolisten tcp \
  > "$W/xvfb_${DISP#:}.log" 2>&1 &
XVFB_PID=$!
cleanup() { kill "$XVFB_PID" 2>/dev/null || true; }
trap cleanup EXIT

for _ in $(seq 1 40); do
  [ -S "/tmp/.X11-unix/X${DISP#:}" ] && break
  sleep 0.5
done
[ -S "/tmp/.X11-unix/X${DISP#:}" ] || { echo "Xvfb failed to start on $DISP" >&2; exit 2; }

export DISPLAY="$DISP"
export MINESTUDIO_DIR="$W"
export MINEEXPLORER_LWJGL_DIR="$W/lwjgl33"
# Java 11 dropped JAXB, which Malmo's EnvServerSocketHandler needs; the published
# image runs JDK 8, so do the same.
export MINEEXPLORER_JAVA="${MINEEXPLORER_JAVA:-$(ls -d "$W"/jdk8/jdk8u*/bin/java 2>/dev/null | head -1)}"
export LIBGL_ALWAYS_SOFTWARE=1
# ~/.local/lib/python3.10/site-packages otherwise leaks into this prefix.
export PYTHONNOUSERSITE=1
export SERVER_PORT="$PORT"

echo "minecraft sandbox (aarch64) starting on $(hostname):$PORT"
echo "export MC_SANDBOX_URL=http://$(hostname):$PORT"

cd "$W/server"
exec "$PY" -m uvicorn mc_server:app --host 0.0.0.0 --port "$PORT" --log-level info
