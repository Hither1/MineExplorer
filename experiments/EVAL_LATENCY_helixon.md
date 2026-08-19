# Where a MineExplorer cell's time goes, and what to do about it (helixon, 2026-08-19)

Measured on the c4h campaign (`outputs/log-c4h-*.txt`, servers `qwen38-s1/2/3` on a227) and
on a dev server (a227 GPU 1, TP=1, `:8004`, prefix cache, campaign wire contract: thinking
off, cap 1024, temp 0.7). Branches `claude/eval-latency` (§1–5: breakdown, serving knobs,
`--prompt-layout`) and `claude/fast-agent` (§6: `--response-style`, real cells, Qwen3.5).
Nothing here changes a running arm: `--prompt-layout legacy --response-style full` (the
defaults) is today's prompt and protocol byte for byte.

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
| MTP depth 3 on all servers | decode ×~1.7 per iteration, all arms; same acceptance on Qwen3.5-27B (§6) | no (exact in distribution) | relaunch of a shared resource → dz; the slots now run Qwen3.5 k=1 (`qwen35-s{1,2,3}.sh`, relaunched 08:17 by the campaign session) | `qwen38-s{1,2,3}-k3.sh` written for Qwen3.8; a Qwen3.5 k=3 file is one `serve.sh --spec-tokens 3` away |
| server layout at relaunch (3 × TP=2 vs 7 × TP=1) | private servers for a 7-cell arm: 4.3 s vs ~7 s per default step; TP=2 k=3 unmeasured | no | dz | measure both at relaunch, pick by numbers |
| `--prompt-layout append-only` for the direct arms | 3 cells/server at single-cell speed (−40 % / −50 % step time) | yes: state after frames, window 20–29 | dz (new campaign, all arms same layout) | implemented, opt-in, smoke-tested |
| `--prompt-layout static-first` | −7 % (default), more for hypothesis | yes (order only) | dz | implemented, opt-in |
| `--response-style compact` for the direct arms | with append-only: default 4.6 → 2.8 s, hypothesis 7.6 → 4.3 s at 3 cells/server (§6) | yes: one-line reply, 1–3-sentence thought, memory / hypotheses / plan only when they change | dz authorised the change class 08:00; adopting it for a campaign is still an arm choice | implemented, opt-in, benched, smoke-tested (§6) |
| `--max-num-batched-tokens 2048` | nothing (same step, worse TTFT) | no | — | measured; keep 8192 |
| codex ceiling 120 s | 47–63 % of the codex arm's wall | yes (scoring policy) | dz | unchanged |


## 5. Recommended contract for the next relaunch / campaign

- Servers: as today (prefix cache, cap 1024, thinking off, temp 0.7/0.8/20, images 128,
  model-len 131072, chunk 8192) **plus `--spec-tokens 3`** — for Qwen3.5 as much as for Qwen3.8
  (§6). Run files `qwen35-serve/run/qwen38-s{1,2,3}-k3.sh` are written for the 3 × TP=2 layout
  (Qwen3.8); the slots have served Qwen3.5 k=1 since 08:17. At a relaunch, spend 12 minutes on
  `bench_agent_latency.py` (default legacy, 1 and 3 cells) against one TP=2 k=3 server and
  against the TP=1 k=3 dev server (`:8004`, GPU 1) to choose between 3 × TP=2 and 7 × TP=1 for
  a 7-cell arm.
- Arms: `PROMPT_LAYOUT` / `RESPONSE_STYLE` unset (legacy / full) keeps every arm comparable
  with the c4h campaign. The two knobs are independent and either can be taken alone:
  `PROMPT_LAYOUT=append-only` alone is −37/−45 % (default 7.3 → 4.6 s, hypothesis 13.7 → 7.6 s
  at 3 cells/server) and changes only what the model *reads* — state after the frames, window
  20–29 — leaving every reply's format and length exactly as the campaign's; adding
  `RESPONSE_STYLE=compact` takes it to −62/−69 % (2.8 s / 4.3 s) but also changes what the
  model *writes*. Smallest protocol delta for most of the speed: layout only. Fastest:
  both, for **all** arms of the comparison (`launch_4hop.sh` tags them
  `-append-only-compact`). dz's choice; nothing here changes by default.
