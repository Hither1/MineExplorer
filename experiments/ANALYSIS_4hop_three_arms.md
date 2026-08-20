# Three arms on 4-hop MineExplorer: what they score, and what they actually do

Qwen3.5-27B, campaign prefix `q35a`, 2026-08-20/21. Companion to
`RESULTS_4hop154_q35a.md`, which holds the protocol and the headline table; this document is
the behavioural analysis behind it.

Scripts that produce every number here, so nothing below is hand-counted:

| script | what it answers |
|---|---|
| `scripts/matched_table.py` | milestone score on the scenes the arms share, three conventions, paired sign test |
| `scripts/tsr_msr_table.py` | task success rate next to milestone success rate |
| `scripts/loop_census.py` | stuck-in-place behaviour, from the one per-step record all arms write |

## 0. Sample sizes, stated once

The sandbox host died mid-run (see `RESULTS_4hop154_q35a.md`), so the arms are not equally
deep: **prolong 154/154, default 33/154, hypothesis 20/154**. Every cross-arm claim below is
computed on the **20 scenes all three share**; where a number comes from an arm's full set it
says so. Twenty scenes is a pilot. It is enough to separate one pair of arms and not the others,
and that is stated rather than smoothed over.

---

## 1. Scores

### Task and milestone success, 20 shared scenes

| arm | TSR strict | TSR achievable | MSR strict | MSR ceiling | MSR msr |
|---|---|---|---|---|---|
| **prolong** (legacy) | 1/20 = 5.0% | 1/20 = 5.0% | **28/80 = 35.0%** | 35.9% | 37.5% |
| default (append-only) | 1/20 = 5.0% | 1/20 = 5.0% | **18/80 = 22.5%** | 23.1% | 25.0% |
| hypothesis (append-only) | 0/20 = 0.0% | 0/20 = 0.0% | **14/80 = 17.5%** | 17.9% | 20.0% |

Conventions: *strict* is `completed / trackable` as the harness records it; *ceiling* is
`completed / (total - presatisfied)`; *msr* counts a spawn-satisfied milestone as met. On a
matched set the three must agree on the ordering, and they do.

**TSR does not discriminate at this scale** — 5%, 5%, 0%. All of the signal is in MSR, and
§3 explains why TSR is structurally near zero for every arm.

### Paired, per scene

| pair | W-L-T | sign test |
|---|---|---|
| prolong vs hypothesis | 10-2-8 | **p = 0.039** |
| prolong vs default | 8-2-10 | p = 0.109 |
| default vs hypothesis | 6-3-11 | p = 0.508 |

Only **prolong > hypothesis** survives n = 20. The other two point the same way and do not
separate. This is consistent with the earlier 24-scene legacy head-to-head (prolong 32.3% vs
hypothesis 18.8%) — a different arm pairing, same direction, similar gap.

### Milestones earned per scene

| arm | 0 | 1 | 2 | 3 | 4 | ≥1 |
|---|---|---|---|---|---|---|
| prolong | 5 | 7 | 4 | 3 | 1 | **75%** |
| default | 9 | 7 | 2 | 1 | 1 | 55% |
| hypothesis | 11 | 6 | 1 | 2 | 0 | 45% |

The clearest single contrast: prolong comes away empty on a quarter of scenes, hypothesis on
more than half.

---

## 2. The benchmark is, in this harness, a visual-search benchmark

Milestone success by the verb in the milestone id, over every cell each arm has:

| verb | n (all arms) | prolong (154) | default (33) | hypothesis (20) |
|---|---|---|---|---|
| **find** | 384 | 177/272 = **65%** | 21/67 = 31% | 13/45 = 29% |
| **mine** | 165 | 3/129 = 2% | 0/25 = 0% | 0/11 = 0% |
| **craft** | 109 | **0/86** | **0/17** | **0/6** |
| **build** | 27 | 0/20 | 0/4 | 0/3 |
| **trade** / **sell** | 25 | 0/19 | 0/3 | 0/3 |
| **collect** | 10 | 0/4 | 0/3 | 0/3 |
| interact | 14 | 3/9 = 33% | 0/3 | 0/2 |
| talk | 3 | 1/1 | 1/1 | 1/1 |
| swim | 3 | 1/1 | 0/1 | 0/1 |
| everything else | ~30 | 0/… | 0/… | 0/… |

