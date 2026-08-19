# Progress: fast-agent

- 08:02 Branch `claude/fast-agent` created off `claude/eval-latency` (229d61e) in worktree MineExplorer-speedup. c4h campaign finished (last cells 07:27 / 07:42); dev server :8004 (GPU 1, TP=1, MTP k=3) up.
- 08:05 Output anatomy measured (findings). Contract fixed: `--response-style {full,compact}`.
- 08:15 `--response-style {full,compact}` implemented (context.py / hypothesis_agent.py prompts in shared pieces, agents, action_space None-safe memory, eval_benchmark, run_cell.sh, launch_4hop.sh, summarize_4hop.py, bench + check scripts, README). Golden: legacy/full IDENTICAL 6/6 (prompt_layout_check) + 6/6 (golden_dump). Wire test on :8004: default compact 77 gen tok/req, hypothesis compact 176; format followed.
- 08:19 Style bench suite started on :8004 (`outputs/bench/run_style.sh` -> `style.txt`).
- 08:20 Two 300-step fast smokes (scene 0306) launched against :8001 -- ABORTED at step 20: the production servers qwen38-s1/2/3 were killed at 08:17 by someone else and `qwen35-s1/2/3` (Qwen3.5) started in their place; connection refused -> default actions. Killed, outputs removed, logs kept as *.aborted-8001-down.txt. Re-run on :8004 after the bench.
