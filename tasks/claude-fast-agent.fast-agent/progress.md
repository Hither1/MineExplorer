# Progress: fast-agent

- 08:02 Branch `claude/fast-agent` created off `claude/eval-latency` (229d61e) in worktree MineExplorer-speedup. c4h campaign finished (last cells 07:27 / 07:42); dev server :8004 (GPU 1, TP=1, MTP k=3) up.
- 08:05 Output anatomy measured (findings). Contract fixed: `--response-style {full,compact}`.
- 08:15 `--response-style {full,compact}` implemented (context.py / hypothesis_agent.py prompts in shared pieces, agents, action_space None-safe memory, eval_benchmark, run_cell.sh, launch_4hop.sh, summarize_4hop.py, bench + check scripts, README). Golden: legacy/full IDENTICAL 6/6 (prompt_layout_check) + 6/6 (golden_dump). Wire test on :8004: default compact 77 gen tok/req, hypothesis compact 176; format followed.
- 08:19 Style bench suite started on :8004 (`outputs/bench/run_style.sh` -> `style.txt`).
- 08:20 Two 300-step fast smokes (scene 0306) launched against :8001 -- ABORTED at step 20: the production servers qwen38-s1/2/3 were killed at 08:17 by someone else and `qwen35-s1/2/3` (Qwen3.5) started in their place; connection refused -> default actions. Killed, outputs removed, logs kept as *.aborted-8001-down.txt. Re-run on :8004 after the bench.
- 08:31 Style bench done; two 300-step fast smokes (default, hypothesis; scene 0306) started on :8004 (`outputs/bench/run_fast_smoke.sh`). Commit 1ad9f8a pushed.
- 08:36 v1 smokes stopped: default ran 55 steps with 0% memory updates (laziness); hypothesis cell never got past env reset (sandbox slow, 5 min). Fixed the compact memory protocol (memory line + prompt), golden still identical (6/6 + 6/6).
- 08:39 v2 smokes launched on :8004 (default + hypothesis, 300 steps, scene 0306).
- 08:57 v2 smokes done: hypothesis 170 steps 4/4 (12 min), default 118 steps 4/4 (6.5 min); both one-line, 0 retries, memory maintained (see findings). Sandbox note: two simultaneous reset_env calls -> one hangs 600 s then succeeds on retry (both v1 and v2).
- 08:58-09:08 Dev server switched to Qwen3.5-27B TP=1 k=3 (`qwen35-serve/run/qwen35-dev.k3.sh`); `run/qwen38-dev.sh` restored to the k3 Qwen3.8 file on disk after a --dry-run overwrote it. Commit 6ca68e7 pushed.
- 09:08-09:29 Qwen3.5 style bench + two 60-step fast cells (staggered 90 s; no reset hang). `run_cell.sh` takes MODEL= now.
- 09:30 Report section 6 complete (bench, real cells, Qwen3.5); memory files updated; dev server left on Qwen3.5 k=3.
- 09:45 dz's follow-ups answered: (1) layout alone is -37/-45%, compact adds the rest -> both documented as independent choices in the report's contract; (2) codex/prolong reach measured and written up; (3) the model name is out of launch_4hop.sh (MODEL/MODEL_DIR), summarize_4hop.py (reads it from result.json, --model filter, labels arms by model when a prefix holds more than one) and prompt_layout_check.py (asks the server via /v1/models -- the hardcoded name 404'd once the dev slot moved to Qwen3.5).
- 10:05 Codex-side cost measured from existing logs/rollouts (no new runs); report section 7 + scripts/codex_cost.py. Answer to dz: MTP k=3 is the codex arms' main free lever, PRO-LONG has almost no headroom, the default x codex tool loop is the arm's definition rather than waste.
