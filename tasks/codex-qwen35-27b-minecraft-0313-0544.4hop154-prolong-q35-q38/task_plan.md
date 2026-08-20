# Task Plan: 4hop154-prolong-q35-q38

## Stable Anchor

- Scientific question: how does the PRO-LONG arm score across the *whole* paper-defined
  4-hop set (all 154 four-milestone scenes), and does the Qwen3.5 > Qwen3.8 ordering seen
  on the strict seven survive at 22x the scene count?
- Target claim or outcome: one MSR-style milestone table per checkpoint over 154 scenes,
  same contract, one seed, so the checkpoint comparison rests on 616 milestones instead of 28.
- Success criterion: 154 `result.json` per checkpoint under one serving layout, 0
  `Agent call failed` / `env.step failed` / `SandboxViolation`, summarised by
  `summarize_4hop.py`; the 3.5-vs-3.8 delta reported with the one-seed caveat.
- Constraints and budget: a227 GPUs 2-7 only, and only after the other session's
  bcp/microvqa servers (`qwen35-t1/t2b/t3`, ports 8010-8012) release them. GPUs 0,1
  (`qwen35-t4`, port 8013) stay theirs. Runner a218 is shared with that session's
  `mllm-search` cells. Est. ~4-5 h wall for q35 + ~6-7 h for q38 at CONC=14.
- Non-goals: no other arm (`default`/`hypothesis`), no extra seeds, no protocol change
  (300 steps stays; the paper's 1800 is a separate L2 decision), no raising CONC above the
  verified 14.

## Current Cycle

- Working hypothesis: the strict-seven result (`prolong` 14/28 on q35 vs 12/28 on q38)
  is scene-driven and will compress toward parity over 154 scenes, ~half of which the
  action space cannot solve at all.
- Main uncertainty: per-cell wall time is estimated from 6 position-tier cells
  (26.3 +/- 7.4 min); the other 147 scenes are inventory / voxel-count tier and unmeasured.
- Next decisive experiment: the q35 154-cell launch itself; its first 14 cells' wall time
  re-estimates the campaign before most of it is spent.
- Expected pass/fail signal: launcher reports 154/154 with results; mean cell wall within
  ~2x of 26 min.
- Fallback: if mean cell wall runs >60 min, stop after q35 and re-scope q38 with the user.

## Success Criteria

- [ ] 154 `result.json` for `q35a-prolong-codex-*` under `Qwen3.5-27B/4-hop/`
- [ ] 154 `result.json` for `q38a-prolong-codex-*` under `Qwen3.8-27B/4-hop/`
- [ ] `summarize_4hop.py --prefix q35a` / `--prefix q38a` render both tables
- [ ] clean-run audit: 0 agent/env failures, `codex_sandboxed: true` in every cell

## Parallel Tracks

| track | owner | mode | worktree / branch | dependency | deliverable | status |
|---|---|---|---|---|---|---|
| primary | primary | integrate | current / codex/qwen35-27b-minecraft-0313-0544 | none | both campaigns + comparison | active |

## Phases

### Phase 1: Prep while GPUs are busy

- [x] Build the 154-scene split (`screen_scenes.py --hops 4 --split-to bench_4hop154/_split`)
- [x] Teach `launch_4hop.sh` a `SPLIT_ROOT` knob (was hardcoded to `bench_4hop7/_split`)
- [x] Verify both checkpoints' k=3 run files carry the campaign contract
- [x] Verify a230 sandbox reachable; Qwen3.8 weights present
- **Status:** complete
- **Evidence:** findings.md 1-4

### Phase 2: Wait for a227 GPUs 2-7, then run q35

- [ ] Monitor until GPUs 2,3,4,5,6,7 are free of the other session's vLLM workers
- [ ] Restart the a230 sandbox only if no session younger than today exists
- [ ] Start `qwen35-s{1,2,3}-k3.sh` (verify remote md5 first), wire-check all three
- [ ] Launch 154 prolong cells, PREFIX=q35a
- **Status:** blocked (GPUs 2-7 held by qwen35-t1/t2b/t3)
- **Evidence:** none

### Phase 3: Swap to Qwen3.8, rerun, compare

- [ ] Stop the three q35 servers, start `qwen38-s{1,2,3}-k3.sh`, wire-check
- [ ] Launch 154 prolong cells, PREFIX=q38a
- [ ] Summarise both, write `experiments/RESULTS_helixon_4hop154.md`
- **Status:** pending
- **Evidence:** none

## Decisions And Blockers

| Item | Decision or blocker | Evidence / owner |
|---|---|---|
| MTP depth | k=3 on both checkpoints (exact in distribution, ~30% faster); both runs same k so the checkpoint comparison is clean | README "the one thing to change"; EVAL_LATENCY §7.1 |
| PREFIX | fresh `q35a` / `q38a`; do *not* resume the recorded 7 `q35` cells (those are k=1, different layout) | costs ~7 extra cells, buys one internally consistent set |
| CONC | 14, not higher. Verified ceiling on the a230 sandbox, and a218 is shared with the other session's mllm-search cells | user instruction 2026-08-20; RESULTS_helixon_4hop.md:51 |
| GPUs 0,1 | not ours. Only 2-7 | user instruction |
| step budget | 300, not the paper's 1800 | keeps the set comparable to the recorded seven; changing it is L2 |
| GUI-impossible scenes | all 154 run, including the 77 the action space cannot solve | user asked for the full paper-defined set |

## Verification Contract

- Command or probe: `python scripts/summarize_4hop.py --prefix q35a --model Qwen3.5-27B --md`
- Expected signal: 154 rows, every cell with a `result.json`, 0 `NO RESULT`
- Experiment/run pointer, if any: `outputs/log-q35a-launcher.txt`, cells `outputs/q35a-prolong-codex-<scene>/`

## Next Action

Wait on the a227 GPU 2-7 monitor; on release, run the Phase 2 checklist in order.
