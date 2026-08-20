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
