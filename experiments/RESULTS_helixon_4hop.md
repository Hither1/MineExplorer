# The strict 4-hop campaign on helixon (2026-08-18)

PRO-LONG (`--agent-mode prolong`, codex channel, sandboxed) against the default
20-frame-buffer agent (direct vLLM channel) on the seven scenes that survive every
screen in `scripts/screen_scenes.py --hops 4 --reachable --min-depth 4 --max-free 0
--no-backwards`. Qwen3.8-27B, thinking off on both channels, temperature 0.7 (top_p 0.8,
top_k 20 server default), output cap 1024 on both channels (server `max_new_tokens`),
300 steps, hint protocol (`--milestone-hint`, premature ESC refused), **one seed per
cell**. Launched 14:31, finished 17:11; `scripts/launch_4hop.sh`; cells under
`outputs/c4h-<agent>-<channel>-<scene>/`, logs `outputs/log-c4h-*.txt`, table by
`python scripts/summarize_4hop.py`.

This is one seed per cell. It is a run, not a claim; the earlier five-seed 0306 runs of
the same morning (`outputs/s0306-*`) spread 2/4–4/4 for PRO-LONG and 3/4–4/4 for the
default arm on one scene, which is the scale of the noise here.

## What ran, exactly

| | default × vllm | prolong × codex |
|---|---|---|
| model channel | `VLLMProvider` → `/v1/chat/completions` | Codex CLI 0.147.0 → `/v1/responses`, `codex exec resume` per turn |
| thinking | server `--default-chat-template-kwargs '{"enable_thinking":false}'` | `CODEX_LOCAL_EFFORT=none` (renders the same closed `<think></think>`; wire-verified: 26 input tokens either way vs 54 with `low`) |
| sampling | temp 0.7 sent by the client; top_p 0.8 / top_k 20 server default | server default temp 0.7 / top_p 0.8 / top_k 20 (codex sends none) |
| output cap | server `max_new_tokens 1024` (client's 4096 is min'ed) | server `max_new_tokens 1024` (codex sends no cap) |
| sandbox | n/a | `prolong_mc/codex_sandbox.sh` (bwrap: workspace-only reads, per-episode CODEX_HOME with an empty skills marker, egress allowlist = the model server); `codex_sandboxed: true` in every result |
| context | the baseline prompt + 20 frames | codex base instructions (20.7k chars) + codex's own skills boilerplate (3.5k chars) + PRO-LONG AGENTS.md (5.8k chars); **no** personal AGENTS.md/skills (the morning's runs had them, see below) |
| frames | 20 per step, 640×360 | 1 per analyzer turn (the current view), verified in every rollout: images == turns, 0 attach failures |

Servers on a227, both `qwen35-serve/scripts/serve.sh` with the same generation config:
A = TP=4 on GPUs 4–7 (:8001), B = TP=2 on GPUs 2,3 (:8002). Scenes alternate: 0306,
0182, 0482, 0763 on A; 0726, 0311, 0603 on B — each server carries both arms of its
scenes, so no arm is confounded with a server. Concurrency 8 cells; sandbox on a230
(podman) handled 8 concurrent sessions without an `env.step` failure.

## Results

| scene | arm | ms | steps | end | frames | wall | server | calls | reqs | tok_in | tok_out | sandboxed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0182 | defaultxvllm | 2/4 | 300 | max_steps | 7,112,-1,-1 | 152m | 8001 | 302 | 0 | 0 | 0 | - |
| 0182 | prolongxcodex | 0/4 | 300 | max_steps | -1,-1,-1,-1 | 67m | 8001 | 31 | 94 | 2263137 | 7022 | True |
| 0306 | defaultxvllm | 4/4 | 136 | agent_esc | 10,41,57,135 | 107m | 8001 | 137 | 0 | 0 | 0 | - |
| 0306 | prolongxcodex | 4/4 | 300 | max_steps | 6,14,20,52 | 38m | 8001 | 26 | 75 | 1528932 | 4126 | True |
| 0311 | defaultxvllm | 1/4 | 300 | max_steps | 31,-1,-1,-1 | 52m | 8002 | 301 | 0 | 0 | 0 | - |
| 0311 | prolongxcodex | 0/4 | 300 | max_steps | -1,-1,-1,-1 | 13m | 8002 | 16 | 49 | 983696 | 4116 | True |
| 0482 | defaultxvllm | 1/4 | 300 | max_steps | 66,-1,-1,-1 | 138m | 8001 | 303 | 0 | 0 | 0 | - |
| 0482 | prolongxcodex | 1/4 | 300 | max_steps | 37,-1,-1,-1 | 48m | 8001 | 18 | 55 | 1171655 | 4694 | True |
| 0603 | defaultxvllm | 0/4 | 300 | max_steps | -1,-1,-1,-1 | 42m | 8002 | 302 | 0 | 0 | 0 | - |
| 0603 | prolongxcodex | 1/4 | 300 | max_steps | 38,-1,-1,-1 | 19m | 8002 | 33 | 97 | 2447481 | 6061 | True |
| 0726 | defaultxvllm | 0/4 | 300 | max_steps | -1,-1,-1,-1 | 56m | 8002 | 304 | 0 | 0 | 0 | - |
| 0726 | prolongxcodex | 4/4 | 159 | agent_esc | 12,63,157,81 | 22m | 8002 | 32 | 96 | 2458128 | 8441 | True |
| 0763 | defaultxvllm | 2/4 | 300 | max_steps | 1,51,-1,-1 | 103m | 8001 | 300 | 0 | 0 | 0 | - |
| 0763 | prolongxcodex | 2/4 | 300 | max_steps | 1,27,-1,-1 | 23m | 8001 | 20 | 58 | 1101336 | 3906 | True |