- Do not add layout/style cells to a legacy campaign, and do not pool them: `summarize_4hop.py`
  labels them `agentxchannel[layout,style]`.

## 6. The response style: say only what changed, in one line (2026-08-19 08:00–)

dz's call of 08:00: prompt order and output length may change as long as the agents keep doing
what the methods do. So, on top of the layout, `--response-style compact` (branch
`claude/fast-agent`, `RESPONSE_STYLE` for the scripts; `full` = today's protocol byte for byte,
still the default).

What the direct arms were spending their decode on (c4h campaign, 7 cells per arm, `/tokenize`):

| arm | reply | thought | memory | action | hypotheses | plan | JSON pretty-printing + fences |
|---|---|---|---|---|---|---|---|
| default × vllm | 237 tok | 74 | 118 | 10 | – | – | ~35 |
| hypothesis × vllm | 508 tok | 126 | 99 | 5 | 134 | 61 | ~83 |

The memory is identical to the previous step's in 36 % (default) / 28 % (hypothesis) of steps and
99 % similar in median; the hypothesis agent sends ≥ 1 hypothesis op on 99 % of steps and repeats
the plan verbatim for runs of steps (e.g. 0306, steps 61–64: same plan four times, same h13 with
the evidence reworded). Compact JSON alone: 237 → 208, 508 → 414 tokens; without the memory:
88 / 302.

`compact` asks for the same fields with the same meaning, but:
- one JSON object on one line (no pretty-printing);
- a 1–3 sentence thought that does not restate the memory, the hint lines or the captions;
- `memory_update` only on steps where the memory changes (new landmark/object, sub-goal done,
  failed direction/attempt, change of plan, or the memory is stale/wrong) — then the FULL memory,
  as before; an absent key means "unchanged", which the runner already treats as "keep";
- hypothesis agent: a hypothesis op only when a hypothesis is new or its confidence moves ≥ 0.1
  or its status changes (id + changed fields + ≤ 15-word evidence); `plan` only when it changes.
  `HypothesisAgent._apply_hypothesis_ops` already treats absent as "keep". The
  hypothesis-writing guidance (one id per claim, decompose the task up front, evidence from the
  position line, retire stale placeholders, Examples 1–6) is unchanged; a "quiet step" example is
  added.
The prompts are built from shared pieces (`_DEFAULT_*` / `_HYP_*` in `mc_agent/`), so `full`
cannot drift from the campaign's prompt (`prompt_layout_check.py --golden`: 6/6 identical).

Measured on the dev server (TP=1, MTP k=3, `outputs/bench/style.txt`; same replay as §2):

| agent | layout | style | cells | step | TTFT | gen tok/req | decode per req | prefix hit |
|---|---|---|---|---|---|---|---|---|
| default | legacy | full | 3 | 7.3 s | 2.62 s | 192 | 36.8 tok/s | 2 % |
| default | append-only | full | 3 | 4.6 s | 1.44 s | 185 | 59.7 | 62 % |
| default | legacy | compact | 3 | 5.5 s | 2.69 s | 76 | 30.2 | 0 % |
| default | append-only | **compact** | 3 | **2.8 s** | 1.14 s | 78 | 49.4 | 69 % |
| default | append-only | compact | 1 | **2.2 s** | 0.68 s | 78 | 64.4 | 63 % |
| hypothesis | legacy | full | 3 | 13.7 s | 2.83 s | 449 | 42.0 | 2 % |
| hypothesis | append-only | full | 3 | 7.6 s | 1.28 s | 347 | 52.8 | 69 % |
| hypothesis | legacy | compact | 3 | 9.7 s | 3.71 s | 178 | 33.2 | 0 % |
| hypothesis | append-only | **compact** | 3 | **4.3 s** | 1.25 s | 154 | 48.9 | 74 % |
| hypothesis | append-only | compact | 1 | **3.7 s** | 0.97 s | 157 | 62.3 | 65 % |

