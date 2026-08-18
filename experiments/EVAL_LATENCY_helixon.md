# Where a MineExplorer cell's time goes, and what to do about it (helixon, 2026-08-19)

Measured on the c4h campaign (`outputs/log-c4h-*.txt`, servers `qwen38-s1/2/3` on a227) and
on a dev server (a227 GPU 1, TP=1, `:8004`, prefix cache, campaign wire contract: thinking
off, cap 1024, temp 0.7). Branch `claude/eval-latency`. Nothing here changes a running arm:
`--prompt-layout legacy` (the default) is today's prompt byte for byte.

## 1. The breakdown

A cell is 300 sequential steps; seven cells per arm already run in parallel, so an arm's wall
time is one cell's. Per step:

| arm | step (median) | of which LLM call | of which env.step | other |
|---|---|---|---|---|
| default × vllm | 7–18 s | 6–17 s | 0.1–0.3 s | JSON retries 0–4 %, mp4 checkpoint ~1 s / 10 steps |
| hypothesis × vllm | 14–17 s | 13.5–16 s | 0.1–0.3 s | same |
| default × codex (ceiling 120 s) | 60–98 s | answered call med 29–45 s; **28–37 % of calls hit the ceiling and take 47–63 % of the wall** | 0.1–0.3 s | 1.04–1.17 calls/step (JSON retry) |

Why one direct-channel call takes 7–18 s (real request rebuilt from a recorded cell and sent
to the server):

- **Prompt: 5.3k tokens (default) / 8.3k (hypothesis), rebuilt from scratch every step.**
  1.7k / 4.8k instruction+memory+hints, 20 × 107 history-text tokens (previous thought and
  action per frame), 20 × 68 image tokens (320×180 PNG → 352×192 after the processor's
  65 536-pixel minimum).
- **The prefix cache never sees it.** Memory and hints sit between the goal and the
  instructions and the 20-frame window slides, so consecutive steps share ~84–143 tokens —
  under one 800-token cache block (the block size vLLM uses for this hybrid GDN model with
  prefix caching on). Per-request hit rate ≈ 0 %; the servers' cumulative rate decays toward
  30–45 % while only vllm cells run.
- **Decode: 200–250 output tokens (default) / 380–460 (hypothesis)** at ~64 tok/s
  single-stream (bf16 27B, TP=2 PCIe A100, MTP k=1: 1.94 tokens per iteration) — but per
  request only ~30 tok/s with 2 running requests and ~22 tok/s with 4, because neighbours'
  5–15k-token prefill chunks (`--max-num-batched-tokens 8192`) stall the decode iterations.
  Aggregate generation barely scales: 1 req 57–72, 3 reqs 82–90, 5 reqs 100 tok/s. KV cache
  never exceeded 7 %.
- The codex arm: 1.6 s codex/bwrap start-up + 3–5 model round trips per answered call (first
  request ~15k input tokens, ~9k uncached; later ones cached) spent on `ls`, PIL pixel
  analysis, `echo done`; the 120 s ceiling on a third of the steps is the arm's price.

## 2. What was measured on the dev server (TP=1, GPU 1)

`scripts/bench_agent_latency.py` replays a cell — recorded frames + thoughts, the model's own
memory fed back — through the real agent code against the server, 12 steps per cell (first
excluded), and reads the server's counters over the run.

Step = wall time of `agent.get_action` (median over 3 × 11 or 1 × 11 steps); TTFT / decode /
prefix-hit / MTP from the server counters over the run. "3 cells" = three replayed cells on the
one server at once, which is what the campaign does (2–3 cells per production server).

