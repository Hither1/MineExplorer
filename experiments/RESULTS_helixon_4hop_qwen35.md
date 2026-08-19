# The same seven 4-hop scenes on Qwen3.5-27B (2026-08-19)

Three arms — `default × vllm`, `hypothesis × vllm`, `prolong × codex` — on the seven
scenes of [RESULTS_helixon_4hop.md](RESULTS_helixon_4hop.md), with the same agents, the
same prompts, the same serving contract and one seed per cell. The only thing that
changed is the checkpoint: `Qwen/Qwen3.5-27B` @ `fc05daec18b0` instead of
`Qwen/Qwen3.8-27B`. `default × codex` was not repeated (on Qwen3.8 its score is a
ceiling-policy lower bound that cost 44.6 h of cell time).

Campaign 08:36–10:30, 1 h 54 min wall for 21 cells. Cells under
`outputs/q35-<agent>-<channel>-<scene>/Qwen3.5-27B/`, logs `outputs/log-q35-*.txt`, table
by `python scripts/summarize_4hop.py --prefix q35 --model Qwen3.5-27B`.

## Why the two checkpoints take identical flags

Qwen3.5-27B and Qwen3.8-27B are the same architecture field for field —
`Qwen3_5ForConditionalGeneration` / `model_type: qwen3_5`, 64 layers (48 gated delta-net
+ 16 full attention), `head_dim` 256, vocab 248320, 262144 positions, a trained
`mtp_num_hidden_layers: 1` head, SigLIP-style ViT. The generated run files
`qwen35-serve/run/qwen35-s{1,2,3}.sh` differ from the Qwen3.8 ones in exactly two lines:
`MODEL_PATH` and `--served-model-name`.

Their chat templates do differ, but only in the thinking-**on** branch: 3.8 injects a
`reasoning_effort` system instruction that 3.5 has no concept of. The thinking-**off**
mechanism is character-identical in both (`enable_thinking is false` → the generation
prompt is prefilled with `<think>\n\n</think>`), and so is the tool-call XML
(`<tool_call><function=…><parameter=…>`), which is why the `qwen3_xml` parser applies
unchanged.

Verified on the wire rather than read off the templates — all three servers, 08:30:

| check | result |
|---|---|
| served id / context | `Qwen3.5-27B`, `max_model_len` 131072 |
| chat cap | `finish_reason: length` at exactly 1024 completion tokens |
| Responses cap (codex's wire) | `status: incomplete`, `reason: max_output_tokens`, 1024 output tokens |
| thinking | no `<think>` and no `reasoning_content` in the reply |
| tool parser | one parsed `tool_calls` entry, `{"city": "Shanghai"}`, no `<tool_call>` text in content |

Serving: three identical TP=2 servers on a227 — `:8001` GPUs 2,3, `:8002` GPUs 4,5,
`:8003` GPUs 6,7 — `--enable-prefix-caching`, MTP `num_speculative_tokens: 1`,
`--limit-mm-per-prompt image:128`, `--max-model-len 131072`,
`--override-generation-config '{"temperature":0.7,"top_p":0.8,"top_k":20,"max_new_tokens":1024}'`,
`--default-chat-template-kwargs '{"enable_thinking":false}'`, `--enable-auto-tool-choice
--tool-call-parser qwen3_xml`. 8.5 min from launch to ready. 21 cells at concurrency 14
dealt round-robin barely loaded them: over the campaign's 1888 engine snapshots, 7 showed
any queue at all (max 4 waiting), running requests peaked at 6 per server and KV usage at
20 %.

## Results

| scene | default × vllm | hypothesis × vllm | prolong × codex |
|---|---|---|---|
| 0182 | 2/4 | 0/4 | 2/4 |
| 0306 | 3/4 | **4/4** (195, ESC) | **4/4** (56, ESC) |
| 0311 | 1/4 | 1/4 | 0/4 |
| 0482 | 0/4 | 1/4 | 1/4 |
| 0603 | 0/4 | 1/4 | 2/4 |
| 0726 | 3/4 | 1/4 | 3/4 |
| 0763 | 2/4 | 2/4 | 2/4 |
| **total** | **11/28** | **10/28** | **14/28** |

Next to Qwen3.8-27B on the same cells:

| arm | Qwen3.8-27B | Qwen3.5-27B |
|---|---|---|
| `default × vllm` | 10/28 | 11/28 |
| `hypothesis × vllm` | 10/28 | 10/28 |
| `prolong × codex` | 12/28 | **14/28** |
| all three | 32/84 | 35/84 |

**The ordering survives the checkpoint change, and so does its size.** PRO-LONG is ahead
on both checkpoints by 2 milestones; the hypothesis DAG is worth 0 on both. Cell by cell,
12 of 21 cells scored exactly the same on the two checkpoints and 18 of 21 are within one
milestone. Only three cells moved by more than one: `0182 hypothesis` 2/4 → 0/4,
`0182 prolong` 0/4 → 2/4, `0726 default` 0/4 → 3/4. Summed over the three arms, the
per-scene totals are nearly unchanged (0182 4→4, 0306 12→11, 0311 1→2, 0482 3→2,
0603 2→3, 0726 4→7, 0763 6→6): **the scene is still what decides the score, not the
checkpoint and not the agent.**

Both checkpoints solve 0306 fully with PRO-LONG and stop early (Qwen3.5 at step 56,
Qwen3.8 at frame 52), and both fail 0311 completely on the codex arm. 0311's ceiling is
2/4 for every arm — two `count_in_box_at_most` milestones are already satisfied at spawn.

## What actually changed between the checkpoints

**PRO-LONG re-plans about twice as often.** Same 300-step budget, but 322 analyzer turns
on Qwen3.5 against 176 on Qwen3.8 — 5.8 steps per turn instead of 11.1. Each turn is a
codex agentic loop, so the wire cost rose with it: 1118 requests and 50.9 M input tokens
against 524 requests and 12.0 M. It is still by far the cheapest arm, and it is the arm
that gained the 2 milestones, but shorter programs are the mechanism, not more thinking
(thinking is off on both).

**The hypothesis DAG collapses.** Qwen3.5 ends an episode with 4–37 nodes at median
confidence 0.5–1.0; Qwen3.8 ends with 26–75 nodes at median confidence 0.1–0.3. Qwen3.5
states far fewer hypotheses and believes them; Qwen3.8 states many and hedges. Neither
behaviour shows up in the score — both are 10/28 — which is the same negative result the
Qwen3.8 campaign reported, now with a second, very different DAG shape behind it.

**Qwen3.5 is somewhat faster per step at equal serving.** The only clean latency pair is
`hypothesis × vllm`, which ran on this exact three-server layout on both checkpoints:
17.5 s/step → 14.8 s/step, 9.3 h → 8.2 h of cell time. Do **not** read the `default ×
vllm` row that way (10.9 h → 6.1 h): the Qwen3.8 number was taken in wave 1 on the older
uncached two-server layout.

| arm | cell-time | steps | s/step | model calls | wire requests | input tokens |
|---|---|---|---|---|---|---|
| `default × vllm` | 6.1 h | 2100 | 10.4 | 2100 | — | — |
| `hypothesis × vllm` | 8.2 h | 1995 | 14.8 | 2003 | — | — |
| `prolong × codex` | 2.7 h | 1856 | 5.2 | 322 turns | 1118 | 50.9 M |

("wire requests" and "input tokens" are codex's own accounting from the rollouts; the
direct-vLLM arms send exactly one request per step.)

## Clean-run audit

All 21 cells: **0** `Agent call failed`, **0** `env.step failed`, **0** `SandboxViolation`,
**0** tracebacks. All 7 codex cells recorded `codex_sandboxed: true`. Across 770
shell/exec calls in the PRO-LONG rollouts, **0** named a repository path outside the
episode workspace and **0** rollout lines contained the benchmark's milestone schema — the
codex arm could not read the answers, same as on Qwen3.8.

## Caveats

- **One seed per cell.** Five seeds of 0306 alone spread 2/4–4/4 for PRO-LONG and 3/4–4/4
  for the default arm. A 2-milestone gap over 28 is inside that. What this campaign
  establishes is that the *pattern* repeats on a second checkpoint, not that the gap is
  significant.
- **Two of the three Qwen3.8 reference arms were taken on a different serving layout.**
  `default × vllm` and `prolong × codex` come from wave 1 (two differently sized servers,
  no prefix caching); only `hypothesis × vllm` shares this campaign's exact layout.
  Prefix caching moves greedy output at the paraphrase level, and at temperature 0.7 with
  one seed that is well inside sampling noise — but it is not nothing, and it is why the
  latency comparison above is restricted to the one arm that matches.
- **The Qwen3.5 arms are all on the same layout as each other**, dealt round-robin, so no
  arm is confounded with a server within this campaign.
- The `agent_esc` terminations (0306 on two arms) are the hint protocol working: the agent
  declared completion and the scorer agreed. Premature ESC is refused.

## Files

- results: `outputs/q35-<agent>-<channel>-<scene>/Qwen3.5-27B/4-hop/<scene>/result.json`,
  logs `outputs/log-q35-*.txt`, launcher `outputs/log-q35-launcher.txt`
- serving: `qwen35-serve/run/qwen35-s{1,2,3}.sh`, tmux `qwen35-s1/s2/s3` on a227,
  logs `qwen35-serve/logs/qwen35-s{1,2,3}.log`
- harness: d9d4b93 (`MODEL` as one variable through runner, launcher and summarizer)
- Qwen3.8 campaign this is compared against: [RESULTS_helixon_4hop.md](RESULTS_helixon_4hop.md)