Read: the two knobs are complementary and both are needed. Style alone leaves the uncached
prefill (TTFT 2.7–3.7 s at 3 cells) and buys 25–30 %; layout alone leaves the 185–350-token
decode and buys 37–45 %; together, at 3 cells per server, a default step goes 7.3 → 2.8 s (−62 %)
and a hypothesis step 13.7 → 4.3 s (−69 %) — against the campaign's own k=1 servers (8.7 s
default at 3 cells) it is −68 %. What is left of a step is now ~1.1 s TTFT (state block +
the newest frame + the tail block that the 800-token cache granularity never hits) + ~1.6 s of
decode for ~78 tokens; the hypothesis agent's ~154 tokens are the state it chose to change.

**Does the model still keep its state?** The first compact cell answered no: 54 steps, three
milestones, and not one `memory_update` — with the memory section simply absent while empty (as
in `full`, where the model rewrites it every step regardless) and an example marked "USE THIS
OFTEN" carrying no memory, the model ran on the captions' thoughts alone, i.e. a memoryless
agent (`outputs/smoke-history/log-fast-default-vllm-0306.v1-nomemory.txt`). So `compact` now
always renders a memory line the model can read staleness off: "empty - write it this step",
otherwise "(last rewritten at step N; rewrite it whenever it no longer records everything you
have found, completed or ruled out)" and, after `MEMORY_REWRITE_DUE` = 20 steps without a
rewrite, "rewrite it this step"; the prompt says write it on step 1, and the examples start with
a first-step memory. The agents track the memory-change step from what the runner hands them;
the runner is untouched. Then, full-length real cells on scene 0306 (the 4-hop corridor; the
legacy c4h cells of both agents finished it) against the dev server, both cells at once
(`scripts/response_stats.py`):

| cell (scene 0306) | steps | milestones (step) | wall | s/step (med) | reply | thought | memory sent | hypotheses / plan sent | retries |
|---|---|---|---|---|---|---|---|---|---|
| default, legacy/full (c4h 08-18 14:32, production server shared with codex cells) | 136, ESC | 4/4 (10, 41, 57, 135) | 106 min | 37 s | 915 ch | 339 ch | 100 % (469 ch) | – | 1 |
| **default, append-only/compact** (dev, k=3) | 118, ESC | 4/4 (39, 60, 74, 117) | 6.5 min | 3.0 s | 270 ch | 201 ch | 37 % (427 ch), first at step 1 | – | 0 |
| hypothesis, legacy/full (c4h 08-19 00:05, production server) | 107, ESC | 4/4 (7, 15, 46, 106) | 30 min | 16 s | 2004 ch | 459 ch | 100 % (431 ch) | 99 % / 99 % | 0 |
| **hypothesis, append-only/compact** (dev, k=3) | 170, ESC | 4/4 (21, 23, 41, 169) | 12 min | 4.0 s | 734 ch | 253 ch | 59 % (280 ch) | 16 % / 56 % | 0 |

Both fast cells finish the scene, every reply was one line, no parse retries, and the state is
what the methods maintain: the default cell writes its memory at step 1 and rewrites it (in
full: locations, findings, failed attempts, current plan) on 37 % of steps; the hypothesis cell
opens the four-hypothesis chain h1→h2→h3→h4 at step 1, confirms h1–h3 with evidence as it
finds them (h4 active at 0.85 when it ESCs), rewrites the memory on 59 % of steps and the plan
on 56 %, and sends a hypothesis op only on 16 % of steps instead of 99 %. Milestone steps are
one seed each and not a quality claim; that is the next campaign's job. Sandbox note: two
`reset_env` calls issued at the same instant made one hang for its 600 s timeout and succeed on
the retry (seen in both smoke rounds); stagger cell starts.