**`craft` is 0 for 109 out of 109 attempts, across all three arms.** So are `build`, `trade`,
`sell` and `collect`. `mine` clears 2%. Essentially the whole score is `find_*`.

The agents say why, unprompted:

> "Spawned near fire and crafting table. **Failed to craft golden helmet due to GUI
> limitations.** Abandoned crafting to proceed to next sub-goal."

> "Confirmed yellow concrete and loom. **Failed to open crafting interface on the loom.**"

25 such statements in 5 of hypothesis's 20 cells, 6 in 3 of default's 33. This is the
concern already raised against the paper's §2.2, which places `a_craft` in "the executable
action space": **this harness exposes no cursor and no click, so a crafting GUI cannot be
operated at all.** The milestone is not hard, it is unreachable.

### What that does to the ceiling

Of the 154 4-hop scenes:

- **136 (88%)** contain at least one milestone from a verb class that is never solved.
- **10 (6.5%)** consist *entirely* of such milestones — a guaranteed 0 for any agent.
  `0675 dark_oak_birch_workshop_v2` is one: `collect_dark_oak_wood`, `collect_dark_oak_fence`,
  `collect_birch_trapdoor`, `craft_light_gray_bed`.
- Only **14 (9%)** are all-`find_*`, i.e. winnable end to end in this harness.

So prolong's TSR of **5/154 = 3.2%** should be read against a structural ceiling of ~9%:
**it fully solved 5 of the 14 winnable scenes, 36%.** The headline number understates the agent
by roughly an order of magnitude, and it understates every arm equally.

**This is the single most important thing in this document.** Any 4-hop TSR reported from this
harness — ours or a baseline's — is mostly measuring how many scenes happen to be all-`find`.

---

## 3. Behaviour: three different ways of being stuck

One definition for all arms, taken from the only per-step record they all write
(`step=N player_pos={x,y,z,pitch,yaw}`), so nothing depends on how an arm talks to the model.

### The common floor

| median per cell | prolong | default | hypothesis |
|---|---|---|---|
| steps moving < 0.25 blocks | 79.4% | 77.4% | 77.9% |
| steps in an already-visited block | 90.1% | 90.0% | 90.5% |
| distinct blocks visited / step | 0.10 | 0.10 | 0.10 |

**All three arms spend ~78% of steps barely moving and ~90% of steps on ground they have
already covered.** Being stuck is the normal state, not an outlier. The taxonomy below only
separates the extremes.

### Taxonomy, 20 shared scenes

| arm | ESC deadlock | navigation freeze | pacing loop | any | clean |
|---|---|---|---|---|---|
| prolong | **0** | 4 | 3 | 7 | 13 |
| default | 0 | 0 | 2 | 2 | 18 |
| hypothesis | 3 | 1 | 2 | 6 | 14 |

Full sets: prolong 59/154 (38%), default 5/33 (15%), hypothesis 6/20 (30%).

#### 3a. ESC deadlock — a harness behaviour, not an agent failure

`eval_benchmark.py:541-566`: if the agent sets `ESC=1` while milestones remain unmet and
`milestone_hint` is on, **the ESC is ignored and the episode continues**. The code comment
records the consequence it was written to handle — "observed: agent can emit ESC=1 for
hundreds" — and that is exactly what happens.

| arm | ESC actions | cells pressing ≥20× | worst |
|---|---|---|---|
| prolong | **0** over 154 cells | 0 | — |
| default | 182 over 33 cells | 1 | `0274`, 166 presses |
| hypothesis | 298 over 20 cells | 3 | `0412`, 166 presses |

