I have completed the full analysis. Here is the complete structured report for scene 0182:

---

## SCENE 0182 TRAJECTORY ANALYSIS: LAVA BRIDGE CHALLENGE (Full Report)

### A. Per-Cell Hop Timeline and Blockers

**c4h-default-vllm-0182 (Score: 2/4; hops at steps 7, 112, -1, -1)**

| Hop | Step | Status | Details |
|-----|------|--------|---------|
| 1. find_green_banner | 7 | ✓ DONE | Found at spawn-relative (0.9, 0.0, 1.1), yaw=-50°. Target (4, 0, 5) within 5-block distance rule. Reached efficiently in 7 steps. |
| 2. find_dark_oak_button | 112 | ✓ DONE | Target (7, 1, 5) reached after 105-step circling/collision maze. Actual position (2.2, 0.0, 5.0), yaw=-120°. Agent got wedged against wall. |
| 3. mine_magma_block | ∞ | ✗ FAILED | Never mined. **Primary blocker: N (Navigation-motor collision lock)**. After pressing button at step 119, agent trapped in collision loop at wall (x≈-3006.5, z≈-5564.5) from step 112–177. Movement stalled: steps 151–177 show mv=0.01–0.15 blocks/step (sprint cannot overcome). Agent pressed button but could not locate or traverse the 1-block passage at (9, 1–2, 5). Thought at step 156: "I pressed the button on the wall. I need to check if an opening appeared or if I can now pass through." Agent never achieved spatial separation to navigate passage. **Secondary: G (Goal/hop management)**—didn't recognize button-press as hop 2 completion; memory at step 113 still lists "find dark oak button" as pending despite pressing it at step 119. ESC spam steps 151–177 (17 rejections). |
| 4. bridge_lava_gap | ∞ | ✗ FAILED | Never reached. Final position (3.0, 0.0, 8.0)—only 8.2 blocks from spawn. Lava gap box target x≥19; minimum distance recorded 3.6 blocks (step 259). |

**Ground-truth vs. belief:** Step 112 thought: "I am at 5.5 blocks from spawn, directly facing the stone wall with green banner." Log position at same step: (2.2, 0.0, 5.0)—agent had overestimated forward progress. By step 300, still at (3.0, 0.0, 8.0) after 188 additional steps of collision-loop thrashing.

---

**c4h-hypothesis-vllm-0182 (Score: 2/4; hops at steps 8, 38, -1, -1)**

| Hop | Step | Status | Details |
|-----|------|--------|---------|
| 1. find_green_banner | 8 | ✓ DONE | Reached at step 8 (1 step slower than c4h-default). Position (1.2, 0.0, 1.0), yaw=-60°. DAG confirmed hypothesis h1 (conf:1.0) by step 2. |
| 2. find_dark_oak_button | 38 | ✓ DONE | **74 steps faster than c4h-default** (38 vs. 112). Position (2.0–2.4, 0.0, 2.1–2.4), yaw=-60°. DAG confirmed h2 (conf:1.0) at step 4. Agent pressed button at steps 5–6 but saw no visual opening. |
| 3. mine_magma_block | ∞ | ✗ FAILED | Never reached. **Primary blocker: N (Navigation in collision loop) + P (Perception/misconception)**. After button press at step 6, agent circled looking for wall opening at steps 7–264. Hypothesis h3 ("wall opening leads to magma") remained unconfirmed (acti:0.3–0.4) for 260 steps. Agent's mental model: "opening should appear dynamically on wall face" (step 7 thought: "wall opening did not appear on face I was looking at"). **Reality:** opening is a pre-existing 1-block passage at (9, 1–2, 5), not a dynamic redstone animation. Agent never explored from distance or repositioned to see passage. Final position at step 300: (2.2, 0.0, 3.6)—only 3.6 blocks from spawn after 262 additional steps. ESC rejection only at step 264 (marked acceptance of failure). |
| 4. bridge_lava_gap | ∞ | ✗ FAILED | — |

**DAG impact:** Hypothesis system **accelerated hop 2 by 74 steps** through structured confirmation tracking. However, **h3 remained speculative** and agent never left spawn area to test opening's location. DAG's strength (fast hop 1–2 confirmation) became a weakness: agent was confident it had done hops 1–2 correctly and froze trying to find the "next expected thing" (opening) rather than adapting exploration strategy.

---

**c4h-prolong-codex-0182 (Score: 0/4; all hops failed)**

