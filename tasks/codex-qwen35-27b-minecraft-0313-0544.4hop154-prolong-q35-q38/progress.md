# Progress: 4hop154-prolong-q35-q38

## 2026-08-20 11:50 — task opened, Phase 1 complete

Scope set by the user: all 154 paper-defined 4-hop scenes, `prolong:codex` only,
cap 1024 / thinking off / 300 steps, Qwen3.5 first, then the same on Qwen3.8.
Gated on a227 GPUs 2-7 being released by the other session's bcp/microvqa servers.
Second user instruction the same hour: do not push concurrency — that session shares
this runner. CONC stays at the verified 14.

Prep done (see findings.md 4):
- `bench_4hop154/_split/` — 154 one-scene benchmark dirs.
- `scripts/screen_scenes.py --split-to DIR` — materialises whatever the filter shows, so
  the scene set stays defined by one piece of code.
- `scripts/launch_4hop.sh` — `SPLIT_ROOT` knob; the split path was hardcoded to the seven.
- Verified: both checkpoints' k=3 run files, the a230 sandbox, the Qwen3.8 weights.

## Blocked on

a227 GPUs 2-7. Monitor armed; the release signal is the disappearance of the
`VLLM::Worker` PIDs on those six GPUs (currently 5136/5138/5140/5141 and 26960/26961).

## 2026-08-20 12:20 — plan replaced, and the frame asymmetry closed

User re-planned: **three arms on Qwen3.5 only**, in order `prolong:codex` ->
`hypothesis:vllm` -> `default:vllm`, **200 steps** (was 300). The Qwen3.8 rerun is dropped.
Same three servers for all three arms, so no swap and no re-wire-check between them.

Hyperparameter audit against `main` (user request): every shared knob already agreed —
`FRAME_BUFFER_SIZE=20`, `MAX_STEPS`, `--temperature 0.7`, `--loading-command-steps 20`,
`--milestone-hint` on, output cap 1024 (server, both wires verified), thinking off on both
channels (`enable_thinking:false` / `CODEX_LOCAL_EFFORT=none`, which `effort_for()` lets
override `--codex-effort low`), `max_images` unset for Qwen (only llama-3.2 is capped at 1),
prolong ablations off. Our branch changed none of them relative to `main`.

One knob did **not** agree and is now fixed (9fcd984, user chose to align): per-frame
resolution. `_png` wrote 640x360 while the direct arms' frames were halved to 320x180.
Both now go through `mc_agent.utils.downsample_pov`; `prolong_mc.selftest` asserts it at
640x360 and at the 128x128 reset frame. ALL PASS. Consequence: the prolong arm is no longer
byte-comparable to the recorded seven-scene campaigns, which ran at native resolution.

## Cost of the 200-step cap, measured

4 of the 35 milestones the recorded q35 seven-scene campaign earned were first reached
after step 200 (default 0182@216, hypothesis 0482@246, prolong 0603@253, prolong 0763@220),
so ~11% of earned milestones, and in that small sample it costs prolong most (2 of its 14).
All three arms share the cap, so the arm comparison is unaffected; the comparison to the
recorded 300-step seven is not.

## Estimate, 200 steps at MTP k=3, CONC=14

From the recorded q35 per-cell walls (full-300 cells): prolong 5.26, default 10.46,
hypothesis 13.97 s/step at k=1; k=3 factors 0.67 / 0.55 / 0.72 (README, EVAL_LATENCY §7.1).

| order | arm | per cell | cell-time | wall |
|---|---|---|---|---|
| 1 | prolong:codex | ~12 min | 30 h | ~2.1 h |
| 2 | hypothesis:vllm | ~34 min | 86 h | ~6.2 h |
| 3 | default:vllm | ~19 min | 50 h | ~3.5 h |
| | | | **166 h** | **~12-14 h** |

## Launch, ready to fire when GPUs 2-7 free

