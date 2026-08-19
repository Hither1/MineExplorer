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
IDs `0313` and `0544`, uses one sandbox worker, and defaults to the
paper-comparable `--no-milestone-hint` protocol. Thinking is not set here: it
is a property of the server and the codex effort value, described under
[the thinking invariant](#the-thinking-invariant) below.

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

### Running the agent × scaffold × task matrix

Three things vary independently. Keeping them separate is the whole design: the
agent axis is the question, the scaffold axis is the control that keeps a
PRO-LONG result from being a Codex-CLI result, and the task axis is what makes
either readable.

| Axis | Variable | Values |
|---|---|---|
| **agent** | `AGENT_MODE` | `default`, `hypothesis`, `prolong` |
| **scaffold** | channel half of `CELLS` | `codex` (through the Codex CLI), `vllm` (straight at the server) |
| **task** | `SCENES` | any directory under `benchmark/`, space-separated |

There is no `prolong:vllm` cell. PRO-LONG is built on `codex exec resume`
sessions, so outside the CLI that agent does not exist.

**One cell, by hand.** Both runners take the same variables; only the channel
differs. `scripts/run_codex_0313_0544.sh` is the codex channel and
`scripts/run_qwen35_0313_0544.sh` is the direct one.

```bash
export MC_SANDBOX_URL=http://<x86-sandbox-host>:8000

env MODEL_SERVER=qwen38-27b MODEL_ID=Qwen/Qwen3.8-27B \
    AGENT_MODE=prolong SCENES="0694 0311" MAX_STEPS=300 \
    MILESTONE_HINT=1 CODEX_EFFORT=low CODEX_TIMEOUT=300 \
    bash scripts/with_minecraft_arm64.sh -- bash scripts/run_codex_0313_0544.sh
```

`SCENES` takes more than one id, and `eval_benchmark.py` walks every scene in
the benchmark directory in one process, so several tasks per job costs nothing
extra. `--resume` skips any scene that already wrote a `result.json`, which
makes a resubmission cheap. `--num-workers` runs them concurrently instead;
the sandbox routes by a per-instance `session_id` and `/list_sessions` shows
them, but concurrent use is untested here — verify before relying on it.

**The whole matrix, as Slurm jobs.** `scripts/launch_matrix.sh` submits one job
per (cell × scene). `DRY=1` prints the commands instead of submitting them,
which is the cheapest way to check a change.

```bash
DRY=1 TAG=m1 MODEL_TAG=qwen38 MODEL_ID=Qwen/Qwen3.8-27B SERVER=qwen38-27b \
  SCENES="0694 0311 0182" MAX_STEPS=300 WALL=05:00:00 \
  CODEX_EFFORT=low CODEX_TIMEOUT=300 \
  CELLS="default:codex hypothesis:codex prolong:codex default:vllm hypothesis:vllm" \
  bash scripts/launch_matrix.sh
```

Set `SERVER=` (empty) with a hosted `MODEL_ID` to run the reference arm through
the same file; that is the one value which makes the runner link the account
credential instead of resolving a local server. Use `SEED_TAG` to distinguish
repeat seeds of an otherwise identical cell.

<a id="the-server-comes-first"></a>
**The server comes first.** Both channels talk to one shared vLLM server, and a
cell refuses to start against a server that cannot outlive it
(`MODEL_SERVER_MIN_REMAINING`, minutes) rather than losing it mid-episode; it
waits `MODEL_SERVER_WAIT` seconds for a suitable one to appear.

```bash
env VLLM_TP=1 VLLM_MAX_MODEL_LEN=131072 SERVER_SLUG=qwen38-27b \
    MODEL_ID=Qwen/Qwen3.8-27B MODEL_REVISION=1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0 \
    bash scripts/serve_vllm.sh
```

Pass anything a run's meaning depends on in the job's own `env` prefix rather
than editing the script: `snapshot_exec.sh` copies `scripts/` at job *start*,
so a queued job picks up edits made after it was submitted, and the manifest's
`commit` field records that state without pinning it.

<a id="the-thinking-invariant"></a>
**The thinking invariant.** The two channels are configured from opposite ends
and must agree, or the scaffold control differs in thinking as well as in
scaffold. The direct arm follows the server's
`VLLM_CHAT_TEMPLATE_KWARGS`; the codex arms follow `CODEX_EFFORT`, because vLLM
synthesises `enable_thinking = (effort != "none")` from the request and lets it
override the server default. Both default to thinking **on**. To turn it off,
change both sides:

```bash
VLLM_CHAT_TEMPLATE_KWARGS='{"enable_thinking": false}'   # server
CODEX_LOCAL_EFFORT=none                                  # cells
```

`python -m prolong_mc.selftest` asserts the two defaults agree, so a
half-applied change fails there rather than in a matrix.

**The request layout (`--prompt-layout`, `PROMPT_LAYOUT` for `run_cell.sh` /
`launch_4hop.sh`).** The default and hypothesis agents resend ~5–8k tokens per
step (instructions, memory, 20 captions, 20 images). In the `legacy` layout —
the default, today's prompt byte for byte — the memory and hints sit between
the goal and the instructions and the 20-frame window slides, so consecutive
steps share under 150 tokens and vLLM's prefix cache (800-token blocks on the
hybrid Qwen3.x servers) reuses nothing; every step re-prefills the whole prompt,
and on a shared server those prefills halve the neighbours' decode speed.
`static-first` moves the per-step state after the frames so the instruction
block caches; `append-only` also keeps the frame buffer append-only (rebased
every 10 steps, so the window is 20–29 frames) with captions that do not name a
frame's position, so the frames cache too. Measured on three cells sharing one
TP=1 server: 7.3 s/step legacy, 6.8 s static-first, 4.4 s append-only
(`experiments/EVAL_LATENCY_helixon.md`). Anything but `legacy` changes what
the model reads — order, and for `append-only` the window — so it is a
different arm: `result.json` records `prompt_layout`, `launch_4hop.sh` gives
such cells a `-<layout>` tag suffix, and `summarize_4hop.py` keeps them out of
the legacy arms. `scripts/prompt_layout_check.py` shows the structure and,
against a server, the shared prefix; `scripts/bench_agent_latency.py` replays a
recorded cell to time the layouts on a given server.

