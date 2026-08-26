# g56l worldmodel arm: trajectory analysis and fixes

Arm 1 of the g56l head-to-head (strict seven, 300 steps, hosted gpt-5.6-sol effort=low,
one codex session per turn). 7/7 results in 33 minutes wall. Raw score 16/28; per scene:

| scene | steps | end       | score | missing                                             |
|-------|-------|-----------|-------|-----------------------------------------------------|
| 0306  | 48    | agent_esc | 4/4   | --                                                  |
| 0726  | 96    | agent_esc | 4/4   | --                                                  |
| 0311  | 87    | agent_esc | 2/4   | hunt_rabbit, hunt_donkey (both presatisfied: 2/2 creditable, legal ESC) |
| 0182  | 300   | max_steps | 2/4   | mine_magma_block, bridge_lava_gap                   |
| 0763  | 300   | max_steps | 2/4   | mine_purple_concrete, build_animal_pen              |
| 0482  | 300   | max_steps | 1/4   | mine_mossy_cobblestone, mine_pink_concrete, build_hidden_room |
| 0603  | 300   | max_steps | 1/4   | find_purple_bed, find_red_nether_brick_stairs, mine_quartz_block |

Mechanism health: CS1 flat (49/70/159s min/med/max turn latency, 0 timeout/empty resets,
5-19 turns per episode), 0 false claims, 0 breaker trips, presatisfied ledger agrees with
the scorer on every scene, milestone-verified queue flush worked every time (0306: 6
turns to 4/4 is the reference trajectory). Tool errors 0-3 per episode, all absorbed
in-turn. The framework did what it was built to do; the losses are below it.

## Where the 12 hops were lost

Missing-hop types: 6 mine_*, 2 build_*, 2 find_*, 1 bridge_*, (+2 presatisfied hunts
that cost nothing). Per-scene digests: subagent reads over logs, workspaces and
per-turn transcripts (traj-0182/0482/0603/0763, 2026-08-26).

**1. The mine gap is a pickup gap, not an aim gap (0763, proven).** All mine_* rules are
`inventory_has` -- the drop must reach the inventory. 0763 equipped the right diamond
pickaxe, broke purple_concrete three times (events.jsonl steps 69/160/173, `use_item
diamond_pickaxe` alongside each), and banked zero: `mine_forward` ended at the break and
nothing ever walked the ~1 block onto the drops. The model met its own three break
events only at the next induction, ~60 steps later, and concluded "need more blocks or
unknown condition" -- then re-mined the same spot instead of collecting. The only mine_*
that succeeded all campaign (0603 white_carpet) is the only target that breaks instantly
and drops itself at the player's feet.

**2. Wrong-target mining (0482).** 84% of the episode on mine_mossy_cobblestone,
attacking exterior grass/leaves (mine_block fired for grass_block x3, spruce_leaves x2,
never the target) across three location hypotheses. Every induction diagnosed the wrong
location correctly ("Do not repeat digging there") and the next plan repeated the
pattern anyway. 14 zoom calls never confirmed block identity before attacking.

**3. Seen-but-not-approached finds (0603).** find_purple_bed is position_near(5) +
facing(30 deg): the agent SAW the bed point-blank in six frames and aimed at it
repeatedly -- from a corridor strip whose z never entered the 5-block radius (~1-2
blocks short the whole episode). Facing was satisfied; distance never was; nothing told
it "too far" and it never learned to close in. The checker is fine: the scene is
winnable. Same episode showed the goal layer working: causal.md re-ranked hops by cost
and took white_carpet (hop 4) first, deliberately.

**4. Rule-shape opacity (all stuck scenes).** The checklist renders bare task text
("mine purple_concrete", "build an animal pen", "bridge the lava gap"); the actual rules
are inventory_has >= 6, six purple_concrete placed inside a spawn-relative box, and
position_inside_box (just reach the far side -- 0182 carried 64 cobblestone and never
attempted either bridging or the crossing; final position ~100 blocks away). No arm gets
rule internals, so the comparison is fair -- but the worldmodel's own doctrine claimed
"targets come with coordinates" (true in MCU, false here), teaching arithmetic
navigation toward coordinates that never arrive.

**5. Misfiled goals thrash the warden (0182).** 13 goal_confirm reverts in 17 turns:
the model filed landmark beliefs (kind=goal) that match no checklist milestone, so the
warden -- correctly, per its goal-only scope (discipline.py:104) -- reverted every
self-confirmation forever. Each cycle burned an op while magma stayed unfound.

## Fixes landed (framework unchanged, prompts + one macro + one prompt line)

1. `mine_forward` now walks 8 ticks into the mined spot after the attack sequence --
   the collection is part of the mining motion (procedures.py; the 0763 case verbatim
   in its docstring).
2. "Milestone shapes" rewritten (prompts.py ACTION_REFERENCE): find = close to 2-3
   blocks then face (3 failed aims at a VISIBLE target => too far, close in); mine =
   inventory is the criterion, tool CLASS matters (stone/concrete/ore drop nothing
   without a pickaxe), check the Inventory line after breaks, one may not be enough;
   build = stand in the area, place the collected material, place MORE before
   concluding the area is wrong; hops chain only when one produces what the next needs
   -- independent hops switch after two stalls, never the same aim a third time.
3. Strategy bullets: "targets come with coordinates" replaced by the search doctrine
   (sweep by 45-degree slices, zoom to confirm identity BEFORE mining, record
   discovered coordinates in spatial.md); new "a stale goal is a verdict" bullet
   (replan around the cheapest unmet milestone immediately).
4. Ops schema now fences `kind: "goal"` to checklist milestones; the warden's revert
   notice tells a misfiled goal to refile as spatial/semantic.
5. Act prompt gained a "Recent ground truth:" line (last 4 events with step numbers,
   deque in agent.py) so a break-without-inventory-gain is visible at the next plan,
   not at the next induction.

selftest: 64 checks, 0 failures (6 new in test_mining_feedback_loop).

## Open decisions (user)

- **Rule-derived requirement rendering** (counts, boxes, radii) into the checklist:
  changes the benchmark's information conditions; would have to ship to every arm
  symmetrically to keep the comparison meaningful. Not done.
- **Fixed-arm rerun**: plan is a single-scene v2 probe on 0763 after the chain
  completes (does the pickup fix flip mine_purple_concrete?), then a full 7-scene
  worldmodel-v2 arm only on explicit go-ahead.