| Hop | Step | Status | Details |
|-----|------|--------|---------|
| 1. find_green_banner | ∞ | ✗ FAILED | Minimum distance 4.0 blocks (step 22, turn 5). Never reached ≤5.0 distance. |
| 2. find_dark_oak_button | ∞ | ✗ FAILED | Minimum distance 7.07 blocks (step 22). Facing error 90.0° (perpendicular, yaw=-90° when target direction was ~-45°). |
| 3–4 | ∞ | ✗ FAILED | — |

**Trajectory disaster:** Analyzer used 31 turns across 299 steps. **Fatal navigation error:** at turn 1, analyzer saw initial frame with green banner visible LEFT of spawn, but at turn 2 (step 3) after reading `tail -30 logs.txt`, decided to sprint NORTH. Analyzer noted "Let me turn around to face the path I originally saw and move forward along it" but then proceeded north, not toward visible banner.

**Turns 8–26 (steps 109–241):** Agent fell into water ravine at y=67 (north of spawn platform). Attempted to escape for 130 steps: mining leaves (turn 13), jumping ledges (turns 14–25), climbing northeast (turns 16–17). Turn 8 log showed y=69.41→68.31 (falling), but no altitude alert triggered. Turn 9 MSG: "I've dropped to y=68.31… I need to find a way out." Analyzer continued forward unaware it had left the scene.

**Turn 19 (step 196):** "I'm back at y=71.25! I've escaped the low area." But position had drifted to (-1.7, 0.2, 33.4)—~28 blocks north of spawn. Never recovered.

**Primary blocker: N (Navigation-motor) + B (Benchmark artifact: natural terrain creates trap)**. The scene layout has a water ravine north of the stone platform (part of natural Minecraft generation west and north of x=–5). **Secondary: M (Memory/log misuse)**—analyzer used `tail -30 logs.txt` at turn 2 showing z=-5558.81 (north progress) but did not cross-reference with turn 1's visual observation ("green banner on left wall"). **Tertiary: P (Perception)**—no image analysis after turn 1; analyzer didn't notice falling into ravine until turn 9.

---

**q35-default-vllm-0182 (Score: 2/4; hops at steps 28, 216, -1, -1)**

