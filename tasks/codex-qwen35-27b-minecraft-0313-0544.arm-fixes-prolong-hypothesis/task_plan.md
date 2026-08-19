# Task Plan: arm-fixes-prolong-hypothesis

Follow-on to the 4-hop trajectory reading (experiments/BEHAVIOR_helixon_4hop.md). Direction set
by dz on 2026-08-19: `default` is the fixed baseline and is not modified; `prolong` must be
checked against the PRO-LONG paper's idea (ARC-AGI-3 original) and brought closer where it
deviates; `hypothesis` is the method under development and is to be improved.

## Stable Anchor

- Scientific question: on the strict 4-hop set, (a) does a paper-faithful PRO-LONG port change
  the prolong arm's behaviour/outcome, and (b) can the hypothesis DAG be made to do work it
  measurably did not do in the first campaigns?
- Target claims: (a) the prolong arm's mechanism is exercised (log parsed, progress read,
  plans cut on verification) and the paper's own control (`--prolong-log-window -1`) exists;
  (b) hypothesis-v2 removes the belief lock-in / ESC-spam failure and, with grounding, recovers
  hops on the mining and compass scenes.
- Success criteria: (a) audit written with mechanism-by-mechanism verdicts; R2/R3/R5/R6
  landed + selftested; (b) v2.0 discipline landed + selftested; v2.1 designed with the
  decisions named; first behavioural run planned (0603/0763/0306, Qwen3.5, 1 seed).
- Constraints: default untouched (mc_agent/agent.py, mc_agent/context.py, shared hints);
  helixon cluster; every GPU carries an unrelated training job on 2026-08-19 (no server without asking).
- Non-goals: scene repairs (BEHAVIOR §4); shared-hint recalibration; multi-seed claims;
  the No-Log control run itself (needs a server).

## Current Cycle

- Working hypothesis: the prolong arm's lead came from plan granularity, not programmatic
  memory; hypothesis's failure is ungrounded self-confirmation. Both are fixable inside the
  arms without touching default.
- Main uncertainty: the information-parity policy (inventory/pose/per-hop verification for
  prolong R1 / hypothesis v2.1) — dz's call.
- Next decisive experiment: when a server is free, hypothesis v2.0 vs finished hypothesis
  cells on 0603/0763/0306 (Qwen3.5), and prolong (R2/R3) + prolong-nolog on 0306/0763.
- Expected signal: esc_dropped>0 with locks and no ESC spam; c4h-0306-type completion ends
  within a turn; prolong vs nolog difference is the memory effect.
- Fallback: if v2.0 changes nothing behavioural, go straight to v2.1 grounding.

## Phases

### Phase 1: audit + decision-free fixes — status: complete (2026-08-19)
- [x] PRO-LONG fidelity audit (experiments/PROLONG_FIDELITY_AUDIT.md + .zh.md)
- [x] prolong R2 (task-level Verified header + flush), R3 (briefing/plan in log), R5 (No-Log
      control), R6 (5 retries); prolong_mc/selftest.py 167 checks
- [x] hypothesis v2.0 (kinds, env-owned goal confirmation, ESC gate + lock, test budget,
      discipline record); mc_agent/hypothesis_selftest.py 32 checks
- [x] design doc experiments/HYPOTHESIS_V2_DESIGN.md + .zh.md

### Phase 2: decisions + first runs — status: pending (needs dz + a server)
- [ ] dz decides: R1 inventory-in-log; per-hop verification protocol; hypothesis v2.1
      channels; gpt-5.6 prolong control (R7)
- [ ] serve Qwen3.5-27B (scripts/serve_vllm.sh) when GPUs free; run the three-scene checks
- [ ] re-write prompt_layout_check golden for the hypothesis cases

## Decisions And Blockers

| Item | Decision or blocker | Evidence / owner |
|---|---|---|
| default | fixed baseline, not modified | dz 2026-08-19 |
| info parity vs fidelity | open — see audit §5 R1/R2 and design §4 | dz |
| GPUs | all 8 carry a mini_t2i training job (55–60 GB, ~100 % util each) since 2026-08-18 ~05:00; a co-located dev server would compete with it — ask before serving | nvidia-smi 2026-08-19 12:40 |
| branch moved under the session | dz merged claude/eval-latency + claude/fast-agent (a7c02bf) at 13:02; hypothesis edits re-done against the merged file | git reflog |

## Verification Contract

- `.venv/bin/python -m prolong_mc.selftest` (167 PASS) and
  `.venv/bin/python -m mc_agent.hypothesis_selftest` (32 PASS) on the committed tree.