**The worst "frozen" cell in each direct arm is this deadlock, not a navigation loop.**
`0412` held one pose for 176 of 200 steps and visited 25 distinct poses in the whole episode;
`0274` froze for 177. The agent concluded it was finished, was refused, had no fallback plan,
and re-pressed ESC until the step budget ran out.

prolong never triggers it because it never presses ESC at all.

#### 3b. Navigation freeze and pacing — everyone, prolong most

prolong has the highest rate of genuine motionless runs: median 18.5% of steps frozen over its
154 cells (7.0% on the shared 20, so the shared subset flatters it), longest run 167 steps
(`0502`, which scored 0/4 with 99% revisit).

The direct arms circle instead of freezing, and **they know it**:

> "0.06 blocks over 8 steps, **proving I am stuck in a loop**. Since 'back' and 'jump' alone
> failed, I will try strafing sideways."

> "still in a circling loop (net 0.22 blocks/8 steps). Environment advises stopping movement to
> do a pure turn, then moving straight."

Self-reported loops: **hypothesis 20/20 cells (100%), default 31/33 (94%), prolong 0/154 (0%)** —
2,035 and 1,199 such statements respectively. The direct
arms reason about their own stuckness every episode and mostly fail to escape it. prolong never
articulates it — it does not re-read its position trace closely enough to notice (§4).

#### 3c. prolong's analyzer loop — invisible to the position trace

It happens before any action reaches the environment. **2,342 of 7,594 analyzer turns (30.8%)
wrote no `actions.json`**, the error dominated by
`Unterminated string starting at: line 1 column 9` — the plan JSON truncated mid-string by the
server's 1024-token `max_new_tokens`, unparsable, retried, truncated again.

Concentrated in 11/154 cells, and 3 of them account for nearly all of it: `0326` (910/914 turns
wasted), `0133` (865/869), `0016` (556/569). Those three cost **12 cell-hours, 18% of the arm**.

**No detectable score effect**: the three looping cells scored 4/12 = 33.3% ceiling-corrected
against 181/552 = 32.8% for the other 151. n = 3 cannot prove absence, but there is no evidence
the loop depressed the arm's result.

---

## 4. PRO-LONG barely uses the thing it exists for

PRO-LONG's premise is an append-only log that can be *retrieved from*, instead of a sliding
window. Across 154 cells its analyzer issued **23,335 shell commands**:

| command | count | share |
|---|---|---|
| `cat … <<'EOF'` (writing `actions.json`) | 9,974 | 42.7% |
| `tail -N logs.txt` | 8,753 | 37.5% |
| `cat actions.json` (reading back its own write) | 1,231 | 5.3% |
| `ls` | 759 | 3.3% |
| **`grep` / `rg`** | **538** | **2.3%** |
| `cat logs.txt` | 19 | 0.1% |
| `view_image` | 1 | 0.004% |

Separating emission from retrieval: **retrieval is 8,753 `tail` against 538 `grep`, 94% to 6%.**

- Only **61/154 cells (40%) ever run a single grep.** Median greps per cell: **0.**
- When it does grep, it works: **489/538 (91%) return matches**, 64% real log content, 26%
  `[STATE]` pose lines, 9% empty.
- But the **median grep returns 1 line.** These are narrow lookups, not recovery of distant
  history.

**PRO-LONG here behaves as a long-window reader, not a retrieval agent.** Its measured advantage
over the direct arms therefore probably comes from (a) committing to multi-step plans and
(b) an append-only prompt that keeps history in context — not from search. That matters for how
the result is described: this run does not evidence "retrieval beats a sliding window", because
retrieval was hardly exercised.

`view_image` was called **once in the whole campaign**, against 154 cells' worth of attached
frames — the analyzer looks at the frame it is given and essentially never asks for another.

---

## 5. Case studies

### 5a. `0726 water_channel_crossing` — prolong 3/4, hypothesis 1/4, default 0/4