**On Qwen3.5-27B, the model the production slots serve since 08:17.** At 08:17 the campaign
session replaced `qwen38-s1/2/3` with `qwen35-s1/2/3` (Qwen3.5-27B, same flags, k=1), so the next
campaign's model is Qwen3.5; the dev slot was switched to Qwen3.5-27B TP=1 k=3
(`qwen35-serve/run/qwen35-dev.k3.sh`) and the same bench and short real cells repeated
(`outputs/bench/style_qwen35.txt`, `outputs/log-fast-q35-*-0306.txt`):

| Qwen3.5-27B, TP=1, k=3, 3 cells | legacy/full | append-only/full | append-only/compact | MTP tokens/iter |
|---|---|---|---|---|
| default step (gen tok/req) | 7.2 s (180) | 4.3 s (162) | **3.3 s** (100) | 3.2–3.4 |
| hypothesis step (gen tok/req) | 12.3 s (416) | 6.8 s (305) | **4.1 s** (127) | 3.3–3.4 |

Same picture as Qwen3.8 (compact replies run ~25 tokens longer on Qwen3.5), and the MTP head is
accepted just as often, so `--spec-tokens 3` is worth the same there. Real 60-step cells on
scene 0306: default 55 steps, 4/4 milestones at 6/15/20/54 then ESC, 3.0 s/step, memory written
at steps 1, 3, 23, 36 (coherent, tracks progress), 98 % one-line, one retry (the model answered a
bare `<think>` once — a Qwen3.5 quirk with thinking off, the retry parsed); hypothesis 60 steps,
3/4 by step 25, 4.0 s/step, 100 % one-line, 0 retries, memory 22 % / hypotheses 40 % / plan
27 %. Two of 38 bench requests on hypothesis/compact came back as junk (` button\n柳`,
` user...`) and were retried — watch the retry column in a Qwen3.5 campaign. `run_cell.sh` now
takes `MODEL=Qwen3.5-27B` (default unchanged); `launch_4hop.sh` / `summarize_4hop.py` still
look for `outputs/<tag>/Qwen3.8-27B/...` and need the model name lifted before a Qwen3.5
campaign is launched through them.

**Which arms these two knobs reach.** Every number above is the direct (vLLM) channel, which is
where the arms' step time actually lives. For the other two:

- `default × codex` and `hypothesis × codex`: the same agent code builds the request, so both
  flags apply and are recorded in `result.json`. `CodexProvider._flatten` renders the message
  list as one text prompt plus image *files* on disk, so the ordering survives while the images
  leave the token stream; measured on the flattened prompt (`prompt_layout_check.py --codex`),
  the step-to-step shared prefix goes 1–3 % (legacy) → 52–75 % (static-first) → 94–96 %
  (append-only), i.e. the cache mechanism works there too. It just does not buy much there —
  see §7, where the codex arms' cost is measured.
- `prolong × codex`: unaffected by construction. PRO-LONG writes its own prompt (`prolong_mc`,
  its own AGENTS.md workflow and one resumed conversation), so `_run_benchmark` **rejects**
  `--prompt-layout` / `--response-style` for `--agent-mode prolong` rather than accepting a flag
  it would silently ignore.

One cost worth naming: the compact instruction block is *bigger* than the full one (default
1789 vs 1588 tokens, hypothesis 4653 vs 4622) — the rules are more explicit and it carries the
memory line. Under `append-only` that block is static and cached, so it is paid once per cell;
under `legacy` it is re-prefilled every step, which is part of why legacy/compact is only
7.3 → 5.5 s.

## 7. What the codex-driven arms actually cost, and where their room is (2026-08-19 10:00)

