# Progress

Append material checkpoints only: phase changes, decision-relevant probes, experiment launches,
failures and replans, verification, commits, pushes, and handoffs. Do not log every command.

## 2026-08-15 — task initialized

- State: initialized
- Evidence: none
- Next: follow `task_plan.md` Current Cycle

## 2026-08-15 — discovery contract frozen

- State: Phase 1 in progress; target directory semantics and official model identity resolved.
- Evidence: Qwen revision `fc05daec18b0a78c049392ed2e771dde82bdf654`; model weight bytes `55,563,022,432`; Docker image platform `linux/amd64`; Slurm allocation `2954030` on `gh005`.
- Blockers: released Minecraft image architecture; existing inference environments are either x86_64 or dependency-inconsistent.
- Next: bounded compute-node architecture and service probe.

## 2026-08-15 — ARM64 and Docker routes separated

- State: implementation in progress.
- Evidence: gh005 is `aarch64` with one NVIDIA GH200 120GB (97,871 MiB visible); no qemu-x86_64 binfmt; image manifest digest `sha256:f7ec400389d7e1e617c28378678cf34f58ad79ab31075215ecb34c6f2e85ac0a` is amd64.
- Change: added a digest-pinned Docker startup/readiness helper for a reachable x86_64 daemon; added a one-GPU Qwen runner on port 30000 and exact two-directory benchmark view.
- Failure/replan: eight-way HF download exceeded a 16 GB step memory limit; resumed the preserved cache with one worker and 32 GB.
- Environment: a task-owned conda clone is being built from the verified native CUDA base; shared environments remain unchanged.
- Blocker: no reachable x86_64 Docker daemon or `MC_SANDBOX_URL` is configured in this session.
- Next: finish environment/model verification, then run the end-to-end evaluation when the Docker endpoint is supplied.

## 2026-08-15 — clean environment and exact model verified

- State: Phase 1 complete; Phase 2 implementation complete.
- Environment: native `aarch64` conda prefix `/work/nvme/bdrx/dzhang5/conda/envs/mineexplorer-qwen35-tf`; Torch 2.9.1/CUDA 12.9; Transformers 5.12.1; `pip check` clean; GH200 CUDA probe passed in Slurm job 2954030.
- Model: all 24 files for revision `fc05daec18b0a78c049392ed2e771dde82bdf654` passed `hf cache verify --fail-on-missing-files` under `/work/nvme/bdrx/dzhang5/huggingface/hub`.
- Smoke: final environment returned exactly `IMAGE_OK` for a 128x128 image; `/health` returned `ok`; evidence is under `artifacts/qwen35-final-env-smoke-2954030/`.
- Interpretation: multimodal serving is engineering-verified; no Minecraft execution or quality claim is made.
- Next: hand off the external x86_64 Docker endpoint requirement and commit the reproducible configuration.

## 2026-08-15 — Docker route configured, end-to-end run gated

- State: Phase 3 handoff in progress.
- Change: added a digest-pinned plain-Docker helper with amd64 enforcement, remote `DOCKER_HOST` support, safe container reuse, and `/monitor/alive` readiness; added the exact 0313/0544 runner and harness launch command.
- Verification: all shell scripts pass `bash -n`; repository diff passes `git diff --check`; clean-environment evaluation CLI imports successfully; `DOWNLOAD_MODEL=0 scripts/setup_deltaai_qwen35.sh` completes idempotently with a clean `pip check`; local Docker negative check fails clearly because no daemon is reachable.
- Blocker: this ARM64 cluster has no Docker daemon or x86 emulation, and no reachable x86 Docker host/`MC_SANDBOX_URL` is configured. Therefore no `result.json` or `episode.mp4` has been fabricated for either scene.
- Next: provide `DOCKER_HOST=ssh://user@x86-host` plus `MC_SANDBOX_URL=http://x86-host:8000`, or an already-running reachable sandbox URL.