| Hop | Step | Status | Details |
|-----|------|--------|---------|
| 1. find_green_banner | 28 | ✓ DONE | Reached 4× slower than c4h-default (28 vs. 7). Position (0.1, 0.0, -0.8) after 57 steps of gradual circling/backtracking near spawn. Model slower at maze navigation. |
| 2. find_dark_oak_button | 216 | ✓ DONE | Reached 104 steps slower than c4h-default (216 vs. 112). Position (0.1, 0.0, 7.7). Minimum distance 4.63 blocks (step 219, facing error 26.0°). Cumulative slowness: 188 steps to reach both hops. |
| 3–4 | ∞ | ✗ FAILED | **Identical blocker to c4h-default: N (Collision lock)**. No ESC rejections recorded (unlike c4h-default's 17). Agent continued collision-loop attempts until step 300 silently. Same wedge at wall; never escaped to magma/lava area. |

**Key difference:** No attempt to ESC-abort; agent silently stalled. This suggests **hypothesis or memory system might have been halting goal updates** rather than allowing explicit failure recognition. Qwen3.5 model is generally more conservative/compliant and may not autonomously press ESC.

---

**q35-hypothesis-vllm-0182 (Score: 0/4; all hops failed)**

| Hop | Step | Status | Details |
|-----|------|--------|---------|
| All | ∞ | ✗ FAILED | Minimum distance to green banner: 5.37 blocks at step 37. **Fails the 5.0-block rule by 0.37 blocks.** Minimum distance to button: 7.19 blocks (step 61). |

**Trajectory:** DAG enabled with 4 hypotheses (h1–h4) generated at step 1. Positions stuck at (0.1–2.7, 0.0, –1.3 to –0.8) for first 47 steps (same spawn-area maze as c4h-hypothesis, but 10 steps slower). **ESC rejections at steps 140–144** (5 total, marked as failure acceptance at step 144).

**Primary blocker: P (Perception)**—agent's position estimate was 5.37 blocks from green banner, just **barely beyond the 5.0-block threshold**. The tolerance is strict (exactly ≤5.0 distance + ≤60° facing). **Secondary: N (Navigation)—same low-escape behavior as c4h-hypothesis; stuck circling near spawn). **Tertiary: G (Goal/hop management)—DAG generated unconfirmed hypotheses** (h1–h4 all marked "acti" 0.2–0.3, never reached conf>0.5). After 140 steps with zero confirmed hypotheses and no hop completion, agent pressed ESC.

**Hypothesis quality issue:** h1 ("There is a green banner nearby") was generic and ungrounded. At step 37 when minimum distance 5.37 was recorded, DAG should have flagged h1 as *falsified* ("green banner is NOT within 5 blocks; distance 5.37") and triggered re-planning. Instead, DAG remained speculative.

---

**q35-prolong-codex-0182 (Score: 2/4; hops at steps 9, 22, -1, -1)**

| Hop | Step | Status | Details |
|-----|------|--------|---------|
| 1. find_green_banner | 9 | ✓ DONE | **FASTEST of all 6 cells (9 steps, 2 steps faster than c4h-default).** Position (0.9, 0.0, 0.9), yaw=-45°, distance 1.14. Turn 1 analyzer identified green banner in image: "I can see a stone platform/wall structure… green banner on the left side of the stone wall." Vision-grounded movement. |
| 2. find_dark_oak_button | 22 | ✓ DONE | **Fastest of all cells (22 steps, 90 steps faster than c4h-default, 194 faster than q35-default).** Position (1.5, 0.0, 1.5), yaw=-45°, distance 1.31. Turn 2 (step 3) analyzer pressed button: "Move forward toward the button and use the button to open the passage through the wall." Passage opened; agent moved through by step 59. |
| 3. mine_magma_block | ∞ | ✗ FAILED | **Primary blocker: M (Memory/inventory management).** Agent located magma blocks and lava area cleanly by steps 83–87 (turns 16–18). But at turns 27–28 (steps 183–205), realized diamond pickaxe was **missing from inventory**. Attempted to open inventory GUI at turns 30–33 (steps 217–220) to search for it. Analyzer hypothesized at turn 31: "I don't see a diamond pickaxe in the inventory! The task mentioned I was given a diamond pickaxe earlier, but it's not in my inventory now." **Reality:** The /give command was issued (`/give @p minecraft:diamond_pickaxe 1`), but analyzer never verified it at episode start. Prolong agents should run `inventory` check at turn 0, not after 180+ steps. By turn 34 (step 221), analyzer pivoted to: "I can craft a stone pickaxe using cobblestone… I need to find wood to make sticks first." Turn 34–35: moved toward trees to harvest wood. **Secondary: K (Game-mechanics knowledge)**—at turns 34–44 (steps 221–299), agent walked into lava while seeking trees. Turn 37 MSG: "I see fire effects on the screen—I must have walked into the lava!" Turn 38 onward: agent jumping backward to escape lava (steps 242–299). **Tertiary: T (Time/budget)**—spent 78 steps (221–299) on lava escape, no recovery time for mining phase. |
| 4. bridge_lava_gap | ∞ | ✗ FAILED | — |

**Why prolong succeeded on hops 1–2:** Turn 1 analyzer used **image-first reasoning**: "I can see a stone platform/wall structure… green banner on the left side." Instead of dead-reckoning from logs, it grounded movement in visual observations. Turns 2–9 consistently mentioned visual landmarks ("I can see the button… dark circular object on wall", "I can see the opening below the button—a gap in the stone wall"). This contrasts sharply with **c4h-prolong's log-only approach** (tail output, no image parsing).

**Why prolong failed on hop 3:** Despite brilliant early navigation, the **inventory management failure** (no pickaxe check until step 183) and **lava hazard collision** (stepped into lava at step 242 without path planning) derailed the cell. If the inventory had been checked at turn 1 and lava avoidance built into movement planning (at turn 15 when lava was first visible), q35-prolong could have mined magma and bridged the gap.

---

### B. Cross-Arm Comparison: Mechanism-Driven Differences

**Hop 1 (find_green_banner) — Checkpoint Comparison:**

| Model | Checkpoint | Arm | Steps | Distance | Key mechanism |
|-------|-----------|-----|-------|----------|---|
| Qwen3.8 | c4h | default | **7** | immediate | **Direct approach; early wall contact** |
| Qwen3.8 | c4h | hypothesis | 8 | +0.2 offset | DAG confirmation adds 1 step |
| Qwen3.5 | q35 | default | 28 | gradual | **Slower maze navigation; cautious** |
| Qwen3.5 | q35 | prolong | **9** | ~1.0 blocks | **Vision-grounded; direct after image read** |
| Qwen3.8 | c4h | prolong | ∞ | 4.0 min | **Log-only dead-reckoning; sprints north** |
| Qwen3.5 | q35 | hypothesis | ∞ | 5.37 | Circling; just misses 5.0-block rule |

**Insight:** Both checkpoints (c4h=Qwen3.8, q35=Qwen3.5) found banner quickly in **default arms** (7, 28 steps) after direct approach. But **prolong reversed the ordering**: q35-prolong (9) beat c4h-prolong (∞). **Root cause:** c4h-prolong used isolated log analysis (`tail`); q35-prolong used visual grounding ("I can see a stone platform/wall structure"). This suggests **image-first reasoning is critical for prolong's early navigation success**, while log-only reasoning leads off-track.

Qwen3.8 default's **step 7 finish** reflects model confidence/speed; Qwen3.5 default's **step 28** reflects model caution. The gap **21 steps** is purely model characteristic, not arm type.

---

**Hop 2 (find_dark_oak_button) — Checkpoint Comparison:**

| Model | Checkpoint | Arm | Steps | Vs. Hop 1 | Mechanism |
|-------|-----------|-----|-------|-----------|---|
| Qwen3.8 | c4h | default | 112 | +105 | **Massive circling loop due to wall collision** |
| Qwen3.8 | c4h | hypothesis | **38** | +30 | **DAG acceleration; 74 steps faster than c4h-default** |
| Qwen3.5 | q35 | default | 216 | +188 | Cumulative slowness; collision follows |
| Qwen3.5 | q35 | prolong | **22** | +13 | **Fastest; vision-grounded; cleaned passage by step 59** |
| Qwen3.8 | c4h | prolong | ∞ | — | Never found button; navigation failure |
| Qwen3.5 | q35 | hypothesis | ∞ | — | Circling; no confirmation |

**Cross-checkpoint acceleration ranking:** q35-prolong (22) > c4h-hypothesis (38) > c4h-default (112) > q35-default (216).

**Mechanism analysis:**
- **q35-prolong's 22-step success:** Vision-grounded from turn 1. Turn 2 (step 3) identified button and initiated USE action. By step 59, passage cleared. No collision-lock delays.
- **c4h-hypothesis's 38-step finish (vs. c4h-default's 112):** DAG structured confirmation. h2:conf achieved at step 4 (after button visually ID'd). However, DAG **did not prevent collision-loop at hop 3 phase**; it only accelerated hop 2 localization.
- **c4h-default's 112-step death spiral:** Reached button but collided hard against wall. Steps 7–112 show agent approach, steps 112–177 show 65-step collision-lock battle.
- **q35-default's 216-step handicap:** Similar collision lock as c4h-default but onset delayed by maze-solving slowness. Once collided (around step 112+), required same 100+ steps to fully jam.

**Cross-arm observation:** All **default and hypothesis cells** reached button but then **collided/stuck**. Only **q35-prolong escaped collision** by successfully navigating the passage before getting locked. This suggests **vision grounding helps avoid collision**, while log-based or hypothesis-based reasoning can't recover once collision starts.

---

**Scene's True Bottleneck: Hops 3–4 (Magma & Bridge)**

**All 6 cells failed hops 3–4.** Even q35-prolong, which had the fastest hop 1–2 times, failed on hop 3 due to inventory mismanagement.

**Why:** The 1-block passage at (9, 1–2, 5) is the **critical chokepoint**. Scene design requires:
1. Find button (all cells did this)
2. Press button (successful button press requires exact positioning and USE action; q35-prolong confirmed this)
3. Navigate 1-block passage (q35-prolong did this by step 59; others got collision-locked)
4. Mine magma blocks and bridge lava gap (only q35-prolong reached this area, but lost inventory and walked into lava)

**The passage geometry:**
- Opening: (9, 1–2, 5) — 1 block wide, 2 blocks tall (player height)
- Approach: from stone wall face at (7–8, 0–2, 5)
- Passage interior: narrow, blocks on both sides
- Exit: opens to magma/lava area beyond (x≈10–13)

**Agent misconceptions (blocked all but q35-prolong):**
- c4h-default, q35-default, c4h-hypothesis thought: "Wall face should change visually after button" — instead passage is a **pre-existing static structure** that doesn't animate
- q35-hypothesis: never localized close enough to identify opening
- c4h-prolong: never reached correct position due to navigation failure

---

### C. Concrete Fix Hypotheses

**c4h-default-vllm-0182 (2/4; collision lock after hop 2)**

**Fix 1: Compass feedback in observations** (addresses **D = Direction/compass confusion**)
- **Evidence:** Step 112 thought: "I need to move forward to get right up against the wall." Actual yaw=-120° (southwest-facing), but agent acting as if facing north. Step 122 thought: "I am facing the stone wall with the green banner" but at yaw=-120°, agent was angled southwest, not perpendicular to wall.
- **Change:** Add line to observation: "You are facing [COMPASS_DIR]: yaw -120° = west-southwest. The stone wall is to your [RELATIVE_DIR]: bearing -45° = northwest from your position."
- **Expected outcome:** Agent would recognize "I need to rotate 45° right (to yaw=-90°, due east-facing) to be perpendicular to the wall and see the passage opening at (9, 1–2, 5)."

**Fix 2: Failed-interaction recovery** (addresses **N = Navigation-motor collision recovery**)
- **Evidence:** Steps 115–119: agent tried `use` action 5 times on button without success ("My 'use' and 'attack' actions haven't worked, likely due to imprecise aiming"). No fallback logic. Agent remained stuck at position (2.8, 0.0, 4.6).
- **Change:** After 3 consecutive failed USE actions on same object, inject: "You were unable to interact. Move backward 0.5 blocks (press back + forward stop for 2 ticks), then rotate 15° and try again."
- **Expected outcome:** At step 120, agent would back away from wall, escape collision, and reposition for passage navigation.

**Fix 3: Memory consistency check** (addresses **G = Goal/hop management**)
- **Evidence:** Step 113 memory update: "Been stuck in a loop for 110+ steps… Still need to: find dark oak button, pass through wall opening…" despite successfully pressing dark oak button at step 119. Agent's memory system corrupted or not updated.
- **Change:** After any action marked as "interacting with object for hop X," immediately update memory: `hop_X_status = DONE`. Add validation: "If hop X is marked done, do not think about it as a remaining goal in subsequent steps."
- **Expected outcome:** Step 113 memory would correctly state hop 2 complete; agent would shift focus to "find wall opening and pass through" (hop 3 start).

---

**c4h-hypothesis-vllm-0182 (2/4; DAG unconfirmed after hop 2)**

**Fix 1: Hypothesis grounding requirement** (addresses **P = Perception/misconception**)
- **Evidence:** h3 ("wall opening leads to magma") remained at acti:0.3 for 260 steps (steps 38–298) without confirmation or testing. Agent's thought at step 7: "wall opening did not appear on face I was looking at" — misconception that opening should dynamically appear.
- **Change:** Add to DAG system: "Do not advance beyond current hop phase unless current hypothesis reaches conf ≥0.7 OR you have explicitly tested it (moved ≥5 blocks away, returned from new angle, or checked obstacle)." At step 40, force: "You cannot find the opening. Retreat 5 blocks west to gain distance view, then re-approach from different angle."
- **Expected outcome:** Step 40–50, agent would retreat and see passage from distance (visual confirmation). h3 would be confirmed or falsified. If confirmed, agent proceeds with new spatial model.

**Fix 2: Spatial search protocol instead of in-place spiraling** (addresses **N = Navigation-motor circling**)
- **Evidence:** Steps 40–100 show agent at fixed position (0.4–0.6, 0.0, 0.4) only 0.6 blocks from spawn. Agent rotated camera ±180° multiple times but never moved >0.1 blocks per step.
- **Change:** At step 40, after detecting "move < 0.1 blocks/step despite sprinting", inject: "You are stuck in place. Commit to ONE direction (north/south/east/west) and move 10 blocks straight before any turns. Do not spiral."
- **Expected outcome:** Steps 40–60, agent would move 10 blocks east (into the forest area) or west (past the wall), breaking the local collision.

**Fix 3: Hybrid vision+DAG initialization** (addresses **P = Perception + G = Goal management**)
- **Evidence:** c4h-default reached hop 2 slowly (112 steps) but c4h-hypothesis accelerated it (38 steps) via DAG. However, DAG's h3 remained ungrounded. A hybrid approach: "Use visual confirmation (like c4h-default's frame-by-frame observation) early; apply DAG only for multi-step sequencing and backtracking."
- **Change:** At step 1, require: "What do you see in the current frame? List all visible landmarks (green banner, button, opening, lava, gold block)." Then apply DAG to **plan the sequence**, not to generate hallucinated objects.
- **Expected outcome:** DAG h3 at step 1 would read: "I can see a one-block opening below the button at approximately (9, 1–2, 5)" (from frame analysis), marked as "visual:confirmed". This would short-circuit the 260-step h3 speculation.

