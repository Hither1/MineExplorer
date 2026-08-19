# The strict 4-hop campaign on helixon (2026-08-18/19)

Four arms — `default × vllm`, `hypothesis × vllm`, `prolong × codex`, `default × codex` —
on the seven scenes that survive every screen in `scripts/screen_scenes.py --hops 4
--reachable --min-depth 4 --max-free 0 --no-backwards`. Qwen3.8-27B, thinking off on both
channels, temperature 0.7 (top_p 0.8, top_k 20 server default), output cap 1024 on both
channels (server `max_new_tokens`), 300 steps, hint protocol (`--milestone-hint`,
premature ESC refused), **one seed per cell**. `scripts/launch_4hop.sh`; cells under
`outputs/c4h-<agent>-<channel>-<scene>/`, logs `outputs/log-c4h-*.txt`, table by
`python scripts/summarize_4hop.py`.

Two waves. **Wave 1** (08-18 14:31–17:11): `default × vllm` and `prolong × codex`, on two
differently sized uncached servers (A = TP=4 GPUs 4–7 :8001, B = TP=2 GPUs 2,3 :8002),
scenes alternating between them. **Wave 2** (08-19 00:03–07:42, added at dz's request):
`hypothesis × vllm` and `default × codex`, on three identical TP=2 servers with prefix
caching (:8001 GPUs 2,3, :8002 GPUs 4,5, :8003 GPUs 6,7), cells dealt round-robin. Same
agents, same prompts, same generation config, same cap; the serving layout differs
between waves (prefix caching moves greedy output at the paraphrase level — qwen35-serve
README), which is one more reason not to read small gaps as differences.

This is one seed per cell. It is a run, not a claim; the earlier five-seed 0306 runs
(`outputs/s0306-*`) spread 2/4–4/4 for PRO-LONG and 3/4–4/4 for the default arm on one
scene, which is the scale of the noise here.

Three of these four arms were repeated on the **Qwen3.5-27B** checkpoint on 2026-08-19,
same scenes and same contract — see
[RESULTS_helixon_4hop_qwen35.md](RESULTS_helixon_4hop_qwen35.md). The ordering below
survives the checkpoint change.

## What ran, exactly

| | default × vllm | hypothesis × vllm | prolong × codex | default × codex |
|---|---|---|---|---|
| agent | 20-frame buffer, thought/action/memory | + an explicit hypothesis DAG and a short plan, both rendered into the prompt and updated from the reply (advisory: it never overrides the chosen action) | append-only `logs.txt`, one analyzer turn plans many steps | same agent as column 1, driven through the Codex CLI |
| model channel | `VLLMProvider` → `/v1/chat/completions` | same | Codex CLI 0.147.0 → `/v1/responses`, `codex exec resume` per turn | Codex CLI 0.147.0 → `/v1/responses`, a fresh `codex exec` per step (stateless, like the other providers) |
| thinking | server `--default-chat-template-kwargs '{"enable_thinking":false}'` | same | `CODEX_LOCAL_EFFORT=none` (renders the same closed `<think></think>`; wire-verified: 26 input tokens either way vs 54 with `low`) | same |
| sampling | temp 0.7 sent by the client; top_p 0.8 / top_k 20 server default | same | server default temp 0.7 / top_p 0.8 / top_k 20 (codex sends none) | same |
| output cap | server `max_new_tokens 1024` (client's 4096 is min'ed) | same | server `max_new_tokens 1024` (codex sends no cap) | same |
| per-call ceiling | none (a vLLM call answers in seconds) | none | `CODEX_TIMEOUT=900` — never reached | **`CODEX_TIMEOUT=120`**, one ceiling then a no-op; this is a policy choice, see below |
| sandbox | n/a | n/a | `prolong_mc/codex_sandbox.sh` (bwrap: workspace-only reads, per-episode CODEX_HOME with an empty skills marker, egress allowlist = the model server); `codex_sandboxed: true` in every result | same wrapper, one home per cell (`outputs/<tag>/codex_home`); `codex_sandboxed: true` in every result |
| context | the baseline prompt + 20 frames | + DAG and plan sections | codex base instructions (20.7k chars) + codex's own skills boilerplate (3.5k chars) + PRO-LONG AGENTS.md (5.8k chars); **no** personal AGENTS.md/skills (the morning's runs had them, see below) | codex base instructions + skills boilerplate + the baseline prompt as the user message |
| frames | 20 per step, 640×360 | same | 1 per analyzer turn (the current view), verified in every rollout: images == turns, 0 attach failures | 20 per step, written to the call's temp workspace and attached with `-i` |

