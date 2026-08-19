# Task Plan: fast-agent

## Stable Anchor

- Scientific question: how fast can a MineExplorer direct-channel cell run when the request
  layout and the response protocol are redesigned for the serving stack, while the agents
  keep doing what the methods do (default: thought/action/rewritten long-term memory;
  hypothesis: + hypothesis DAG + plan)?
- Target claim or outcome: a `fast` configuration (`--prompt-layout append-only` +
  `--response-style compact`) that cuts the direct arms' per-step time by >= 2x against the
  c4h legacy arm at the same server load, with the state the model maintains (memory,
  hypotheses, plan) still evolving in a real episode.
- Success criterion: bench (`scripts/bench_agent_latency.py`, dev server k=3, 3 cells) shows the
  per-step time of default and hypothesis under fast vs legacy; a real-sandbox smoke of each
  agent under fast runs >= 60 steps with no parse-retry storm and with memory/hypotheses/plan
  updates when the scene changes.
- Constraints and budget: dz authorised prompt-order and output-length changes (2026-08-19 08:00,
  "只要思路是我们这些方法的思路"). Legacy/full stays byte-identical and the default. Production
  servers :8001-:8003 untouched (dz decides the relaunch); dev server :8004 (GPU 1, k=3, TP=1)
  is the bench. No campaign launched here.
- Non-goals: PRO-LONG/codex arms; server relaunch; a success-rate comparison (that is dz's next
  campaign); reducing frame count or resolution.

## Current Cycle

- Working hypothesis: the direct arms' output is mostly re-emitted unchanged state (memory
  identical step-to-step in 28-36% of steps, 99% similar in median; hypothesis ops/plan repeated
  verbatim), plus pretty-printed JSON and long recaps in "thought"; a protocol that emits only
  what changed, in one line, halves the decode, and with append-only prefill the step becomes
  ~TTFT + a short decode.
- Main uncertainty: does the model still update memory/hypotheses when it should under the
  compact protocol (laziness), and how far does the thought shrink without instructions to.
- Next decisive experiment or implementation: implement `--response-style compact` for both
  agents (+ runner/launcher plumbing), bench legacy/full vs append-only/full vs
  append-only/compact at 1 and 3 cells on the dev server, then a 60-step real-sandbox smoke of
  each agent under fast.
- Expected pass/fail signal: default step at 3 cells 4.4 s (append-only/full) -> ~3.5 s;
  hypothesis 7.0 -> ~5.5 s; smoke shows memory updates on >= 20% of steps and no retry storm.
- Fallback: keep the elision of unchanged state but drop the thought-length guidance if the
  smoke's thoughts look degenerate.

## Success Criteria

- [ ] `prompt_layout_check.py --golden` still IDENTICAL for legacy/full after the change.
- [ ] Bench table legacy/full vs append-only/full vs append-only/compact (default, hypothesis; 1 and 3 cells).
- [ ] Real-sandbox smoke (>= 60 steps) per agent under fast with memory/hypothesis/plan update rates recorded.
- [ ] Report + task files + memory updated; branch pushed.

## Parallel Tracks

| track | owner | mode | worktree / branch | dependency | deliverable | status |
|---|---|---|---|---|---|---|
| primary | primary | integrate | MineExplorer-speedup / claude/fast-agent | none | code + bench + smoke + report | active |

## Phases

### Phase 1: Discover and specify

- [x] Output anatomy measured from the c4h logs (see findings 08:05).
- [x] Contract: `--response-style {full,compact}` orthogonal to `--prompt-layout`; full/legacy byte-identical.
- **Status:** complete
- **Evidence:** findings.md 08:05

### Phase 2: Implement or run the decisive test

- [ ] context.py / hypothesis_agent.py compact prompts; agents accept response_style; None-safe parse.
- [ ] eval_benchmark.py / run_cell.sh / launch_4hop.sh / summarize_4hop.py plumbing; result.json records it.
- [ ] Golden check; bench on dev server; real-sandbox smoke x2.
- **Status:** in_progress
- **Evidence:** none

### Phase 3: Interpret and hand off

- [ ] Report section + decision table; memory; commit/push.
- **Status:** pending
- **Evidence:** none

## Decisions And Blockers

| Item | Decision or blocker | Evidence / owner |
|---|---|---|
| Two knobs, not one profile | layout (prefill/cache) and style (decode) are separately attributable; both recorded in result.json and in the arm label | primary |
| Production relaunch (k=3) | still dz's call; c4h campaign finished 07:42 | dz |

## Verification Contract

- Command or probe: `.venv/bin/python scripts/prompt_layout_check.py --golden <golden_legacy.json>`; `scripts/bench_agent_latency.py --layout append-only --style compact --concurrency 3`; `PROMPT_LAYOUT=append-only RESPONSE_STYLE=compact scripts/run_cell.sh ... 60 steps`
- Expected signal: golden IDENTICAL; step time as in Current Cycle; smoke result.json records layout+style
- Experiment/run pointer, if any: `outputs/bench/`, `outputs/smoke-fast-*`

## Next Action

Implement `--response-style compact` in mc_agent/context.py and mc_agent/hypothesis_agent.py.