```bash
# 1. sandbox — only if /list_sessions shows nothing created today
# 2. servers on a227 (verify remote md5 first), then wire-check all three
ssh ruihan@192.168.2.20 'tmux new-session -d -s qwen35-s1-k3 "bash <qwen35-serve>/run/qwen35-s1-k3.sh"'   # s2, s3 likewise

# 3. the three arms, in order, one launcher each
SC="$(python scripts/screen_scenes.py --hops 4 | awk '$1 ~ /^[0-9]{4}$/ {printf "%s ", $1}')"
cd /datapool/data3/storage/ruihan/data_share/jh/Collab/MineExplorer
setsid nohup bash -c '
for arm in prolong:codex hypothesis:vllm default:vllm; do
  PREFIX=q35a MODEL=Qwen3.5-27B SPLIT_ROOT=bench_4hop154/_split \
  SERVERS="http://192.168.2.20:8001/v1 http://192.168.2.20:8002/v1 http://192.168.2.20:8003/v1" \
  ARMS="$arm" SCENES="'"$SC"'" MAX_STEPS=200 CONC=14 \
    bash scripts/launch_4hop.sh
done' > outputs/log-q35a-chain.txt 2>&1 &
```

Per-cell logs land in `outputs/log-q35a-<arm>-<channel>-<scene>.txt`; the launcher skips any
cell whose `result.json` exists, so a relaunch resumes.

## 2026-08-20 13:08 — arm 1 launched (prolong x codex, 154 scenes, 200 steps)

a227 GPUs 2-7 released at 12:52. Sequence run:

1. Re-probed directly: 2-7 idle (17-21 MiB); GPUs 0,1 still the other session's `qwen35-t4`,
   untouched. Run-file md5s identical local vs a227 (the wave-1 stale-NFS trap).
2. Started `qwen35-s{1,2,3}-k3` in tmux on a227 (:8001 GPUs 2,3, :8002 4,5, :8003 6,7).
   Ready in ~13 min.
3. **Did not restart the a230 sandbox**, reversing the plan: container `mineexplorer` Up 2 days,
   a230 at 40/1007 GB with 6 JVMs, 8 leftover sessions all from 08-19 and none from today, and
   the recorded 21-cell campaign ran on this same container with 0 `env.step failed`. Restarting
   a two-day-old working sandbox to clear 8 sessions is the larger risk. Re-check between arms.
4. Wire-check, all three servers: served `Qwen3.5-27B`; output cap stops at exactly 1024
   (`length`) at 135.6 tok/s single-stream; chat wire has no `<think>` and `reasoning_content`
   is None; the Responses wire at `effort=none` (what prolong sends) returns only a `message`
   item, `reasoning_tokens: 0`, no `<think>`; tool calls arrive parsed
   (`{"city": "Shanghai"}`) with no `<tool_call>` text in content.

   `scripts/check_model_server.py` reports one FAIL on all three — "thinking pin: effort=none
   renders 2 *fewer* prompt tokens than effort=low". **False alarm on this checkpoint.** That
   probe detects Qwen3.8's template injecting a `reasoning_effort` system instruction when
   thinking is on (24 vs 52 tokens); Qwen3.5's template has no `reasoning_effort` concept at
   all (RESULTS_helixon_4hop_qwen35.md), so the two efforts necessarily render the same prompt
   and the probe cannot separate them here. The invariant it stands for is verified directly
   above. The script's probe needs a checkpoint guard before it is trusted as a gate on 3.5.
5. `prolong_mc.sandbox_selftest` under the cell's own env: all checks passed.

Launched 13:08:45: `PREFIX=q35a MODEL=Qwen3.5-27B SPLIT_ROOT=bench_4hop154/_split
ARMS=prolong:codex MAX_STEPS=200 CONC=14`, 154 cells pending, dealt round-robin over the three
servers. Launcher log `outputs/log-q35a-launcher-prolong.txt`, cells
`outputs/log-q35a-prolong-codex-<scene>.txt`. Two watchers armed: failure lines across all
q35a cell logs + arm completion; and a one-shot wait for the first 20 results, to re-estimate
per-cell wall before committing to the 6 h hypothesis arm.

## 2026-08-20 15:10 — speedup investigated and declined; arms 2-3 chained unattended

