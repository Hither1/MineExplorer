Perfect! Now I have all the data. Let me compile the complete analysis report:

---

## Scene 0603 (three_room_exploration_corridor) — Trajectory Analysis Report

### A. Per-Cell Analysis

#### **c4h-default-vllm-0603** | Score: 0/4 → 0/2 (artifacts removed)

**Hop-by-hop timeline:**
- Hops 1–2 (find_purple_bed, find_red_nether_brick_stairs): Position artifacts; real bed at (0,0,1), real stairs at (5-7,0,5-6).
- **Hop 3 (mine_white_carpet):** Steps 6–7: Attacked at pitch +40°, position (0,0,0.2). Step 85: "I can see the purple bed and white carpet on the floor." Steps 91–93: Three attack steps at pitch –10°. Never acquired white carpet.
- **Hop 4 (mine_quartz_block):** Steps 74–89: Navigated eastward ~8.7 blocks (through/past stairs). Steps 90–103: 103 steps of attack runs at position ~x=9.2–9.3 (remaining in middle room, not reaching quartz at x=12–14). Steps 90–102: "I am right next to the white quartz block" thought, but crosshair was on obstacle, not quartz. Position never reached x≥12.

**Beliefs vs. ground truth:**
- Step 47: "I've been stuck in the bedroom for many steps, unable to mine the white carpet" — TRUE; no mining progress.
- Step 85: "I can see the white quartz block in the far room" — FALSE; position still in middle room.
- Step 90: "I am right next to the white quartz block" — FALSE; at x=8.9, ~3 blocks short.

**Primary blockers:**
- **N (navigation-motor):** Spent steps 27–73 navigating through doorway; jumped over nether stairs, circled, backed up 10+ steps. Movement coupling and wall collision.
- **K (game-mechanics):** Pitch clamped to ~–10° when trying to attack floor blocks near chest height. Never looked down enough (pitch 60° needed; max used was 40°). Attack held ≤3 consecutive steps per phase; carpet needs 5–10.
- **P (perception):** Believed it saw quartz blocks on red stairs at x=9 (actually red brick stairs). No inventory feedback; never checked whether carpet was actually in inventory.

**Secondary:** G (goal/hop management): Abandoned white carpet mining after three 1-2 step attempts; never retried. Did not verify carpet mined before moving east.

#### **c4h-hypothesis-vllm-0603** | Score: 1/4 → 0/2 (artifact removed)

**Hop-by-hop timeline:**
- **Hop 1 (find_purple_bed):** Artifact, ignored.
- **Hop 2 (mine_white_carpet):** Steps 1–10: Rotated yaw to –75°, attempted attack×3. Steps 26–168: Looped turning, jumping, strafing around perceived "red bed" obstacle blocking doorway. Believed red bed was physical blocker; never attacked white carpet.
- **Hop 3 (find_red_nether_brick_stairs):** **Step 264: Milestone fired** (position artifact). Real position at step 264: (6.2,2.2). Position targets claimed satisfied despite facing error 84° (tolerance ±22.5°); artifact of 5-block south shift.
- **Hop 4 (mine_quartz_block):** Never attempted; cap hit at step 300.

**Beliefs vs. ground truth:**
- Step 6: "I can see the purple bed to my right, the red nether brick stairs ahead-left, and the white carpet on the floor in the center" — MISIDENTIFIED. Saw red bed (not purple), red stairs at distance. Carpet is adjacent to player at (±1,0,6-7) in real coords.
- Step 160–170: "The red bed is blocking my path to the exit" — RED BED DOES NOT EXIST; purple bed is at spawn-relative (0,0,1), not blocking doorway at (2-3,0,5-6).
- Step 159: "I need to strafe left to clear the bed" — Wasted 40+ steps assuming phantom obstacle.

**Primary blockers:**
- **P (perception):** Critical misidentification. Red bed spawned at inventory but not visible in world; agent saw "red" and assumed solid object. No inventory line told it the bed was item, not block.
- **G (goal/hop management):** Abandoned mining white carpet (zero attacks on carpet itself in first 50 steps, despite being adjacent). Committed to phantom doorway problem.
- **K (game-mechanics):** Believed jumping + forward would overcome bed; tried ×4 times (steps 166–167) with no effect.

