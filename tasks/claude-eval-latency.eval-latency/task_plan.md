# Task Plan: eval-latency

Authorized by dz 2026-08-19 05:4x ("我觉得可以开一个新branch来做这些事情") after the latency analysis
of the c4h campaign (memory: eval-latency-breakdown). Branch `claude/eval-latency`, worktree
`../MineExplorer-speedup`; the campaign keeps running untouched in the main worktree.

## Stable Anchor

- Scientific question: how much of a MineExplorer cell's wall time (300 sequential steps) can be
  removed without changing what the arms measure -- and, for the knobs that do change the protocol,
  what exactly each one buys, so dz can choose with numbers.
- Target claim or outcome: (a) a serving contract for the next campaign (MTP depth, prefill chunk,
  layout) measured on realistic 20-frame agent requests; (b) an opt-in `--prompt-layout` for the
  direct (vllm) arm whose `legacy` value is byte-identical to today's prompt and whose other values
  make the prompt prefix-cache friendly, with the per-step latency of each measured; (c) a decision
  table for dz on the protocol-affecting knobs (frame window policy, memory length, codex ceiling).
- Success criterion: measured step latency (LLM call, TTFT, decode tok/s, prefix hit rate) for
  {legacy, static-first, append-only} x {MTP k=1,3} on the same server and prompts; legacy messages
  unchanged (golden check); a written recommendation; commits pushed to the personal branch.
- Constraints and budget: no change to the running c4h campaign (main worktree, servers :8001-:8003
  until it finishes ~07:00); dev measurements on a227 GPU 1 (TP=1, :8004, tmux qwen38-dev); the
  production servers are relaunched only after the campaign ends and only with dz's OK; same wire
  contract as the campaign (thinking off, cap 1024, temp 0.7) so numbers transfer.
- Non-goals: changing the default agent's prompt in place; touching PRO-LONG/codex prompts; new
  seeds/scenes; quantization (candidate for later, changes numerics); TP=1 x 7 as a layout
  (same total prefill capacity, no interference gain -- see findings).

## Current Cycle

- Working hypothesis: per-step latency of the direct arm = prefill of a 5-8k-token prompt that
  shares only ~143 tokens with the previous step (below the 800-token cache block, so 0 hits) +
  decode of 200-460 tokens at 30-60 tok/s, halved by neighbours' prefill chunks. Static-first
  ordering recovers 2-5 cached blocks per step; append-only frames + state-last recovers most of
  the prompt; MTP k=3 raises accepted tokens/iteration from 1.94 toward ~2.7-3.
- Main uncertainty: (1) MTP k=3 acceptance on JSON output at temperature 0.7 -- lossless in
  distribution, but is the draft accepted often enough to pay for the extra draft passes? (2) how
  much of the neighbour-interference loss the cache-friendly layout actually recovers under 3-4
  concurrent cells (the bench must run concurrent realistic requests, not single-stream).
- Next decisive experiment or implementation: (i) dev server TP=1/GPU 1 with MTP k=3 + prefix
  cache; bench realistic default/hypothesis requests single-stream and 3-concurrent; relaunch with
  k=1 and repeat -> MTP verdict. (ii) implement `--prompt-layout`, golden-check legacy, measure
  token-prefix sharing per layout, then a 12-step live smoke per layout on the dev server.
- Expected pass/fail signal: MTP: mean acceptance length >= 2.5 with k=3 and single-stream tok/s
  >= 1.25x k=1 -> adopt; layout: legacy sha256 unchanged; static-first >= 1600 shared tokens/step
  (default) and append-only >= 75% of the prompt reused; smoke step latency ordered
  legacy > static-first > append-only.
- Fallback: if k=3 does not pay, test k=2; if append-only's gain is small (< 20%), keep only
  static-first as the opt-in and record why.

## Success Criteria

- [x] MTP k verdict with numbers (dev server, both k on the same GPU/prompts): k=3 adopts (findings 06:43).
- [x] `--prompt-layout {legacy,static-first,append-only}` in eval_benchmark/agents/run_cell;
      legacy byte-identical (golden sha256); layout recorded in result.json (commit fce429a).
