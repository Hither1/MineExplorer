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

## 2026-08-18 15:05 — server A (TP=4) is prefill-bound; vllm cells on it crawl

- A (:8001, TP=4 GPUs 4-7) with 2-3 prolong cells + 3 vllm cells: prompt ~2.9k tok/s, generation
  1.8-33 tok/s aggregate, GPUs 100% util at 130-200 W (PCIe-bound). Each 8192-token prefill chunk
  takes ~2.9 s per engine step, so decoding requests advance one token per chunk: vllm cells on A
  see model latency median 70-80 s (max 211 s) vs 6-9 s on B (:8002, TP=2, lightly loaded).
- No `Agent call failed` yet (client timeout 120 s x up to 3 OpenAI retries); the monitor watches.
- Decision: no server change mid-campaign (a restart burns steps of every running cell as
  agent-call retries); accept ~17:30 finish. Lesson for next time: TP=4 on PCIe A100s buys
  nothing here; the lever is `--prefix-cache` (5-8x less prolong prefill) plus keeping prolong
  and vllm cells on separate servers.

## 2026-08-18 17:11 — campaign complete

- 14/14 cells finished (14:31-17:11), all clean: `Agent call failed`=0, `env.step failed`=0,
  every prolong rollout: images==turns, 0 attach failures, 0 compactions, no global instructions,
  no outside-workspace reads, `codex_sandboxed: true`.
- Milestones: default×vllm 10/28 (0306 fully), prolong×codex 12/28 (0306, 0726 fully); per-scene
  2 wins / 3 ties / 2 losses each way. One seed — a run, not a claim.
- Server A (TP=4) was prefill-bound while it hosted 2 prolong cells; wall clocks reflect scheduling.
- Written up in experiments/RESULTS_helixon_4hop.md; scan_rollout fixed to count direct
  view_image function_calls (audits refreshed).
