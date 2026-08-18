# Progress

Append material checkpoints only: phase changes, decision-relevant probes, experiment launches,
failures and replans, verification, commits, pushes, and handoffs. Do not log every command.

## 2026-08-19 — task initialized

- State: initialized
- Evidence: none
- Next: follow `task_plan.md` Current Cycle
- 2026-08-19 05:52 branch `claude/eval-latency` + worktree ../MineExplorer-speedup off 9210527 (campaign HEAD); .venv/bench_4hop7 symlinked, .env copied, own outputs/.
- 2026-08-19 05:53 dev server launched: a227 GPU 1 (idle), TP=1, :8004, tmux qwen38-dev, prefix cache, MTP k=3, campaign wire contract (cap 1024, thinking off, qwen3_xml, images 128, model-len 131072); run file md5 verified on a227 before tmux.
- 2026-08-19 05:56 golden snapshot of legacy messages (default/hypothesis @ steps 1/25/26) -> scratchpad golden_legacy.json (sha256 per case) before any code change.
- 2026-08-19 06:03 dev server up (TP=1 fits: 51.9 GiB weights, KV 231k tokens at util 0.90; attention block 800 tokens); wire-verified cap 1024 (finish=length @1024), thinking off (28 prompt tokens), MTP k=3 metrics present.
- 2026-08-19 06:04 code: --prompt-layout {legacy,static-first,append-only} in mc_agent/context.py, agent.py, hypothesis_agent.py, eval_benchmark.py (+ append-only frame window, result.json field), run_cell.sh (PROMPT_LAYOUT). Golden check: legacy messages byte-identical (6/6 sha256, default+hypothesis @ steps 1/25/26). scripts/prompt_layout_check.py --tokenize-url: shared prefix legacy 84 tokens (0 blocks) / static-first 1583 default (1 block) & 4617 hypothesis (5 blocks) / append-only 94-96%.
- 2026-08-19 06:06 bench suite (scripts/bench_agent_latency.py, replay cell from c4h-0182 video+log) started on the dev server, MTP k=3: outputs/bench/k3.txt.