- [x] Token-prefix sharing per layout measured (scripts/prompt_layout_check.py); bench of every
      layout at 1/3 cells (outputs/bench/*.txt) and an append-only smoke through run_cell.sh.
- [x] Recommendation + decision table written (experiments/EVAL_LATENCY_helixon.md, README);
      commits pushed to `claude/eval-latency`.

## Parallel Tracks

| track | owner | mode | worktree / branch | dependency | deliverable | status |
|---|---|---|---|---|---|---|
| primary | primary | integrate | ../MineExplorer-speedup / claude/eval-latency | none | code, measurements, synthesis | active |
| campaign | other session | read-only here | ../MineExplorer / codex/qwen35-27b-minecraft-0313-0544 | none | 14 c4h cells (not touched) | running |

## Phases

### Phase 1: Serving knobs on the dev server (GPU 1)

- [x] dev server up (TP=1, :8004, prefix cache, MTP k=3, campaign wire contract); wire-verify cap
      1024 / thinking off.
- [x] bench: realistic default (5.3k) and hypothesis (8.3k) requests, single-stream and 3-concurrent
      -> TTFT, decode tok/s, acceptance length; then k=1 and k=3+chunk 2048 on the same server.
- **Status:** complete
- **Evidence:** outputs/bench/k3.txt, outputs/bench/k1_and_k3b2048.txt; findings 06:07-06:59

### Phase 2: `--prompt-layout` (code) + measurements

- [x] context builders: static block / state block split; append-only captions; agents assemble
      per layout; runner window policy; CLI + run_cell passthrough; result.json records it.
- [x] golden check (legacy unchanged); token-prefix sharing per layout; bench per layout at 1/3
      cells; 12-step append-only smoke through run_cell.sh (result.json prompt_layout set).
- **Status:** complete
- **Evidence:** commit fce429a; scratchpad golden_*.json; outputs/bench/*.txt; outputs/smoke-layout-append-only

### Phase 3: Interpret and hand off

- [x] decision table + recommended next-campaign contract (experiments/EVAL_LATENCY_helixon.md); commit; push branch.
- [ ] production relaunch (3 x TP=2 or 7 x TP=1 with k=3) only after the campaign ends and dz
      agrees; then wire-verify as on 08-18 23:56 and measure TP=2 k=3 vs TP=1 k=3.
- **Status:** in_progress (waiting on dz + campaign end)
- **Evidence:** qwen35-serve/run/qwen38-s{1,2,3}-k3.sh written; dev server :8004 up with k=3

## Decisions And Blockers

| Item | Decision or blocker | Evidence / owner |
|---|---|---|
| where to measure | a227 GPU 1 (idle, 41 MiB) as a TP=1 dev server; production untouched until the campaign ends | nvidia-smi 05:52 |
| default layout value | `legacy` stays the default everywhere; the new layouts are new arms, not a drop-in | dz's non-goal "changing any agent prompt" for the campaign |
| append-only window | frames kept append-only, rebased every 10 steps (window 20-29) so the prefix stays fixed between rebases | design, this task |

## Verification Contract

- Command or probe: `.venv/bin/python scripts/prompt_layout_check.py --golden <json>`;
  `.venv/bin/python scripts/bench_agent_latency.py --base-url http://192.168.2.20:8004/v1 ...`;
  smoke: `PROMPT_LAYOUT=<layout> VLLM_URL=http://192.168.2.20:8004/v1 bash scripts/run_cell.sh
  default vllm bench_4hop7/_split/0306 smoke-layout-<layout> 12`.
- Expected signal: golden sha256 equal for legacy; shared-prefix tokens as above; smoke result.json
  with `prompt_layout` set and step latencies ordered as hypothesised.
- Experiment/run pointer, if any: outputs/smoke-layout-*/ (worktree), qwen38-dev.log

## Next Action

dz decides: (a) relaunch production with MTP k=3 after the c4h campaign ends (and which layout, 3xTP=2 vs 7xTP=1, measured then); (b) whether the next campaign uses PROMPT_LAYOUT=append-only for all arms.
