#!/bin/bash
# aarch64 replacement for MineStudio's launchClient.sh.
#
# Two changes versus upstream:
#   1. LWJGL 3.3.3 (with linux-arm64 natives) is placed ahead of the fat jar on the
#      classpath, so `-cp` replaces `-jar`. The published engine bundles LWJGL 3.2.2,
#      whose natives are x86-64 only.
#   2. LWJGL's bundled jemalloc aborts on GH200's 64 KiB pages, so the system
#      allocator is used instead.
# Xvfb and DISPLAY are managed by the caller; upstream's xvfb-run/vglrun are not
# installed on DeltaAI.

set -uo pipefail

port=0
seed="NONE"
maxMem="2G"
device="cpu"
fatjar=build/libs/mcprec-6.13.jar

while [ $# -gt 0 ]; do
    case "$1" in
        -replaceable) ;;
        -port) port="$2"; shift;;
        -seed) seed="$2"; shift;;
        -maxMem) maxMem="$2"; shift;;
        -device) device="$2"; shift;;
        -fatjar) fatjar="$2"; shift;;
        *) echo >&2 "usage: $0 [-replaceable] [-port <port>] [-seed <seed>] [-maxMem <maxMem>] [-device <device>] [-fatjar <fatjar>]"
           exit 1;;
    esac
    shift
done

if ! [[ $port =~ ^-?[0-9]+$ ]]; then
    echo "Port value should be numeric" >&2
    exit 1
fi
if [ \( $port -lt 0 \) -o \( $port -gt 65535 \) ]; then
    echo "Port value out of range 0-65535" >&2
    exit 1
fi

LWJGL_DIR=${MINEEXPLORER_LWJGL_DIR:-/work/nvme/bdrx/dzhang5/mc-arm64/lwjgl33}
if ! compgen -G "$LWJGL_DIR/*.jar" > /dev/null; then
    echo "no LWJGL jars in $LWJGL_DIR; set MINEEXPLORER_LWJGL_DIR" >&2
    exit 1
fi
if [ ! -f "$fatjar" ]; then
    echo "engine jar not found: $fatjar" >&2
    exit 1
fi
if [ -z "${DISPLAY:-}" ]; then
    echo "DISPLAY is unset; start Xvfb before launching the engine" >&2
    exit 1
fi

CP="$(ls "$LWJGL_DIR"/*.jar | tr '\n' ':')$fatjar"

# The published image runs the engine on JDK 8; DeltaAI's system java is 11, under which
# OptiFine loses several reflective fallbacks. Prefer a JDK 8 when one is configured.
JAVA_BIN=${MINEEXPLORER_JAVA:-java}

exec "$JAVA_BIN" -Xmx"$maxMem" \
    -Dorg.lwjgl.system.allocator=system \
    -cp "$CP" \
    net.minecraft.client.main.Main --envPort="$port"