`ms` = milestones completed / trackable; `frames` = the step each milestone was first
satisfied, in task order (−1 = never); `calls` = model calls the runner made (vllm: one per
step; codex: analyzer turns); `reqs`/`tok_*` = codex's own request and token accounting
from the rollout (each turn is a tool loop of ~3 requests re-sending the conversation).

| | default × vllm | prolong × codex |
|---|---|---|
| milestones | **10/28** | **12/28** |
| scenes fully done | 1 (0306) | 2 (0306, 0726) |
| scenes won / tied / lost | 2 (0182, 0311) / 3 / 2 | 2 (0603, 0726) / 3 / 2 |
| wall clock, all 7 scenes | 10.8 h cell-time (42–152 min each) | 3.8 h cell-time (13–67 min each) |
| model requests, all 7 | 1949 (one per step) | 176 analyzer turns = 524 requests |

Read: 12 vs 10 milestones out of 28, both arms solving 0306 outright and only PRO-LONG
solving 0726, only the default arm getting anything on 0182 and 0311. Same total on
0482 and 0763. With one seed and a spread of ±1 milestone per scene seen on the
morning's 0306 seeds, this is not a difference; it is the sample the next design has to
be sized against.

Where the two arms did the same thing they did it at very different cost: PRO-LONG's
scenes took 13–67 min and 49–97 model requests; the default arm's 42–152 min and ~300
requests. The wall clocks are not comparable across servers or across the campaign
(below), but the request counts are what they are.

## Caveats that belong next to any number above

- **One seed.** Fixed up front (memory `fix-seed-count-up-front`); nothing here separates
  arm from seed. The morning's five 0306 PRO-LONG seeds ran 2/4, 4/4, 3/4, 4/4, 4/4.
- **0311's ceiling is 2/4 for both arms.** `hunt_rabbit`/`hunt_donkey` are
  `count_in_box_at_most` and were already satisfied at spawn (both cells log "already
  satisfied at spawn"), so the runner excludes them. `screen_scenes.satisfied_at_spawn`
  only knows position rules; a static screen cannot see this.
- **Wall clocks are contention, not the arms.** Server A (TP=4 over PCIe) was prefill-bound
  while two prolong cells re-sent 10–45k-token uncached conversations three times a turn:
  its vllm cells ran at 0.4–1.5 steps/min (model latency median 70–80 s, max 211 s) until
  the prolong cells finished, then 17–25 s/step; server B's vllm cells ran at 6–9 s/step
  throughout. No client timeout fired (`Agent call failed` = 0 in every log), so no step
  was lost, but the "wall" column measures the schedule. Next time: `--prefix-cache` on
  the server (5–8× less prolong prefill; changes numerics, see qwen35-serve README) and
  never two prolong cells on one server; TP=4 on PCIe A100s bought nothing.
- **Servers differ in TP (4 vs 2), so numerics differ across scenes**, not across arms:
  each scene's two cells ran against the same server.
- **The morning's `outputs/s0306-*` runs are a different arm** and must not be pooled
  with these: they ran through the `codex` wrapper on PATH, which put the user's global
  AGENTS.md (9.3k chars) and ~40 personal skills (11k chars) into every codex request and
  left the whole filesystem readable (`codex_sandboxed: false`), and their vLLM cap was
  4096 (never binding: longest reply 2726 chars). Fixed in 33be080.
- **default × codex was not run.** With thinking off the model loops `view_image`/PIL on
  the attached frames at the 20-frame steady state (69 requests in 420 s in the probe,
  then a timeout no-op); dz dropped the arm.
- **PRO-LONG rarely ends its own episode.** 0306 reached 4/4 at frame 52 and ran to
  300; only 0726 pressed ESC (at 159). Under the hint protocol the [MILESTONE] line does
  say the task is verified; the analyzer just keeps planning. Cost, not score.
- **view_image**: the analyzer chose to look at an earlier frame once in 0182 and never
  otherwise (rollout counts; `scan_rollout` now counts the direct `function_call` shape,
  which the first version missed).

## Cost, for planning the next round

Per scene, this configuration: default × vllm ≈ 300 requests × 3.5k input tokens
(1.1M) and 40–65 min alone on a server (5–10 s/step) — 100–150 min when it shares a
server with PRO-LONG; prolong × codex ≈ 16–33 turns, 49–97 requests, 1.0–2.5M input
tokens, 13–67 min. Two arms × 7 scenes finished in 2h40 wall with 8 concurrent cells on
two servers; with prefix caching and one prolong cell per server at a time this should
be nearer 1h30.

## Files

- fixes: 33be080 (find_rollout, sandbox in run_cell.sh, `-i` before `-m`, process-group
  kill on timeout, screen_scenes --no-backwards), c404390 (launcher), 9375375 (summarizer)
- serving: `qwen35-serve/run/qwen-serve-qwen3-8-27b.sh` (A), `run/qwen38-b.sh` (B); the
  first relaunch of A ran a stale run file (NFS view lagged the write) — verify remote
  md5 before `tmux new-session`, or use `--dry-run` first
- task record: `tasks/codex-qwen35-27b-minecraft-0313-0544.prolong-vs-default-4hop-helixon/`
