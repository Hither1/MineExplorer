# Findings: q35-3arms-4hop-helixon

## The arm ordering is not a property of the Qwen3.8 checkpoint (high confidence for the run, low for the gap)

Three arms, seven strict 4-hop scenes, one seed, same contract:

| arm | Qwen3.8-27B | Qwen3.5-27B |
|---|---|---|
| `default x vllm` | 10/28 | 11/28 |
| `hypothesis x vllm` | 10/28 | 10/28 |
| `prolong x codex` | 12/28 | **14/28** |

PRO-LONG leads by 2 milestones on both checkpoints; the hypothesis DAG is worth 0 on both.
12 of 21 cells scored identically across checkpoints, 18 of 21 within one milestone; only
`0182 hypothesis` (2->0), `0182 prolong` (0->2) and `0726 default` (0->3) moved further.
Per-scene totals over the three arms are nearly unchanged, so the scene still dominates.
Evidence: `experiments/RESULTS_helixon_4hop_qwen35.md`, `outputs/q35-*`.

Confidence in the ordering repeating: moderate-high (it repeated, cell by cell, on a
different checkpoint). Confidence that the 2-milestone gap is real: low — one seed, and
five seeds of 0306 alone spread 2/4-4/4 for PRO-LONG.

## PRO-LONG re-plans twice as often on Qwen3.5 (high confidence)

Same 300-step budget: 322 analyzer turns vs 176, i.e. 5.8 steps per program instead of
11.1, and with it 1118 wire requests / 50.9 M input tokens vs 524 / 12.0 M. Still the
cheapest arm (2.7 h cell time vs 6.1 and 8.2), and it is the arm that gained.

## The hypothesis DAG has a completely different shape and the same score (high confidence)

Qwen3.5 ends an episode with 4-37 nodes at median confidence 0.5-1.0; Qwen3.8 with 26-75
nodes at median confidence 0.1-0.3. Both score 10/28. The DAG is genuinely maintained in
both cases (evidence-carrying nodes, live 1-6 step plans) -- it just does not reach the
action.

## Both checkpoints take literally the same serving flags (high confidence)

Same architecture field for field; the generated run files differ in exactly two lines
(`MODEL_PATH`, `--served-model-name`). Chat templates differ only in the thinking-ON
branch. Wire-verified on all three servers: cap 1024 on chat and Responses, no `<think>`,
`qwen3_xml` parses the tool call. Evidence: scratchpad `wirecheck.py` output 08:30.

## Qwen3.5 is ~15% faster per step at equal serving (moderate confidence, n=7 cells)

`hypothesis x vllm` is the only arm whose Qwen3.8 reference ran on this exact layout:
17.5 -> 14.8 s/step. The `default x vllm` cell-time drop (10.9 h -> 6.1 h) is mostly the
layout change (wave-1 uncached two-server -> three prefix-cached), not the checkpoint.