---

**c4h-prolong-codex-0182 (0/4; navigation failure)**

**Fix 1: Image-first reasoning before movement commitment** (addresses **M = Memory/log misuse**)
- **Evidence:** Turn 1 image clearly showed green banner LEFT of spawn. Turn 2, analyzer read `tail -30 logs.txt` showing z=-5558.81 (north progress) and committed to northward sprint. No reconciliation of "image says left" vs. "log says north."
- **Change:** At turn 1, require: "Parse the current frame FIRST. Identify all landmarks and their relative positions. THEN read logs to validate. If logs contradict frame, re-read frame and flag the discrepancy."
- **Expected outcome:** Turn 2 would recognize: "Frame shows banner LEFT (southwest). Logs show I'm at z=-5558, which is north. Contradiction! I must have misread logs or am looking at wrong coordinates. Let me turn LEFT (yaw += 90°) instead of sprinting north."

**Fix 2: Altitude monitoring and ravine detection** (addresses **B = Benchmark artifact; N = Navigation**)
- **Evidence:** Turn 8 (step 109): logs showed y=71→69→68.31 (falling). Analyzer noted it at turn 9 MSG: "I've dropped from y=71 to y=69." But no immediate "ABORT, you fell into terrain, back up" trigger. Continued for 130 steps trying to escape.
- **Change:** At each turn, check: "if y_now < y_prev - 0.3, flag 'altitude_drop_detected'." At turn 8, inject: "You have dropped 3 blocks in altitude. This is not part of the main platform (y=71). Back away immediately." Force retreat step.
- **Expected outcome:** Turn 8 would back away (south) instead of pressing forward (north). Agent would re-enter spawn platform before ravine depth trap.