**Secondary:** N (navigation-motor): Eight-step "circling" warning issued by environment; ignored.

#### **c4h-prolong-codex-0603** | Score: 1/4 → 0/2 (artifact removed)

**Hop-by-hop timeline:**
- **Hop 2 (mine_white_carpet):** Steps 9–26: Moved to (0,0,0.2), yaw=0, pitch=55–65°. Turn 6 (step 12): attack×3. Turn 7 (step 15): attack×5. Turn 8 (step 21): attack×5. Saw particles at step 21: "carpet is cracking." Turn 9 (step 26): "carpet appears mined (particles visible)." **Never acquired item.** Position stayed at (0,0,0.2); carpet location correct, but attack not held long enough or block was wrong adjacent carpet copy.
- **Hop 1 (find_purple_bed):** **Step 38: Artifact milestone fired.** Position (–1.2, 0.1, 1.2); yaw=0; real bed ~1 block away at spawn-relative (0,0,1). Analyzer correctly noted at turn 13 "found doorway" at step 38; position was _exiting_ bedroom, not at bed.
- **Hop 3 (find_red_nether_brick_stairs):** Steps 87–100: Sprinted through doorway into middle room at x=2–4. Detected red stairs at step 87: "can see the red nether brick stairs." Position min_dist 4.63 (within 5 blocks) but facing error 90.4° (tol ±22.5° failed). Steps 100–151: Attacking red stairs and adjacent blocks at x=6.9–8.4, y=1.0. Turn 22–30: Tried "use" action (step 173), pitch varied –10° to +45°, yaw –90° to –15°. Block stayed intact; likely hitting red brick stairs (hardness 2.0) not quartz (1.5).
- **Hop 4 (mine_quartz_block):** Never reached x≥12; exhausted at 299 steps.

**Closest mining attempt (quartz):** Step 108–151. Position (6.9–8.4, 1.0, 0.5). Yaw –90° (facing east). Pitch +20°. Attack×5 to ×20 per turn. Block did not break. Real quartz at (12–14, 0, 5–6); agent 4–6 blocks short in x-direction.

**Beliefs vs. ground truth:**
- Turn 8 (step 21): "The white carpet is cracking — continuing to mine it with 5 more ticks" — UNCERTAIN; could have been stone brick floor or adjacent carpet.
- Turn 9 (step 26): "Carpet appears mined (particles visible)" — FALSE; never inventory-confirmed.
- Turn 22 (step 108): "The white block on top of the red nether brick stairs (likely the quartz block)" — MISIDENTIFIED. Red stairs have block on top in visual, but quartz is 6–8 blocks further east, on the floor of room 3.

**Primary blockers:**
- **N (navigation-motor):** Steps 33–87 (54 steps) searching for doorway; got stuck in corners, bounced off walls, backed up repeatedly.
- **K (game-mechanics):** Attack not sustained (3–5 ticks per phase). Pitch wrong for floor blocks; +20° to +30° targets block above floor (red stairs step surface), not quartz at y=0. Never adjusted after turn 15.
- **P (perception):** Misidentified red stairs block as quartz. No "block under crosshair" text line to confirm target.

**Secondary:** M (memory/context): Analyzer used `tail -20` to `-30` lines of log; never grepped for MILESTONE or parsed inventory changes to detect failed mining.

**Analyzer strategy:** Mostly adjusted pitch/yaw 5–10° per turn (turns 21–30); tried "use" action once (turn 27). Did not attempt combined forward+attack. Turns skipped from 33 to 35.

#### **q35-default-vllm-0603** | Score: 0/4 → 0/2

**Hop-by-hop timeline:**
- Similar to c4h-default: attempted mining at low pitch without holding attack. Never left bedroom effectively (last position ~x=1.2, only 1.2 blocks east of spawn).
- Never reached middle room or quartz.

**Belief (Step 145):** "I need to stop turning and moving in the same tick. I need to execute a strict 'turn, then move' strategy" — Correctly diagnosed oscillation but never recovered; continued circling.

**Primary blockers:** N, K, G (same as c4h-default, amplified by smaller navigation range).

#### **q35-hypothesis-vllm-0603** | Score: 1/4 → 0/2 (artifact removed), 202 ESC presses (steps 98–105 cluster, then 209–228 massive block)