**The response style (`--response-style`, `RESPONSE_STYLE` for `run_cell.sh` /
`launch_4hop.sh`).** The layout is about the prefill; the style is about the
decode, which is what a step waits for once the prefill is cached. Under `full`
— the default, today's protocol byte for byte — the model answers with
pretty-printed JSON, rewrites the whole memory every step and, for the
hypothesis agent, re-emits hypothesis ops and the plan every step: 237 tokens
per default step of which 118 are a memory that is identical to the previous
step's in a third of the steps, 508 per hypothesis step. `compact` asks for the
same fields with the same meaning but on one line, with a 1–3 sentence thought,
and with `memory_update` / `hypotheses` / `plan` sent only on the steps where
they change (an absent key means "unchanged", which the runner and
`HypothesisAgent` already treat as "keep"; `_HYP_THOUGHT_PROCESS_COMPACT` /
`_DEFAULT_THOUGHT_PROCESS_COMPACT` in `mc_agent/` are the exact wording, the
hypothesis-writing guidance is unchanged). Because the memory is now sent only
when the model decides to, the compact state block always carries a memory line
— "empty - write it this step", or "last rewritten at step N" and, after 20
steps without a rewrite, "rewrite it this step" (`MEMORY_REWRITE_DUE`); the
first compact cell without that line ran 54 steps and three milestones without
ever writing a memory. What the model maintains does not
change; what it re-emits does — so it is a different arm, recorded in
`result.json` as `response_style`, suffixed `-compact` by `launch_4hop.sh` and
kept apart by `summarize_4hop.py`. `bench_agent_latency.py --style compact`
times it and reports how often the memory / graph / plan actually changed.

Both knobs apply to the default and hypothesis agents on **either** channel — the same
code builds the request, and `CodexProvider` flattens it into one text prompt plus image
files, so the ordering survives (`prompt_layout_check.py --codex` measures the shared
prefix there: 1–3 % legacy → 94–96 % append-only). What they buy on the codex channel is
small, though: that arm is priced by its 120 s ceiling and 3–5 round trips per answered
call, not by our prefill. PRO-LONG writes its own prompt, so `--agent-mode prolong`
rejects both flags rather than ignoring them.