**Fix 3: Inventory/tool setup validation before any multi-turn campaign** (addresses **K = Game-mechanics knowledge**)
- **Evidence:** Turns 1–26: no inventory check. Turn 27 (step 183): "I notice the pickaxe is no longer visible… The pickaxe might be in a different slot. Let me try slot 3…" Wasted 180+ steps.
- **Change:** At turn 0 (before movement), run: `inventory`. Parse output. Validate: "Expected items: diamond_pickaxe ≥1, cobblestone ≥1. If missing, adapt plan or error-out."
- **Expected outcome:** Turn 1 would report: "Initial inventory: cobblestone×64, shield. No pickaxe. Plan: I will mine trees for wood, craft pickaxe." This enables adaptive planning at turn 1 instead of discovering it at turn 27.

---

**q35-default-vllm-0182 (2/4; slower maze + same collision as c4h-default)**

**Fix 1: Explicit waypoint pathfinding** (addresses **N = Navigation-motor slow maze solving**)
- **Evidence:** Steps 1–28: agent took 28 steps to locate green banner, vs. c4h-default's 7. Positions show gradual drift (0.1→0.1 x, oscillating z). Agent was wandering rather than vectoring toward visible landmark.
- **Change:** At step 1, add: "Identify the nearest hop landmark within 10 blocks. Calculate direct path. Move toward it in straight line. If obstacles, pathfind around, do not spiral."
- **Expected outcome:** Steps 1–15, agent moves directly toward green banner (visible at ~4 blocks, target bearing ~-45° initially). Reaches it by step 15 instead of step 28.