**Hop-by-hop timeline:**
- Steps 1–12: Found red nether brick stairs (misidentified carpet attack as success).
- Steps 98–105: Pressed ESC 8 times; each rejected. Thought text at step 98: "The environment warning about circling was resolved by my previous turn and move." FALSE; circling warning still active.
- **Steps 209–228 (202 presses):** Stationary at (8.2, 0.0, 1.7). Repeatedly pressed ESC and thought: "I have completed all physical objectives: mining the white carpet, red nether brick stairs, and quartz block." **FALSE on all counts.** No white carpet in inventory. Position nowhere near quartz (x=8.2 vs x=12–14). Believed memory of successful actions despite no inventory feedback.

**Beliefs vs. ground truth (step 212):**
"I have completed all three mining objectives (white carpet, red nether brick stairs, quartz block) as confirmed by my long-term memory." — **COMPLETE FALSE COMPLETION BELIEF.** Memory corrupted or hypothesis.conf carried false state.

**Primary blockers:**
- **M (memory/context):** Critical. Memory text claimed mining success without verification. Hypothesis system believed state was terminal.
- **G (goal/hop management):** ESC spam (202 instances) attempting to pause/exit; on_esc_rejected did not trigger re-planning. No fallback when ESC failed.
- **P (perception):** Position never changed during ESC spam; stationary at wrong location. Never checked inventory or detected failure.

**Secondary:** K (game-mechanics): No attack; only ESC key pressed 202 times. Believed ESC would verify task completion.

#### **q35-prolong-codex-0603** | **Score: 2/4 → 2/2 (ONLY REAL SUCCESS)**

**Hop-by-hop timeline:**

