# Task Plan: rebuild-minecraft-sandbox-arm64

## Stable Anchor

- Scientific question: can the MineExplorer Minecraft sandbox service run natively on
  DeltaAI (aarch64 / GH200), so that benchmark evaluation no longer requires an external
  x86_64 Docker host?
- Target claim or outcome: a native aarch64 sandbox exposing the same HTTP contract
  (`/monitor/alive`, `/create_env`, `/reset_env`, `/step`, `/close_env`) that
  `eval_benchmark.py` / `generate_benchmark.py` reach through `MC_SANDBOX_URL`.
- Success criterion: from the evaluation client, `create_env` + `reset_env` + N `step`
  calls return decodable non-degenerate POV frames, and one existing benchmark scene
  runs end to end.
- Constraints and budget: no root, no subuid/subgid, no Docker daemon, no qemu binfmt.
  Login node for build/smoke; Slurm `ghx4` for real runs. Reuse the published engine
  artifact; do not rebuild Minecraft from source unless forced.
- Non-goals: reproducing the published image bit-for-bit; GPU-accelerated rendering as a
  requirement (nice-to-have); modifying benchmark task definitions or the evaluator.

## Current Cycle

- Working hypothesis: the published engine is architecture-portable except for its
  LWJGL 3.2.2 x86-64 natives; substituting LWJGL 3.3.3 `linux-arm64` on the classpath and
  disabling jemalloc is sufficient to run the same `mcprec-6.13.jar` on GH200.
- Main uncertainty: the Python side — whether MineStudio 1.1.5 and its pinned deps
  (`opencv-python==4.8.0.74`, `av==13.1.0`, `cuda-python`, `pyrender`) install on aarch64,
  and whether `MinecraftSim` drives the patched engine without further x86 assumptions.
- Next decisive experiment: install MineStudio into the aarch64 env, point it at the
  patched engine, and run one `MinecraftSim` reset + step producing a real POV frame.
- Expected pass/fail signal: a saved PNG showing a rendered Minecraft scene (not black /
  not uniform), plus a non-error `step` return.
- Fallback: install MineStudio with `--no-deps` and add only the modules the simulator
  import path actually needs; if MineStudio itself proves x86-bound, drive the
  `MalmoEnvServer` socket directly and reimplement the thin FastAPI layer.

## Success Criteria

- [x] LWJGL/GLFW/OpenGL context creation works on aarch64 under Xvfb.
- [x] `mcprec-6.13.jar` (Minecraft 1.16.5) boots on aarch64 and opens `MalmoEnvServer`.
- [ ] MineStudio `MinecraftSim` reset/step returns a valid POV frame on aarch64.
- [ ] `mc_server.py` serves the five HTTP endpoints on a DeltaAI node.
- [ ] One existing benchmark scene runs end to end against `MC_SANDBOX_URL`.

## Parallel Tracks

| track | owner | mode | worktree / branch | dependency | deliverable | status |
|---|---|---|---|---|---|---|
| primary | primary | integrate | current branch | none | native aarch64 sandbox + startup script | active |

## Phases

### Phase 1: Establish why podman/Docker cannot work here, and inventory the engine

- [x] Prove the blocker is architecture + rootless config, not the container engine.
- [x] Extract the published image without executing it; recover the server source and engine.
- **Status:** complete
- **Evidence:** `findings.md` rows 1-5.

### Phase 2: Make the Java engine run natively on aarch64

- [x] Verify GLFW + OpenGL under Xvfb with LWJGL 3.3.3 arm64 natives.
- [x] Boot the real engine jar with the LWJGL substitution.
- **Status:** complete
- **Evidence:** `findings.md` rows 6-8; `/work/nvme/bdrx/dzhang5/mc-arm64/run/mc2.log`.

### Phase 3: Port the Python side and serve the HTTP contract

- [ ] Install MineStudio on aarch64; record which pinned deps need relaxing.
- [ ] Patch `launchClient.sh` (LWJGL classpath, system allocator, own Xvfb, no vglrun).
- [ ] `MinecraftSim` reset/step smoke with a saved frame.
- [ ] Run `mc_server.py`; verify all five endpoints.
- **Status:** in_progress
- **Evidence:** none yet

### Phase 4: Integrate and hand off

- [ ] Add a repo startup script for the native aarch64 sandbox (sibling of the Docker helper).
- [ ] Run one benchmark scene end to end; commit the reproducible configuration.
- **Status:** pending
- **Evidence:** none

## Decisions And Blockers

| Item | Decision or blocker | Evidence / owner |
|---|---|---|
| container route | abandoned_with_evidence: podman/apptainer cannot help; the blocker is amd64-only image + no binfmt + no subuid | findings.md rows 1-3 |
| engine source rebuild | not needed; binary LWJGL substitution is sufficient | findings.md rows 7-8 |
| jemalloc | disabled via `-Dorg.lwjgl.system.allocator=system`; GH200 uses 64 KiB pages | findings.md row 8 |
| eval env | do not mutate the verified `mineexplorer-qwen35-tf`; sandbox gets its own prefix | prior task progress.md |

## Verification Contract

- Command or probe: `MinecraftSim(...).reset()` then one `.step()`, saving the returned
  POV frame; afterwards `curl $MC_SANDBOX_URL/monitor/alive` and a `create_env`/`reset_env`
  round trip.
- Expected signal: non-degenerate rendered frame (pixel variance well above zero) and
  `{"status":0}` responses from all endpoints.
- Experiment/run pointer, if any: `none` (login-node smoke first; Slurm run after)

## Next Action

Read run `20260815-181330-mc-arm64-http-verify-67a3`; on pass, commit the repository
integration and run one benchmark scene end to end.
