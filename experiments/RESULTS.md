# What the DeltaAI campaign measured

Written 2026-08-16, when the cluster became unavailable. This is the synthesis that has to
outlive `artifacts/`, which lives on `/work/nvme` and does not.

`LEDGER.md` records what was submitted. `RUN_LEDGER.txt` records which runs are trustworthy.
This file records what they add up to, including the part that is a null result.

## The headline

**159 runs were submitted. 31 produced an episode. 11 survive the validity ledger. None of
them measures the thing the project is about.**

The central claim -- that PRO-LONG's memory architecture helps on long-horizon,
multi-hop tasks -- requires a hard scene and a PRO-LONG arm. Every attempt to get both at
once was killed before it produced a score. The single hard-scene episode that finished
(0694) is the *default* arm of the reference model.

This is a real outcome and not a bookkeeping artifact: the failures were infrastructural
and scheduling-related, not scientific, and each one is recorded below so the next campaign
does not rediscover it.

## What this branch defaults to now

Stated because none of the runs below were taken under it, and a new cluster will start
here. Not a claim that it is correct -- it is the last state of an investigation that the
allocation ended before it could be finished.

| | default | how to change it |
|---|---|---|
| thinking | **on**, both channels | `VLLM_CHAT_TEMPLATE_KWARGS` and `CODEX_LOCAL_EFFORT=none` together |
| output cap | 16384 | `VLLM_MAX_OUTPUT_TOKENS` |
| sampling | 1.0 / 0.95 / top_k 20 (the card's thinking recipe) | `VLLM_SAMPLING` |
| per-call ceiling | 900s provider, 1800s PRO-LONG | `CODEX_TIMEOUT` sets both |

The thinking default is *reversed* from what most of the ledger entries below were taken
under, and reversed from what was chosen operationally on the final day. It changed
because thinking off was measured to break the non-PRO-LONG arms; see the findings
section. `python -m prolong_mc.selftest` asserts the two channels agree on it, so a
half-applied change fails there rather than silently in a matrix.

## The valid episodes

Eleven results pass `load_invalid()`. Grouped by what they can support:

### Easy scenes, matched serving (`think-on,nocap`), cap 150

The only cells where a default arm and a PRO-LONG arm were run under the same server, the
same cap, and the same protocol. Both arms reach the same milestone total; they differ in
how long they take to get there.

| scene | arm | milestones | steps to last milestone | total steps |
|---|---|---|---|---|
| 0313 | default | 2/2 | 19 | 20 |
| 0313 | prolong | 2/2 | 39 | 60 |
| 0313 | prolong (seed 2) | 2/2 | 44 | 45 |
| 0313 | prolong (seed 3) | 2/2 | 76 | 80 |
| 0802 | default | 1/1 | 25 | 26 |
| 0802 | prolong | 1/1 | 50 | 58 |

**PRO-LONG is consistently slower to the same milestone total** -- 39/44/76 steps against
20 on 0313, 50 against 25 on 0802. Three PRO-LONG seeds on 0313 all exceed the single
default run, so this is not seed noise on the PRO-LONG side.

Read it narrowly. These scenes carry one and two milestones at shallow dependency depth --
`screen_scenes.py` exists precisely because such scenes cannot discriminate between agents,
and every arm here scores full marks. What the table shows is a cost (more steps for the
same result), not the absence of a benefit; the benefit, if any, is claimed for horizons
these scenes never reach. Both arms also ended by `agent_esc`, meaning they chose to stop,
so "total steps" measures when an agent believed it was finished.

### Hard scene, single arm

| run | scene | arm | milestones | steps | note |
|---|---|---|---|---|---|
| `20260816-152559-axis-gpt56-default-0694` | 0694 | default (gpt-5.6) | 3/4 | 400/400 | 400 calls, zero timeouts, 88 min |

Milestones completed at frames 166, 17, 64 -- **out of task order, and the first hop never
completed at all**. If milestones on a depth-4 scene can be satisfied by wandering into
them, the scene does not enforce the four sequential hops it was selected for. Worth
checking before 0694 anchors any claim: `screen_scenes.py` filters scenes satisfied *at
spawn* but not scenes satisfiable *out of order*.

Because the milestones land at frames ≤166, this run is still readable at a 300-step cap.

### The remaining two

`20260815-234642-codex-qwen35-default` reached 3 steps on each of 0313 and 0544. Kept as
valid but too short to carry anything. `20260816-144322-probe40-qwen38-prolong-0313` is a
40-step probe whose score is meaningless at that cap; its value is the serving evidence
below.

## What the failures established

61 runs are marked invalid or cancelled. They cost the campaign its result, and they are
the campaign's actual output. Grouped: scheduling/cancellation 25, model serving 10,
protocol/scoring 8, sandbox/engine 8, other 10.

The findings worth carrying forward:

**Qwen3.8 with thinking off degenerates into repetition loops on the non-PRO-LONG arms.**
The 0313 diagnostic timed out on 6 of 13 calls with the server demonstrably alive. The
kept event streams show what the stalls were: `bash -lc 'echo ok'` 85 times in one call,
the same PIL crop command 7 times in another, every one returning `exit_code=0`
instantly. Not a wire hang and not a tool hang -- the model emits no-op commands instead
of the action JSON until the client ceiling fires. The damage is one-sided: PRO-LONG's
probe ran 40 steps in 9 minutes with no stalls. **A comparison run in this configuration
would have credited PRO-LONG for a defect in its baseline.** Whether the cause is thinking
or the sampling recipe was never separated -- both were changed together, and the model
card prescribes `presence_penalty=1.5` for the non-thinking mode specifically to stop
repetition, which vLLM cannot apply as a server-side default and codex cannot send.

**Serving configuration silently changes what is being measured.** Qwen3.8's chat template
opens a `<think>` block in the *prompt*, so an output with zero `<think>` tags and
`reasoning_output_tokens: 0` looks exactly like thinking being off when it is not. vLLM
synthesises `enable_thinking` from a Responses request's `reasoning.effort`, which
overrides the server's own default -- so the server flag governs the direct-vLLM arm while
the codex arms need the matching client-side setting. Runs served differently cannot pool,
which is why `RUN_LEDGER.txt` carries a `SERVING:` axis.

**Shared nodes broke runs in ways that read as success.** Two jobs both wanting Xvfb `:99`
ended with one scoring against the other's Minecraft world (`session not found`, hundreds
of times, step counter still climbing) while `/monitor/alive` answered from the winner's
server. A fixed model-server port produced the same class of failure. Port and display are
now derived from the job id, and teardown is scoped by reading `DISPLAY` out of
`/proc/<pid>/environ` rather than matching the JVM by class name.