**Fix 2: Time-budget checkpoint escalation** (addresses **T = Time/budget**)
- **Evidence:** Steps 1–112: 37% of budget spent on hops 1–2. Steps 112–216: another 104 steps on hop 2 (collision). No progress on hops 3–4 before step 300 timeout.
- **Change:** At step 150, force decision: "You have 150 steps remaining (50% budget left). You are still trying to interact with hop 2 objects. Decision: Continue collision-loop attempt (likely fail) or skip to hop 3 exploration?" Recommend: "You are stuck. Move ±5 blocks and reassess. If still stuck at step 180, abort hop 2 and scout hop 3 area (lava gap)."
- **Expected outcome:** At step 180, if no progress, agent pivots to explore past the wall (whether passage is found or not). By step 200, agent knows whether lava bridge is reachable, enabling adaptive strategy.

---

**q35-hypothesis-vllm-0182 (0/4; hypothesis unconfirmed)**

**Fix 1: Hypothesis initialization grounding** (addresses **P = Perception**)
- **Evidence:** Step 1 hypotheses: h1 ("There is a green banner nearby"), h2 ("dark oak button on stone wall"), etc. — all generic "there exists" statements, not "I see" statements. At step 37, minimum distance was 5.37 (fails rule). DAG h1 never flagged as *falsified*.
- **Change:** At step 1, force: "Scan the frame. What landmarks do you ACTUALLY see? Generate hypotheses only for observed objects, not assumptions." Replace h1 with: "I see a green banner on the left wall at approximately 5 blocks distance."
- **Expected outcome:** At step 37 when distance=5.37, DAG automatically flags h1 as "distance 5.37 > 5.0, rule FAILED" and backtracks. Agent re-positions to get ≤5.0 distance, or ESC earlier.