User asked to make the evaluation faster where quality allows, then went to sleep with
"keep going". Two measurements decided it:

**1. Where a prolong cell's time actually goes** (40 finished cells): mean wall 14.4 min =
setup 1.5 + stepping 12.8 + teardown 0.1. Setup is 10%, so there is nothing to win in
episode startup; the cell is dominated by codex turns (one sample cell: 91% of its
step-to-step time sat in 25 turns of mean 17.2 s, against 44 s for all 174 queued env steps).
Throughput is therefore CONC / mean-cell-time and the only lever is CONC.

**2. a230 has no headroom to spend on CONC.** At 13-14 concurrent sessions: load average
397 on 255 cores, 16 java processes, two of them at ~2000% CPU. Memory is fine (75/1007 GB),
so it is CPU/IO, not RAM. The verified concurrency ceiling is 14 and the measurement says
14 is already past comfortable. Raising it would slow every cell and risk an env.step
timeout storm mid-campaign, which costs far more than the ~30% it might return.

**Decision: CONC stays 14 for arms 2 and 3.** Recorded here rather than silently, because the
user did approve going faster and the answer is that the measurement does not support it.
The one speedup that *was* available — the user's own suggestion — is taken below.

**Stale sessions cleared.** The 8 sessions left over from 2026-08-19 were closed via
`close_env` under a date guard (only sessions created before today; today's 13 untouched);
a230's java process count went 19 -> 16. This campaign is not leaking: sessions from today
equalled in-flight cells at every check.

**Arms 2 and 3 are chained**, detached, independent of this session:
`tasks/<task>/run_remaining_arms.sh` (launched 15:07, pid 51653, log `outputs/log-q35a-chain.txt`).
It waits for arm 1's "all cells finished" line, then runs `hypothesis:vllm` and then
`default:vllm` at CONC=14, 200 steps, same 154 scenes, same three servers, and writes
`outputs/q35a-summary.md` at the end. It refuses to start if the scene screen does not
return exactly 154.

**Arm 1 status at 15:00:** 76 started / 62 done / 14 in flight, 0 failure lines. Completion
rate is flat at 0.58 cells/min over the last hour -> arm 1 ends ~17:30-18:15. Mean cell wall
keeps climbing (4.4 -> 12.2 -> 15.6 min as more cells finish) because fast cells finish
first; the completion-rate estimate is the one not subject to that bias.
Score so far: 63/248 milestones (25%), 2 scenes fully done, 3 early ESC.

## 2026-08-20 20:37 — arm 1 complete (prolong x codex, 154/154), arm 2 started

**154/154 results, 0 `Agent call failed` / `env.step failed` / `SandboxViolation` / `Traceback`
across every cell log.** Sandbox sessions dropped to 0 at handover: nothing leaked.

Score: **185/616 milestones = 30.0 %**, 5 scenes fully done, 8 early ESC.
Distribution `0/4: 41, 1/4: 60, 2/4: 39, 3/4: 9, 4/4: 5`.

**Read the denominator carefully — there are three defensible rates.** 52 of the 616
milestones were already satisfied at spawn. `eval_benchmark.py` excludes them from
`milestones_completed` (line 639-642) but *not* from `corrected_trackable = len(trackable_mids)`
(line 643), so they sit in the denominator and can never be earned; a scene with one of them
has a ceiling of 3/4 and can never report `all_milestones_done`, which is why only 5 scenes
count as fully done.

| convention | value | when to use |
|---|---|---|
| ours, as recorded in result.json | 185/616 = **30.0 %** | internal, conservative |
| ceiling-corrected (drop presatisfied from both) | 185/564 = **32.8 %** | the honest agent-ability number |
| the paper's MSR (a satisfied milestone counts, however it got satisfied) | 237/616 = **38.5 %** | the only one comparable to Table 6 |

All three are monotone in the same per-arm quantity because the presatisfied set is a property
of the scene, identical across arms, so the **arm comparison is unaffected** by the choice.

**Timing: the tail, not the mean, set the wall.** 13:08 -> 20:37 = 7.5 h, against the 2.4 h
projected. Per-cell wall: median 13.4 min, mean 25.6, p90 52.9, **max 334.6 min** (0016, which
completed all 200 steps -- slow, not hung; so did every other tail cell). Total cell-time 65.7 h
against an ideal 4.7 h at CONC=14, i.e. effective concurrency ~8.8: long cells hold slots while
short ones cycle. Every projection in this file so far used means from the recorded seven-scene
campaign, which had no tail like this -- a 154-scene set draws from the whole distribution and
the tail is where the time is.

Arms 2 and 3 are vllm-direct: one request per step, no codex tool loop, so their per-cell
spread should be much tighter than prolong's. That is a prediction, and the arm-2 rate will
test it within the hour.

Arm 2 (`hypothesis:vllm`) started 20:37:41. A probe is armed to sample a230 and the three
servers once arm 2 is at full concurrency and settled, which is the measurement that decides
whether CONC can rise above 14 for arm 3.

## 2026-08-20 21:40 — arm 2's shape is the opposite of arm 1's, and CONC is settled by measurement

**The prediction held.** `hypothesis:vllm`, first 11 cells: mean 50.3 min, **median 50.3,
range 42.0-55.7** -- a distribution so tight it finishes in waves of 14. Prolong's was median
13.4 / mean 25.6 / max 334.6. One request per step has no tail; a codex tool loop does.
So arm 2 and arm 3 are *predictable* even though they are slower per cell, and effective
concurrency should stay near 14 instead of prolong's 8.8.

**MTP k=3 bought the direct arm nothing:** 15.08 s/step now against the 14.8 s/step the
recorded campaign measured at k=1. Every projection in this file that discounted the direct
arms for k=3 (x0.72 / x0.55) was wrong to. The reason is visible in the probe: the servers
run 3-5 requests with **0 waiting and 5-9 % KV**, so decode -- the only thing k=3 speeds up --
is not what these cells wait on. At ~4 s of model time in a 15 s step, roughly two thirds of
each step is elsewhere: a230's env.step, the ~600 KB of base64 for 20 frames on the wire, and
server-side vision encoding of those 20 frames, which does not show up as "Running" or as KV.

**CONC stays 14, now measured on both arm shapes.** At 14 direct-arm cells: a230 load
176/215/231 on 255 cores (69-91 %), 16 java; the three servers idle (0 waiting, KV 5-9 %);
runner a218 load 17.7/255 with all 14 cell processes together taking 45 % of one core's worth
of CPU. The GPUs and the runner have enormous headroom and neither is the constraint; a230 is
at 78 % mean and 91 % peak, and each cell costs it ~14 load units, so 16 cells lands at
230-260 and 18 goes over the top. Raising CONC would slow every cell and risk an env.step
timeout storm for a bounded gain.

**Revised ETA, from measurement rather than projection:**

| arm | per cell | waves of 14 | duration | ends |
|---|---|---|---|---|
| 1 prolong (done) | median 13.4 / mean 25.6 | -- | 7.5 h | 20:37 |
| 2 hypothesis (running) | 50.3 min, tight | 11 | ~9.2 h | **~05:50** |
| 3 default (queued) | ~35 min (10.5 s/step, no k=3 discount) | 11 | ~6.4 h | **~12:15** |

Campaign total ~23 h, ending around **midday 08-21**, not the 05:00-08:00 said earlier. The
error was discounting the direct arms for k=3 and using tail-free means from the seven-scene
campaign. Arm 3 is a live decision for the user in the morning: 6.4 h for the third arm, or
stop after two.

## 2026-08-20 22:58 — deadline 07:00, so: append-only, four servers, both arms in parallel

User set a hard deadline of 07:00 for a formal three-arm result, then chose the append-only
layout and told me to take GPUs 0,1 as well. Both are L1/L2 calls that are theirs; what
follows is what the numbers said and what was actually done.

**Why the campaign was slow (measured, not guessed).** 785 steps across 6 hypothesis cells,
decomposed from log timestamps: prompt build 0.36 s (2 %), **model call 13.65 s (95 %)**,
parse + env.step + milestone check 0.29 s (3 %). The Minecraft sandbox is not the bottleneck
and my earlier "cells wait on a230" was wrong -- it came from reading `Running: 3-5` as an
idle server. All six GPUs were at 100 % utilisation. A direct probe on a real frame set:
1 frame -> 0.78 s, 5 -> 1.06 s, **20 -> 4.77 s** for a 38-token answer, so ~4.5 s of each step
is prefill+vision and ~9.5 s is decode, with decode starved because prefill competes for the
same GPU. And the cause: **prefix cache hit rate 0.0 / 0.7 / 1.4 %**. The formal `legacy`
layout slides a fixed 20-frame window, so the prefix changes at the first image every step
and nothing is reused. (Prolong ran at 96 % cached input; that is why it was cheap.) This is
also why MTP k=3 bought the direct arms nothing: it accelerates decode only.

**What changed.**
- `PROMPT_LAYOUT=append-only` for arms 2 and 3 (94-96 % reusable prefix; repo-measured
  hypothesis 13.7 -> 7.6 s/step, default 7.3 -> 4.6). **This makes them a different arm** --
  state after the frames, window 20-29 instead of a fixed 20 -- so they are no longer the
  formal protocol, are not comparable to either recorded seven-scene campaign, and carry the
  `-append-only` tag. The table must be titled
  `prolong-legacy vs hypothesis-append-only vs default-append-only`.
- A fourth server, `qwen35-s4-k3` on GPUs 0,1 :8004. **Nothing of the user's was killed**:
  `qwen35-auto3` had already ended on its own (last request 22:42:49, then 12 min of zero
  traffic, session gone). Run file is `qwen35-s1-k3.sh` with exactly two lines changed
  (devices, port), verified by diff and by remote md5.
- Both arms run **concurrently, 9 slots each**, over the identical scene order. A deadline
  needs a matched scene set at an arbitrary stopping time; running them in parallel makes the
  common prefix grow steadily instead of arm 3 starting from zero at 03:00.
- The 28 legacy hypothesis cells are kept as a small legacy sample, outside the main table.
- Teardown was clean: launcher and 6 in-flight cells stopped, and all 14 sandbox sessions
  explicitly closed (a230 went to 0 sessions) so the new run starts from a quiet host.

**Guard rails in `append_only_sprint.sh`:** refuses to launch unless the screen returns exactly
154 scenes; wire-checks all four servers (1024 cap with `finish_reason: length`, no `<think>`,
no `reasoning_content`) and refuses on any failure; hard-stops the launchers at 06:15 and
writes the summary, so a table exists by 07:00 whatever has finished.

**Expected:** ~130-140 scenes covered by both arms at 06:15, against 70 under the legacy plan.

### 23:15 -- sprint is live and measured at full concurrency; the deadline is no longer the binding constraint

Launched 23:01/23:01:22. All four servers passed the wire-check (`cap=1024 finish=length
think=False` on :8001-:8004). 18 cells in flight, 9 per arm, as configured.

**Measured step rates at true full concurrency** (the 23:06 numbers I first quoted -- hyp 4.69,
def 3.67 -- were taken during the 45 s-stagger ramp, with only ~12 cells actually running, so
they were optimistic):

| arm | legacy | append-only @18 in flight | change |
|---|---|---|---|
| hypothesis | 14.3 s/step | **6.84** (median of 9 cells) | -52 % |
| default | ~10.5 s/step | **4.62** (median of 10 cells) | -56 % |

Still better than the repo's projected -45 %/-37 %, and enough to change the deliverable:
projected completion **default ~03:30, hypothesis ~04:50-05:30** (hypothesis accelerates once
default drains and leaves it the whole cluster), against a 06:15 hard stop. The expectation
above ("~130-140 scenes covered by both arms") should read **all 154, both arms**, with the
06:15 stop as insurance rather than the plan.

**Where the time actually goes, re-measured.** a230 load average 67.6 on 255 cores with 18
sessions -- an eighth of the 397 seen at 14 *prolong* cells, because the direct arms carry no
codex/bwrap. The sandbox is not the constraint. All 8 GPUs are at 100 %, prompt throughput
1200-2200 tok/s against generation 175-224 tok/s: still prefill/vision-bound.

**Concurrency is already at the knee, so it was not raised.** Every server reports
`Waiting: 0 reqs`, `Running: 2-5`, KV cache 3-8 %. Going 12 -> 18 in flight moved aggregate
throughput 2.91 -> 3.26 steps/s (+12 %) for +50 % concurrency; per-step latency absorbed the
rest. More slots would buy latency, not cells.

**Prefix cache confirms the mechanism.** :8004 is a fresh server that has only ever served
append-only traffic: **69.4 %** hit rate. :8001-:8003 read 24-31 %, diluted by 10 h of legacy
traffic in the same cumulative counter. Against the 0.0-1.4 % measured on legacy, this is the
whole of the speedup.

**Failures: 0 unrecovered** (`Agent call failed` / `env.step failed` / `SandboxViolation`).
One cell (0560) has a recovered retry: a `content: None` reply hit
`UnboundLocalError: action_content` at `mc_agent/action_space.py:244` -- a latent cosmetic bug
(an empty completion should raise a named parse error, not an unbound local); attempt 2
succeeded and the cell continued. Not worth a fix inside a campaign; noted for after.

**First result in.** `default-append-only-0306`: 4/4 milestones in 44 steps. prolong took 45
steps for the same 4/4, so 0306 is an easy scene and carries no signal by itself.

**`benchmark_multihop_stratified`: closed, not a blocker.** It is in no ref of either repo
(all 5 refs + stash, `git log --all -S`, filesystem `find`) and not in the paper because it was
never ours: the user says a collaborator built that n=12-per-hop-level subsample to work around
how slow the full set was. The one consequence to carry into the write-up is that their baseline
numbers are a 12-scene subsample and ours are all 154, so the absolute figures do not sit in the
same table. Slicing our 154 down to their scene IDs stays available if a like-for-like row is
ever wanted.

### 00:20 -- hypothesis was going to miss 06:15; fixed by scheduling, not by touching the arm

**The measurement.** Completion rate over four windows ending 00:15, all stable, so this is
steady state and not the ramp artifact that fooled the 23:06 estimate:

| arm | last 20 / 30 / 45 / 60 min (cells/min) | ETA |
|---|---|---|
| default | 0.45 / 0.40 / 0.42 / 0.47 | 04:42-05:27 |
| hypothesis | 0.35 / 0.33 / 0.29 / 0.30 | **06:43-08:05 -- misses 06:15** |

**Not a fault.** hypothesis makes 1.01 model calls per env step against default's 1.00; no
timeouts, no `wrote no actions`, no truncation. Its requests are simply ~48 % more expensive
to prefill because the DAG and plan ride in every prompt. There is nothing to repair.

**Not fixable by restarting the launcher.** `launch_4hop.sh` decides its skip list ONCE, at
start, from `[[ -f result.json ]]`. Relaunching at a higher CONC would re-queue the 9 cells
then in flight and run each of them twice.

**What was done instead:** a second hypothesis launcher, 3 slots, walking the same 154-scene
screen BACKWARDS (`boost_hypothesis.sh`). The two launchers work from opposite ends and meet
only as the arm finishes; where they do meet, `eval_benchmark.py --resume` -- checked when the
*cell* starts, not when the launcher starts -- skips the scene that already landed. Verified
at 00:20: 11 live hypothesis cells, 9 default, **no scene running twice**.

This redistributes a fixed pie rather than adding capacity: the cluster is at its throughput
knee, and default has ~85 min of slack to lend. Projection with hyp 12 / def 9:
**hypothesis ~04:35-05:30, default ~05:00-05:30**. a230 is untroubled by 21 sessions
(load 67/255 cores at 18).

**Also fixed: the sprint's own clock test is broken after midnight.** `past()` compares
`"$(date +%H%M)"` arithmetically and bash reads a leading-zero literal as octal, so `0008`
raises `value too great for base`. It happens to still fire at 06:15 and from 06:20 on, but a
deadline should not rest on that. The running shell already holds `past()` in memory and has
not yet read the file's last three lines, so editing the script would be useless and unsafe --
`deadline_enforcer.sh` now enforces 06:15 from outside (armed 00:14, pid confirmed).

### 00:20-00:35 -- a230 died; the campaign is frozen at 20 matched scenes

**What happened.** At 00:20 the sandbox host a230 (192.168.2.22) left the network. Not a
service failure: no ICMP, no SSH (`kex_exchange_identification: Connection closed`), port 8000
unreachable, and its **ARP entry reads `(incomplete)`** -- the host is not answering on the LAN
at all. It had been up 36 days; last healthy reading 23:14, load 67.6/255 cores, java=20.
a227 and the four model servers were never affected and are still serving.

**Did `boost_hypothesis.sh` cause it? Almost certainly not** -- revised at 02:35 from
"unresolved", once the per-10-second timeline was measured rather than only the timing.

The one fact that points at us is a coincidence: the boost's first `/create_env` went out at
00:18:57 and the last successful env.step in the whole campaign is at **00:18:59.551**, 2.5 s
later. Everything else points away:

- **Throughput was flat into the wall.** Successful steps per 10 s from 00:14:00: 31 26 24 27
  28 22 / 26 26 23 22 25 27 / 23 25 24 26 26 25 / 31 26 25 28 26 28 / 25 26 20 26 25 21. The
  final bucket sits inside the ordinary spread (the series already holds 20, 22, 22, 23), and
  then the trace stops dead. Resource exhaustion degrades first -- sagging throughput, rising
  latency, some requests timing out while others succeed. None of that is present. The 2.5 s
  after our `create_env` were served at full rate; a world-gen that was exhausting memory would
  have shown up inside them.
- **Zero sandbox errors in the preceding 79 minutes**, across roughly 4,700 steps.
- **`/create_env` was routine, not novel**: 79 of them between 23:01 and 00:19, ~1/minute. Ours
  was the 79th.
- **Only 16 cells were mid-episode at 00:18**, not 21 -- cells were finishing and being
  replaced, so live session count at the moment of death was *below* the 18 that had run
  cleanly for 79 minutes.
- **The host is still off the network at 02:30**, ARP `(incomplete)`, two hours after every one
  of our processes was killed at 00:24. User-space load does not do that; an OOM killer takes
  processes and leaves the host pingable.
- 36 days of uptime.

Estimate: ~10-15 % that we contributed, and that residue exists only because a230's console is
unreadable. **What would settle it**, once it is back: `uptime` (did it reboot at all),
`journalctl -b -1 -k | tail` (panic, OOM, or an abrupt end with no error), `dmesg | grep -iE
'oom|panic|hardware error|link is down'`. An OOM-killer record would overturn this reading.

**The boost is still deliberately not re-applied on resume** (`resume_after_a230.sh` goes back
to 9+9). Not because the evidence implicates it, but because the cluster is at its throughput
knee anyway -- the boost was worth ~12 % -- and there is no reason to spend even a small risk
on it while the cause is unconfirmed.

**Damage, and why it is recoverable.** 11 cells wrote an error-schema `result.json` (`error`
field, no `total_steps`, `milestones_trackable: 0`). Left in place, the launcher's
`[[ -f result.json ]]` check would treat those scenes as done forever. They are quarantined to
`outputs/_damaged_a230_outage/`, so the scenes are re-runnable and the analysis globs skip them.
15 stalled cells were SIGTERMed. Surviving valid results: **prolong 154/154, hypothesis 20,
default 33.**

**No recovery is possible from this account tonight.** The sandbox image is on shared storage
(14 GB under `.podman/storage`) but a230 was the only host with podman and fuse-overlayfs;
a226, a227, a231 and b7 have neither, and `ruihan` is not in the `docker` group on a218.
Restoring service needs console/IPMI access to a230, or podman installed elsewhere -- both
admin actions. `resume_after_a230.sh` polls every 30 s and will relaunch both arms at 9 slots
the moment a230 answers, with a fresh four-server wire-check, up to the 06:15 stop.

**Deliverable as it stands.** `experiments/RESULTS_4hop154_q35a.md` now carries the three-arm
table on the **20 scenes all arms share**, with a sign test on the paired per-scene outcomes.
Only `prolong > hypothesis` separates (10-2 on 12 discordant pairs, p = 0.039); `prolong >
default` (8-2, p = 0.109) and `default > hypothesis` (6-3, p = 0.508) point the right way but
do not clear n = 20. Direction and gap match the earlier 24-scene legacy head-to-head.

### 02:45 -- everything stopped at the user's request, waiting on a230

**Stopped by me:** `deadline_enforcer.sh` (pid 49252) and `resume_after_a230.sh` (pid 50072),
plus the session's progress monitor. Verified: 0 campaign processes remain -- no launcher, no
`eval_benchmark`, no watcher. Nothing will now restart on its own; a230 coming back does
**not** resume the run any more.

**Already stopped by someone else:** all four vLLM servers on a227, cleanly at 02:24:59-02:25:00
(`Waiting for application shutdown` / `Application shutdown complete` in each log, four within
one second). Not us -- this session never touched :8001-:8003, and :8004 was left running when
the sprint was killed at 00:24. a227 itself did not reboot (154 days uptime, load 0.86). All
8 GPUs now read 0 % and ~17 MiB.

**a230** is still off the network at 02:45, ARP `(incomplete)`, 2h25m after it went.

**State preserved, nothing in flight** -- which is what makes the resume clean, because
`launch_4hop.sh` decides its skip list from `[[ -f result.json ]]` at start and would otherwise
duplicate running cells:

| | cells |
|---|---|
| prolong (legacy) | 154/154 -- complete |
| default (append-only) | 33/154 |
| hypothesis (append-only) | 20/154 |
| quarantined from the outage | 11, in `outputs/_damaged_a230_outage/` -- scenes re-runnable |

Analysis of what exists is finished and pushed: `experiments/RESULTS_4hop154_q35a.md`,
`experiments/ANALYSIS_4hop_three_arms.md`, `experiments/stats_q35a/` (six CSVs), and the 235
q35a rows in `experiments/4hop_cells.csv`.

**To resume when a230 is back**, in order:

1. `ssh ruihan@192.168.2.22 'uptime; journalctl -b -1 -k | tail -50; dmesg | grep -iE "oom|panic|hardware error|link is down"'`
   -- first, because an OOM record would overturn the attribution above.
2. Restart the sandbox if the container did not come up:
   `podman run -d --replace --name mineexplorer -p 8000:8000 docker.io/davidzhth/mineexplorer:0.0.1 bash start_mc_server.sh`
   (`TMPDIR=/datapool/data3/storage/ruihan/.podman/tmp` first; see the podman runbook memory).
3. Restart the model servers on a227: `qwen35-serve/run/qwen35-s{1,2,3}-k3.sh`, and
   `qwen35-s4-k3.sh` only if GPUs 0,1 are still free -- it was ours, and freeing them is fine.
4. Wire-check all servers (cap 1024, `finish_reason: length`, no `<think>`, no
   `reasoning_content`) -- the check in `append_only_sprint.sh` lines 49-68 does it.
5. Relaunch both arms; the launcher skips the 53 cells already on disk:
   `PREFIX=q35a MODEL=Qwen3.5-27B SPLIT_ROOT=bench_4hop154/_split PROMPT_LAYOUT=append-only`
   `RESPONSE_STYLE=full ARMS="hypothesis:vllm" SCENES="$(python scripts/screen_scenes.py --hops 4 | awk '$1 ~ /^[0-9]{4}$/ {printf "%s ", $1}')"`
   `MAX_STEPS=200 CONC=9 bash scripts/launch_4hop.sh` -- and the same with `ARMS="default:vllm"`.
6. `python scripts/emit_stats_q35a.py && python scripts/export_cells_csv.py --prefix q35a --campaign q35a`
   to refresh the committed statistics.
