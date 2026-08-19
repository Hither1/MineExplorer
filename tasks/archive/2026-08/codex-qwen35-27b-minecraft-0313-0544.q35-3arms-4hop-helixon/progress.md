# Progress: q35-3arms-4hop-helixon

## 2026-08-19

- 08:1x  Checked the Qwen3.5-27B checkpoint: complete (52 GB, 11/11 shards, 0 incomplete
  blobs), `Qwen3_5ForConditionalGeneration` / `model_type: qwen3_5`, text config identical
  to Qwen3.8-27B field for field (64 layers, 262144 positions, `mtp_num_hidden_layers: 1`,
  vocab 248320). Chat templates differ only in the thinking-ON branch (3.8 adds a
  `reasoning_effort` system instruction); the thinking-OFF mechanism
  (`enable_thinking is false` -> prefill `<think>\n\n</think>`) and the tool-call XML are
  the same, so the same flags apply.
- 08:16  `MODEL` parametrized through `run_cell.sh` / `launch_4hop.sh` / `summarize_4hop.py`
  (commit d9d4b93). Summarizer with the defaults still reproduces the Qwen3.8 campaign
  (10/28, 10/28, 12/28, 9/28).
- 08:17  `qwen35-serve/run/qwen35-s{1,2,3}.sh` generated with `serve.sh --dry-run`; diff
  against `qwen38-s{1,2,3}.sh` is exactly two lines (MODEL_PATH, --served-model-name).
  md5 verified from a227.
- 08:17  Stopped `qwen38-s{1,2,3}` (GPUs 2-7 back to 17-21 MiB; `qwen38-dev` on GPU 1 left
  alone -- another session's), launched `qwen35-s{1,2,3}` on GPUs 2,3 / 4,5 / 6,7.
- 08:28  All three up after 511 s.
- 08:30  Wire check ALL PASS on :8001/:8002/:8003 -- `Qwen3.5-27B` at 131072; chat stops
  at 1024 with `length` and no `<think>`; `/v1/responses` stops at 1024 with `incomplete`
  / `max_output_tokens`; a tool call arrives as one parsed `tool_calls` entry with no
  `<tool_call>` text in content (the `qwen3_xml` parser applies to this checkpoint too).
  Script: scratchpad `wirecheck.py`.
- 08:35  Two 2-step smokes on 0306 pass: `prolong x codex` (turn 1 queued 15 steps,
  `codex_sandboxed: true`) and `default x vllm` (real actions + memory_update). No
  `Agent call failed` / `env.step failed` / `SandboxViolation` / traceback in either.
- 08:36  Campaign launched: 21 cells, `default:vllm prolong:codex hypothesis:vllm` x 7
  scenes, CONC=14, 45 s stagger, dealt round-robin over the three servers.
  `outputs/log-q35-launcher.txt`, per-cell `outputs/log-q35-<agent>-<channel>-<scene>.txt`.
- 10:30  All 21 cells finished (1 h 54 min wall). Clean-run audit: 0 `Agent call failed`,
  0 `env.step failed`, 0 `SandboxViolation`, 0 tracebacks; 7/7 codex cells
  `codex_sandboxed: true`; 0 of 770 shell/exec calls in the PRO-LONG rollouts named a repo
  path outside the episode workspace; 0 rollout lines carried the milestone schema.
- 10:4x  `experiments/RESULTS_helixon_4hop_qwen35.md` written; cross-link added to the
  Qwen3.8 report. Scores 11/28, 10/28, 14/28 (default x vllm, hypothesis x vllm,
  prolong x codex) against 10/28, 10/28, 12/28 on Qwen3.8.
