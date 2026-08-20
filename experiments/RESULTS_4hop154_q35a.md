# 4-hop x 154 scenes, Qwen3.5-27B: PRO-LONG vs hypothesis vs default

Campaign prefix `q35a`, 2026-08-20/21. Numbers are filled from
`python scripts/matched_table.py --prefix q35a --arms '<the three labels>' --md`;
everything above the table is the part a reader needs in order to know what the numbers mean.

## Status: incomplete -- the sandbox host died mid-run

**The 4-hop set was NOT completed for arms 2 and 3.** At 00:20 on 2026-08-21 the Minecraft
sandbox host a230 (192.168.2.22) went off the network entirely -- no ICMP, no SSH, port 8000
unreachable, and its ARP entry incomplete, so this is the host being gone rather than a service
failing. It had been up 36 days. a227, which serves the models, was never affected and is
still healthy.

What that leaves:

| arm | cells | note |
|---|---|---|
| 1 prolong (legacy) | **154/154** | complete, finished 20:37 the previous evening, untouched by the outage |
| 2 hypothesis (append-only) | 20/154 | frozen at the outage |
| 3 default (append-only) | 33/154 | frozen at the outage |

Eleven cells that were mid-episode wrote an error-schema `result.json` (an `error` field, no
`total_steps`, `milestones_trackable: 0`). Those are quarantined under
`outputs/_damaged_a230_outage/` rather than deleted, and their scenes are therefore re-runnable
instead of being silently skipped by the launcher's `[[ -f result.json ]]` check. The table
below is built only from cells that carry the full schema.

No sandbox can be restarted anywhere on this cluster tonight: the image is on shared storage
(`/datapool/data3/storage/ruihan/.podman/storage`, 14 GB) but a230 was the only host with
podman and fuse-overlayfs installed -- a226, a227, a231 and b7 all lack both, and this
account is not in the `docker` group on a218. `resume_after_a230.sh` is armed and will
relaunch both arms at 9 slots each the moment a230 answers, up to the 06:15 stop.

## What was run

The **full 4-hop set: all 154 scenes**, not a subsample. `hop` is the paper's definition --
the number of atomic tasks in the instance, `len(reasoning_graph.nodes)` -- and
`scripts/screen_scenes.py --hops 4` returns exactly the 154 that Table 2's valid rates and
generated counts imply (260/254/145/154 = 813). No `--min-depth`, `--reachable`, `--max-free`
or `--no-backwards` screen was applied; those are ours and would have cut the set.

| arm | agent | channel | request layout |
|---|---|---|---|
| 1 | `prolong` (PRO-LONG) | codex, sandboxed | legacy |
| 2 | `hypothesis` (DAG + plan) | vLLM direct | **append-only** |
| 3 | `default` (20-frame buffer) | vLLM direct | **append-only** |

