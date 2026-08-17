#!/usr/bin/env bash
# Start the MineExplorer sandbox under rootless podman.
#
# `start_minecraft_docker.sh` needs a Docker daemon, and this cluster gives no
# user a docker socket: not in the docker group, no sudo, no rootless socket.
# Podman needs no daemon, so a static build under $TOOLS plus this script is the
# whole dependency. See tools/podman-env.sh for why the store lives on the
# node's local /tmp and why single-UID mapping is what we get.
#
#   scripts/start_minecraft_podman.sh                  # start on this host
#   MC_PODMAN_HOST=192.168.2.22 scripts/start_minecraft_podman.sh   # over ssh
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source "$ROOT_DIR/docker/minecraft-sandbox.conf"

TOOLS=${TOOLS:-/datapool/data3/storage/ruihan/data_share/jh/Collab/tools}
MINECRAFT_IMAGE=${MINECRAFT_IMAGE_OVERRIDE:-$MINECRAFT_IMAGE}
MINECRAFT_CONTAINER_NAME=${MINECRAFT_CONTAINER_NAME_OVERRIDE:-$MINECRAFT_CONTAINER_NAME}
MINECRAFT_HOST_PORT=${MINECRAFT_HOST_PORT_OVERRIDE:-$MINECRAFT_HOST_PORT}
MC_PODMAN_HOST=${MC_PODMAN_HOST:-}

run_here() {
  # shellcheck source=../../tools/podman-env.sh
  source "$TOOLS/podman-env.sh"

  if ! podman image exists "$MINECRAFT_IMAGE"; then
    echo "image not in the local store: $MINECRAFT_IMAGE" >&2
    echo "pull it first (docker.io runs ~150 KB/s from here, so budget hours):" >&2
    echo "  source $TOOLS/podman-env.sh && podman pull $MINECRAFT_IMAGE" >&2
    exit 2
  fi

  if podman container exists "$MINECRAFT_CONTAINER_NAME"; then
    if [[ $(podman inspect --format '{{.State.Running}}' "$MINECRAFT_CONTAINER_NAME") == true ]]; then
      echo "already running: $MINECRAFT_CONTAINER_NAME"
    else
      podman start "$MINECRAFT_CONTAINER_NAME" >/dev/null
    fi
  else
    podman run --detach \
      --name "$MINECRAFT_CONTAINER_NAME" \
      --init \
      --shm-size "$MINECRAFT_SHM_SIZE" \
      --publish "$MINECRAFT_HOST_PORT:8000" \
      "$MINECRAFT_IMAGE" >/dev/null
  fi

  for _ in $(seq 1 100); do
    if podman exec "$MINECRAFT_CONTAINER_NAME" \
         python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/monitor/alive',timeout=3)" \
         >/dev/null 2>&1; then
      echo "minecraft sandbox ready on $(hostname) port $MINECRAFT_HOST_PORT"
      exit 0
    fi
    sleep 3
  done

  echo "sandbox did not answer /monitor/alive within 300s" >&2
  echo "inspect with: podman logs $MINECRAFT_CONTAINER_NAME" >&2
  exit 1
}

if [[ -n "$MC_PODMAN_HOST" ]]; then
  ssh -o BatchMode=yes -o ConnectTimeout=8 "ruihan@$MC_PODMAN_HOST" \
    "MINECRAFT_HOST_PORT_OVERRIDE='$MINECRAFT_HOST_PORT' bash '$ROOT_DIR/scripts/start_minecraft_podman.sh'"
else
  run_here
fi