**The codex channel's reply shape (`--codex-output-schema`, `CODEX_OUTPUT_SCHEMA=1`).**
Implemented and off by default, and it should stay off unless a single-shot codex arm
is what is wanted. With it, `CodexProvider` writes the agent's reply schema
(`default_reply_schema` / `hypothesis_reply_schema`, which track the RESPONSE FORMAT
block and the response style) into the call's workspace — it must be *inside* it, the
sandbox gives codex a read scope of the workspace only — and passes `codex exec
--output-schema`. **codex applies that constraint to every assistant turn, not only the
final one, so the model cannot emit a tool call at all**: told explicitly to run a shell
command first, it ran none 3/3 with the schema on and made 4 tool calls with it off. That
makes the flag a change of arm — the default/hypothesis codex arms are PRO-LONG's
scaffold control, same tool surface — rather than a reliability switch. What it buys is
narrow: of 2266 calls on the c4h `default × codex` arm, 148 were retried on a parse
failure (46 prose answers with no JSON, which a schema fixes; 102 repetition collapses,
which today are caught and retried successfully and under a schema can come back as a
well-formed object with a degenerate string), and the 748 ceiling timeouts are untouched.
Recorded in `result.json` as `codex_output_schema`, tagged `-schema` by `launch_4hop.sh`,
and rejected for `--agent-mode prolong`.

**None of the three reaches the prolong arm, and a mixed campaign is fine.** PRO-LONG
writes its own prompt (`prolong_mc`: its own AGENTS.md workflow and one resumed
conversation), so `eval_benchmark.py` rejects all three for `--agent-mode prolong` rather
than accept a flag it would silently ignore. `run_cell.sh` therefore does not pass them
for that agent, and `launch_4hop.sh` gives a prolong cell no tag suffix: one campaign can
set `PROMPT_LAYOUT` / `RESPONSE_STYLE` / `CODEX_OUTPUT_SCHEMA` for the direct arms while
`prolong:codex` runs its own protocol unchanged, and the prolong cells resume into — and
are pooled with — the prolong cells of a `legacy` run of the same `PREFIX`, since under
any setting of the three they are the same arm. `result.json` records `legacy` / `full`
for them, which is what they ran.

### Helixon: the strict 4-hop campaign (the formal runs)

Everything in `experiments/` whose name says `helixon` came from the configuration below,
on the **helixon cluster**. `experiments/README.md` is the record of what ran — settings
in full, per-wave serving layout, and the 49 episodes as one CSV row each; this section is
how to run it again. The two are meant to be read together: if they disagree, the record
is right about what happened and this is right about what to type.

**Three hosts, three things to start, in this order.** A cell holds its sandbox session and
its server for the whole episode and there is no readiness gate on this path — the
`MODEL_SERVER_*` waits belong to the Slurm runner (`scripts/launch_matrix.sh`), not to
`launch_4hop.sh` — so both must be up and verified before the first cell starts, and must
stay up for the hours the campaign runs.

| host | what runs there | reached as |
|---|---|---|
| `a230` | the Minecraft sandbox, one rootless podman container | `192.168.2.22:8000` (`MC_SANDBOX_URL`) |
| `a227` | the vLLM servers, three of them, TP=2 on GPUs 2–7 of eight A100 80GB | `192.168.2.20:8001-8003` (`SERVERS`) |
| `a219` | the runner — `launch_4hop.sh` and every cell process | — |

Nothing is scheduled: these are long-lived tmux sessions on shared nodes, so re-probe the
GPUs before launching and stop only PIDs you have verified are yours.