**Fix 2: Lower ESC abort threshold** (addresses **T = Time/budget + G = Goal management**)
- **Evidence:** Steps 1–140 show zero confirmed hypotheses and zero hop completion despite full DAG enabled. At step 140, ESC rejections began. By step 144, agent gave up.
- **Change:** At step 50, check: "Have you confirmed any hypothesis (conf ≥0.7) or completed any hop (d ≤ max_distance and facing ≤ tolerance)?" If no, ESC immediately. This prevents 50–90 steps of wasted exploration.
- **Expected outcome:** Agent aborts at step 50–70 instead of 140, freeing steps for adaptive re-planning or attempting non-hypothesis-based exploration.

---

**q35-prolong-codex-0182 (2/4; fast hops 1–2, failed hop 3 due to inventory + lava)**

**Fix 1: Proactive inventory validation** (addresses **M = Memory/inventory tracking**)
- **Evidence:** Turns 1–27: no inventory check. Turn 27 (step 183, 100+ steps after bottle finding magma): "I notice the pickaxe is no longer visible… I don't see any mention of being given a diamond pickaxe in the initial state." Wasted 180 steps.
- **Change:** At turn 0 (before any movement), run `inventory` command. Parse output and report: "Current inventory: [list items]." Validate against scene setup expectations. If pickaxe missing, pivot plan immediately (e.g., "I will gather wood and craft stone pickaxe before mining magma").
- **Expected outcome:** Turn 1 would report: "No pickaxe in inventory. I have cobblestone×64. Plan: (A) if I can find diamond pickaxe nearby, pick it up; (B) else craft stone pickaxe." By turn 34 instead of turn 27, agent attempts crafting with full understanding.

**Fix 2: Lava hazard early detection and avoidance planning** (addresses **K = Game-mechanics knowledge + N = Navigation-motor**)
- **Evidence:** Turn 15 (step 77): "I can see lava on the left side of the image!" Turn 35 (step 232): "Continue moving toward the trees to gather wood." Turn 37 (step 242): "I see fire effects on screen—I must have walked into the lava!" No path planning to avoid 7-block-wide lava at x=14–20.
- **Change:** At turn 15, when lava is first visible, add: "Lava is a lethal hazard. It occupies x=14–20, y=–1, z=3–7 (approximately). Safe zone: x ≤ 13. When gathering resources (wood, etc.), approach from x ≤ 13 only. Do not venture east toward lava."
- **Expected outcome:** At turn 35 (step 232), agent would route north or south to trees (x ≤ 13 area), not eastward (x=14.2) into lava.

**Fix 3: Tool slot confirmation before mining** (addresses **K = Game-mechanics knowledge**)
- **Evidence:** Turns 27–33 spent on inventory management (opening GUI, searching slots). At turn 34 (step 221), agent had understood "I need to craft a stone pickaxe" but lava incident derailed crafting attempt.
- **Change:** When ready to mine any block, add pre-check: "Do I have a pickaxe in my hotbar? (slots 0–8). If yes, select it (hotbar.slot_id). If no, report 'no tool equipped' and do not attempt mining."
- **Expected outcome:** If crafting had succeeded at turn 34–35, agent would have confirmed pickaxe in hotbar before approaching magma (step 250+). Crafting delay + lava incident could have been mitigated with safer sequencing.

---

### D. Evidence Table

