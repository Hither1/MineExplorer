## 1. Scores

20 shared scenes: 80 milestones, 49 of them `position_near_with_facing`, 31 of other rule types (never earned by any arm).

| arm | milestones / 80 | / 49 reachable |
|---|---|---|
| prolong(legacy) | 28/80 = 35.0% | 26/49 = 53.1% |
| default(append) | 18/80 = 22.5% | 18/49 = 36.7% |
| hypothesis(append) | 14/80 = 17.5% | 14/49 = 28.6% |
| hypothesis(legacy) | 18/80 = 22.5% | 18/49 = 36.7% |

| pair | sum | mean diff/scene ± se | W-L-T | sign test |
|---|---|---|---|---|
| default(append) − hypothesis(append) | 18 vs 14 | +0.20 ± 0.17 | 6-3-11 | p = 0.508 |
| hypothesis(legacy) − hypothesis(append)  **same agent** | 18 vs 14 | +0.20 ± 0.25 | 5-4-11 | p = 1.000 |
| default(append) − hypothesis(legacy) | 18 vs 18 | +0.00 ± 0.21 | 4-6-10 | p = 0.754 |
| prolong(legacy) − hypothesis(append) | 28 vs 14 | +0.70 ± 0.25 | 10-2-8 | p = 0.039 |
| prolong(legacy) − default(append) | 28 vs 18 | +0.50 ± 0.22 | 8-2-10 | p = 0.109 |
| prolong(legacy) − hypothesis(legacy) | 28 vs 18 | +0.50 ± 0.26 | 8-2-10 | p = 0.109 |

## 2. Geometry: what the milestones actually ask for

The 49 position milestones sit a median **10.1 blocks** from spawn behind a median **5-block** radius, so the median milestone asks the agent to close **5.1 blocks** and point the camera within half of a 60° tolerance.

| arm | ever inside the radius | of those, earned | never near | near, never faced | median closest approach − radius |
|---|---|---|---|---|---|
| default(append) | 21/49 | 18/21 | 28 | 3 | +1.09 blocks |
| hypothesis(append) | 20/49 | 14/20 | 29 | 6 | +0.52 blocks |
| hypothesis(legacy) | 23/49 | 18/23 | 26 | 5 | +0.14 blocks |

## 3. Behaviour

Medians over the 20 shared scenes; the sign test is paired per scene against `default`.

| metric | default(append) | hypothesis(append) | hypothesis(legacy) |
|---|---|---|---|
| steps issuing a manipulation action | 0.2% | 5.0% (W-L 15-2, p = 0.002) | 14.8% (W-L 16-1, p = 0.000) |
| steps issuing a camera move | 36.5% | 30.0% (W-L 8-11, p = 0.648) | 26.8% (W-L 8-12, p = 0.503) |
| steps issuing a locomotion key | 53.0% | 57.5% (W-L 11-9, p = 0.824) | 72.0% (W-L 15-5, p = 0.041) |
| yaw swept over the episode (°) | 4865 | 3103 (W-L 10-10, p = 1.000) | 1500 (W-L 4-16, p = 0.012) |
| blocks walked | 21 | 21 (W-L 8-12, p = 0.503) | 29 (W-L 16-4, p = 0.012) |
| reply size (chars) | 899 | 1359 (W-L 20-0, p = 0.000) | 1704 (W-L 20-0, p = 0.000) |

| arm | ESC actions, 20 scenes | cells with any ESC | cells with ≥20 |
|---|---|---|---|
| default(append) | 16 | 2/20 | 0 |
| hypothesis(append) | 296 | 6/20 | 3 |
| hypothesis(legacy) | 53 | 6/20 | 1 |

## 4. The hypothesis agent's own counters

Across all **48 hypothesis cell-runs** (both layouts, 719 graph nodes):

- **653 reverted goal confirmations** (13.6 per cell; 47 of 48 cells have at least one). Each one is the model marking a task goal `confirmed` while the environment says NOT verified.
- **429 dropped ESC presses**, in 15 of 48 cells (5 of them ≥ 20).
- Node kinds: **mechanism 47%**, **goal 25%**, **location 22%**, **other 4%**, **state 3%**.
- Node status at the end: refuted 41%, active 37%, confirmed 13%, stale 6%, locked 3%, under test 0%.

Cells that try to end the episode early, over every cell each arm has: **hypothesis 15/48 (31%) against default 3/33 (9%)** — Fisher exact **p = 0.028**.