**1. The sandbox (a230).** One container serves the whole campaign; `scripts/run_cell.sh`
reads its URL from `.env`. See [Reproducible Docker sandbox startup](#reproducible-docker-sandbox-startup)
— on helixon it is podman, since no user on these nodes has a Docker socket.

```bash
# .env, on the runner
MC_SANDBOX_URL=http://192.168.2.22:8000
```

**2. The servers (a227).** The campaign's servers come from the sibling `qwen35-serve`
repository, not from `scripts/serve_vllm.sh` — that one is the generic single-server path
described under [the server comes first](#the-server-comes-first). Three identical TP=2
servers, one per GPU pair, so `launch_4hop.sh` can deal cells round-robin over them:

| session / run file | GPUs | port |
|---|---|---|
| `qwen35-s1-k3` | 2,3 | 8001 |
| `qwen35-s2-k3` | 4,5 | 8002 |
| `qwen35-s3-k3` | 6,7 | 8003 |

The run files are already generated and are launched one per server (about 10 minutes to
load); `scripts/serve.sh` regenerates them and starts each inside its own named tmux
session on the target host:

```bash
# in the qwen35-serve repository, from the login node
scripts/serve.sh --model qwen3.5-27b --session qwen35-s1-k3 \
  --host a227 --ip 192.168.2.20 --gpus 2,3 --port 8001 \
  --tp 2 --max-model-len 131072 --spec-tokens 3 --prefix-cache
```

What the evaluation actually depends on is the flag set, whoever generates it. These are
the ones a result is only comparable across if they match — `--override-generation-config`
because it is the only output cap that reaches both channels (codex sends none), and
`enable_thinking` because it is half of [the thinking invariant](#the-thinking-invariant):

```
--served-model-name Qwen3.5-27B …        # = the results subdirectory, and MODEL below
--tensor-parallel-size 2  --max-model-len 131072
--max-num-seqs 64  --max-num-batched-tokens 8192  --gpu-memory-utilization 0.90
--limit-mm-per-prompt '{"image":128,"video":1}'
--speculative-config '{"method":"qwen3_5_mtp","num_speculative_tokens":3}'
--enable-prefix-caching
--override-generation-config '{"temperature":0.7,"top_p":0.8,"top_k":20,"max_new_tokens":1024}'
--default-chat-template-kwargs '{"enable_thinking":false}'
--enable-auto-tool-choice  --tool-call-parser qwen3_xml
```

Wire-check all three before spending a campaign on them: the served name answers at
131072, a chat completion stops at 1024 with `length` and no `<think>`, and a tool call
arrives as a parsed `tool_calls` entry rather than `<tool_call>` text in the content.

**3. The campaign (a219).** The scene set is the strict 4-hop seven — everything that
survives `scripts/screen_scenes.py --hops 4 --reachable --min-depth 4 --max-free 0
--no-backwards`, split one directory per scene under `bench_4hop7/_split/<scene>/`. It is
not in the repository; regenerate it before the first run.

```bash
PREFIX=q35 MODEL=Qwen3.5-27B \
SERVERS="http://192.168.2.20:8001/v1 http://192.168.2.20:8002/v1 http://192.168.2.20:8003/v1" \
ARMS="default:vllm prolong:codex hypothesis:vllm" \
SCENES="0306 0726 0182 0311 0482 0603 0763" \
MAX_STEPS=300 CONC=14 \
  bash scripts/launch_4hop.sh 2>&1 | tee outputs/log-q35-launcher.txt
```

`PREFIX` and `MODEL` are the whole of what moves a campaign between checkpoints —
`MODEL` must be the served name, because it is also the results subdirectory. Add
`default:codex` to `ARMS` for the four-arm version — budget for it, it is 44.6 h of
cell-time against 10.8 h for `default × vllm` over the same seven scenes
(`experiments/RESULTS_helixon_4hop.md`). The launcher skips any cell
whose `result.json` exists, so a re-launch resumes; per-cell logs land in
`outputs/log-<tag>.txt`.

**The formal protocol is `legacy` / `full`.** The three knobs above default to it, which is
today's prompt and reply byte for byte. `append-only` / `compact` are faster and are a
different arm — do not mix them into a campaign whose other cells ran `legacy`, and note
that they do not reach `prolong:codex` at all.

**4. Reading it back.**

```bash
python scripts/summarize_4hop.py --prefix q35 --md    # scene × arm, from the cells' own files
python scripts/export_4hop.py --campaign q35:Qwen3.5-27B   # 4hop_cells.csv + trajectories/
```

**What the recorded 49 episodes used, and the one thing to change.** They ran at MTP
**k=1** (`qwen35-s{1,2,3}.sh`, no `-k3`); the `-k3` files above came later. Depth 3 is
exact in distribution — it changes speed, not the output distribution — and on this
layout it is worth roughly `default` 9.5 → 5.2 s/step and `hypothesis` 12.7 → 9.2 s/step
at three cells a server, so a new campaign should use it and is still comparable to the
recorded ones. Two further caveats live in `experiments/README.md` rather than here: wave 1
of the Qwen3.8 campaign ran without prefix caching on a different server layout, and
`prolong × codex` carries a 900 s per-call ceiling it never reaches while `default × codex`
carries a 120 s one that bounds its score.

### The codex arms' sandbox

Upstream PRO-LONG runs its agent in a Docker container on an `--internal` network
whose only exit is a squid allowlist proxy to the model API. The earlier decision
here was "no containers — codex's own bubblewrap sandbox is enough"
(`-s workspace-write`, findings #12–14). That was right about the mechanism and
wrong about the coverage: codex's inner sandbox bounds *writes* and the agent
shell's network, but **not reads** — and on this benchmark the answers are files.
Every milestone is `position_near_with_facing` against a spawn-relative
coordinate written in `benchmark/<scene>/multi-agent/metadata.json`; reading it is
the solution to a navigation task, not a hint about one. `milestone_checker.py`
and other arms' `result.json` are equally readable.

Worse, one route to those coordinates never touches this filesystem at all.
Codex hands the model whatever the authenticated account carries, *before* any
sandbox applies, because those tools run server-side. Measured on codex-cli
0.147.0 with this account: `web_search` defaults to `"cached"` and the model used
it; ~250 `mcp__codex_apps__*` connectors (github, gmail, slack, drive,
hugging_face) were in the tool list; `spawn_agent` was offered, so one analyzer
turn could fan out into threads the request accounting never sees. This is also
the 275 KB of tool schema per request that overflowed a 65536-token context and
failed 94% of one run's calls — the same defect, seen as cost.

So there are now two pieces, and both are on by default:

| what | where |
|---|---|
| only the workspace is reachable; no network but the model API | `prolong_mc/codex_sandbox.sh` — one bwrap mount + **network** namespace per `codex exec`, with an allowlisting CONNECT proxy on a unix socket (`prolong_mc/sandbox_proxy.py`) |
| a minimal, declared tool surface | `prolong_mc.codex_backend.SAFE_CODEX_FLAGS`, applied on the first turn and on `codex exec resume`, to `CodexTurn` and `CodexProvider` alike |

With the flags in force the model's whole tool surface is `apply_patch`,
`exec_command`, `update_plan`, `view_image`, `write_stdin`; anything else in a
transcript raises `SandboxViolation` and stops the run. (`--disable multi_agent`
does *not* remove the sub-agent tools; `agents.enabled=false` does.)

**The Minecraft server is deliberately not on the allowlist.** `MC_SANDBOX_URL`
is the runner's, not the agent's — the runner steps the world, the agent only
writes `actions.json` — and upstream draws the same line. A *local model* server
is different and is added automatically from `CODEX_BASE_URL` by
`scripts/run_codex_0313_0544.sh`.

`scripts/run_codex_0313_0544.sh` sets `CODEX_BIN` to the wrapper by default and
runs `python -m prolong_mc.sandbox_selftest` before the job; each result records
`codex_bin` and `codex_sandboxed`, because a run taken with the sandbox is not
the same arm as one taken without and the two must not be pooled. On DeltaAI
(aarch64) bwrap need not be installed — codex ships one that works as the outer
wrapper too:

```bash
export BWRAP_BIN=$NODE_DIR/lib/node_modules/@openai/codex/node_modules/\
@openai/codex-linux-arm64/vendor/aarch64-unknown-linux-musl/codex-resources/bwrap
python -m prolong_mc.sandbox_selftest              # no model, no quota
python -m prolong_mc.sandbox_selftest --with-model # + the live tool surface
```

**Runs taken before this landed** carried the full account tool surface and an
unbounded read of the repository. No transcript shows an agent using either, but
that is an audit of the runs we looked at, not a property of the harness — record
it next to any number quoted from them.

**Re-check finding #30 before quoting it.** "The analyzer could open `frames/` with
the image viewer but never looked (zero `view_image` calls)" was measured from
`codex_turns/*.events.jsonl`. Codex 0.147 runs the model's tools inside an `exec`
code-mode cell and `--json` reports only *shell* commands, so a nested
`tools.view_image(...)` **never appears in that stream at all** — the counter reads 0
whether or not the model looked. Verified on the sibling mllm-search port: an episode
whose event stream mentions `view_image` zero times has a conversation containing 20
calls that returned 60 images. The vision audit now reads the rollout instead, and
also counts `image_attach_failures` — the "Codex could not read the local image" line
that means `-i` never landed and the arm silently became vision-on-demand. Whether the
v3/v4 runs were actually blind is still answerable, but only from their rollouts:

```bash
grep -ho 'view_image' <run>/codex-home/sessions/*/*/*/rollout-*.jsonl | wc -l
grep -c 'could not read the local image' <run>/codex-home/sessions/*/*/*/rollout-*.jsonl
```

**PRO-LONG's own ablations** vary the scaffold inside the agent, and are read
only by `AGENT_MODE=prolong`: `PROLONG_LOG_WINDOW=N` truncates its log to the
last N entries (`0` is upstream's "latest state only") and `PROLONG_STATELESS=1`
removes the carried workspace. Setting either on another agent is refused at
launch rather than silently ignored.

**Reading the results.** `scripts/export_results.py` writes one row per scored
episode — task, pass/fail, and the settings it actually ran under — joining the
result files with each run's manifest and the trust judgements in
`RUN_LEDGER.txt`. `scripts/compare_runs.py` builds the comparison table.
`experiments/RESULTS.md` records what the DeltaAI campaign established, and
`experiments/results.csv` is the exported table.

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
