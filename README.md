<div align="center">
  <img src="https://raw.githubusercontent.com/Jometeorie/MineExplorer/main/figures/longcat-logo-full-20260504.png" alt="LongCat Logo" width="300"/>
</div>

# MineExplorer: Evaluating Open-World Exploration of MLLM Agents in Minecraft

<div align="center">
  <img src="https://raw.githubusercontent.com/Jometeorie/MineExplorer/main/figures/minecraft_bench.png" alt="LongCat Logo" width="900"/>
</div>

[![arXiv](https://img.shields.io/badge/arXiv-2605.30931-b31b1b.svg)](https://arxiv.org/abs/2605.30931)

MineExplorer is a benchmark for evaluating the open-world exploration capabilities of multimodal large language model (MLLM) agents in Minecraft. We first filter atomic tasks whose solutions rely heavily on Minecraft-specific knowledge to better reflect general open-world reasoning, then organize the benchmark around a ReAct-style capability formulation and compose atomic tasks into implicit multi-hop tasks. To construct reliable instances, MineExplorer uses a multi-agent synthesis workflow that jointly designs task graphs, sandbox scenes, and rule-based milestone evaluators. Experiments show that open-world exploration remains challenging: strong models handle many single-hop tasks but degrade sharply when hidden prerequisites must be coordinated over longer trajectories, and larger models or thinking modes do not consistently translate into better performance.

---

## 1. Minecraft Sandbox Environment

MineExplorer uses a Minecraft sandbox service built on top of [MineStudio](https://github.com/CraftJarvis/MineStudio), an open-source framework that provides a Minecraft simulator engine controllable via HTTP API. The sandbox allows you to programmatically create and control Minecraft game environments — spawning scenes, issuing commands, resetting episodes, and capturing first-person screenshots.

We release a ready-to-use Docker image: **`davidzhth/mineexplorer:0.0.1`**

### Image Specifications

| Component | Version / Details |
|-----------|-------------------|
| Base OS | Ubuntu 22.04 |
| Python | 3.10 |
| Java | OpenJDK 8 (Minecraft runtime dependency) |
| Framework | [MineStudio](https://github.com/CraftJarvis/MineStudio) (bundled Minecraft simulator engine) |
| Rendering | Xvfb virtual framebuffer (headless rendering, no display required) |

### Starting the Sandbox

```bash
docker run -d --name mineexplorer -p 8000:8000 davidzhth/mineexplorer:0.0.1
```

The service listens on port `8000`. On first launch, Minecraft needs to load the world — this typically takes **60–120 seconds**. You can check readiness with:

```bash
curl http://localhost:8000/monitor/alive
# Returns: {"status":"alive", ...}
```

### Local Environment Configuration

Once the sandbox is running, set the following environment variable so that both `generate_benchmark.py` and `eval_benchmark.py` connect to it automatically:

```bash
export MC_SANDBOX_URL=http://localhost:8000
```

You are then ready to generate and evaluate the benchmark as described in the sections below.

### Reproducible Docker sandbox startup

The repository includes a startup helper that pins the published image by
manifest digest, verifies that the Docker daemon is Linux/x86_64, reuses an
already-correct container, and waits for `/monitor/alive`:

```bash
scripts/start_minecraft_docker.sh
```

When Docker runs on a separate x86_64 host, use a Docker SSH context and give
the helper the HTTP address that is reachable from the evaluation node:

```bash
export DOCKER_HOST=ssh://<user>@<x86-docker-host>
export MC_SANDBOX_URL=http://<x86-docker-host>:8000
scripts/start_minecraft_docker.sh
```

The helper deliberately refuses an ARM64 Docker daemon. The published image
has no ARM64 manifest, and emulated Minecraft is not a valid benchmark
runtime. It also never replaces an existing same-named container that points
at a different image.

### Native ARM64 sandbox (no Docker)

On an ARM64 cluster such as NCSA DeltaAI (GH200) there is no way to run the
published image: it is `linux/amd64` only, the nodes have no qemu binfmt
handler, and rootless podman has no subuid range to unpack a distro image
with. The sandbox therefore runs **natively** instead, reusing the same
`mcprec-6.13.jar` engine the image ships.

Only two things about the engine are architecture-bound, and both are
replaced rather than emulated:

| Component | Published image | Native ARM64 |
|-----------|-----------------|--------------|
| LWJGL | 3.2.2, x86-64 natives bundled in the fat jar | 3.3.3 with `natives-linux-arm64`, placed ahead of the jar on the classpath (`-cp`, not `-jar`) |
| Memory allocator | LWJGL's bundled jemalloc | system allocator — jemalloc aborts on GH200's 64 KiB pages |
| JDK | OpenJDK 8 | Temurin 8 (aarch64); Java 11 breaks Malmo's env server, which needs JAXB |
| Rendering | Xvfb + Mesa `swrast` (llvmpipe) | identical — the image ships no VirtualGL and no GPU GL |

Provision once, then start the service:

```bash
scripts/setup_minecraft_arm64.sh          # LWJGL, JDK 8, conda env, engine, patches
scripts/start_minecraft_arm64.sh          # Xvfb + uvicorn on port 8000
export MC_SANDBOX_URL=http://<node>:8000
```

Both honour `MC_ARM64_ROOT` (default `/work/nvme/bdrx/dzhang5/mc-arm64`),
`MC_SANDBOX_ENV`, and `MC_SANDBOX_PORT`. Because the service is CPU-rendered,
run it inside a Slurm allocation rather than on a login node; the evaluation
client can then reach it at `http://127.0.0.1:8000` from the same job.

Known limitation: `/create_env` without `yaml_config` or `commands` falls back
to `gym.make()` via the `minerl` package, which is not installed in the ARM64
environment. The benchmark always supplies a scene config, so this path is
unused.

---

## 2. Environment Setup

Install the required Python packages:

```bash
pip install gymnasium numpy requests pillow loguru python-dotenv typer fastapi uvicorn pydantic imageio imageio-ffmpeg
```

Set the required environment variables:

```bash
export AGENT_API_KEY="your_api_key"
export AGENT_API_BASE="https://your-api-endpoint/v1/openai/native"
```

---

## 3. Generating the Benchmark

Use `generate_benchmark.py` to generate Minecraft evaluation tasks. The `benchmark` directory contains the benchmark used in the paper, covering single-hop to 4-hop tasks.

```bash
python generate_benchmark.py multi \
    --model aws.claude-opus-4.6 \
    --num-samples 10 \
    --k-min 1 \
    --k-max 1 \
    --candidate-num 1 \
    --output benchmark_new
```

### Key Arguments

| Argument | Description |
|----------|-------------|
| `multi` / `single` | Multi-agent or single-agent benchmark generation. The paper uses multi-agent mode, which produces more reliable instances but is slower due to sandbox interaction. |
| `--model` | Model name to use for generation |
| `--num-samples` | Number of samples to generate |
| `--k-min` / `--k-max` | Range of subtask hops per sample (e.g., set both to `1` for single-hop tasks only) |
| `--candidate-num` | Number of candidate atomic tasks |
| `--output` | Output directory |

### Output Structure

```
benchmark_new/
├── 0000/
│   └── multi-agent/
│       ├── metadata.json        # Scene configuration
│       ├── milestones.json      # Milestone definitions
│       ├── reasoning_graph.json # Dependency graph
│       └── debate_log.json      # Agent dialogue log
├── 0001/
│   └── multi-agent/
│       └── ...
```

### Want to Generate Harder Tasks?

You can generate extremely challenging tasks by increasing `--k-min`, `--k-max`, and `--candidate-num`. For example, the following command generates tasks with 8–12 prerequisite hops and 15 candidate atomic tasks:

```bash
python generate_benchmark.py multi \
    --model aws.claude-opus-4.6 \
    --num-samples 10 \
    --k-min 8 \
    --k-max 12 \
    --candidate-num 15 \
    --output benchmark_hard
```

This produces tasks with deeply nested, multi-branch dependency graphs — far more complex than standard benchmark instances:

<div align="center">
  <img src="https://raw.githubusercontent.com/Jometeorie/MineExplorer/main/figures/hard_reasoning_graph.png" alt="Hard Task Dependency Graph" width="900"/>
</div>

---

## 4. Evaluating the Benchmark

Use `eval_benchmark.py` to run an agent on the generated benchmark and evaluate its performance.

### Using an OpenAI-compatible API

```bash
python eval_benchmark.py \
    --model aws.claude-opus-4.6 \
    --benchmark-dir benchmark_new \
    --output-dir results \
    --num-workers 10 \
    --resume
```

### Using a Local vLLM Service

Start the vLLM server first:

```bash
python -m vllm.entrypoints.openai.api_server \
    --model Qwen2.5-7B \
    --port 8000
```

Then run evaluation:

```bash
python eval_benchmark.py \
    --model Qwen2.5-7B \
    --benchmark-dir benchmark_new \
    --output-dir results \
    --num-workers 10 \
    --use-vllm
```

### Common Arguments

| Argument | Description |
|----------|-------------|
| `--model` | Model to use for evaluation |
| `--benchmark-dir` | Path to the benchmark directory |
| `--output-dir` | Directory to save results |
| `--num-workers` | Number of parallel sandbox workers |
| `--resume` | Resume from checkpoint (skip completed tasks) |
| `--limit` | Limit number of evaluation samples (for testing) |

### DeltaAI: Qwen3.5-27B on scenes 0313 and 0544

DeltaAI GH200 nodes are `aarch64`, but the released
`davidzhth/mineexplorer:0.0.1` sandbox image is `linux/amd64` only. Run that
container on a reachable x86_64 Docker host with
`scripts/start_minecraft_docker.sh` and expose its port 8000 to the compute
node. The Qwen service itself runs on one GH200 and uses port 30000, avoiding
the README examples' port-8000 collision.

Create the native task environment once. By default this also downloads and
checksum-verifies the pinned model revision (about 56 GB) in
`/work/nvme/bdrx/dzhang5/huggingface/hub`, using one download worker to avoid
the memory spike from concurrent 5 GB shards:

```bash
scripts/setup_deltaai_qwen35.sh
```

Set `DOWNLOAD_MODEL=0` only when creating or repairing the Python environment
without populating the model cache.

The runner pins the official model revision
`fc05daec18b0a78c049392ed2e771dde82bdf654`, selects exactly the directory
IDs `0313` and `0544`, uses one sandbox worker, disables model thinking for
action-JSON reliability, and defaults to the paper-comparable
`--no-milestone-hint` protocol.

```bash
export MC_SANDBOX_URL=http://<x86-sandbox-host>:8000

scripts/launch.sh \
  -s qwen35-0313-0544 -t E1 \
  -p 'Qwen3.5-27B can execute both selected Minecraft scenes; pass if both write auditable result artifacts' \
  -T 06:00:00 -N 1 -g 1 -c 16 -m 96G \
  -C qwen35-27b-transformers-nonthinking \
  -D benchmark-directories-0313-0544 \
  -K Qwen3.5-27B@fc05daec18b0 \
  -- scripts/run_qwen35_0313_0544.sh
```

Use `scripts/monitor.sh <run-id>` to inspect the recorded Slurm run. Heavy
logs and results are written under the harness-provided artifact directory.

### Output Structure

```
results/
└── aws.claude-opus-4.6/
    ├── 0000/
    │   ├── result.json       # Evaluation result
    │   ├── episode.mp4       # Episode replay video
    │   └── messages/         # Conversation logs
    ├── 0001/
    │   └── ...
    └── eval_summary.json     # Aggregated statistics
```

---

## Results

<div align="center">
  <img src="https://raw.githubusercontent.com/Jometeorie/MineExplorer/main/figures/results.png" alt="Benchmark Results" width="900"/>
</div>

---

## Citation

If you find this work useful, please cite:

```bibtex
@misc{ju2026mineexplorerevaluatingopenworldexploration,
      title={MineExplorer: Evaluating Open-World Exploration of MLLM Agents in Minecraft}, 
      author={Tianjie Ju and Yueqing Sun and Zheng Wu and Wei Zhang and Yaqi Huo and Xi Su and Qi Gu and Xunliang Cai and Gongshen Liu and Zhuosheng Zhang},
      year={2026},
      eprint={2605.30931},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2605.30931}, 
}
```

---

## License

This project is released under the [MIT License](LICENSE).