Milestones: `find_seagrass`, `swim_across_channel`, `find_diamond_block`, `find_soul_campfire`.
Three of the four sit on the far bank, so the episode is gated on one physical traversal.

| arm | y range | x span | z span | outcome |
|---|---|---|---|---|
| prolong | 70.3 – 72.2 | 2.4 | **16.3** | crossed at frame 81, then found both far-bank objects (frames 175, 184) |
| default | **68.0** – 71.3 | 8.6 | 6.8 | fell in (y 68), thrashed: 115 `sprint` + 99 `forward` + 17 `back` + 5 `jump`, never crossed |
| hypothesis | 71.0 – 72.3 | 10.6 | 8.5 | never entered the water at all |

prolong queued plans of 15, 12, 20, 20, 20 steps and walked a near-straight line — x span 2.4
against z span 16.3. **Committing to twenty steps of one heading is what crosses a channel**;
choosing one action per frame, with the far bank not yet visible, does not. This is the
cleanest illustration of prolong's structural advantage.

### 5b. `0074 village_trail_trade` — the counter-example

| arm | score | got | missed |
|---|---|---|---|
| prolong | 2/4 | `find_blue_concrete_powder`, `talk_to_villager` | `find_potted_pink_tulip`, `trade_for_pumpkin_pie` |
| default | **3/4** | + `find_potted_pink_tulip` | `trade_for_pumpkin_pie` |
| hypothesis | **3/4** | + `find_potted_pink_tulip` | `trade_for_pumpkin_pie` |

Both direct arms spotted a potted tulip that prolong walked past. The obvious reading — prolong
executes but does not perceive — **does not survive the aggregate**: on the shared 20 prolong
leads on `find` milestones too (53.3% vs 37.8% and 28.9%). `0074` is a real failure mode
(a queued multi-step plan does not stop to look) but it is an exception, not the pattern.

`trade_for_pumpkin_pie` is unreachable for everyone — see §2.

### 5c. `0412` — 176 steps of pressing a button that is disabled

hypothesis held one pose, `(-3005.75, 71.0, -5571.15, pitch -10, yaw -30)`, for **176 of 200
steps**, and visited 25 distinct poses in the entire episode. The action it emitted throughout
was `{"ESC": 1}` — 166 times. It had decided the task was done; the ESC lock refused; it had no
alternative and re-pressed until the budget expired. It still scored 1/4, from a milestone
earned before the deadlock.

Same story in default's `0274`: 177 frozen steps, 166 ESC presses, 0/4.

### 5d. `0326` — 914 analyzer turns, 910 of them producing nothing

prolong spent 202 minutes and 914 turns on this cell. From roughly turn 4 onward every turn
returned the same truncated-JSON error and wrote no actions. It still reached step 200 and
scored 2/4, because the handful of turns that did parse had already moved it somewhere useful.
A cell that is 100% wasted compute and 50th-percentile score at the same time.

### 5e. `0675`, `0130`, `0408` — all three arms scored 0, and two of them could not have scored

- `0675 dark_oak_birch_workshop_v2`: `collect_dark_oak_wood`, `collect_dark_oak_fence`,
  `collect_birch_trapdoor`, `craft_light_gray_bed` — **four milestones, zero of them from a
  solvable class.** A guaranteed 0 regardless of agent.
- `0130 quartz_path_workshop`: two `find_*`, then `mine_dark_oak_slab`, `craft_oak_button`.
- `0408 landmark_mining_tower_challenge`: two `find_*`, then `mine_gray_concrete`,
  `build_tower`.

The two `find_*` milestones in `0130` and `0408` were missed on merit; the other two were never
in play.

---

## 6. Arm by arm

### PRO-LONG (`prolong`, codex channel, legacy layout)

**Strengths**
- Highest milestone yield on every cut: 35.0% vs 22.5% and 17.5% strict on the shared 20, and
  ahead on *both* `find` (53.3%) and act/traverse (12.1% vs 3.0%) milestones.
