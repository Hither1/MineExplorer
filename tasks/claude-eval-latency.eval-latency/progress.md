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
- 2026-08-19 06:20 k=3 bench suite done (outputs/bench/k3.txt): default legacy 4.3 s single / 7.3 s @3 cells; static-first 6.8 s @3; append-only 4.4 s @3; hypothesis legacy 8.0 s single / 13.7 s @3; append-only 7.0 s @3. MTP k=3 accepted 2.37-2.53 tok/draft (3.4-3.5 tok/iter) throughout. Commit fce429a pushed to origin/claude/eval-latency.
- 2026-08-19 06:21 12-step append-only smoke through run_cell.sh (default x vllm, 0306, dev server) launched: outputs/log-smoke-layout-append-only.txt.
- 2026-08-19 06:23 append-only smoke through run_cell.sh OK: 12 steps, result.json prompt_layout=append-only, 1/4 @ frame 10, 4.0 s/step (LLM 3.6 s, env 0.3 s); summarize_4hop shows it as defaultxvllm[append-only]. Commit 008e190.
- 2026-08-19 06:24-06:43 dev server relaunched k=1 (same TP=1 GPU); k1 suite done (numbers in findings). 06:43 relaunched k=3 + --max-num-batched-tokens 2048; suite running -> outputs/bench/k1_and_k3b2048.txt.
- 2026-08-19 06:59 k3+chunk2048 suite done (no gain; keep 8192). Report written: experiments/EVAL_LATENCY_helixon.md (breakdown, 14-row bench table, levers, decision table, recommended contract). Dev server being relaunched to the recommended k=3/8192 config (tmux qwen38-dev, :8004, GPU 1) and left up; production run files with k=3 written to qwen35-serve/run/qwen38-s{1,2,3}-k3.sh, NOT launched (campaign cells 0182/0726/0482/0603 still running at 06:54; production relaunch waits for dz).
