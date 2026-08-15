#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CONDA_BIN=${CONDA_BIN:-/u/dzhang5/miniforge3/bin/conda}
BASE_ENV=${BASE_ENV:-/work/nvme/bdrx/dzhang5/conda/envs/searchr1-sglang-ghx4-py310}
TARGET_ENV=${TARGET_ENV:-/work/nvme/bdrx/dzhang5/conda/envs/mineexplorer-qwen35-tf}
PIP_CACHE_DIR=${PIP_CACHE_DIR:-/work/nvme/bdrx/dzhang5/pip-cache}
HF_HOME=${HF_HOME:-/work/nvme/bdrx/dzhang5/huggingface}
MODEL_REPO=${MODEL_REPO:-Qwen/Qwen3.5-27B}
MODEL_REVISION=${MODEL_REVISION:-fc05daec18b0a78c049392ed2e771dde82bdf654}
DOWNLOAD_MODEL=${DOWNLOAD_MODEL:-1}

if [[ "$TARGET_ENV" == "$BASE_ENV" ]]; then
  echo "refused: TARGET_ENV must not overwrite BASE_ENV" >&2
  exit 2
fi
if [[ ! -x "$BASE_ENV/bin/python" ]]; then
  echo "missing native DeltaAI base environment: $BASE_ENV" >&2
  exit 2
fi
if [[ ! -x "$TARGET_ENV/bin/python" ]]; then
  "$CONDA_BIN" create -y -p "$TARGET_ENV" --clone "$BASE_ENV"
fi

export HF_HOME PIP_CACHE_DIR PYTHONNOUSERSITE=1

# SGLang is not used by this environment. Removing the inherited package
# avoids its Transformers 4.x pin conflicting with Qwen3.5 support in 5.12.1.
"$TARGET_ENV/bin/python" -m pip uninstall -y sglang || true
"$TARGET_ENV/bin/python" -m pip install --upgrade -r "$ROOT_DIR/requirements-qwen35.txt"
"$TARGET_ENV/bin/python" -m pip check

"$TARGET_ENV/bin/python" - <<'PY'
import platform

import gymnasium
import imageio
import openai
import torch
import transformers
from transformers import AutoModelForMultimodalLM

assert platform.machine() == "aarch64", platform.machine()
assert transformers.__version__ == "5.12.1", transformers.__version__
print(f"python_machine={platform.machine()}")
print(f"torch={torch.__version__} cuda={torch.version.cuda}")
print(f"transformers={transformers.__version__}")
print(f"gymnasium={gymnasium.__version__} imageio={imageio.__version__}")
print(f"openai={openai.__version__}")
print(f"multimodal_loader={AutoModelForMultimodalLM.__name__}")
PY

if [[ "$DOWNLOAD_MODEL" == 1 ]]; then
  # One worker avoids the high host-memory peak observed when several 5 GB
  # shards are transferred concurrently. HF_HOME/hub is the cache root used
  # by Transformers when the evaluation service starts.
  export HF_HUB_DISABLE_XET=1
  "$TARGET_ENV/bin/hf" download "$MODEL_REPO" \
    --revision "$MODEL_REVISION" \
    --cache-dir "$HF_HOME/hub" \
    --max-workers 1
  "$TARGET_ENV/bin/hf" cache verify "$MODEL_REPO" \
    --revision "$MODEL_REVISION" \
    --cache-dir "$HF_HOME/hub" \
    --fail-on-missing-files
fi
