# Progress

Append material checkpoints only: phase changes, decision-relevant probes, experiment launches,
failures and replans, verification, commits, pushes, and handoffs. Do not log every command.

## 2026-08-15 — task initialized

- State: initialized. Follows the blocker left open by
  `tasks/codex-qwen35-27b-minecraft-0313-0544.configure-qwen3.5-27b-environment-and-run-minecraft-tasks-0313-a`
  ("no reachable x86_64 Docker daemon").
- Trigger: user asked whether podman could drive the Minecraft environment, then chose to
  attempt a native arm64 rebuild after the podman route was refuted.

## 2026-08-15 — Phase 1 complete: container route abandoned with evidence

- State: Phase 1 complete.
- Evidence: findings rows 1-3. Podman runs on this node but cannot execute amd64 images
  (no binfmt) and cannot even unpack ordinary distro images (no subuid).
- Change: none in the repository; probes only. Test podman store under `/tmp` was removed.

## 2026-08-15 — image dissected without executing it

- State: Phase 1 evidence gathering.
- Method: pulled manifest + selected layers straight from the Docker Hub registry API and
  streamed `tar -tz` listings; no container runtime involved.
- Recovered: `mc_server.py` (314-line FastAPI wrapper), `start_mc_server.sh`, and
  `engine.zip` → `mcprec-6.13.jar`. Working copies in `/work/nvme/bdrx/dzhang5/mc-arm64/`.
- Evidence: findings rows 4-5.

## 2026-08-15 — Phase 2 complete: Minecraft 1.16.5 runs natively on GH200

- State: Phase 2 complete; the central feasibility question is answered positively.
- Sequence: (1) LWJGL 3.3.3 arm64 GL probe passed → GL 4.5 llvmpipe under Xvfb;
  (2) first engine launch crashed in `GLX._initGlfw` (jemalloc `Unsupported system page size`
  on 64 KiB pages, cascading to an NPE in `GLFWErrorCallbackI`);
  (3) relaunch with `-Dorg.lwjgl.system.allocator=system` booted fully and opened
  `MalmoEnvServer on port 29999`.
- Evidence: findings rows 6-9; `/work/nvme/bdrx/dzhang5/mc-arm64/run/mc2.log`.
- Interpretation: engineering feasibility only. No benchmark or scientific claim is made yet,
  and rendering equivalence with the published x86 image has **not** been checked.

## 2026-08-15 — Phase 3 started: Python/MineStudio port

- State: Phase 3 in progress.
- Environment: new aarch64 prefix `/work/nvme/bdrx/dzhang5/conda/envs/mineexplorer-sandbox-arm64`
  (python 3.10). The verified eval/serving env `mineexplorer-qwen35-tf` is untouched.
- Launched: `pip install minestudio fastapi uvicorn pyyaml`; log at
  `/work/nvme/bdrx/dzhang5/mc-arm64/pip_minestudio.log`.
- Next: patch `launchClient.sh` for the LWJGL classpath / system allocator / own Xvfb, then
  run a `MinecraftSim` reset+step frame smoke.

## 2026-08-15 — Python side wired; E0 smoke submitted

- Install: `minestudio 1.1.6` + deps installed cleanly on aarch64 (torch 2.8.0,
  opencv-python 4.8.0.74 aarch64 wheel, fastapi 0.141.1). No pin needed relaxing.
- Wiring: `MINESTUDIO_DIR` selects the engine root, so the patched engine at
  `/work/nvme/bdrx/dzhang5/mc-arm64/engine/build/libs/mcprec-6.13.jar` is used as-is.
  The installed `minestudio/simulator/minerl/env/launchClient.sh` was replaced with the
  aarch64 version (`-cp` with LWJGL 3.3.3 first, system allocator, caller-managed Xvfb);
  the upstream file is preserved as `launchClient.sh.orig`.
- Equivalence check: the published x86 image has no VirtualGL and no NVIDIA GL, only
  Xvfb + Mesa swrast — the same software-rendering path this port uses (findings row 10).
- Launched: run `20260815-180254-mc-arm64-sim-smoke-60b9` (Slurm 2954865, ghx4, E0).
  DeltaAI refuses `-g 0`, so the CPU-rendered smoke still requests one GPU.