Read off the finished c4h cells and the running q35 cells — their logs and the rollouts codex
itself wrote — with no new runs (`scripts/codex_cost.py --prefix <c4h|q35> --arm <default|prolong>`;
the numbers below are per arm, all seven cells pooled).

| | `default × codex` (c4h, Qwen3.8, ceiling 120 s) | `prolong × codex` (q35, Qwen3.5, prefix-cached) |
|---|---|---|
| model calls | 1.07 per **step** (one fresh `codex exec` each) | one turn per **6–11 steps** (one resumed conversation) |
| step / turn time | step med 63 s (p90 121 s) | turn med 16–20 s (p90 41 s) → **4.1–6.5 s of model time per step** |
| requests per call/turn | med 7 (p90 33) | med 3 (p90 4) |
| input tokens per call/turn | 117k, **88 % cached** | 106k, **96 % cached** |
| **output tokens per call/turn** | **1172–1450 (answered)**, p90 3.5–4k | **220** (p90 466) |
| tools per call/turn | 4.0 PIL analyses, 3.6 `view_image`, 3.8 `echo`, 1.3 other | 2.1 `exec_command`, ~0 `view_image` |
| tool execution time | 3.7 s (5 % of the call) | 0.5 s (3 % of the turn) |
| ceiling | 33 % of calls, **57 % of the arm's call time**; 99 % of the arm's wall is inside these calls | not reached |

**Both codex arms are decode-bound at the server's per-request rate, exactly like the direct
arms.** Matching each rollout to its log call (`answered` calls only): 1172–1450 output tokens in
38–48 s = **29–30 tokens/s effective**, which is precisely the per-request decode rate measured
for 2–3 concurrent requests at MTP k=1. Nothing else is material: tool execution is 5 %, the
first request (startup + prefill + first decode) is 3.7 s, the sandbox start is ~1.6 s. And a
call that hits the ceiling is **not hung**: it has generated 3.0–3.5k tokens at 25–29 tok/s when
the ceiling cuts it — it is an unbounded generation loop running at full speed.

What follows, ranked:

1. **MTP `--spec-tokens 3` is the biggest lever for the codex arms too, and it is free.** Their
   time is ~95 % decode, so ×1.7 decode ⇒ answered calls 38–48 s → **22–28 s**, PRO-LONG's turn
   16–20 s → ~10–13 s. It should also *raise the score*: within the same 120 s ceiling a stalled
   call would produce ~5–6k tokens instead of 3.0–3.5k, so the calls that needed a little more
   room answer instead of becoming no-ops. Exact in distribution, no protocol change. (This is
   the same recommendation as §5; the point is that it is worth *more* in absolute seconds on the
   codex arms than on the direct ones.)
2. **Decode headroom per cell.** 29–30 tok/s is the *shared-server* rate; single-stream is
   43–70 tok/s. A step that is 1200–3500 generated tokens pays that rate linearly, so how many
   cells share a server matters more for the codex arms than for anything else. Scheduling, not
   code.
3. **The prompt-side knobs are weak here.** `append-only` moves the codex prompt's reusable
   prefix from 1–3 % to 94–96 % (§6), but prefill is only ~4 s of a 40–85 s call and codex's own
   conversation is already 90–96 % cached from the second request on: ~1–2 s. `compact` shortens
   only our final JSON (~200–400 of 1200–3500 tokens): ~10–20 % on answered calls, nothing on
   stalled ones. Take them if the direct arms take them; do not adopt them *for* codex.
