#!/usr/bin/env bash
# Provision the MineExplorer Minecraft sandbox natively on aarch64 (DeltaAI/GH200).
#
# Replaces the x86_64-only Docker route. The published engine jar is reused verbatim;
# only its LWJGL 3.2.2 x86-64 natives are bypassed by putting LWJGL 3.3.3 with
# linux-arm64 natives ahead of it on the classpath (see docker/minecraft-sandbox.conf
# for the image this engine comes from).
#
# Every step is idempotent and skips work that is already in place.
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=${MC_ARM64_ROOT:-/work/nvme/bdrx/dzhang5/mc-arm64}
ENV_PREFIX=${MC_SANDBOX_ENV:-/work/nvme/bdrx/dzhang5/conda/envs/mineexplorer-sandbox-arm64}
CONDA=${CONDA_BIN:-/u/dzhang5/miniforge3/bin/conda}
LWJGL_VERSION=${LWJGL_VERSION:-3.3.3}
LWJGL_MODULES="lwjgl lwjgl-glfw lwjgl-opengl lwjgl-openal lwjgl-stb lwjgl-tinyfd lwjgl-jemalloc"

if [[ "$(uname -m)" != aarch64 ]]; then
  echo "refused: this script provisions the aarch64 sandbox, but the host is $(uname -m)." >&2
  echo "on x86_64 use scripts/start_minecraft_docker.sh instead." >&2
  exit 2
fi

mkdir -p "$ROOT/lwjgl33" "$ROOT/engine/build/libs" "$ROOT/server"

echo "== 1/5 LWJGL $LWJGL_VERSION (linux-arm64) =="
for module in $LWJGL_MODULES; do
  for classifier in "" "-natives-linux-arm64"; do
    jar="${module}-${LWJGL_VERSION}${classifier}.jar"
    if [[ ! -s "$ROOT/lwjgl33/$jar" ]]; then
      curl -sSfL -o "$ROOT/lwjgl33/$jar" \
        "https://repo1.maven.org/maven2/org/lwjgl/${module}/${LWJGL_VERSION}/${jar}"
      echo "  fetched $jar"
    fi
  done
done

echo "== 1b/5 JDK 8 (aarch64) =="
# Java 11 dropped JAXB, which Malmo's env server needs; the published image runs JDK 8.
if ! compgen -G "$ROOT/jdk8/jdk8u*/bin/java" > /dev/null; then
  mkdir -p "$ROOT/jdk8"
  curl -sSfL -o "$ROOT/jdk8/temurin8-aarch64.tar.gz" \
    "https://api.adoptium.net/v3/binary/latest/8/ga/linux/aarch64/jdk/hotspot/normal/eclipse"
  tar xzf "$ROOT/jdk8/temurin8-aarch64.tar.gz" -C "$ROOT/jdk8"
  rm -f "$ROOT/jdk8/temurin8-aarch64.tar.gz"
fi
compgen -G "$ROOT/jdk8/jdk8u*/bin/java" > /dev/null || { echo "JDK 8 missing under $ROOT/jdk8" >&2; exit 1; }

echo "== 2/5 conda env =="
if [[ ! -x "$ENV_PREFIX/bin/python" ]]; then
  "$CONDA" create -y -p "$ENV_PREFIX" python=3.10
fi
if ! "$ENV_PREFIX/bin/python" -c "import minestudio" 2>/dev/null; then
  "$ENV_PREFIX/bin/python" -m pip install --no-cache-dir minestudio fastapi uvicorn pyyaml psutil loguru
fi

echo "== 3/5 simulator engine =="
JAR="$ROOT/engine/build/libs/mcprec-6.13.jar"
if [[ ! -s "$JAR" ]]; then
  # Same artifact MineStudio itself downloads (minestudio/simulator/entry.py).
  "$ENV_PREFIX/bin/python" - "$ROOT" <<'PY'
import sys, zipfile, os, huggingface_hub
root = sys.argv[1]
path = huggingface_hub.hf_hub_download(repo_id="CraftJarvis/SimulatorEngine",
                                       filename="engine.zip", local_dir=root)
with zipfile.ZipFile(path) as z:
    z.extractall(root)
os.remove(path)
PY
fi
[[ -s "$JAR" ]] || { echo "engine jar still missing: $JAR" >&2; exit 1; }

echo "== 4/5 patch launchClient.sh =="
SITE=$("$ENV_PREFIX/bin/python" -c "import minestudio,os;print(os.path.dirname(minestudio.__file__))")
TARGET="$SITE/simulator/minerl/env/launchClient.sh"
[[ -f "$TARGET.orig" ]] || cp "$TARGET" "$TARGET.orig"
install -m 0755 "$SCRIPT_DIR/minecraft_arm64/launchClient.sh" "$TARGET"

echo "== 5/5 sandbox server =="
install -m 0644 "$SCRIPT_DIR/minecraft_arm64/mc_server.py" "$ROOT/server/mc_server.py"

cat <<EOF

provisioned. start the sandbox with:
  MC_ARM64_ROOT=$ROOT $SCRIPT_DIR/start_minecraft_arm64.sh
then point the evaluation client at it:
  export MC_SANDBOX_URL=http://<node>:8000
EOF
