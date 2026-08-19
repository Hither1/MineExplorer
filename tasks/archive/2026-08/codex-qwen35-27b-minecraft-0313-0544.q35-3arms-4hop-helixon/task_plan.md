# Task Plan: q35-3arms-4hop-helixon

## Stable Anchor

- Scientific question: on the same seven strict 4-hop scenes and the same serving
  contract, does the Qwen3.5-27B checkpoint reproduce the Qwen3.8-27B arm ordering
  (`prolong x codex` > `default x vllm` = `hypothesis x vllm`), or is that ordering
  checkpoint-specific?
- Target claim or outcome: a Qwen3.5-27B row for the three arms dz asked for, directly
  comparable cell-for-cell to the Qwen3.8-27B campaign in
  `experiments/RESULTS_helixon_4hop.md`.
- Success criterion: 21/21 cells finish with `result.json`, no `Agent call failed`, no
  `env.step failed`, no `SandboxViolation`, `codex_sandboxed: true` on every codex cell;
  a scene x arm table next to the Qwen3.8 one.
- Constraints and budget: one seed per cell (fixed up front, as in the Qwen3.8 campaign);
  300 steps; thinking off both channels; temperature 0.7; server cap 1024
  (`max_new_tokens`); a227 GPUs 2-7 only (GPU 0 is another user's, GPU 1 is another
  session's `qwen38-dev`); one shared Minecraft sandbox on a230; ~3 h wall.
- Non-goals: `default x codex` (its Qwen3.8 result is ceiling-bound and it costs 44.6 h
  of cell time); multi-seed; any change to agent code, prompts, or scoring; any change
  to the serving flags beyond the checkpoint itself.

## Current Cycle

- Working hypothesis: Qwen3.5-27B is the same architecture field-for-field and takes the
  same flags, so the campaign runs unchanged and the arm ordering is a property of the
  agent design rather than of the checkpoint.
- Main uncertainty: whether Qwen3.5's chat template plus the `qwen3_xml` tool parser
  behave as Qwen3.8's did. The two templates differ (3.8 adds a `reasoning_effort`
  system instruction when thinking is ON); the thinking-off mechanism and the tool-call
  XML are identical, but that is a read, not a measurement.
- Next decisive experiment: wire-verify the three new servers (cap on both channels,
  thinking off, tool call parsed), then a 2-step `prolong x codex` smoke, then the
  21-cell campaign.
- Expected pass/fail signal: chat stops at 1024 with `length`, Responses stops at 1024
  with `incomplete`, no `<think>` in the reply, a tool call arrives as a parsed
  `tool_calls` entry rather than as `<tool_call>` text; the smoke answers both steps.
- Fallback: if the tool parser does not apply to this checkpoint, only the codex arm is
  affected -- report the two vllm arms and say why prolong is missing.

## Success Criteria

- [x] Three Qwen3.5-27B servers on a227 GPUs 2-7, wire-verified against the same contract.
- [x] 21/21 cells with `result.json` and a clean-run audit.
- [x] Qwen3.5 scene x arm table written next to the Qwen3.8 one.

## Parallel Tracks

| track | owner | mode | worktree / branch | dependency | deliverable | status |
|---|---|---|---|---|---|---|
| primary | primary | integrate | current | none | campaign + write-up | complete |

## Phases

### Phase 1: Serving swap and verification

- [x] Confirm the Qwen3.5-27B checkpoint is complete and takes the same flags.
- [x] Parametrize `MODEL` through `run_cell.sh` / `launch_4hop.sh` / `summarize_4hop.py`.
- [x] Stop `qwen38-s{1,2,3}`, launch `qwen35-s{1,2,3}`, wire-verify all three.
- **Status:** complete
- **Evidence:** `qwen35-serve/run/qwen35-s{1,2,3}.sh` differ from the Qwen3.8 run files
  only in `MODEL_PATH` and `--served-model-name`; wire check ALL PASS 08:30 (cap 1024 on
  both channels, thinking off, `qwen3_xml` parses the tool call).

### Phase 2: Campaign

- [x] 2-step `prolong x codex` smoke on 0306 (and one `default x vllm`).
- [x] 21 cells: `default:vllm prolong:codex hypothesis:vllm` x 7 scenes, CONC=14.
- **Status:** complete
- **Evidence:** 08:36-10:30, 21/21 with `result.json`, `outputs/log-q35-launcher.txt`.

### Phase 3: Interpret and hand off

- [x] Clean-run audit, cost table, Qwen3.5 vs Qwen3.8 comparison.
- [x] Commit/push, update memory, archive.
- **Status:** complete
- **Evidence:** `experiments/RESULTS_helixon_4hop_qwen35.md`; findings.md.

## Decisions And Blockers

| Item | Decision or blocker | Evidence / owner |
|---|---|---|
| seeds | one seed per cell, fixed before launch | dz's standing rule; matches the Qwen3.8 campaign |
| arms | three, not four; `default x codex` excluded | its Qwen3.8 result is a ceiling-policy lower bound at 44.6 h cell-time |
| GPUs | 2-7 only | GPU 0 another user, GPU 1 another session's `qwen38-dev` (:8004) |
| MTP | keep `num_speculative_tokens: 1` | the k=3 run files are unlaunched pending dz; changing it here would confound the checkpoint comparison |

## Verification Contract

- Command or probe: `.venv/bin/python scripts/summarize_4hop.py --prefix q35 --model Qwen3.5-27B`
- Expected signal: 21 rows, every `end` in {`max_steps`, `all_milestones`}, no cell missing.
- Experiment/run pointer, if any: `outputs/q35-*`, launcher log `outputs/log-q35-launcher.txt`.

## Next Action

none - ready to archive