4. **The cost driver on `default × codex` is the model's own tool loop** — ~1400 of its ~1800
   output tokens are `exec_command` arguments (PIL pixel analyses, `echo`), not the answer. That
   loop is *what this arm measures*: it is PRO-LONG's scaffold control, same tool surface, so
   removing the tools would make it a different arm and break the comparison. If a cheaper
   control is wanted it is a protocol decision (e.g. "answer from the attached frames, do not
   analyse them with code" in both codex arms' prompts — a blanket no-tools is impossible since
   PRO-LONG's workflow writes files), not an optimisation.
5. **The ceiling is a shallow trade, and k=3 improves it for free.** Measured what-if over the
   arm's 2248 calls: ceiling 90 s → 85 % of today's call time, 5 % of answered calls lost;
   75 s → 77 %, 11 % lost; 60 s → 67 %, 22 % lost. The arm is expensive because an answered call
   is 40 s, not only because a third of them stall.
6. **PRO-LONG has little headroom and needs none.** It is already the cheapest arm per step
   (4.1–6.5 s of model time, one turn per 6–11 steps, 220 output tokens per turn, 96 % cached
   input, 3 % tool time). Its queue depth is part of the method, not a knob to tune.
7. **Already fine, do not "fix":** a ceiling kills the whole process group (`run_codex`,
   `start_new_session` + `killpg`), so a stalled call stops costing the server immediately;
   JSON retries are 1.07 calls/step; prefix caching is working on the codex conversation.

## 8. Can codex's tools be restricted, and what else is tunable there (2026-08-19 11:00)

Verified against the codex the arms actually run (`codex-cli 0.147.0`, upgraded to 0.148.0
by another user at 11:23 mid-session — the tool list is unchanged under 0.148, but a codex
upgrade changes the harness the arms run inside, so runs taken across it are not bit-comparable;
through
`prolong_mc/codex_sandbox.sh`, model on the dev server). Nothing below is committed to an arm —
these are the knobs and what each is worth.

**The tool surface can be restricted, and codex validates the names.** Today's
`SAFE_CODEX_FLAGS` leave the model with `exec_command, write_stdin, update_plan,
request_user_input, view_image` (asked the model to print its own tool list):

| flag | tools left | note |
|---|---|---|
| today's `SAFE_CODEX_FLAGS` | exec_command, write_stdin, update_plan, request_user_input, view_image | |
| `--disable view_image` | the same minus `view_image` | accepted |
| `--disable shell_tool` | update_plan, request_user_input, view_image | removes `exec_command` **and** `write_stdin` |
| `--disable plan_tool` / `update_plan` / `request_user_input` | — | `Error: Unknown feature flag` |
| `-c include_plan_tool=false` | unchanged | accepted and silently ignored by 0.147 |

So `view_image` and the shell can be taken away; `update_plan` and `request_user_input` cannot
(0.5 and ~0 calls per step, so it does not matter).

**But on Qwen3.5 there is nothing to restrict.** Replaying five real `default × codex` steps
(the agent's own message list, 20 frames, through `CodexProvider` and the sandbox) against the
dev server:

| | Qwen3.8 (c4h campaign, 2093 steps) | Qwen3.5 (this probe, 5 steps) | Qwen3.5, `--disable view_image` |
|---|---|---|---|
| model requests per step | 7 (p90 33) | **1** | 1 |
| tool calls per step | 4.0 PIL + 3.6 `view_image` + 3.8 `echo` | **0** | 0 |
| output tokens per step | 1634 | **207** | 161 |
| call time | 40 s answered, 33 % hit the 120 s ceiling | **9 s**, 5/5 answered | 8 s, 5/5 answered |

The PIL/`view_image` loop that makes this arm expensive is a **Qwen3.8-with-thinking-off
behaviour**, not a property of the scaffold: given the same prompt and the same tools, Qwen3.5
answers in one message without touching a tool. Since the campaign's servers now serve Qwen3.5,
restricting the tool surface would buy ~1 s per step. (Five replayed steps on an idle server is
not a campaign — the number to trust is the first real `default × codex` cell on Qwen3.5.)

**And `view_image` must not be disabled anyway, because the two codex arms are not handed their
frames the same way.** `SAFE_CODEX_FLAGS` is shared, so removing the tool would remove it from
both arms — an identical tool *surface* — but not an identical *capability*:

| | frames attached per call/turn | route to older frames | `view_image` calls actually made |
|---|---|---|---|
| `default × codex` | **20** (the whole buffer, as `-i` files) | already attached | 1.64 per call (Qwen3.8), 0 (Qwen3.5) |
| `prolong × codex` | **1** (the current view; `ATTACHED_NOTE`) | the `[FRAME] frames/step_NNNN.png` paths in its log, opened with the image viewer (`prompts.py`: "use the image viewer on the older paths") | 1 call in 176 turns (Qwen3.8); 5 in 322 (Qwen3.5) |

So the same flag would leave the baseline with all 20 frames in front of it and leave PRO-LONG
with a one-frame window and no way back — a targeted handicap on the arm under test, not a
neutral speed knob. The fact that PRO-LONG almost never uses the viewer (0.01–0.02 calls per
turn) does not make it safe to remove: "the analyzer had the option to re-read pixels and chose
the numeric log instead" is a claim about PRO-LONG's architecture, and it stops being sayable
once the option is taken away. In the other direction, on Qwen3.8 the baseline uses the viewer
1.64 times per call, so removing it would change the *baseline's* behaviour materially while
barely touching PRO-LONG — asymmetric either way.

`prolong_mc/sandbox_selftest.py` already asserts this in both directions (a tool that disappears
fails the check exactly like one that appears), with the same reasoning in its comment.
**Recommendation: do not restrict the tools. Re-measure the arm on Qwen3.5 before assuming it is
expensive.**

**`--output-schema` is the one codex setting worth adopting, and it is a reliability fix —
now implemented** as `--codex-output-schema` / `CODEX_OUTPUT_SCHEMA=1` (opt-in, default off).
It constrains codex's final message to the agent's reply schema. What it buys: the codex arms
cannot answer with unparsable text. On the c4h campaign the `default × codex` arm logged 148
parse failures / retry-exhaustions over 2266 calls (~7 % of calls are retries the arm pays for
at 8–40 s each) while the direct arms logged none.

The one implementation detail that decides whether it works: **the schema file must be inside
the call's sandbox workspace** — with the file in `/tmp` outside the workspace codex fails the
whole call with `schema file …: No such file or directory` (measured both ways), so
`CodexProvider` writes it into the per-call workdir rather than taking a static flag. The schema
comes from `default_reply_schema` / `hypothesis_reply_schema`, which track the prompt: under
`compact` the keys the model only sends when they change (`memory_update`, `hypotheses`, `plan`)
stay optional.

Verified on codex 0.148, both agents × both styles, three real replayed steps each:

| | schema off | schema on |
|---|---|---|
| reply keys | the right ones, but the object arrives markdown-fenced under `full` | exactly the schema's key set, never fenced |
| `compact` optional keys | model's choice | still the model's choice (one reply came back `thought`+`action` only) |
| step time (n=3, dev server) | 24 / 19 / 15 / 12 s | 18 / 14 / 13 / 10 s |

and end to end through `run_cell.sh`: a 10-step `default × codex` cell on Qwen3.5, 8 s/step,
**0 parse failures**, `result.json` carrying `codex_output_schema: true`. The step times say it
is not slower — three steps per cell is too few to claim it is faster. `_run_benchmark` rejects
the flag for `--agent-mode prolong` and for non-codex runs, and (fixed while here) all such
argument checks now run *before* the sandbox session is created, so a rejected combination no
longer leaks an environment.

**Everything else on the codex side, measured or checked:** the ceiling is a policy knob (§7);
`--ephemeral` would drop the rollouts, which are the only record of what a call did — do not use
it; `web_search`, apps, sub-agents, plugins, image generation and goals are already off and
`prolong_mc.selftest` asserts the resulting tool list, so a codex upgrade that adds a tool fails
there rather than silently changing an arm.

