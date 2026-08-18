# Task Plan: prolong-vs-default-4hop-helixon

Authorized by dz 2026-08-18 ~13:30 ("先把 1、2 修了，然后重启 server 加 1024 上限；然后跑7个就可以；
我睡觉了，你持续推进"). Runs on the helixon cluster: model server a227 (192.168.2.20:8001),
Minecraft podman sandbox a230 (192.168.2.22:8000), runner on a219.

## Stable Anchor

- Scientific question: does PRO-LONG's programmatic memory (`--agent-mode prolong`, codex
  channel) change milestone completion on real depth-4 MineExplorer scenes relative to the
  default 20-frame-buffer agent (direct vLLM channel), with Qwen3.8-27B, thinking off?
- Target claim or outcome: per-scene milestone counts and steps for both arms on the 7
  strict 4-hop scenes, one seed each, under one recorded serving contract.
- Success criterion: 14 result.json files (7 scenes × {prolong×codex, default×vllm}) with
  `codex_sandboxed: true` for the codex arm, taken against the 1024-cap server, plus a
  comparison table.
- Constraints and budget: thinking OFF both channels, temperature 0.7 (top_p 0.8, top_k 20
  server default), output cap 1024 on both channels (server `max_new_tokens`), 300 steps,
  hint protocol on (`--milestone-hint`, run_cell.sh default), one seed per cell — fixed up
  front (see memory `fix-seed-count-up-front`). Shared a227 server; ≤5 concurrent cells.
- Non-goals: default×codex (not viable with thinking off — measured 2026-08-18); hypothesis
  arm; more seeds; scenes outside the strict-7 set; any change to the agents' prompts.

## Current Cycle

- Working hypothesis: with the two harness defects fixed (dead vision audit; codex wrapper
  contamination + no sandbox) and the cap pinned server-side, both arms run cleanly on the
  7 scenes and produce comparable scores.
- Main uncertainty: the 5 inventory/voxel-tier scenes have never been scored on this
  sandbox; the first step of each will show whether `inventory`/`voxels` come back.
- Next decisive experiment or implementation: fixes → server relaunch → one short smoke
  per arm → launch the 14 cells.
- Expected pass/fail signal: smoke: prolong turn attaches 1 frame, sandboxed, no
  "could not read the local image"; vllm call capped at 1024. Campaign: 14 result.json.
- Fallback: if a scene's judges never fire (voxel/inventory unreported), record it as
  unscorable and keep the position-tier scenes.

## Scenes (strict 4-hop set)

0306 0726 0182 0311 0482 0603 0763 — depth 4, nothing satisfied at spawn, no GUI-only
task, not satisfiable out of order (0694 and 0435 excluded for that).

## Success Criteria

- [ ] `find_rollout` implemented; vision audit reads real numbers.
- [ ] `run_cell.sh` runs codex through `codex_sandbox.sh` (per-episode home, no personal
      AGENTS.md/skills, read scope bounded); `-` sentinel ordering fixed; timeouts kill the
      process group.
- [ ] a227 server relaunched with `max_new_tokens:1024`; verified on both channels.
- [ ] 14 cells finished; `scripts/compare_runs.py`-style table written.

## Parallel Tracks

| track | owner | mode | worktree / branch | dependency | deliverable | status |
|---|---|---|---|---|---|---|
| primary | primary | integrate | current branch | none | fixes, server, launches, synthesis | active |

## Phases

### Phase 1: Harness fixes (items 1 and 2)

- [ ] `prolong_mc/codex_backend.py`: implement `find_rollout`; kill process group on timeout.
- [ ] `mc_agent/llm_provider.py`: `-i` before `-m` (stdin sentinel no longer eaten); process group on timeout.
- [ ] `scripts/run_cell.sh`: `CODEX_BIN=prolong_mc/codex_sandbox.sh`, allowlist the model server, `CODEX_SANDBOX_NO_AUTH=1`; keep per-cell workspace.
- [ ] `scripts/screen_scenes.py`: wire `satisfiable_out_of_order` into the filter.
- [ ] selftests pass; commit.
- **Status:** in_progress
- **Evidence:** none yet

### Phase 2: Serving + smoke

- [ ] relaunch a227 with `--override-generation-config` incl. `max_new_tokens:1024`.
- [ ] verify: chat and Responses both cap at 1024; thinking off both.
- [ ] one 3-step prolong smoke and one 3-step vllm smoke through run_cell.sh.
- **Status:** pending
- **Evidence:** none

### Phase 3: Campaign

- [ ] bench dir with the 7 scenes; launch 14 cells (≤5 concurrent) under nohup/tmux with logs.
- [ ] monitor; rerun crashed cells with --resume.
- [ ] export table + short interpretation; commit.
- **Status:** pending
- **Evidence:** none

## Decisions And Blockers

| Item | Decision or blocker | Evidence / owner |
|---|---|---|
| default×codex | dropped: loops on view_image with thinking off (probe 2026-08-18 13:03) | dz, this session |
| control arm | default×vllm (channel confound accepted, see memory) | dz |
| output cap | server-side `max_new_tokens:1024`, both channels | dz |

## Verification Contract

- Command or probe: `python -m prolong_mc.selftest`; `python -m prolong_mc.sandbox_selftest`;
  wire probe of `/v1/chat/completions` and `/v1/responses` for the 1024 cap; smoke cells.
- Expected signal: selftests PASS; `usage.completion_tokens == 1024, finish_reason length`
  on a long-answer prompt; smoke result.json with `codex_sandboxed: true`.
- Experiment/run pointer, if any: outputs/c4h-* (this campaign's tag prefix)

## Next Action

Implement Phase 1 fixes.
