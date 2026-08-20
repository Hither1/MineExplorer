# The 4-hop `hypothesis` arm against `default`: reading the trajectories, not the gap

Qwen3.5-27B, campaign `q35a`, 20 shared 4-hop scenes, 200 steps. Companion to
[`ANALYSIS_4hop_three_arms.md`](ANALYSIS_4hop_three_arms.md), which reports
`hypothesis` last of the three arms (17.5 % against `default`'s 22.5 %). This document
asks what the trajectories say about that ranking, and the first thing they say is that
the ranking is not there.

Every number below comes from `python scripts/hyp_vs_default.py`, which writes
`experiments/stats_hyp_vs_default/{report.md,paired_scores.csv,geometry.csv,behaviour.csv,discipline.csv}`.

---

## 0. A fourth run that was not in the three-arm table

The hypothesis agent ran the 4-hop set **twice** in this campaign. Arm 2 launched on the
`legacy` prompt layout, was stopped when the prefix-cache diagnosis moved the direct arms to
`append-only`, and relaunched. Both runs survive on disk:

| run | layout | cells | covers the shared 20 |
|---|---|---|---|
| `hypothesis` | append-only | 20 | yes — this is the arm in the three-arm table |
| `hypothesis` | legacy | 28 | **yes, all 20** |

The legacy run was left out of `ANALYSIS_4hop_three_arms.md` because it is a different arm by
this repo's layout rule, and for a three-way comparison that is right. For *this* question it is
the control that matters: it is the same agent, same model, same scenes, same 200-step budget,
temperature 0.7, differing only in where the state block sits in the request.

---

## 1. The gap is not larger than the agent's own run-to-run spread

| arm | milestones / 80 | / 49 reachable |
|---|---|---|
| prolong (legacy) | 28/80 = 35.0 % | 26/49 = 53.1 % |
| default (append-only) | 18/80 = 22.5 % | 18/49 = 36.7 % |
| **hypothesis (legacy)** | **18/80 = 22.5 %** | **18/49 = 36.7 %** |
| hypothesis (append-only) | 14/80 = 17.5 % | 14/49 = 28.6 % |

*(31 of the 80 milestones are `craft`/`mine`/`trade`-class rules that no arm ever earned in
this harness — see `ANALYSIS_4hop_three_arms.md` §2. The right-hand column drops them.)*

| pair | sum | mean diff / scene ± se | W-L-T | sign test |
|---|---|---|---|---|
| default − hypothesis(append) | 18 vs 14 | +0.20 ± 0.17 | 6-3-11 | p = 0.508 |
| **hypothesis(legacy) − hypothesis(append)** — *same agent* | 18 vs 14 | **+0.20 ± 0.25** | 5-4-11 | p = 1.000 |
| default − hypothesis(legacy) | 18 vs 18 | +0.00 ± 0.21 | 4-6-10 | p = 0.754 |
| prolong − hypothesis(append) | 28 vs 14 | +0.70 ± 0.25 | 10-2-8 | p = 0.039 |
| prolong − default | 28 vs 18 | +0.50 ± 0.22 | 8-2-10 | p = 0.109 |
| prolong − hypothesis(legacy) | 28 vs 18 | +0.50 ± 0.26 | 8-2-10 | p = 0.109 |

**The hypothesis agent beats itself by exactly the margin `default` beats it by**, and its other
run ties `default` milestone for milestone (18 vs 18, W-L-T 4-6-10). +0.20 ± 0.17 per scene is
a difference smaller than the standard error of the same agent measured twice. On a wider cut —
`default`'s 33 cells against the legacy run's 27 shared with them — the two are 20/108 vs 20/108,
W-L-T 6-7-14.

So the question "why is hypothesis worse than default" has no measured effect behind it yet.
`prolong > hypothesis` is the only pair in the campaign that separates, and it separates against
both hypothesis runs equally (10-2 and 8-2).

Per-scene, the same agent swings by up to three milestones on one scene:

| scene | hyp(legacy) | hyp(append) | | scene | hyp(legacy) | hyp(append) |
|---|---|---|---|---|---|---|
| 0232 | **3** | **0** | | 0306 | 1 | 3 |
| 0410 | 2 | 0 | | 0560 | 0 | 1 |
| 0576 | 2 | 0 | | 0412 | 0 | 1 |
| 0435 | 1 | 0 | | 0074 | 2 | 3 |

---

## 2. Why the variance is that large: the scoring rule is a few blocks of drift

49 of the 80 milestones are `position_near_with_facing`. It reads no frame and no agent claim —
it fires when the player is inside a radius of a spawn-relative coordinate **and** the yaw is
within half the facing tolerance (`benchmark_gen/utils.py:84`). The rest of the milestone is
whether the agent physically got there.

The distances involved are tiny. The median position milestone sits **10.1 blocks** from spawn
behind a **5-block** radius: the agent must close a median of **5.1 blocks** and point the camera
within ±30°. Against that, every arm walks a median of **21-29 blocks of path in a whole
200-step episode** and spends ~78 % of steps moving under 0.25 blocks.

The margins in the losses are correspondingly absurd:

- `0694/find_iron_door`: hypothesis's closest approach was **5.01 blocks** against a 5.00-block
  radius. It missed by a centimetre; `default` got it.
- `0726/find_seagrass`: `default`'s best facing while inside the radius was **23.8°** against a
  22.5° half-tolerance. It missed by 1.3°; hypothesis got it.
- `0232`: the same hypothesis agent reached z = −5563.3 in its legacy run and z = −5570.1 in its
  append-only run, on a target needing z ≥ −5567.5. **2.6 blocks of forward drift, three
  milestones.** Both runs spent the episode fumbling at the same door.

A benchmark decided by 1-3 blocks of accumulated drift, in a control loop that moves 0.1 blocks
per step and self-reports circling on every episode, cannot resolve a 4-milestone difference at
n = 20.

---

## 3. Where the four milestones went anyway

Splitting every position milestone into *never entered the radius* and *entered it and never
looked*:

| arm | ever inside the radius | of those, earned | never near | near, never faced | median closest approach − radius |
|---|---|---|---|---|---|
| default (append) | 21/49 | 18/21 | 28 | 3 | +1.09 blocks |
| hypothesis (append) | 20/49 | 14/20 | 29 | 6 | **+0.52 blocks** |
| hypothesis (legacy) | 23/49 | 18/23 | 26 | 5 | **+0.14 blocks** |

Both arms fail the same way and at nearly the same rate: **~58 % of targets are never physically
reached by anybody.** Proximity does not separate them — and on the closest-approach median the
hypothesis runs are the ones that get *nearer*.

The seven milestones `default` took and hypothesis(append) did not:

| scene / milestone | how hypothesis missed |
|---|---|
| `0182/find_dark_oak_button` | never near — closest 6.35 (radius 5) |
| `0232/find_spruce_door` | never near — closest 8.06 (radius 5) |
| `0232/find_spruce_planks` | never near — closest 11.17 (radius 8) |
| `0410/find_black_wool` | never near — closest 11.75 (radius 5) |
| `0694/find_iron_door` | never near — closest **5.01** (radius 5) |
| `0306/find_granite` | inside the radius (2.06 of 3), best facing 40.2° against ±30° |
| `0576/find_magenta_stained_glass` | inside the radius (4.91 of 5), best facing 58.4° against ±30° |

Five navigation misses, two camera misses, three of them decided by under a block or under 15°.
The three going the other way are the same story mirrored.

---

## 4. What *is* robustly different, and replicates across both hypothesis runs

The score is a tie; the behaviour is not. These are measured on ~4,000 steps per run and hold in
both hypothesis runs independently.

### 4a. It runs experiments where the benchmark pays for looking

| metric (median over the 20 scenes) | default | hypothesis (append) | hypothesis (legacy) |
|---|---|---|---|
| steps issuing a manipulation action (`attack` / `use` / `inventory` / hotbar) | **0.2 %** | **5.0 %** (W-L 15-2, p = 0.002) | **14.8 %** (W-L 16-1, p = 0.0003) |
| steps issuing a camera move | 36.5 % | 30.0 % (p = 0.648) | 26.8 % (p = 0.503) |
| steps issuing a locomotion key | 52.5 % | 57.2 % (p = 0.824) | 72.0 % (p = 0.041) |

Campaign totals on the shared 20: **351/4000 (8.8 %) and 659/4000 (16.5 %) manipulation steps
against `default`'s 89/3844 (2.3 %)** — a 4× to 7× difference, significant in both runs.

This is the prompt working as designed. `_HYP_DISCIPLINE` asks the model to name, in `"testing"`,
the hypothesis each action tests, and `mechanism` is the most common node kind it invents
(47 % of 719 nodes: "attacking this trunk clears the path", "the button opens the door"). A
mechanism hypothesis is tested by manipulating the world. But 61 % of the scorable milestones
here are `position_near_with_facing`, which no `use` or `attack` can ever satisfy, and the
`craft`/`mine` classes that *would* reward manipulation are 0/109 for every arm because the
harness exposes no GUI. **The scaffold converts steps from the only two actions that score —
walk and turn — into the one that cannot.**

### 4b. It declares victory, and the graph keeps the claim

Across all **48 hypothesis cell-runs**, the agent's own counters record:

- **653 reverted goal confirmations** (13.6 per cell; 47 of 48 cells have at least one). Each is
  the model marking a task goal `confirmed` while the environment's status line says NOT verified.
- **429 dropped ESC presses** in 15 of 48 cells, 5 of them ≥ 20 presses.

Cells that try to end the episode early, over every cell each arm has:
**hypothesis 15/48 (31 %) against default 3/33 (9 %) — Fisher exact p = 0.028.**

Both agents carry a nearly identical ESC rule in their prompt, so the difference is not the
instruction, it is the store. `0232` is the clean case. At step 2 the model wrote

> `{"id": "h1", "confidence": 0.95, "status": "confirmed", "evidence": "Visual confirmation of
> spruce button and spruce door on the front wall"}`

while standing 8 blocks from the door. `h1` finishes the episode at **confidence 0.99** with the
evidence line "Visually confirmed the building with spruce door and button in earlier frames."
For the remaining 198 steps the prompt told the model, every step, that finding the button and
door was settled — so it spent the episode trying to *open* the door rather than walk up to the
wall and look at it, and scored 0/4 on a scene its own legacy run scored 3/4.

The graph is an unverified-claim store: the model's visual guess becomes prompt state with a
confidence attached, and is read back as fact. `_enforce_discipline` catches the label (653
reverts) but not the belief — confidence up to 0.9 survives the revert, and the statement is
never rewritten.

**This did not measurably cost score.** Cells with ≥ 20 ESC presses average 0.60 milestones
against 0.74 for the rest (n = 5), and paired within a scene the heavy-ESC run scored higher as
often as lower (`0412`: 164 presses → 1, the quiet run → 0; `0306`: 33 presses → 1, 4 presses → 3).
The lock burns steps the agent was already wasting.

### 4c. It costs about half as much again per step

| | default | hypothesis (append) | hypothesis (legacy) |
|---|---|---|---|
| median reply | 899 chars | **1359** (W-L 20-0) | **1704** (W-L 20-0) |
| median wall clock / cell | 18.0 min | 28.0 min | 51.0 min |

`response_style=full` makes the hypothesis agent emit `thought`, `action`, a full 200-word
`memory_update`, the `hypotheses` ops, `plan` and `testing` on **every** step. That is +51 %
output tokens and +56 % wall clock for the same 200 steps.

One thing it is *not*: truncation. With the server's 1024-token cap, the hypothesis arm's
attempt-1 parse rate is **99.5 % (3981/4000)** against `default`'s 99.8 % — the failure that cost
PRO-LONG 30.8 % of its calls does not touch this arm.

---

## 5. The DAG never delivers the thing it exists for

The graph is meant to structure a multi-step task. If it worked, the arm should be relatively
stronger on the *later* hops, where knowing the chain matters. Earn rate by position in the
4-hop chain, shared 20:

| arm | hop 1 | hop 2 | hop 3 | hop 4 |
|---|---|---|---|---|
| prolong | 11/20 | 9/20 | 6/20 | 2/20 |
| default | 7/20 | 4/20 | 4/20 | 3/20 |
| hypothesis (append) | 7/20 | 3/20 | 3/20 | 1/20 |
| hypothesis (legacy) | 10/20 | 3/20 | 5/20 | 0/20 |

No late-hop advantage in either run; if anything the reverse. And of 719 graph nodes, only 22 %
are `location` — the one kind that could inform "walk this way". 47 % are `mechanism`, about a
world the agent barely touches; 25 % are `goal`, which are restatements of the task text the
model was already given.

The deeper reason is that the task has no epistemic structure to exploit. Every milestone here is
"stand within N blocks of a fixed coordinate and point the camera at it". Nothing is hidden that
inference could uncover; the coordinates are not deducible from anything observable, so no
hypothesis can be *tested* into a shorter search. What the scenes actually demand is sustained
straight-line travel — which is exactly what `prolong` supplies with its 15-20-step committed
plans (`ANALYSIS_4hop_three_arms.md` §5a), and the only arm-level effect the campaign resolves.

---

## 6. What follows

1. **Do not report `hypothesis < default`.** The two are 18 vs 18 on one pairing and 18 vs 14 on
   another, of the same agent. The honest statement is that the direct arms are indistinguishable
   from each other and both sit below `prolong`.
2. **The measurement, not the arm, is the bottleneck.** Milestones decided by 0.01 blocks and 1.3°
   cannot rank agents at n = 20. Before another hypothesis-vs-default comparison: raise the step
   budget from 200 (the paper runs 1,800), and run ≥ 2 seeds per cell — the same-agent spread
   measured here, ±0.25 milestones/scene, sets the resolution any future claim has to beat.
3. **If the hypothesis arm is kept, cut what the benchmark cannot pay for.** Steer the graph
   toward `location` and away from `mechanism`, and switch it to `response_style=compact` so the
   graph and plan ride only on the steps they change — the +51 % output buys nothing measurable.
4. **Rewrite the statement, not just the status, on a reverted confirmation.** Capping a goal's
   label while leaving "Visually confirmed the spruce door" in the prompt at 0.99 leaves the
   belief that produced the ESC intact.
5. **The 28-cell legacy hypothesis run should be reported.** It is a complete, usable arm on the
   shared 20 and it is the only within-agent variance estimate this campaign has.