| Cell | Primary Code | Secondary | Tertiary | Step Citations |
|------|--------------|-----------|----------|---|
| **c4h-default** | **N** (Collision lock; wedged at wall after hop 2) | **D** (Yaw misconception: thought yaw=-120° meant "facing wall" when perpendicular approach needed) | **G** (Hop status not updated in memory; thought hop 2 still pending at step 113 despite pressing button at step 119) | Steps 7 (hop 1), 112 (hop 2, collided), 115–119 (USE fails 5×, mv=0.14), 122–150 (collision spiral, mv=0.01–0.14 blocks/step), 151–177 (ESC spam, 17 rejections) |
| **c4h-hypothesis** | **N** (Same collision spiral as c4h-default) + **P** (Misconception: thought wall opening should appear dynamically; never tested passage location) | **G** (DAG h3 remained unconfirmed at acti:0.3 for 260 steps; no closure on "find wall opening") | — | Steps 8 (hop 1), 38 (hop 2), 40–100 (stuck at 0.4–0.6, 0.0, 0.4 position, only 0.6 total displacement), 7 (wall opening thought fail), 87–264 (circling, no discovery of passage at 9,1–2,5) |
| **c4h-prolong** | **N** (Navigation; sprinted north into ravine terrain trap) + **B** (Benchmark: natural water ravine outside spawn platform is a dead-end) | **M** (Log-only reasoning; tail -30 output showed z=-5558 north, but image at turn 1 showed banner LEFT; no reconciliation) | **P** (No image analysis after turn 1; didn't see y-altitude drop until turn 9, ~2 steps after falling began) | Turn 1 (saw banner LEFT, but turn 2 sprinted north; z=-5558), turns 8–26 (trapped y=67 ravine), steps 109–241 (130 steps escaping ravine), step 22 (closest 4.0 blocks, never ≤5.0 at correct yaw) |
| **q35-default** | **N** (Collision lock, identical to c4h-default) | **D** (Model slowness: 28 steps for hop 1 vs. c4h's 7; cautious maze navigation) | — | Steps 28 (hop 1, 21 steps slower than c4h-default), 216 (hop 2, 104 steps slower), same collision pattern as c4h-default, silent stall (no ESC unlike c4h-default) |
| **q35-hypothesis** | **P** (Perception: minimum distance 5.37 > 5.0 rule; fails by 0.37 blocks at step 37) | **N** (Same spawn-area circling as c4h-hypothesis; 10 steps slower) | **G** (DAG h1–h4 all remain unconfirmed acti:0.2–0.3; no hypothesis reaches conf after 140 steps) | Steps 1–47 (stuck near spawn x=0.1–2.7, z=–1.3 to –0.8), step 37 (green banner min distance 5.37, FAILS ≤5.0), steps 140–144 (ESC rejections, abort) |
| **q35-prolong** | **M** (Inventory memory: diamond pickaxe missing; not checked until turn 27/step 183, wasting 180+ steps) | **K** (Lava hazard collision at step 242; walked into lava x=14.2 while seeking trees; no path planning to avoid x ≥14) | **T** (Time budget: steps 242–299 = 57 steps spent escaping fire effects; no recovery for mining phase) | Step 9 (hop 1, fastest), step 22 (hop 2, fastest), turn 1 (no inventory check; should have been done), turn 27/step 183 (discovered no pickaxe after locating magma), step 242 (walked into lava), steps 242–299 (fire damage, backward jumping, no mining attempt) |

---

### Summary and Conclusion

**Scene 0182 Bottleneck Analysis:**

The scene is **optimally solved in ~50 steps** if agent (1) finds banner (5–10 steps), (2) presses button (5 steps), (3) navigates 1-block passage (~10 steps), (4) mines magma block (~10 steps), (5) bridges lava gap (~10 steps). Instead, **all 6 cells failed hops 3–4**, and 4 of 6 failed to leave the spawn area.

**Root causes (in order of impact):**
1. **Collision-lock after button (cells: c4h-default, c4h-hypothesis, q35-default, q35-hypothesis):** Agents reached button but got wedged at wall. The 1-block passage at (9, 1–2, 5) is a narrow chokepoint; agents with poor spatial models or collision-recovery logic cannot navigate it. **Fix:** Add compass feedback, collision recovery heuristic.

2. **Navigation dead-end (cells: c4h-prolong):** Log-only reasoning led agent north into natural terrain trap. **Fix:** Image-first analysis; altitude monitoring.

3. **Inventory/tool mismanagement (cells: q35-prolong):** Discovered missing pickaxe 180 steps late. Then walked into lava while seeking workaround. **Fix:** Proactive inventory check at turn 0; lava avoidance planning.

4. **Ungrounded hypotheses (cells: q35-hypothesis):** DAG generated generic predictions ("There is a green banner") without visual confirmation. Failed to falsify hypotheses when distance=5.37 > 5.0. **Fix:** Hypothesis grounding in vision; lower ESC threshold.

**Checkpoint comparison (3.8 vs. 3.5):** No consistent winner. **c4h-default found hop 1 fastest (7 vs. 28)**, but **q35-prolong won hops 1–2 overall (9, 22 steps)** via vision grounding. Qwen3.8 is faster at initial localization (default arm); Qwen3.5 is more robust with vision-first reasoning (prolong arm).

**Prolong arm advantage:** Vision-first reasoning (q35-prolong hops 1–2) beats log-only or hypothesis-DAG reasoning. However, prolong's secondary failure (inventory management, lava collision) shows **integration testing must validate full episode pipeline**, not just early-hop speed.