**Hop 2 (mine_white_carpet) — SUCCESS at step 42:**
- Steps 1–9: Rotated yaw –90° to –110°, pitch 0° to 60° (aggressive downward look).
- Turns 6–8 (steps 12–21): attack×3, attack×5, attack×5. Saw particles.
- **Step 42: MILESTONE FIRED.** Position (0.3, 0.6, 0.2), yaw=–65°, pitch=60°. Carpet successfully acquired.
- Key difference: Pitch 60° looks nearly straight down (vs. c4h-prolong's max 45°); agent 2 blocks from start position.

**Hop 3 (find_red_nether_brick_stairs):** Artifact; position (6.1, –0.3) at step 51. No real achievement; ignored hereafter.

**Hop 4 (mine_quartz_block) — SUCCESS at step 253:**
- Steps 52–66: Sprint forward 3.8 blocks east; position (3.9, 0.0, –0.2), saw red stairs.
- Steps 67–165: Attacked white block on stairs (~x=4–6). Turns 18–32 tried angles –100° to –80°, pitch 20° to 30°. No progress on wrong block.
- **Turn 35 (step 166): CRITICAL PIVOT.** Analyzer noted: "Let me try a different approach - move forward and attack without changing camera angle first." Changed to **forward+attack×10** combined action.
- Steps 166–175: forward+attack×10 loop (10 steps). Position moved from 6.6 to 8.3 blocks east. Turn 36: "Now I can see the quartz block clearly with the crosshair centered on it!"
- Steps 176–235: attack×10 repeated 6 times. Position crept from 8.4 to ~10.9 blocks east. Quartz blocks are at real x=12–14, spawn-relative. Position at step 253: (11.0, 0.0, 0.2).
- **Step 253: MILESTONE FIRED.** Yaw –85°, pitch 20°, attack×10. Quartz block successfully mined.

**Closest mining attempts:**
- **Step 42 (white carpet):** position (0.3, 0.6, 0.2), pitch 60°, yaw –65°, attack×1 (4/5 of a 5-tick chain). Carpet at spawn-relative (±1, 0, 6-7); agent 1 block away, correct pitch.
- **Step 253 (quartz):** position (11.0, 0.0, 0.2), pitch 20°, yaw –85°, attack×1 (8/10 of a 10-tick chain). Quartz at (12–14, 0, 5–6); agent 1–3 blocks away, level pitch, floor-side hit.

**Beliefs vs. ground truth:**
- Turn 15 (step 50): "New Recipes Unlocked! which typically indicates an item was collected. The white carpet might have been mined!" — CORRECT; inventory verified at step 42.
- Turn 18 (step 67): "The white block on top of the red nether brick stairs (likely the quartz block)" — WRONG BLOCK, but analyzer explicitly re-assessed at turn 35 and corrected.
- Turn 35 (step 166): "The issue is that I'm not looking directly at the quartz block. Let me try a different approach - move forward and attack without changing camera angle first" — CORRECT DIAGNOSIS; adaptive strategy.
- Turn 36 (step 176): "Now I can see the quartz block clearly with the crosshair centered on it!" — TRUE; first successful targeting.

**Primary blockers:** NONE. Completed 2/2 real hops.

**Analyzer strategy:**
- Turn 1: Read full log with `head -100`.
- Turns 9, 12, 15, 17+: Used `grep "MILESTONE"` or `tail -40` to check progress.
- Turns 1–34: Adjusted yaw ±10–45° per turn; changed pitch ±10° per turn; held attack 3–5 ticks.
- **Turn 35: CRITICAL CHANGE:** Switched to forward+attack×10 combined action. Maintained this through turn 39.
- Turns 36–39: Held attack×10 (10 steps per turn) without camera changes.
- No `use` action attempted. No backtracking after turn 35.

**Turn granularity:** 2–20 steps per turn early (highly adaptive). Steps 176+ (turns 36–39): 10 steps per turn (steady press).

---

### B. Cross-Arm Comparison (Real Score: q35-prolong 2/2; all others 0/2)

**What explains the gaps:**

1. **Carpet mining (Step 42 success only):**
   - q35-prolong: Pitch 60° (nearly vertical), yaw narrowed to –65° (southeast), position (0.3, 0.6, 0.2) ≈1.5 blocks from spawn.
   - c4h-prolong: Pitch 55–65°, yaw 0° (south), position (0,0,0.2). Saw particles but never held attack ≥5 consecutive steps; gave up at turn 9.
   - c4h-default: Pitch +40°, yaw 0°, position (0,0,0.2). Attack×2, then gave up; moved away.
   - q35-default: Same as c4h-default; did not persist.
   - **Hypothesis cells:** Misidentified red bed as obstacle; never targeted carpet.
   - **Mechanism:** Carpet requires pitch ≥55° and attack held ≥5 ticks _without moving or turning_. q35-prolong achieved this; c4h-prolong saw cracks but analyzer stopped too early. Others never reached the threshold.

2. **Quartz mining (Step 253 success only):**
   - q35-prolong: Moved forward+attack simultaneously (turns 35+), reached x=11 (within 1–3 blocks of quartz at x=12–14). Pitch 20° (level gaze). Final position had direct line-of-sight to floor quartz.
   - c4h-prolong: Stayed at x≈8.9 (4–6 blocks short). Attacked red stairs surface (y=1.0, stairs are 1 block tall). Analyzer never attempted forward+attack or increased pitch to hit floor blocks. Tried "use" action (turn 27) instead of more attack ticks.
   - q35-hypothesis: Reached x≈8.2, then ESC-spammed; never attempted to mine.
   - c4h/q35-default: Did not reach middle room.
   - **Mechanism:** Quartz on floor (y=0) requires approach to within 4 blocks and level or downward pitch. Only q35-prolong reached this range. c4h-prolong got stuck on stairs (y=1.0) and never descended to floor level or moved further east.

3. **Navigation (doorways, stairs):**
   - q35-prolong: Found doorway at step 87 (after 35 steps of searching; turn 19). Reached stairs, then crept east while attacking.
   - c4h-prolong: Found doorway at step 87 (same). Reached stairs, circled, did not progress further east.
   - Both: Stairs are obstacle; navigated over (jumping) or climbed (y changed from 0 to 1).
   - **Difference:** q35 did not give up; c4h analyzer believed it had failed and did not retry.

**Real bottleneck:** q35-prolong's **adaptive forward+attack strategy (turn 35)** combined with **persistent rechecking of progress (grep MILESTONE)** allowed it to recover from initial wrong-block attacks and inch toward the actual quartz. c4h-prolong had all the motor skills but lacked the analyzer's ability to recognize failure and change action type (separate attack → combined forward+attack).

---

### C. Concrete Fix Hypotheses

**For c4h-prolong:**
1. **Carpet mining (step 21):** Add harness feedback after attack×5: "You see particle effects on the [BLOCK] block." If no particles, retry with higher pitch (65°). **Fix:** Harness output line confirming target block identity.
2. **Quartz navigation (steps 100–151):** After 20 attack steps with no break, issue "Block not breaking; re-center crosshair or approach closer." **Fix:** Detector for false-block-targeting: "block under crosshair" text line per step.
3. **Stalled mining (turn 27):** Tried "use" action instead of persisting "attack." **Fix:** Analyzer template to try forward+attack×10 if attack-only stalls ≥15 steps.

**For q35-hypothesis:**
1. **White carpet (steps 98–108):** Memory marked "mining: success" without inventory check. **Fix:** Always verify with "You now have WHITE_CARPET ×1" or similar before advancing hop.
2. **ESC spam (steps 209–228):** on_esc_rejected did not trigger re-plan. **Fix:** After ESC rejected ≥3 times, force new plan (e.g., "ESC did not work; resume mining.").

**For c4h/q35-default:**
1. **Carpet pitch (steps 6–7):** Pitch +40° is too high for floor block 1 block away. **Fix:** Prompt: "For a block at your feet, aim pitch 60–80°."
2. **Doorway discovery (steps 27–35):** Turned in place; never moved and looked. **Fix:** Add to task: "Walk east to find doorway; look around as you move (forward + camera turns in same step are allowed)."

**Benchmark/checker artifacts beyond known /tp shift:**
- None detected. The /tp artifact is sufficient to explain find_purple_bed and find_red_nether_brick_stairs false successes.

---

### D. Evidence Table

| **Cell** | **Primary Code** | **Secondary Codes** | **3 Most Telling Step Citations** |
|---|---|---|---|
| c4h-default | N | K, P, G | Step 89 ("I can see white quartz block" at x=0.0, not x=12); step 90–103 (103 attack steps, no break); step 26 (left bedroom without mining carpet) |
| c4h-hypothesis | P | N, G, K | Step 159 (strafed around phantom "red bed"); step 170 ("move around bed to reach exit" — bed is not physical); step 300 (never reached quartz) |
| c4h-prolong | K | N, M | Step 21 ("carpet is cracking" but only 3 attacks so far; need 5+); step 26 (gave up mining after cracking, no inventory check); step 151 (attacking red stairs at x=8.9, real quartz at x=12–14) |
| q35-default | N | K, P, G | Step 145 (diagnosed "oscillation" correctly but never recovered); step 300 (never reached middle room); step 65 (abandoned doorway search after 35 steps) |
| q35-hypothesis | M | G, P, K | Step 98 (ESC rejected but thought "problem solved"); step 212 (claimed "completed all mining" while stationary at x=8.2, no inventory); step 228 (202nd ESC press, still no plan change) |
| **q35-prolong** | **None (SUCCESS)** | **N/A** | **Step 42 (white carpet mined: pitch 60°, yaw –65°, attack×5, inventory confirmed); Step 166 (analyzer pivot: "move forward and attack without changing camera"); Step 253 (quartz mined at x=11.0, pitch 20°, attack×10)** |

---

### Summary

Scene 0603 revealed a stark difference in **online adaptation and action composability.** The prolong arm (Codex via harness) had access to log inspection (`grep`, `tail`) and could dynamically adjust action sequences mid-episode. The standard arms (vLLM) operated with fixed prompt cycles and inventory-only feedback.

**q35-prolong succeeded (2/2 real hops) because:**
1. Turn 35 analyzer switch to forward+attack×10 (combined action, not sequential).
2. Persistent log checking (grep MILESTONE) to confirm mining or detect failure.
3. Willingness to abandon wrong-block attacks and retry with new positioning.

**All others failed (0/2 real hops) because:**
- Carpet: Never held attack ≥5 ticks with correct pitch (55–80°).
- Quartz: Never reached x=12–14 (q35-prolong got to x=11; others maxed x=8–9).
- Misconceptions: c4h-hypothesis believed a phantom red bed; q35-hypothesis believed memory of non-existent mined items.

**The carpet is the early filter:** three agents got close (saw particles) but did not persist to break. This suggests attack-hold duration and/or block-position feedback are critical. **The quartz is the progression gate:** only forward+attack (continuous approach + strike) covered the final 3-block gap. Sequential forward-then-attack lost ground to animation delays.