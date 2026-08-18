# Task Plan: arms34-4hop-helixon

Authorized by dz 2026-08-18 23:2x ("我觉得还需要跑一下 default x codex 和 hypothesis x vllm，用同样的
设置跑这七个 scene；另外我们四卡 launch vllm，要保证服务于我们快速的 evaluation，提高效率和速度").
Continues the archived task prolong-vs-default-4hop-helixon (2026-08-18 campaign, 10/28 vs 12/28).

## Stable Anchor

- Scientific question: on the same 7 strict 4-hop scenes, what do the two remaining cells of the
  {default, hypothesis, prolong} x {vllm, codex} design score -- default x codex (the codex-scaffold
  control for PRO-LONG) and hypothesis x vllm (the hypothesis-DAG agent on the direct channel)?
- Target claim or outcome: per-scene milestone counts/steps for both arms, one seed each, under a
  recorded serving contract, in one 4-arm table next to the earlier two arms.
- Success criterion: 14 more result.json (7 scenes x {default x codex, hypothesis x vllm}),
  `codex_sandboxed: true` for the codex arm, and the 4-arm table in
  experiments/RESULTS_helixon_4hop.md; serving reconfigured for throughput.
- Constraints and budget: same settings as the first campaign -- thinking OFF both channels,
  temperature 0.7 (top_p 0.8 / top_k 20 server default), server-side output cap 1024, 300 steps,
  hint protocol on, one seed per cell (fixed up front). Serving: a227 GPUs 2-7 (GPU 0 is another
  user's, GPU 1 left idle), three TP=2 servers with prefix caching, same generation config.
- Non-goals: re-running the first two arms; more seeds; hypothesis x codex; changing any agent
  prompt; a hidden loop-breaker for default x codex (the arm runs as implemented; only the
  per-call ceiling is chosen for it, and it is written down).

## Current Cycle

- Working hypothesis: default x codex loops `view_image` on the 20 attached frames at the 20-frame
  steady state with thinking off (measured 13:03 and 13:13; the calls succeeded, the model just
  kept viewing), so its steps end at the per-call ceiling; hypothesis x vllm runs like default x
  vllm (~20 s/step, s0694 05:38-06:20 ran 127 steps cleanly).
- Main uncertainty: the loop's base rate per step (every step >= N frames? stochastic?) and how
  fast one loop iteration is with prefix caching -- both decide the ceiling and the campaign wall.
- Next decisive experiment or implementation: relaunch serving (3 x TP=2, prefix cache) ->
  20-frame probe x3 + 8/12-frame probes -> pick CODEX_TIMEOUT for the arm -> smoke both arms ->
  launch 14 cells.
- Expected pass/fail signal: probe: fraction of 20-frame calls that answer within 120 s; smoke:
  3-step cells finish with result.json (codex_sandboxed true). Campaign: 14 result.json.
- Fallback: if default x codex loops at every step, the arm is scored as run (no-op steps) and the
  report says the score is the ceiling policy, not the agent.

## Scenes (strict 4-hop set)

0306 0726 0182 0311 0482 0603 0763 (bench_4hop7/_split/<scene>) -- unchanged.

## Success Criteria

- [x] three TP=2 servers up on a227 (:8001 GPUs 2,3; :8002 GPUs 4,5; :8003 GPUs 6,7), prefix
      caching on, cap 1024 / thinking off verified on both channels of each.
- [x] default x codex path smoke-tested through run_cell.sh + codex_sandbox.sh (per-cell episode
      home, rollouts kept); loop probe done and the ceiling recorded (120 s).
- [ ] 14 cells finished; 4-arm table in experiments/RESULTS_helixon_4hop.md; committed.

## Parallel Tracks

| track | owner | mode | worktree / branch | dependency | deliverable | status |
|---|---|---|---|---|---|---|
| primary | primary | integrate | current branch | none | serving, harness, launches, synthesis | active |

## Phases

### Phase 1: Serving for throughput

- [x] stop A (:8001 TP=4) and B (:8002 TP=2); launch S1/S2/S3 TP=2 with --prefix-cache, same
      generation config; verify remote run-file md5 before tmux (NFS lag).
- [x] wire-verify each server: chat cap 1024, Responses cap 1024, thinking off both, prefix cache on.
- **Status:** complete
- **Evidence:** qwen35-serve/run/qwen38-s{1,2,3}.sh, logs/qwen38-s*.log; progress.md 23:54

### Phase 2: Harness + probes

- [x] run_cell.sh: per-cell CODEX_EPISODE_HOME for non-prolong codex cells (rollouts kept, no /tmp
      litter); CODEX_TIMEOUT settable per arm from the launcher.
- [x] launch_4hop.sh: ARMS list + per-cell server round-robin; summarize_4hop.py counts
      CodexProvider calls/timeouts.
- [x] loop probe (4/8/12/16/20 frames) on the new servers; smokes of both arms; agents no longer
      retry a ceiling hit.
- **Status:** complete
- **Evidence:** findings.md 23:57/00:17; outputs/smoke-c4h-*

### Phase 3: Campaign

- [x] launch 14 cells (7 hypothesis x vllm at 00:03, 7 default x codex at 00:37) across the three servers.
- [ ] monitor to completion; summarize; write the 4-arm table + interpretation; commit + push.
- **Status:** active
- **Evidence:** outputs/log-c4h-launcher-hyp.txt, outputs/log-c4h-launcher-dc.txt

## Decisions And Blockers

| Item | Decision or blocker | Evidence / owner |
|---|---|---|
| default x codex | run as implemented (dz 23:2x), despite the measured view_image loop | probe 13:03/13:13 |
| serving | 3 x TP=2 + prefix cache (numerics not bit-comparable with the first campaign; sampling noise dominates) | qwen35-serve README |
| CODEX_TIMEOUT for default x codex | 120 s, one ceiling then no-op (probe: answers at 67/193 s, 5/7 stalls at 240 s); ~10 h campaign if every step stalls | findings.md 23:57 |

## Verification Contract

- Command or probe: wire probes of /v1/chat/completions and /v1/responses on each server; 3-step
  smokes via scripts/run_cell.sh; `python scripts/summarize_4hop.py`.
- Expected signal: `completion_tokens == 1024, finish_reason length` on a long prompt; smoke
  result.json with `codex_sandboxed: true`; 14 result.json.
- Experiment/run pointer, if any: outputs/c4h-default-codex-*, outputs/c4h-hypothesis-vllm-*

## Next Action

monitor the 14 cells; summarize + write the 4-arm table when done (Phase 3)
