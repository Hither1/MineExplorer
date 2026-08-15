# Task Plan: configure Qwen3.5-27B environment and run Minecraft tasks 0313 and 0544

## Stable Anchor

- Scientific question: Can the repository's current multimodal agent evaluate directory tasks 0313 and 0544 with the official Qwen/Qwen3.5-27B checkpoint on DeltaAI GH200?
- Target claim or outcome: A reproducible ARM64/GH200 runtime plus auditable result artifacts for exactly benchmark directories 0313 and 0544.
- Success criterion: The Qwen3.5 service accepts an image chat request, both Minecraft scenes start, and each produces result.json plus episode evidence (success is recorded but not required for engineering completion).
- Constraints and budget: One existing GH200 allocation when safe; single-node and fewer than four GPUs; no login-node GPU inference; large files under /work/nvme; exact model revision recorded; paper-comparable evaluation uses no milestone hint.
- Non-goals: Benchmark-wide evaluation, hyperparameter sweeps, model-quality claims, changing task/milestone semantics, or productionizing the repository.

## Current Cycle

- Working hypothesis: The clean ARM64 Transformers 5.12.1 environment can serve Qwen3.5-27B on one GH200; the evaluation can target the two directory IDs through a two-link benchmark view.
- Main uncertainty: The released Minecraft Docker image is amd64-only, while DeltaAI is aarch64, and no reachable x86_64 Docker daemon or remote Minecraft endpoint is currently configured.
- Next decisive experiment or implementation: Start the digest-pinned sandbox on a user-provided x86_64 Docker daemon, then launch the recorded two-scene E1 run.
- Expected pass/fail signal: A live /monitor/alive response from the x86 Docker sandbox and a successful multimodal /v1/chat/completions response from Qwen3.5 on GH200.
- Fallback: If no x86 Docker daemon is reachable, preserve the native Qwen service/environment and stop before fabricating Minecraft results; hand off the exact `DOCKER_HOST`/`MC_SANDBOX_URL` requirement.

## Success Criteria

- [x] An ARM64-compatible, reproducible Python/inference environment is recorded and passes imports inside Slurm.
- [x] Qwen/Qwen3.5-27B revision fc05daec18b0a78c049392ed2e771dde82bdf654 serves an image request through an OpenAI-compatible endpoint.
- [ ] Exactly directory tasks 0313 and 0544 are selected and each writes result.json and episode.mp4.
- [ ] Run ID, Slurm job ID, commands, model/data identity, logs, and artifact paths are preserved.

## Parallel Tracks

| track | owner | mode | worktree / branch | dependency | deliverable | status |
|---|---|---|---|---|---|---|
| primary | primary | integrate | current | none | final synthesis | active |
| repository runtime | repo_runtime | read-only | current | none | launcher/backend/environment evidence | complete |
| task semantics | task_semantics | read-only | current | none | exact 0313/0544 selection and outputs | complete |
| model compatibility | model_compat | read-only | current | none | official Qwen3.5 identity and backend constraints | complete |

## Phases

### Phase 1: Discover and specify

- [x] Confirm live state and relevant owners.
- [x] Record the smallest implementation and verification contract.
- **Status:** complete
- **Evidence:** `findings.md`; Qwen model SHA from Hugging Face API; `benchmark/{0313,0544}/multi-agent`; Slurm allocation 2954030

### Phase 2: Implement or run the decisive test

- [x] Make the smallest coherent environment, Docker, and exact-task-selection change.
- [x] Record the clean-environment Qwen multimodal smoke and external sandbox blocker.
- **Status:** complete
- **Evidence:** `artifacts/qwen35-final-env-smoke-2954030/`; checksum verification of 24 files; `scripts/{setup_deltaai_qwen35,start_minecraft_docker,run_qwen35_0313_0544}.sh`

### Phase 3: Interpret and hand off

- [x] Compare the evidence against the stable anchor and expected signal.
- [ ] Close remaining phases as complete, superseded_by_evidence, or abandoned_with_evidence.
- [ ] Commit/push coherent work and archive or hand off the task.
- **Status:** in_progress
- **Evidence:** Qwen image request passed; Minecraft service check cannot run without a reachable x86_64 daemon.

## Decisions And Blockers

| Item | Decision or blocker | Evidence / owner |
|---|---|---|
| task identity | Interpret 0313 and 0544 as directory IDs because eval_benchmark.py uses directory names as scene_id; embedded metadata IDs are inconsistent. | `eval_benchmark.py`; task_semantics |
| protocol | Use default agent, one worker, and `--no-milestone-hint` for paper-comparable semantics. | `eval_benchmark.py` CLI help |
| sandbox blocker | Published image `davidzhth/mineexplorer:0.0.1` has only linux/amd64 manifest; no Friday or remote sandbox variables are configured. A digest-pinned Docker helper now enforces an x86 daemon and readiness check. | `docker manifest inspect --verbose`; `scripts/start_minecraft_docker.sh` |
| inference environment | Use a task-owned native conda clone with Transformers 5.12.1; do not use the x86_64 vLLM venv or dependency-broken SGLang overlay. | clean `pip check`; Slurm CUDA probe; final multimodal smoke |

## Verification Contract

- Command or probe: sandbox `GET /monitor/alive`; Transformers `GET /v1/models` plus one image chat completion; `eval_benchmark.py` over a two-symlink benchmark view.
- Expected signal: both services become ready, model returns a parseable multimodal response, and outputs exist only for scene IDs 0313 and 0544.
- Experiment/run pointer, if any: existing reserved allocation Slurm job `2954030`; Qwen smoke artifacts at `artifacts/qwen35-final-env-smoke-2954030/`; Minecraft run ID pending a sandbox endpoint.

## Next Action

Obtain a reachable `linux/amd64` Docker daemon and `MC_SANDBOX_URL`, run `scripts/start_minecraft_docker.sh`, then launch the exact two-scene E1 command recorded in `README.md`.