**Editing a script under a running job corrupts it silently.** bash reads scripts
incrementally; a cross-filesystem `mv` is `open(O_TRUNC)` plus copy onto the inode bash
still holds. Runs died at `exit 0` with results already written. `snapshot_exec.sh` exists
for this.

**A pending job is not pinned to the code it was submitted with.** `snapshot_exec.sh`
copies `scripts/` at job *start*; the manifest's `commit` and `dirty_diff_sha12` only
record. A server job submitted against one serving config would have started with whatever
the working tree held hours later. Anything a run's meaning depends on belongs in the job's
own `env` prefix, where it lands in `command_shell_escaped`.

**The Codex account credential poisons the context.** Linking `~/.codex/auth.json` pulls in
the account's MCP app tools -- 23 tools and 312 KB of JSON schema instead of 10 and 18 KB,
about 78k tokens against 4.6k. That alone overflowed a 65536-token context and failed 94%
of one run's calls.

**Milestone counts lie in two directions.** Milestone count is not dependency depth (16 of
154 four-milestone scenes have only two edges), and a `position_near_with_facing` milestone
can be satisfied at spawn -- in 12 of 19 four-milestone navigation scenes, one scene
handing over three of four. 138 of 299 scenes with 3+ milestones contain a task the action
space cannot perform at all (crafting, trades, furnaces: `ActionState` opens the inventory
GUI but has no cursor and no click), so scoring zero there measures the harness.

**Scheduling, on the last day.** An 11:30 walltime does not backfill on ghx4: six-hour
cells were scheduled within hours while the whole local matrix was estimated a full day
out, behind a server that would have expired first. DeltaAI also refuses a GPU-less job at
submit, so all 23 non-server cells had to hold a GH200 they never computed on. Each
resubmission to fix the alignment started at the back of the queue, which cost more than
the misalignment did.

## What was never obtained

- Any PRO-LONG episode on a hard (depth-4, zero-spawn-satisfied) scene.
- **Any valid episode on the direct-vLLM channel.** All eleven reach the model through the
  Codex CLI. The channel axis exists so that a PRO-LONG result cannot be read as a
  Codex-CLI result, and it has no data on one of its two levels -- so even the easy-scene
  table above is a within-codex comparison with its control missing.
- Any comparison under the `think-off,cap4096` serving configuration; the 15 cells were
  cancelled while queued and never started.
- The factorial that separates thinking from the sampling recipe. Its server ran; its four
  cells were never submitted.
- Any seed replication outside 0313 PRO-LONG.

## If this resumes elsewhere

Two things dominated the loss and both are fixable in the design rather than the science.

1. **Let each cell serve its own model.** The shared-server design created an alignment
   problem with no solution on a contended queue: the launcher has no `--dependency`
   passthrough, and this Slurm silently ignores `SBATCH_*` environment equivalents. Since
   the scheduler forces a GPU onto every cell anyway and that GPU sat idle in all 23 of
   them, a self-contained job removes the failure mode and wastes nothing.
2. **Run several scenes per job.** `eval_benchmark.py` already walks every scene in
   `--benchmark-dir`, `--resume` already skips finished ones, and the sandbox already
   routes by a per-instance `session_id` with `/list_sessions` to see them -- so the
   sequential form needs no code at all, and `--num-workers` for the concurrent form needs
   one flag. Splitting one scene per job is what spread nine 68-minute cells across an
   eight-hour queue window.

Verify before trusting the concurrent form: three Minecraft JVMs on one Xvfb display, and
one `CODEX_HOME` shared by three concurrent codex processes, are both untested here.