- The only arm that completes sustained physical manoeuvres (§5a). Twenty-step committed plans
  are what cross a channel.
- Immune to the ESC deadlock: 0 ESC presses in 154 cells.
- Straightest paths (tortuosity 1.9-2.2 vs 3.2-3.3) — though this is confounded, since freezing
  shortens the path as well as the displacement.

**Weaknesses**
- **Most expensive by far**: 25.6 min/cell mean (21.3 excluding the three pathological cells)
  against default's 17.0. It is 40% of a three-arm campaign's bill.
- **30.8% of its model calls produce no action**, from the 1024-token truncation loop (§3c).
- Highest genuine freeze rate: 18.5% of steps frozen (median, full 154), worst run 167 steps.
- **Does not use retrieval** (§4): 6% of its reads are searches, 40% of cells never grep once,
  `view_image` called once in the entire campaign.
- Never notices it is stuck — 0/154 cells self-report a loop, against 100% and 94% for the
  direct arms.
- A queued plan does not stop to look, so it walks past objects (§5b).

### `hypothesis` (DAG + plan, vLLM direct, append-only)

**Strengths**
- Explicit self-diagnosis: **every one of its 20 cells** reasons about its own circling and
  tries named counter-measures (strafe, pure turn, back off). Whether that counts as a strength
  is arguable — it diagnoses itself correctly and still scores last.
- Cheapest to reason about — one model call per step, no codex, no sandbox per cell.

**Weaknesses**
- **Lowest score of the three**, and the only pair that separates statistically is its loss to
  prolong (p = 0.039).
- **Most ESC-deadlock-prone**: 298 ESC presses over 20 cells, 3 cells ≥20, and its worst cell
  burned 176 of 200 steps that way.
- ~48% more expensive per step than `default` (6.84 s vs 4.62 at matched concurrency) because
  the DAG and plan ride in every prompt — and it buys nothing here.
- Never earned 4/4 on any shared scene.

### `default` (20-frame buffer, vLLM direct, append-only)

**Strengths**
- **Cheapest per cell** (17.0 min) and per step (4.62 s).
- **Fewest extreme loops**: 2/20 shared scenes, against 7 and 6.
- Scores between the other two, closer to prolong than hypothesis is.

**Weaknesses**
- Wanders most (tortuosity 3.2) and self-reports circling in 31/33 cells.
- No mechanism to commit to a multi-step manoeuvre — it fell into the channel in `0726` and
  sprinted in place for the rest of the episode.
- Also hits the ESC deadlock, once, and that one cell cost 177 frozen steps.

---

## 7. What follows from this

1. **Report TSR against the structural ceiling, or not at all.** 3.2% and "36% of the 14
   winnable scenes" describe the same run. Only the second is informative.
2. **Fix or exclude the unreachable verb classes.** `craft` 0/109 with the agents explicitly
   naming the missing GUI is a harness gap, not a difficulty result. Until it is resolved, 88%
   of 4-hop scenes carry at least one milestone no agent can reach, and 6.5% cannot be scored
   at all.
3. **The ESC lock needs a fallback.** Refusing ESC without giving the agent anything else to do
   converts "agent finished early" into "agent freezes for 176 steps". Cheapest fix: on
   rejection, tell it which milestone is outstanding (it already gets `milestone_hint`) and
   force one non-ESC action.
4. **Bound PRO-LONG's plan length or raise its output cap.** 30.8% of its calls are wasted on
   truncated JSON. Either cap the plan to fit 1024 tokens or detect N consecutive unparsable
   turns and fall back to a single action.
5. **This run does not test PRO-LONG's retrieval claim.** With 6% of reads being searches and a
   median of zero greps per cell, it was evaluated as a long-window agent. If retrieval is the
   claim, it needs a prompt that forces the search or a task whose evidence is out of window.
6. **Finish the arms before trusting anything but the prolong/hypothesis gap.** Everything here
   rests on 20 shared scenes.