Servers on a227, all from `qwen35-serve/scripts/serve.sh` with the same generation
config. Wave 1: A = TP=4 on GPUs 4–7 (:8001), B = TP=2 on GPUs 2,3 (:8002), no prefix
caching; scenes alternate (0306, 0182, 0482, 0763 on A; 0726, 0311, 0603 on B) so each
server carries both arms of its scenes. Wave 2: three TP=2 servers with
`--enable-prefix-caching` (:8001 GPUs 2,3, :8002 GPUs 4,5, :8003 GPUs 6,7), cells dealt
round-robin (`default × codex`: 0306/0311/0763 → :8003, 0726/0482 → :8002, 0182/0603 →
:8001). Concurrency 8 (wave 1) and 7+7 (wave 2); the podman sandbox on a230 carried 14
concurrent Minecraft sessions without one `env.step` failure or one `Agent call failed`
in any of the 28 cells.

## Results

| scene | default × vllm | hypothesis × vllm | prolong × codex | default × codex |
|---|---|---|---|---|
| 0182 | **2/4** | **2/4** | 0/4 | 1/4 |
| 0306 | **4/4** (136, ESC) | **4/4** (107, ESC) | **4/4** (frame 52, ran to 300) | 3/4 |
| 0311 | **1/4** | 0/4 | 0/4 | 0/4 |
| 0482 | 1/4 | 1/4 | 1/4 | 1/4 |
| 0603 | 0/4 | 1/4 | 1/4 | 1/4 |
| 0726 | 0/4 | 0/4 | **4/4** (159, ESC) | 1/4 |
| 0763 | 2/4 | 2/4 | 2/4 | 2/4 |
| **milestones** | **10/28** | **10/28** | **12/28** | **9/28** |
| scenes fully done | 1 | 1 | 2 | 0 |

Every cell ran the full 300 steps except the three that pressed ESC after the environment
verified the task (0306 default×vllm at 136 and hypothesis×vllm at 107; 0726 prolong×codex
at 159).

Cost, per arm, all seven scenes:

| | default × vllm | hypothesis × vllm | prolong × codex | default × codex |
|---|---|---|---|---|
| cell-time | 10.8 h (42–152 min) | 9.3 h (31–93 min) | 3.8 h (13–67 min) | 44.6 h (354–423 min) |
| model calls the runner made | 1949 | 1941 | 176 analyzer turns | 2266 codex calls (300 steps + 166 JSON retries) |
| requests on the wire | 1949 | 1941 | 524 | 30,987 |
| input tokens | ~7 M | ~7 M | 12.0 M | **541 M** (85–90% prefix-cache hits) |

Per-cell rows, with the frame each milestone was first satisfied (−1 = never), the wall
clock, the server, and — for the codex arms — codex's own request/token accounting and
`view_image` count:

| scene | arm | ms | steps | end | frames | wall | server | calls | ceil | reqs | views | tok_in | tok_out | sandboxed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0182 | defaultxcodex | 1/4 | 300 | max_steps | 52,-1,-1,-1 | 423m | 8001 | 341 | 129 | 4988 | 1676 | 86671038 | 713774 | True |
| 0182 | defaultxvllm | 2/4 | 300 | max_steps | 7,112,-1,-1 | 152m | 8001 | 302 | 0 | 0 | 0 | 0 | 0 | - |
| 0182 | hypothesisxvllm | 2/4 | 300 | max_steps | 8,38,-1,-1 | 93m | 8003 | 309 | 0 | 0 | 0 | 0 | 0 | - |
| 0182 | prolongxcodex | 0/4 | 300 | max_steps | -1,-1,-1,-1 | 67m | 8001 | 31 | 0 | 94 | 1 | 2263137 | 7022 | True |
| 0306 | defaultxcodex | 3/4 | 300 | max_steps | 10,33,-1,82 | 374m | 8003 | 311 | 93 | 3710 | 509 | 63378232 | 596966 | True |
| 0306 | defaultxvllm | 4/4 | 136 | agent_esc | 10,41,57,135 | 107m | 8001 | 137 | 0 | 0 | 0 | 0 | 0 | - |
| 0306 | hypothesisxvllm | 4/4 | 107 | agent_esc | 7,15,46,106 | 31m | 8001 | 107 | 0 | 0 | 0 | 0 | 0 | - |
| 0306 | prolongxcodex | 4/4 | 300 | max_steps | 6,14,20,52 | 38m | 8001 | 26 | 0 | 75 | 0 | 1528932 | 4126 | True |
| 0311 | defaultxcodex | 0/4 | 300 | max_steps | -1,-1,-1,-1 | 354m | 8003 | 312 | 95 | 4516 | 1440 | 78538473 | 524186 | True |
| 0311 | defaultxvllm | 1/4 | 300 | max_steps | 31,-1,-1,-1 | 52m | 8002 | 301 | 0 | 0 | 0 | 0 | 0 | - |
| 0311 | hypothesisxvllm | 0/4 | 300 | max_steps | -1,-1,-1,-1 | 86m | 8001 | 304 | 0 | 0 | 0 | 0 | 0 | - |
| 0311 | prolongxcodex | 0/4 | 300 | max_steps | -1,-1,-1,-1 | 13m | 8002 | 16 | 0 | 49 | 0 | 983696 | 4116 | True |
| 0482 | defaultxcodex | 1/4 | 300 | max_steps | 55,-1,-1,-1 | 381m | 8002 | 327 | 113 | 4838 | 1513 | 86181324 | 625044 | True |
| 0482 | defaultxvllm | 1/4 | 300 | max_steps | 66,-1,-1,-1 | 138m | 8001 | 303 | 0 | 0 | 0 | 0 | 0 | - |
| 0482 | hypothesisxvllm | 1/4 | 300 | max_steps | 27,-1,-1,-1 | 90m | 8002 | 304 | 0 | 0 | 0 | 0 | 0 | - |
| 0482 | prolongxcodex | 1/4 | 300 | max_steps | 37,-1,-1,-1 | 48m | 8001 | 18 | 0 | 55 | 0 | 1171655 | 4694 | True |
| 0603 | defaultxcodex | 1/4 | 300 | max_steps | -1,-1,273,-1 | 378m | 8001 | 331 | 112 | 5025 | 1632 | 88157578 | 614317 | True |
| 0603 | defaultxvllm | 0/4 | 300 | max_steps | -1,-1,-1,-1 | 42m | 8002 | 302 | 0 | 0 | 0 | 0 | 0 | - |
| 0603 | hypothesisxvllm | 1/4 | 300 | max_steps | -1,-1,264,-1 | 76m | 8003 | 300 | 0 | 0 | 0 | 0 | 0 | - |
| 0603 | prolongxcodex | 1/4 | 300 | max_steps | 38,-1,-1,-1 | 19m | 8002 | 33 | 0 | 97 | 0 | 2447481 | 6061 | True |
| 0726 | defaultxcodex | 1/4 | 300 | max_steps | 27,-1,-1,-1 | 409m | 8002 | 332 | 112 | 4077 | 526 | 72912153 | 720736 | True |
| 0726 | defaultxvllm | 0/4 | 300 | max_steps | -1,-1,-1,-1 | 56m | 8002 | 304 | 0 | 0 | 0 | 0 | 0 | - |
| 0726 | hypothesisxvllm | 0/4 | 300 | max_steps | -1,-1,-1,-1 | 88m | 8002 | 306 | 0 | 0 | 0 | 0 | 0 | - |
| 0726 | prolongxcodex | 4/4 | 159 | agent_esc | 12,63,157,81 | 22m | 8002 | 32 | 0 | 96 | 0 | 2458128 | 8441 | True |
| 0763 | defaultxcodex | 2/4 | 300 | max_steps | 2,146,-1,-1 | 359m | 8003 | 312 | 94 | 3833 | 758 | 65051270 | 554021 | True |
| 0763 | defaultxvllm | 2/4 | 300 | max_steps | 1,51,-1,-1 | 103m | 8001 | 300 | 0 | 0 | 0 | 0 | 0 | - |
| 0763 | hypothesisxvllm | 2/4 | 300 | max_steps | 3,234,-1,-1 | 92m | 8001 | 311 | 0 | 0 | 0 | 0 | 0 | - |
| 0763 | prolongxcodex | 2/4 | 300 | max_steps | 1,27,-1,-1 | 23m | 8001 | 20 | 0 | 58 | 0 | 1101336 | 3906 | True |
defaultxcodex: 7 scenes, milestones 9/28, all-done scenes 0
defaultxvllm: 7 scenes, milestones 10/28, all-done scenes 1
hypothesisxvllm: 7 scenes, milestones 10/28, all-done scenes 1
prolongxcodex: 7 scenes, milestones 12/28, all-done scenes 2

