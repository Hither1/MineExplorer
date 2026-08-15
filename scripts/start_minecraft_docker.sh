#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
DOCKER_BIN=${DOCKER_BIN:-docker}

# shellcheck source=../docker/minecraft-sandbox.conf
source "$ROOT_DIR/docker/minecraft-sandbox.conf"

MINECRAFT_IMAGE=${MINECRAFT_IMAGE_OVERRIDE:-$MINECRAFT_IMAGE}
MINECRAFT_CONTAINER_NAME=${MINECRAFT_CONTAINER_NAME_OVERRIDE:-$MINECRAFT_CONTAINER_NAME}
MINECRAFT_HOST_PORT=${MINECRAFT_HOST_PORT_OVERRIDE:-$MINECRAFT_HOST_PORT}

if ! "$DOCKER_BIN" info >/dev/null 2>&1; then
  cat >&2 <<'EOF'
Cannot reach a Docker daemon. On DeltaAI, point DOCKER_HOST at a reachable
x86_64 Docker host, for example: export DOCKER_HOST=ssh://user@x86-host
EOF
  exit 2
fi

server_os=$("$DOCKER_BIN" info --format '{{.OSType}}')
server_arch=$("$DOCKER_BIN" info --format '{{.Architecture}}')
if [[ "$server_os" != linux ]]; then
  echo "unsupported Docker server OS: $server_os (linux required)" >&2
  exit 2
fi
case "$server_arch" in
  amd64|x86_64) ;;
  *)
    cat >&2 <<EOF
refused: Docker server architecture is $server_arch, but the pinned
MineExplorer image is linux/amd64 only. Use an x86_64 Docker host; emulated
Minecraft is not a valid benchmark runtime.
EOF
    exit 2
    ;;
esac

existing_image=$("$DOCKER_BIN" inspect --format '{{.Config.Image}}' "$MINECRAFT_CONTAINER_NAME" 2>/dev/null || true)
if [[ -n "$existing_image" && "$existing_image" != "$MINECRAFT_IMAGE" ]]; then
  echo "refused: container '$MINECRAFT_CONTAINER_NAME' already uses $existing_image" >&2
  echo "remove or rename it explicitly before starting $MINECRAFT_IMAGE" >&2
  exit 2
fi

if [[ -z "$existing_image" ]]; then
  "$DOCKER_BIN" pull --platform linux/amd64 "$MINECRAFT_IMAGE"
  "$DOCKER_BIN" run --detach \
    --name "$MINECRAFT_CONTAINER_NAME" \
    --platform linux/amd64 \
    --init \
    --shm-size "$MINECRAFT_SHM_SIZE" \
    --publish "$MINECRAFT_HOST_PORT:8000" \
    "$MINECRAFT_IMAGE"
elif [[ $("$DOCKER_BIN" inspect --format '{{.State.Running}}' "$MINECRAFT_CONTAINER_NAME") != true ]]; then
  "$DOCKER_BIN" start "$MINECRAFT_CONTAINER_NAME" >/dev/null
fi

if [[ -n ${MC_SANDBOX_URL:-} ]]; then
  sandbox_url=${MC_SANDBOX_URL%/}
elif [[ -z ${DOCKER_HOST:-} || ${DOCKER_HOST:-} == unix://* ]]; then
  sandbox_url="http://127.0.0.1:$MINECRAFT_HOST_PORT"
else
  cat >&2 <<EOF
The remote Docker container is running, but MC_SANDBOX_URL is not set.
Export the x86 host address reachable from DeltaAI, for example:
  export MC_SANDBOX_URL=http://x86-host:$MINECRAFT_HOST_PORT
Then rerun this script to perform the readiness check.
EOF
  exit 2
fi

for _ in $(seq 1 80); do
  if curl -fsS "$sandbox_url/monitor/alive" > /dev/null 2>&1; then
    echo "minecraft sandbox ready: $sandbox_url"
    echo "export MC_SANDBOX_URL=$sandbox_url"
    exit 0
  fi
  sleep 3
done

echo "Minecraft sandbox did not become ready within 240 seconds." >&2
echo "Inspect it with: $DOCKER_BIN logs $MINECRAFT_CONTAINER_NAME" >&2
exit 1
