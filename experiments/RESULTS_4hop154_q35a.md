# 4-hop x 154 scenes, Qwen3.5-27B: PRO-LONG vs hypothesis vs default

Campaign prefix `q35a`, 2026-08-20/21. Numbers are filled from
`python scripts/matched_table.py --prefix q35a --arms '<the three labels>' --md`;
everything above the table is the part a reader needs in order to know what the numbers mean.

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

<!-- matched_table.py output goes here -->

## Notes on cost

<!-- step rates, wall clock, and what the prefix cache bought -->
