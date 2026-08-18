# Progress

Append material checkpoints only: phase changes, decision-relevant probes, experiment launches,
failures and replans, verification, commits, pushes, and handoffs. Do not log every command.

## 2026-08-18 — task initialized

- State: initialized
- Evidence: none
- Next: follow `task_plan.md` Current Cycle

## 2026-08-18 13:30-13:50 — Phase 1 done, server relaunching

- Fixes committed as 33be080 (find_rollout, run_codex process-group kill, CodexProvider `-i` before `-m`,
  run_cell.sh through codex_sandbox.sh with sandbox selftest gate, sandbox_selftest accepts proxy 403,
  screen_scenes --no-backwards). Verified: 98/98 selftest PASS, sandbox selftest all-pass, find_rollout
  finds today's rollouts, run_codex leaves no orphans, sandboxed prolong smoke (2 turns) OK.
- a227 server relaunched 13:49 with `max_new_tokens:1024` (previous run file kept as
  `qwen35-serve/run/qwen-serve-qwen3-8-27b.sh.pre-cap1024.bak`).
- bench_4hop7/ (7 scenes, + _split/<scene>) and scripts/launch_4hop.sh written.
- Next: verify cap on both channels, 3-step smokes via run_cell.sh, launch 14 cells (CONC=4).

## 2026-08-18 14:00-14:31 — servers relaunched, smokes pass, campaign launched

- First relaunch (13:48) silently ran the STALE run file (a227's view of the NFS file lagged
  the write by a second): the process argv had no max_new_tokens although the file did.
  Now generated with --dry-run, remote md5 verified, then launched.
- Server A: TP=4 GPUs 4-7 :8001 (up 14:13), Server B: TP=2 GPUs 2,3 :8002 (up 14:29) — both
  thinking off / temp 0.7 top_p 0.8 top_k 20 / max_new_tokens 1024. Verified on both: chat with
  client max_tokens=4096 → 1024 `length`; Responses without cap → 1024 `incomplete`; effort=none
  renders 26 input tokens = chat default (thinking off), effort=low 54.
- Smokes via run_cell.sh (3 steps, 0306): prolong×codex `codex_sandboxed: true`, vision audit
  source found; default×vllm OK.
- dz (14:00): use the remaining a227 cards for serving and raise scene concurrency → two
  servers, scenes alternate between them (both arms per server), CONC=8.
- 14:30:57 launched `scripts/launch_4hop.sh` (setsid nohup; log outputs/log-c4h-launcher.txt);
  cell logs outputs/log-c4h-<agent>-<channel>-<scene>.txt; results
  outputs/c4h-*/Qwen3.8-27B/4-hop/<scene>/result.json. Relaunching the script resumes.