| server (TP=1, GPU 1) | agent | layout | cells | step | TTFT | decode per req | prefix hit | tokens/iter |
|---|---|---|---|---|---|---|---|---|
| MTP k=1 (today's depth) | default | legacy | 1 | 6.7 s | 1.86 s | 43.7 tok/s | 0 % | 1.91 |
| MTP k=1 | default | legacy | 3 | 8.7 s | 2.70 s | 30.7 tok/s | 2 % | 1.92 |
| MTP k=1 | default | append-only | 3 | 6.3 s | 1.10 s | 36.2 tok/s | 62 % | 1.93 |
| MTP k=1 | hypothesis | legacy | 1 | 12.7 s | 2.30 s | 41.4 tok/s | 0 % | 1.92 |
| **MTP k=3** | default | legacy | 1 | **4.3 s** | 1.58 s | 70.8 tok/s | 0 % | 3.48 |
| MTP k=3 | default | legacy | 3 | 7.3 s | 2.62 s | 36.8 tok/s | 2 % | 3.37 |
| MTP k=3 | default | static-first | 3 | 6.8 s | 2.08 s | 44.5 tok/s | 16 % | 3.47 |
| MTP k=3 | default | **append-only** | 3 | **4.4 s** | 1.16 s | 55.2 tok/s | 62 % | 3.53 |
| MTP k=3 | hypothesis | legacy | 1 | 8.0 s | 2.30 s | 66.4 tok/s | 0 % | 3.43 |
| MTP k=3 | hypothesis | legacy | 3 | 13.7 s | 2.83 s | 42.0 tok/s | 2 % | 3.45 |
| MTP k=3 | hypothesis | **append-only** | 3 | **7.0 s** | 1.59 s | 56.6 tok/s | 70 % | 3.47 |
| MTP k=3, `--max-num-batched-tokens 2048` | default | legacy | 1 | 4.6 s | 2.02 s | 70.2 tok/s | 0 % | 3.44 |
| MTP k=3, chunk 2048 | default | legacy | 3 | 7.3 s | 3.04 s | 39.0 tok/s | 1 % | 3.46 |
| MTP k=3, chunk 2048 | hypothesis | legacy | 3 | 13.5 s | 3.34 s | 41.4 tok/s | 0 % | 3.44 |

For scale: the campaign's production servers (TP=2, k=1, 2–3 cells each) ran the default agent
at 6–18 s/step and the hypothesis agent at 14–17 s/step. Prompt/output sizes in the replay match
the campaign's (default 5.2k → 180–200 tokens, hypothesis 8.3k → 320–450); the append-only
window makes the prompt 5.8k / 8.9k, of which 62–70 % is served from cache.

The append-only smoke through the real runner (`run_cell.sh`, scene 0306, 12 steps, dev server):
result.json records `prompt_layout: append-only`, milestone 1/4 at frame 10, 4.0 s/step
(`outputs/smoke-layout-append-only`).


## 3. Levers, ranked

1. **Serving, no protocol change — MTP depth 3.** The checkpoint's MTP head is accepted
   2.4–2.5 times per draft on this JSON output at temperature 0.7 (3.4–3.5 tokens per
   iteration vs 1.94 with depth 1), so decode is ~1.7× faster per iteration for every arm,
   codex round trips included. Speculative decoding is exact in distribution; a relaunch flag
   (`serve.sh --spec-tokens 3`; run files `qwen35-serve/run/qwen38-s{1,2,3}-k3.sh` are written,
   not launched). Measured against k=1 on the same GPU: single-stream step 6.7 → 4.3 s (default), 12.7 → 8.0 s (hypothesis); with three legacy cells sharing the server 8.7 → 7.3 s — the prefill interference caps what faster decode can buy there.
2. **Serving, no protocol change — one server per cell instead of 2–3 cells per server.**
   TP=1 fits (51.9 GiB weights, 231k-token KV at util 0.90); a 7-cell arm on seven TP=1
   servers (GPUs 1–7) would run each cell single-stream: default legacy 4.3 s/step,
   hypothesis 8.0 s/step on TP=1 with k=3, against 7.3 / 13.7 s when three share a server.
   Whether TP=2 × 3 with k=3 beats that for a 7-cell arm is unmeasured (production was busy);
   measure at the relaunch (`scripts/bench_agent_latency.py`, 12 steps, 2 min). Two arms at
   once (14 cells) puts 2 per TP=1 server, which is still less interference than 4–5 per
   TP=2 server.
3. **`--prompt-layout append-only` (new arm; dz's call).** Three cells per server run at
   the single-cell speed: default 7.3 → 4.4 s, hypothesis 13.7 → 7.0 s (prefix hit 62–70 %,
   TTFT 2.6–2.8 → 1.2–1.6 s, decode 37–42 → 55–57 tok/s per request). What changes for the
   model: state (memory, hints, hypothesis graph, plan) after the frames instead of before
   the instructions; window 20–29 frames instead of exactly 20; captions `Frame [Step k]`.
   All arms of a comparison must use the same layout, so this is for a *next* campaign, not
   for adding cells to the current one.
4. **`--prompt-layout static-first`** alone: 7.3 → 6.8 s default (one 800-token block cached),
   more for hypothesis (5 blocks) — not worth a protocol change by itself.
5. **Output length (protocol; not implemented).** With prefill cached, decode is the step:
   186–199 tokens ≈ 2.7 s of a 4.3 s default step, 320–450 tokens ≈ 6 s of an 8 s hypothesis
   step. Every step rewrites the full ≤200-word memory (~300 tokens); the hypothesis JSON adds
   hypotheses + plan. Halving the output halves the step. Prompt change → dz.
6. **`--max-num-batched-tokens 2048`** does not help: with three legacy cells the step is the
   same (7.3 s / 13.5 s), TTFT is worse (3.0–3.3 s vs 2.6–2.8 s) and per-request decode only
   2 tok/s better. Keep 8192. The interference is prefill *volume*, not chunk size.
7. **Codex arm.** Only the ceiling and MTP touch it; the arm as implemented spends 3–5 round
   trips per answered call and a third of its steps at the ceiling. Not this task's to change.


## 4. Decision table for dz

| knob | what it buys (measured) | changes the protocol? | who decides | status |
|---|---|---|---|---|
| MTP depth 3 on all servers | decode ×~1.7 per iteration, all arms | no (exact in distribution) | relaunch of a shared resource → dz OK, after the c4h campaign ends | run files written; not launched |
| server layout at relaunch (3 × TP=2 vs 7 × TP=1) | private servers for a 7-cell arm: 4.3 s vs ~7 s per default step; TP=2 k=3 unmeasured | no | dz | measure both at relaunch, pick by numbers |
| `--prompt-layout append-only` for the direct arms | 3 cells/server at single-cell speed (−40 % / −50 % step time) | yes: state after frames, window 20–29 | dz (new campaign, all arms same layout) | implemented, opt-in, smoke-tested |
| `--prompt-layout static-first` | −7 % (default), more for hypothesis | yes (order only) | dz | implemented, opt-in |
| shorter outputs (memory rewrite, hypothesis JSON) | up to −50 % of the remaining step | yes | dz | not implemented |
| `--max-num-batched-tokens 2048` | nothing (same step, worse TTFT) | no | — | measured; keep 8192 |
| codex ceiling 120 s | 47–63 % of the codex arm's wall | yes (scoring policy) | dz | unchanged |


## 5. Recommended contract for the next relaunch / campaign

- Servers: as today (prefix cache, cap 1024, thinking off, temp 0.7/0.8/20, images 128,
  model-len 131072, chunk 8192) **plus `--spec-tokens 3`**. Run files
  `qwen35-serve/run/qwen38-s{1,2,3}-k3.sh` are written for the current 3 × TP=2 layout; at the
  relaunch, spend 12 minutes on `bench_agent_latency.py` (default legacy, 1 and 3 cells) against
  one TP=2 k=3 server and against the TP=1 k=3 dev server (`:8004`, GPU 1) to choose between
  3 × TP=2 and 7 × TP=1 for a 7-cell arm.
- Arms: `PROMPT_LAYOUT` unset (legacy) keeps every arm comparable with the c4h campaign;
  `PROMPT_LAYOUT=append-only` for **all** arms of a new comparison halves the direct arms'
  step time at 3 cells/server (and `launch_4hop.sh` tags them `-append-only`). Both are dz's
  choice; nothing here changes by default.
- Do not add layout cells to a legacy campaign, and do not pool them: `summarize_4hop.py`
  labels them `agentxchannel[layout]`.