- Note: an earlier attempt to smoke on the login node was aborted — the shell killed itself
  via a `pkill -f` pattern that matched its own command line, and sustained llvmpipe
  rendering does not belong on a login node anyway.
- Next: read the smoke result; if frames are valid, serve `mc_server.py` and verify the
  five HTTP endpoints.

## 2026-08-15 — MinecraftSim renders real frames on aarch64 (E0 passed)

- Failures and fixes along the way, in order:
  1. `psutil` missing (undeclared MineStudio dep) — run `…-smoke-60b9`, Slurm 2954865.
  2. user-site leakage hid `lxml` and others; reinstalled under `PYTHONNOUSERSITE=1`,
     `pip check` now clean.
  3. JDK 11 booted and rendered but Malmo's `EnvServerSocketHandler` died on
     `NoClassDefFoundError: javax/xml/bind/JAXBException` — run `…-smoke-2080`,
     Slurm 2954884 (cancelled once diagnosed). Switched to Temurin 8u502 aarch64.
- PASS: run `20260815-180850-mc-arm64-sim-smoke-6d75` (Slurm 2954905, gh051) returned
  `RESULT: ok`. `reset` frame 360x640x3 uint8, mean 57.48 / std 50.91 / 255 unique values;
  after a 30° camera turn the frame differs (mean 45.25). Saved frames show a correctly
  rendered forest scene with HUD and player hand:
  `/work/nvme/bdrx/dzhang5/mc-arm64/smoke_reset.png`, `smoke_after_turn.png`.
  Under JDK 8 the OptiFine reflection errors disappear entirely.
- Interpretation: the aarch64 engine is functionally equivalent at the frame level for a
  default world. This is an engineering pass, not yet a benchmark-parity claim.
- Launched: run `20260815-181107-mc-arm64-http-verify-0a33` (Slurm 2954927) to exercise the
  five HTTP endpoints through `mc_server.py`.

## 2026-08-15 — Phase 3 complete: HTTP contract verified on aarch64

- Two more shallow failures first: `loguru` missing (another user-site casualty), then my own
  readiness assertion checking `status == 0` instead of `"alive"` (runs `…-0a33`, `…-2acf`).
- PASS: run `20260815-181330-mc-arm64-http-verify-67a3` (Slurm 2954950, gh019) returned
  `RESULT: ok` for all six endpoints, with `env_step_ms=21`, `encode_ms=3`.
- Phase 3 status: complete.

## 2026-08-15 — Phase 4: repository integration

- Added `scripts/setup_minecraft_arm64.sh` (LWJGL 3.3.3 arm64, Temurin JDK 8, conda env,
  engine from HF, launchClient patch, server install), `scripts/start_minecraft_arm64.sh`,
  and `scripts/minecraft_arm64/{launchClient.sh,mc_server.py}`; `mc_server.py` is the
  service recovered from the published image, vendored so the ARM64 path does not depend on
  pulling that image. README gained a "Native ARM64 sandbox" section next to the Docker one.
- Committed as `d65bd2f` on `codex/qwen35-27b-minecraft-0313-0544`.

## 2026-08-15 — real benchmark scene verified; sandbox rebuild complete

- PASS: run `20260815-181739-mc-arm64-scene-verify-203d` (Slurm 2954983) drove
  `benchmark/0313` through the repository's own `MineRLBenchmarkEnv` against the native
  sandbox. Scene built in 10.6 s, `Successfully filled 21 blocks`, and the rendered frame
  is the designed desert temple with the player facing the entrance
  (`/work/nvme/bdrx/dzhang5/mc-arm64/scene_0313.png`).
- State: the Docker/x86 blocker recorded by the previous task is resolved for DeltaAI.
  Phases 1-4 complete for the sandbox rebuild.
- Explicitly NOT established: a full agent episode, milestone scoring, and any comparison
  of scores against the published x86 sandbox. Rendering-path equivalence is argued from
  the image's contents (findings row 10), not measured frame-by-frame.
- Handoff: the remaining step is the Qwen3.5-27B evaluation of 0313/0544 through
  `scripts/run_qwen35_0313_0544.sh` with `MC_SANDBOX_URL` pointing at the native sandbox
  started in the same Slurm job. Awaiting the user's go-ahead — it is evaluation work,
  not sandbox engineering.