Serving contract, identical across arms: Qwen3.5-27B, TP=2, output cap **1024**
(`max_new_tokens` in the server's `--override-generation-config`, so it binds both channels),
temperature 0.7 / top_p 0.8 / top_k 20, **thinking off**, `qwen3_xml` tool parser,
`--enable-prefix-caching`, MTP `num_speculative_tokens: 3`. Four servers on 8xA100-80G;
the Minecraft sandbox is one rootless-podman host. Verified per server before launch:
`completion_tokens=1024`, `finish_reason=length`, no `<think>`, no `reasoning_content`.

## Three things that must not be read past

**1. Arms 2 and 3 are not the formal `legacy` protocol.** They ran `PROMPT_LAYOUT=append-only`,
which is a different arm by this repo's own rule: it moves the episode state after the frames
and lets the frame window run 20-29 instead of a fixed 20, so the model reads something
different, not merely in a different order. It was chosen for one reason -- `legacy` slides a
fixed 20-frame window, so the request prefix changes at the first image every step and the
measured prefix-cache hit rate was 0.0-1.4 %, i.e. every step re-prefilled 20 frames.
append-only raised it to 69 % and cut the step time by about half, which is the only reason
all 154 scenes fit before the deadline. Arm 1 is untouched legacy: the layout knobs never
reach `prolong` (`run_cell.sh` drops them). **So the comparison is
`prolong-legacy vs hypothesis-append-only vs default-append-only`**, and arms 2-3 are not
byte-comparable to either recorded seven-scene campaign.

**2. 200 steps, where the paper runs 1,800.** The repo default is 300; 200 was chosen for the
deadline. On the recorded runs, 4 of 35 milestones (~11 %) were first reached after step 200,
so every arm here is measured below its own ceiling. This deflates all three arms, but not
necessarily equally -- an arm that explores slowly is penalised more by a short horizon.

**3. `milestones_trackable` is not a ceiling.** Across arm 1's 154 cells, 52 milestones were
`presatisfied_at_spawn` and **not one of them was ever scored** (`completed: True` and
`presatisfied_at_spawn: True` co-occur zero times in 616 milestones). They sit in the
`trackable` denominator and can never enter the numerator. Hence the three conventions in the
table. Presatisfaction is a property of the scene, so on a matched set all three rank the arms
identically and differ only in the absolute number; `matched_table.py` asserts that the arms
agree scene-by-scene on the presatisfied count rather than assuming it.

## Results

The behavioural analysis behind these numbers -- what each arm actually does, why `craft` is
0/109, the ESC deadlock, and how little of PRO-LONG's retrieval is used -- is in
[`ANALYSIS_4hop_three_arms.md`](ANALYSIS_4hop_three_arms.md).

On the **20 scenes all three arms share**. Read this as a pilot, not the campaign: the set is a
prefix of `screen_scenes.py --hops 4` order (sorted by spawn-free milestones ascending, depth
descending, distance descending), so it is systematic rather than random, and biased toward the
harder/cleaner end of the 154. It does not bias the comparison *between* arms, which all see
the identical set.

```
# Qwen3.5-27B, prefix q35a
per-arm cells: prolongxcodex 154, defaultxvllm[append-only] 33, hypothesisxvllm[append-only] 20
matched set: 20 scenes

arm                           scenes  strict         ceiling        msr            all-done  esc  mean steps
prolongxcodex                 20      28/80 = 35.0%  28/78 = 35.9%  30/80 = 37.5%  1         1    192       
defaultxvllm[append-only]     20      18/80 = 22.5%  18/78 = 23.1%  20/80 = 25.0%  1         1    192       
hypothesisxvllm[append-only]  20      14/80 = 17.5%  14/78 = 17.9%  16/80 = 20.0%  0         0    200       

paired, per scene (milestones earned):
  prolongxcodex vs defaultxvllm[append-only]: 8 win / 2 loss / 10 tie  -- sign test on the 10 discordant pairs, p = 0.109 (not significant)
  prolongxcodex vs hypothesisxvllm[append-only]: 10 win / 2 loss / 8 tie  -- sign test on the 12 discordant pairs, p = 0.039 (significant)
  defaultxvllm[append-only] vs hypothesisxvllm[append-only]: 6 win / 3 loss / 11 tie  -- sign test on the 9 discordant pairs, p = 0.508 (not significant)
```

**What survives the sample size.** Only `prolong > hypothesis` does: 10 wins against 2 losses
on the 12 discordant pairs, sign test p = 0.039. `prolong > default` (8-2, p = 0.109) and
`default > hypothesis` (6-3, p = 0.508) are the right direction but do not separate at n = 20.
The three score conventions agree on the ordering, as they must on a matched set.

This is consistent with the earlier 24-scene legacy head-to-head (prolong 32.3 % vs hypothesis
18.8 %), which is a different arm pairing but the same direction and roughly the same gap.

## Notes on cost

<!-- step rates, wall clock, and what the prefix cache bought -->