`ms` = milestones completed / trackable; `calls` = calls the runner made (vllm: one per
step; codex: analyzer turns for PRO-LONG, one per step plus JSON retries for
default×codex); `ceil` = calls that ended at the per-call ceiling; `reqs`/`views`/`tok_*`
= codex's own accounting from the rollouts.

## Caveats that belong next to any number above

- **One seed.** Fixed up front (memory `fix-seed-count-up-front`); nothing here separates
  arm from seed. The morning's five 0306 PRO-LONG seeds ran 2/4, 4/4, 3/4, 4/4, 4/4.
- **0311's ceiling is 2/4 for every arm.** `hunt_rabbit`/`hunt_donkey` are
  `count_in_box_at_most` and were already satisfied at spawn (all four cells log "already
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
- **Servers differ between the waves and, in wave 1, between scenes.** Wave 1's two cells
  of a scene shared a server (TP=4 or TP=2, uncached); wave 2's cells were dealt
  round-robin across three identical prefix-cached TP=2 servers. Prefix caching changes
  greedy output at the paraphrase level, so wave-2 numbers are not bit-comparable with
  wave-1 numbers — at n=1 that is well inside the noise, but it is a second reason the
  arms are not perfectly matched.
- **Wave 2's wall clocks are honest, wave 1's are not.** In wave 2 no server was ever
  backed up (2–3 running requests, KV cache 3–4%, no queue), so a cell's wall clock is
  its own cost; wave 1's are the schedule (below).
- **The morning's `outputs/s0306-*` runs are a different arm** and must not be pooled
  with these: they ran through the `codex` wrapper on PATH, which put the user's global
  AGENTS.md (9.3k chars) and ~40 personal skills (11k chars) into every codex request and
  left the whole filesystem readable (`codex_sandboxed: false`), and their vLLM cap was
  4096 (never binding: longest reply 2726 chars). Fixed in 33be080.
- **`default × codex`'s score is a ceiling policy as much as an agent.** With thinking
  off, the model treats each call as an agentic session: it `ls`-es the temp workspace,
  calls `view_image` on the frames it was already given (median 0–3 times on calls that
  answer, up to 50 on calls that do not) and writes PIL crops "to read the debug info in
  the corner". A pre-campaign probe (08-18 23:57, 7 parallel calls at 4/8/12/16/20 frames,
  240 s ceiling) had 5 of 7 calls still looping at 240 s; the two that answered took 67 s
  and 193 s. The arm was therefore run with a **120 s per-call ceiling and no retry**
  (one ceiling → the runner's no-op action, as for any failed call). Outcome over all
  2266 calls: **59.7% valid JSON, 33.0% ceiling, 4.5% degenerate (the reply is a run of
  `!!!!!!`), 2.1% other prose, 0.7% empty** — so roughly a third of this arm's steps did
  nothing, and its 9/28 is a lower bound under that policy. A higher ceiling would raise
  it at ~1 h per 100 s of ceiling per scene; it would not fix the loop.
- **The two codex arms could not read the answers.** Across 23,326 shell calls in this
  campaign's codex rollouts, 47 named a repository path outside the episode workspace;
  every one returned only the bind-mount skeleton (`MineExplorer/` shows `outputs` and
  `prolong_mc` and nothing else). Scanning every rollout line of both campaigns (132,468
  lines, 2,280 sessions), none names a `bench_*` path, the scene metadata or the checker —
  the one apparent hit is a `find`-style listing of GNOME extensions' own `metadata.json`
  under `/usr/share`. No `SandboxViolation` (web_search / MCP / subagents) in any cell.
- **PRO-LONG rarely ends its own episode.** 0306 reached 4/4 at frame 52 and ran to
  300; only 0726 pressed ESC (at 159). Under the hint protocol the [MILESTONE] line does
  say the task is verified; the analyzer just keeps planning. Cost, not score. The two
  direct-vLLM arms did press ESC on 0306 (136 and 107).
- **The hypothesis DAG was maintained, not decorative**: 26–75 nodes per episode with
  evidence lists and a live 3-step plan (`hypothesis_graph.json`, `hypothesis_plan.json`
  in each cell). It changed nothing in the score at n=1.
- **view_image**: the analyzer chose to look at an earlier frame once in 0182 and never
  otherwise (rollout counts; `scan_rollout` now counts the direct `function_call` shape,
  which the first version missed).

## Cost, for planning the next round

Per scene, this configuration: `default × vllm` ≈ 300 requests × 3.5k input tokens (1.1M),
40–65 min alone on a server; `hypothesis × vllm` the same plus the DAG sections, 31–93 min
at 7 cells over 3 servers; `prolong × codex` ≈ 16–33 turns, 49–97 requests, 1.0–2.5M input
tokens, 13–67 min; `default × codex` ≈ 300 steps × ~10 requests, 63–88M input tokens,
**6–7 h**. Wave 2's 14 cells took 7h40 wall clock end to end, and `default × codex` alone
accounted for all but the first 100 minutes of it.

For a next round: three TP=2 prefix-cached servers carried 14 concurrent cells with no
queueing, so the direct-vLLM arms are cheap enough to seed properly — **7 scenes × 5 seeds
of `default × vllm` + `prolong × codex` is about 10 h wall** on this hardware, and that is
the experiment that would actually separate the agents. `default × codex` is not worth
repeating at this ceiling; if the arm matters, it needs a codex-side fix (a tool policy
that forbids `view_image` on frames already attached), not more compute.

## Files

- wave-1 fixes: 33be080 (find_rollout, sandbox in run_cell.sh, `-i` before `-m`,
  process-group kill on timeout, screen_scenes --no-backwards), c404390 (launcher),
  9375375 (summarizer), 16d0898 (results + the view_image counting fix)
- wave-2 harness: 9210527 (one ceiling then a no-op instead of three retries; per-cell
  codex home for the provider path; ARMS × servers launcher; ceiling/view columns)
- serving: wave 1 `qwen35-serve/run/qwen-serve-qwen3-8-27b.sh` (A) and `run/qwen38-b.sh`
  (B); wave 2 `run/qwen38-s{1,2,3}.sh` (tmux `qwen38-s1/s2/s3` on a227). The first
  relaunch in wave 1 ran a stale run file (NFS view lagged the write) — verify the remote
  md5 before `tmux new-session`, or use `--dry-run` first
- task records: `tasks/archive/2026-08/codex-qwen35-27b-minecraft-0313-0544.prolong-vs-default-4hop-helixon/`
  (wave 1), `tasks/codex-qwen35-27b-minecraft-0313-0544.arms34-4hop-helixon/` (wave 2)
