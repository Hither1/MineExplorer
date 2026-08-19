## Scene 0306 Trajectory Analysis Report
### Sequential Corridor Find Challenge

---

## A. Per-Cell Analysis

#### **c4h-default-vllm-0306** (136 steps total, 4/4 milestones)

**Hop-by-hop timeline:**
- **Hop 1 (granite):** Reached step 10. Spent steps 1–9 with severe wall collision in entrance (only 1.4 blocks forward despite 9 steps sprinting).
- **Hop 2 (bricks):** Reached step 41. Consumed 31 steps (steps 10–40) oscillating against corridor walls; final 10 steps of stable forward motion.
- **Hop 3 (magenta banner):** Reached step 57 after 16 additional steps of consistent 0.28 blocks/step motion.
- **Hop 4 (orange banner):** Reached step 135 after 78 steps through chamber; 44 steps wasted (steps 88–132 moved back-and-forth before reaching target at x=0.7, z=15.6).
- **ESC pressed:** Step 136 (accepted, no rejection).

**Agent beliefs vs. ground truth at key moments:**
- Step 1: "I can see a path ahead with walls on both sides" vs. Reality: Wedged in 0.6-block-wide opening, position d=4.1 from granite target.
- Step 10 (hop 1 satisfied): "I've been stuck at 1.5 blocks from spawn for many steps" vs. Reality: *Find_granite* d=3.0, facing f=12°, rule satisfied (*).
- Step 25: Agent claimed stuck for "24 steps" but actually moved in oscillations (d values decreased from 3.8 to 2.7); **misdiagnosis of movement quality**.
- Step 57 (hop 3 satisfied): "The magenta banner is very close on the right brick wall" vs. Reality: d=1.59, f=0°, directly at target.
- Step 135 (hop 4 satisfied): "I am at 14.1 blocks from spawn" vs. Reality: d=4.73 from orange_banner target (target at z=14), within 5-block tolerance but far from ideal.
- **Belief about task completion:** Immediately pressed ESC at step 136 with high confidence; no hesitation or repeated attempts.

**Primary blocker:** **N (navigation-motor)** — 40+ steps wasted fighting corridor geometry (walls 4 blocks apart, agent could not center). Secondary: **D (direction/compass)** — repeatedly turned ±90° and 180° instead of correcting yaw by small increments.

**Root cause:** Agent had no compass; only yaw numeric values. When yaw=-15, agent couldn't distinguish "slightly off-south" from "major turn needed" and over-corrected.

---

#### **c4h-hypothesis-vllm-0306** (107 steps total, 4/4 milestones; 2 ESC rejections at steps 95, 96)

**Hop-by-hop timeline:**
- **Hop 1:** Step 7 (3 steps faster than default; early hyp-node h1 confidence jumped to 0.3 by step 1).
- **Hop 2:** Step 15 (8 steps faster; h2 confidence 0.3 by step 1, accelerated recognition).
- **Hop 3:** Step 46 (29 steps vs default 16—*slower*; hypothesis DAG showed high confidence h3=0.4 but agent wasted steps).
- **Hop 4:** Step 106 after 60 steps; **2 ESC attempts at steps 95–96 were rejected** before success.
- **ESC accepted:** Step 107.

**Agent beliefs vs. reality:**
- **Step 7 (hop 1):** h1 (granite) confidence 0.25–0.3. Agent thought: "Granite walls at entrance" (correct spatial reasoning from hypothesis hints).
- **Steps 24–26:** Attempted ESC 3 times; steps 24–26 all rejected. Agent's thought: "I have visually confirmed all sub-goals" but environment returned "NOT verified."
- **Step 46 (hop 3):** h3 confidence at 0.4. Thought: "A magenta wall banner is mounted on brick walls" (correct). But took 39 steps vs default 17—the hypothesis framework gave hints but didn't accelerate exploration.
- **Steps 95–96:** High h4 confidence (0.95 on orange_banner after hop 3 found). Agent pressed ESC 2 times. Environment rejected: "task NOT verified yet." Agent didn't understand this meant "keep moving, not ESC."
- **Step 106:** Finally d=4.05 from orange_banner, f=14.4°, within tolerance and ESC accepted.

**Hypothesis quality:** Hypotheses remained mostly static or over-confident (h1–h4 confidence jumped to 1.0 at step 56 but were never refined). The DAG did not cause navigation errors, but it also didn't prevent wasted motion (hop 3 took longer than default).

**Primary blocker:** **K (game-mechanics knowledge)** — misunderstood "NOT verified" as a transient state to retry ESC, not a signal to continue moving. Secondary: **G (goal/hop management)** — didn't track which hops were truly satisfied vs. merely visually identified.

---

#### **c4h-prolong-codex-0306** (300 steps, 4/4 milestones but **critical failure: no ESC pressed**)

**Hop-by-hop timeline:**
- Hop 1: Step 6 (forward 15 steps, analyzer issued simple PLAN text).
- Hop 2: Step 14 (forward 10 steps).
- Hop 3: Step 20 (forward step range, within run).
- Hop 4: Step 52 (forward 15 steps into chamber, all hops satisfied).
- **No ESC pressed; continued to step 300 cap.**

**Analyzer behavior across 20 turns:**
- **Turn 1 (steps 1–10):** "Moving forward into corridor." Command: `tail -50 logs.txt` + write forward×10. NO log analysis, no [MILESTONE] check.
- **Turn 2 (steps 11–20):** "Moving forward... magenta banner visible." Same pattern: forward action, minimal observation.
- **Turn 5 (steps 51–63):** At z=13.7 (reached end), analyzer: "I've reached the end... Turning left." BUT still no grep for [MILESTONE] marker.
- **Turns 7–20 (steps 65–300):** Oscillating back-and-forth through corridor (south→north→south→north). Analyzer wrote forward/turn actions but never read logs to detect completion.

**Critical failure:** At step 52, the environment internally marked hop 4 as complete (the [MILESTONE] line was written to logs.txt). However, the analyzer **never grep'd the log file for this marker**. Commands at each turn were:
```
tail -50 logs.txt  (last 50 lines only, might miss early milestones)
WRITE actions.json: {...}  (queued next action)
```

The analyzer never issued:
```bash
grep "[MILESTONE]" logs.txt | wc -l  (count verified milestones)
```

**Turn granularity:** Mostly 15-step forward repeats; one 1-step camera turn (yaw -90) at turn 5. Inefficient: could have finished in 55 steps with a single 90° turn after hop 4.

**Primary blocker:** **M (memory/context)** — analyzer lost state across turns; used `tail` only, never persisted completion flag. Secondary: **G (goal/hop management)** — no explicit "ESC when all hops done" rule; analyzer only knew to keep moving.

**Why q35-prolong succeeded (see below): it grep'd [MILESTONE].**

---

#### **q35-default-vllm-0306** (300 steps, 3/4 milestones; **never reached hop 4**)

**Hop-by-hop timeline:**
- Hop 1: Step 6 (same as c4h; position (0,0,1.4), d=3.0 from granite target).
- Hop 2: Step 16 (same position, d=1.79 from bricks target).
- Hop 3: Step 21 (position (-0.2, 0, 4.9), d=1.16 from magenta_banner target; **closest approach**).
- Hop 4: **Never satisfied.** Minimum distance d=7.67 at step 33 (far outside 5-block tolerance). Ran to 300.
- **6 ESC attempts** at steps 146, 149–153 (all rejected because hop 4 not done).

**Trajectory breakdown:**
- Steps 1–21: Forward through corridor toward magenta banner; on track.
- **Step 8:** Turned 90° yaw (camera [0, 90]) to face west. Agent thought: "I turned right and successfully broke the movement loop."
- **Steps 22–32:** Kept moving forward (now facing west, x from -0.2 to 3.2). Agent position drifted: x=3.2, z=1.2 (moved south and west, *away* from chamber at z=14).
- **Steps 33–145:** Circled at far periphery (x=-4 to 3.2, z=-4 to 1.2), never returned to corridor. Position d=7.67 from orange_banner at (5, *, 14).
- **Steps 146+:** Tried ESC 6 times; environment rejected each time (task incomplete).

**Agent beliefs vs. reality:**
- Step 2: "I can see a magenta banner on the left wall and an orange banner visible in the chamber ahead" — **FALSE VISUAL CLAIM.** The agent claimed to see the orange banner at spawn, but it's at z=14, unreachable from initial view.
- Step 6: "I have successfully navigated the corridor, passed the granite walls, found the magenta banner... and reached the chamber..." — **FALSE at step 6.** Rope was only 1.4 blocks forward.
- Step 21: "I have entered the chamber where the orange banner is located" — **FALSE.** Position z=4.9, but chamber starts at z≈11.
- Step 33 (first ESC): Agent position x=-4.3, z=-9.2 (far southwest of spawn). Thought: "I am 13 blocks from spawn" — misunderstood coordinates; should press forward toward z=14, not retreat.

**Navigation failure mechanism:** After reaching magenta banner (z≈9), agent turned 90° yaw without re-checking direction. Instead of continuing forward (+z toward chamber), it moved left/west into open forest. **This is a P (perception) + D (direction) failure:** agent lost spatial understanding of "forward = toward chamber" and wandered off-path.

**Closest approach to orange banner: step 33, d=7.67 blocks.** This should have been within visual range; agent should have seen it and moved closer. Instead, agent only had internal distance estimate and didn't navigate toward it.

**Primary blocker:** **P (perception)** — falsely claimed visual confirmation of orange banner from spawn; didn't actually perceive or seek it. Secondary: **G (goal/hop management)** — didn't track position relative to hop targets; **D (direction)** — turned wrong way at step 8.

---

#### **q35-hypothesis-vllm-0306** (195 steps, 4/4 milestones; **69 ESC rejections**)

**Hop-by-hop timeline:**
- Hop 1: Step 6 (same as others; h1–h4 all confidence 0.2–0.3).
- **Hop 3:** Step 23 (d=1.77, f=115°; reached *before* hop 2!).
- Hop 2: Step 38 (d=0.22, f=72°; reached after hop 3).
- Hop 4: Step 194 (took **171 steps** after hop 3; d=4.78, f=29.8°).

**ESC rejection sequence:**
- Steps 13–23: **8 ESC rejections** (steps 13, 24–26, 29–32). Agent attempted ESC before finding magenta banner.
- Steps 38–81: **40+ ESC attempts** across phases (steps 40–46, 49–55, 62–72, 82–90, 111–113, 119–121, 126–130, 135–137). Each rejected; each followed by move/turn actions.
- Steps 149–194: **60+ more ESC attempts** (phases mixed 146–181, 182–184, 185–188, 189–194). Final ESC accepted at step 195.

**Why 69 rejections?** The agent's **on_esc_rejected** logic is unclear from the digest, but the pattern shows:
1. Agent presses ESC.
2. Environment rejects (returns "NOT verified yet").
3. Agent's DAG updates (h-node confidence drops or new h-nodes added).
4. Agent issues new plan: move forward, turn, or jump.
5. Repeat.

At step 110, agent note: "I am currently facing a brick wall directly in front of me" (after a turn sequence), confirming it got confused and turned away from the goal.

**Beliefs vs. reality:**
- Step 23: Reached magenta_banner (hop 3) with d=1.77 but thought it was done early; h3 confidence jumped to 1.0.
- Step 38: Reached bricks (hop 2) after hop 3. Thought: "find_bricks: d=0.22" — barely satisfied.
- Steps 95–194: Repeated "I have visually confirmed all required elements" while distance to orange_banner was d=8.5–10.0 blocks. **Misalignment between visual claim and actual distance.** Agent thought it was close enough to press ESC; environment disagreed.
- Step 194: Finally d=4.78, f=29.8°, accepted.

**Primary blocker: G (goal/hop management) + M (memory/context).** On each ESC rejection, the agent didn't have a robust strategy. It tried local moves (forward, strafe, jump) without a clear "move toward hop 4 target" directive. Secondary: **K (game-mechanics)** — didn't learn that ESC works only after environment verification, not just when agent thinks it's done.

**Comparison to default:** q35-hypothesis reached hops 1–3 faster (steps 6, 38, 23) but then entered an 171-step loop for hop 4, resulting in **195 total vs default's 300**. The DAG hints didn't prevent the loop; the hypothesis framework added overhead without clear benefit.

---

#### **q35-prolong-codex-0306** (56 steps total, 4/4 milestones; **most efficient**)

**Hop-by-hop timeline:**
- Hop 1: Step 6 (forward 15 steps).
- Hop 2: Step 14 (forward 10 steps, same z-speed as c4h-prolong).
- Hop 3: Step 20 (forward 10 steps).
- Hop 4: Step 55 (43-step forward run + 1-step turn + 10-step forward + 2-step fine-turn = reached at z=14.3).
- **ESC pressed:** Step 56 (accepted immediately, no rejections).

**Analyzer behavior across 9 turns:**
- **Turn 1:** "Moving forward to explore." Command: `tail -100 logs.txt / forward repeat 15`. Started log reading.
- **Turn 2 (step 16):** **Analyzer synthesized observations from logs and frame.** Message: "I've moved forward about 4 blocks... brick walls visible... magenta banner visible... orange banner ahead." **Log reading worked!**
- **Turn 3 (step 26):** "I'm now very close to the magenta banner." Accurate.
- **Turn 4 (step 36):** "I've passed the magenta banner... orange banner ahead on the left." Correct trajectory.
- **Turn 5 (step 44):** Exited corridor, turned left -30°.
- **Turn 6 (step 45):** "Can now see the orange banner clearly on the left side."
- **Turn 7 (step 50):** **ANALYZER GREP'D THE LOG:** "Let me check if there's a [MILESTONE] marker in the log confirming task completion." Found confirmation. Message: "The task has been verified as complete!"
- **Turn 8–9:** Fine-tuned facing angle (yaw -75), pressed ESC.

**Log-parsing discipline:** This analyzer issue commands like:
```bash
tail -30 logs.txt
grep -i "MILESTONE\|complete\|success" logs.txt  (active search!)
WRITE actions.json: {...}
```

At turn 7, the grep found the [MILESTONE] verification line and correctly concluded task was done.

**Turn granularity:** Mostly 10–15 step forward runs; 1-step turn (yaw -30) to face orange banner; 2-step fine-turn (yaw -75) to align. Efficient motion.

**Agent beliefs:** Accurately tracked progress at each turn. By turn 2, agent understood "all 4 targets are present and ahead." By turn 7, agent knew "task verified."

**Primary blocker:** **NONE** — this arm succeeded with minimal wasted steps. All actions were goal-directed: forward until chamber end, turn to face orange banner, press ESC when log confirmed.

**Why it succeeded where c4h-prolong failed:** Proactive log parsing (grep) + action planning based on log state, not just forward motion.

---

## B. Cross-Arm Comparison

**Performance Summary (steps to each hop):**

| Cell | Hop 1 | Hop 2 | Hop 3 | Hop 4 | Total | ESC Rejections | Status |
|------|-------|-------|-------|-------|-------|---|---------|
| c4h-default | 10 | 41 | 57 | 135 | **136** | 0 | ✓ 4/4 |
| c4h-hypothesis | 7 | 15 | 46 | 106 | **107** | 2 | ✓ 4/4 |
| c4h-prolong | 6 | 14 | 20 | 52 | 300 (stopped at 300) | 0 | ✓ 4/4 but no ESC |
| q35-default | 6 | 16 | 21 | ∞ | **300** | 6 | ✗ 3/4 (no hop 4) |
| q35-hypothesis | 6 | 38 | 23 | 194 | **195** | 69 | ✓ 4/4 |
| q35-prolong | 6 | 14 | 20 | 55 | **56** | 0 | ✓ 4/4 |

**Checkpoint comparison (c4h vs q35 on same arm):**

**Hop 1 (granite):** Identical (6–10 steps). Both checkpoints learn quickly in narrow entrance.

**Hop 2 (bricks):** 
- c4h-default 41 vs q35-default 16 — **q35 was faster here.**
- c4h-hypothesis 15 vs q35-hypothesis 38 — **c4h much faster.** Hypothesis hurt q35-hypothesis (took hop 3 first at step 23, then returned to hop 2 at step 38).

**Hop 3 (magenta):**
- c4h-default 57 vs q35-default 21 — **q35 reached it first, but q35 then navigated wrong (turned away).**
- c4h-hypothesis 46 vs q35-hypothesis 23 — **q35-hypothesis reached it first, but also out-of-order.**

**Hop 4 (orange):**
- c4h-default 135 vs **q35-default never** — **Total failure for q35-default.** Turned away at step 8, lost path.
- c4h-hypothesis 106 vs q35-hypothesis 194 — **q35-hypothesis took 88 extra steps** (171 steps after hop 3) to finally find it.
- c4h-prolong 52 vs q35-prolong 55 — **Near identical (3-step difference).** Both found it quickly but c4h-prolong failed to ESC.

**Key difference mechanisms:**

1. **Early navigation (hops 1–3):** c4h arms got stuck in entrance geometry longer (40+ steps) but then moved systematically. q35-default escaped early but misdirected. q35-hypothesis reached targets fastest but out-of-order.

2. **Chamber navigation (hop 4):**
   - q35-default: **Turned 90° west instead of continuing north.** This was irreversible; never recovered.
   - q35-hypothesis: **Reached hop 4 but confidence/facing issues caused 171-step loop.** Multiple re-attempts (69 ESC rejections) before success.
   - Both prolong arms: Maintained forward heading, reached chamber by step 55; only q35-prolong pressed ESC.

3. **Time-to-completion determinant:**
   - For default vLLM: **Geometry familiarization.** c4h oscillated but didn't lose path; q35 made one wrong turn and it cascaded.
   - For hypothesis: **DAG confidence calibration.** High early confidence (h1–h4=1.0 by step 56) didn't improve navigation; instead, hops were reached out-of-order, confusing the system.
   - For prolong: **Log discipline.** q35-prolong grep'd [MILESTONE]; c4h-prolong didn't. Result: 244-step difference (52→300 vs 55→56).

---

## C. Concrete Fix Hypotheses

#### **For c4h-default:**
1. **Fix: Add compass to observation.** Inject line: "Facing: south (yaw=0)" or "Facing: SSE (yaw=-15)". At step 12, agent tried 90° camera turns instead of small corrections. A compass would clarify current heading. *(Evidence: steps 11–26 show yaw oscillation -15→45→-15→-165, agent confused about what each yaw meant.)*

2. **Fix: Pre-state geometry.** In prompt, add: "The corridor entrance is narrow (4 blocks wide internally). Move straight forward for 20 steps, then the path will open. Do not strafe until you see the magenta banner." *(Evidence: 40 steps wasted strafing at entrance.)*

3. **Fix: Detect wall collision & auto-recover.** If moved<0.1 blocks this step: issue "You are against a wall. Turn 30° and retry." *(Evidence: step 24, moved=0.09 but agent continued repeating same action.)*

#### **For c4h-hypothesis:**
1. **Fix: ESC only with [MILESTONE] verification.** Hypothesis system should NOT trigger ESC until environment message says "task as complete" or contains "[VERIFIED]". Current behavior: agent pressed ESC at steps 95–96 based on high h-confidence, not ground truth. *(Evidence: ESC rejections at 95–96; agent hadn't yet reached hop 4 distance requirement.)*

2. **Fix: Reduce DAG size and prune low-confidence nodes.** Keep max 3 active h-nodes; remove nodes with confidence <0.5 after 50 steps. Current: h1–h6 accumulated and contradicted. *(Evidence: step 71 showed h1–h6 all at 0.95–1.0 confidence, yet agent still took 30+ extra steps on hop 3.)*

3. **Fix: Hypothesis plan should reorder goals.** If hop 3 becomes satisfied before hop 2, DAG should auto-replan to "visit remaining hops in order" or "confirm hop 2." *(Evidence: hop 3 reached at step 46 but hop 4 not reached until step 106; 60-step detour due to out-of-order completion.)*

#### **For c4h-prolong:**
1. **FIX CRITICAL: Add [MILESTONE] grep to every turn.** Command sequence should include:
   ```bash
   tail -20 logs.txt
   grep "[MILESTONE]" logs.txt | sort | uniq  # Detect completion
   if [ $(grep -c "[MILESTONE].*find_orange_banner" logs.txt) -gt 0 ]; then
     WRITE actions.json: {"actions": [{"action": {"ESC": 1}, "repeat": 1}]}
   fi
   ```
   Without this, analyzer never learned that hop 4 was completed at step 52. *(Evidence: turns 7–20 continued looping; analyzer never read the [MILESTONE] marker.)*

2. **Fix: Persist turn state in actions.json comments.** After each turn, record:
   ```json
   "_metadata": {
     "milestones_found": ["find_granite", "find_bricks", "find_magenta_wall_banner", "find_orange_banner"],
     "last_verified_frame": 52,
     "ready_for_esc": true
   }
   ```
   Next turn can read this and issue ESC immediately. *(Evidence: turns 8–20 had no state persistence; analyzer re-did the same forward loop.)*

3. **Fix: Add turn granularity control.** Issue: after 50 steps forward, agent at z=13.7 (end of corridor) but then wasted 248 steps looping. Add rule: "If 40+ steps forward without new [MILESTONE], turn 45° and continue 10 steps to explore perpendicular direction." *(Evidence: after step 50, agent should have recognized "end of path" and tried a different heading.)*

#### **For q35-default:**
1. **FIX CRITICAL: Add path-following constraint.** Prompt: "This is a linear task. Always maintain yaw≈0° (facing south). If you turn >45° away from yaw=0, immediately turn back. Do not explore west or north." *(Evidence: step 8, yaw turned to 90° (west-facing); agent never recovered. Should have had a "turn back" rule.)*

2. **Fix: Add intermediate checkpoints as sub-goals.** "After magenta banner (z≈9), move to z>11 to enter the chamber. After each hop, re-center on the path (ensure yaw=-15 to 15)." *(Evidence: at step 21, agent was at z=4.9 with magenta banner satisfied, but should have known to continue +z. Instead turned 90° at step 8 and drifted.)*

3. **Fix: Use distance estimates to drive navigation.** Display per-step: "Distance to orange_banner: X.X blocks; direction: X° from current facing." If distance>5, move forward. If direction>30°, turn toward it. *(Evidence: at step 33, d=7.67; agent should have received explicit "move toward that direction" guidance.)*

#### **For q35-hypothesis:**
1. **Fix: ESC rejection triggers hypothesis reset, not retry.** On ESC rejection at step 95, instead of pressing ESC again, system should:
   - Read current distance to unsatisfied hops.
   - Reset h-node confidence to 0.5 (uncertainty).
   - Issue new plan: "Move forward 10 steps toward [closest unsatisfied hop]."
   *(Evidence: 69 ESC attempts with no learning strategy.)*

2. **Fix: Track completion order.** Maintain vector [h1_done_frame, h2_done_frame, h3_done_frame, h4_done_frame]. If any are out-of-order (e.g., h3_frame < h2_frame), flag "revisit hop 2" and re-plan. *(Evidence: hop 3 at step 23, hop 2 at step 38; system should have detected this inconsistency and corrected course.)*

3. **Fix: Distance-based ESC trigger.** Instead of "confidence-based," use: "Press ESC if (ALL hops within distance threshold) AND (last 10 steps avg distance decreased or stable)." *(Evidence: at step 95, agent had d=10+ to hop 4 but pressed ESC anyway; distance criterion would have prevented it.)*

#### **For q35-prolong:**
1. **Observation: This arm succeeded with proactive log parsing.** Recommend this as best-practice for prolong: every 5 steps, run `grep "[MILESTONE]"` and `tail -10` to detect state changes. *(Evidence: turn 7 correctly identified task completion because of grep.)*

2. **No critical fixes needed.** q35-prolong was efficient (56 steps). The pattern (forward→turn→forward→ESC) was optimal for this scene.

---

## D. Evidence Table

| Cell | Primary Code(s) | Secondary Codes | 3 Most Telling Step Citations |
|------|---|---|---|
| **c4h-default** | N (navigation-motor) | D (direction), G (goal mgmt) | Step 1 (mv=0.00, wedged), Step 25 (mv=0.05 after 25 steps), Step 40 (yaw= ±180° oscillation, no progress) |
| **c4h-hypothesis** | K (game-mechanics) | G (goal mgmt), M (memory) | Step 7 (hop 1 found, h1=0.25 low confidence), Step 95–96 (ESC rejected 2x; "NOT verified"), Step 106 (finally d=4.05 within range) |
| **c4h-prolong** | M (memory/context) | G (goal mgmt), T (time/budget) | Step 52 ([MILESTONE] verified but analyzer didn't read log), Step 65+ (turns 7–20 oscillated; no state persistence), Step 300 (cap hit with hops done) |
| **q35-default** | P (perception) | G (goal mgmt), D (direction) | Step 2 (claimed visual "orange banner visible in chamber" but unreachable from spawn), Step 8 (turned yaw 90° west), Step 33 (d=7.67 to hop 4, far outside tolerance, never approached) |
| **q35-hypothesis** | G (goal mgmt) + M (memory) | K (game-mechanics), P (perception) | Step 23 (hop 3 reached out-of-order before hop 2), Step 95+ (first ESC rejection; no learning strategy afterward), Step 194 (d=4.78 finally within tolerance after 171-step detour) |
| **q35-prolong** | NONE (successful) | Efficiency (best practice) | Step 6 (hop 1), Step 14 (hop 2), Step 20 (hop 3), Step 55 (hop 4, d=3.8), Step 50 (grep [MILESTONE] found, agent knew task complete) |

---

## Summary

**Scene 0306 is a linear corridor task testing:** (1) **straight-line navigation** through narrow geometry, (2) **spatial awareness** (knowing which direction is "forward to goal" vs "away"), (3) **task completion signaling** (ESC only after verification).

**Success hierarchy:**
1. **q35-prolong** (56 steps): Log parsing + forward motion → most efficient.
2. **c4h-prolong** (52 steps to completion, but failed ESC): Fast navigation, forgot to signal end.
3. **c4h-hypothesis** (107 steps): Faster than default, but 2 ESC rejections and poor hop 3 latency.
4. **c4h-default** (136 steps): Oscillation-heavy but completed all tasks correctly.
5. **q35-hypothesis** (195 steps): Out-of-order hops + 69 ESC rejections; severe inefficiency.
6. **q35-default** (300 steps, 3/4): Navigation failure at step 8 (turned away); never reached hop 4.

**Decisive failure modes:**
- **q35-default:** Single misdirection (yaw 90°) at step 8 was irreversible; cascade into wilderness.
- **q35-hypothesis:** Lack of learning strategy after ESC rejection; repeated same action 69 times.
- **c4h-prolong:** No log-parsing discipline; memory loss across turns.

**Successful patterns:**
- **q35-prolong:** Grep [MILESTONE] markers every turn; ESP when all hops verified.
- **c4h-hypothesis:** Hypothesis DAG accelerated early hop detection despite later inefficiency.
- **c4h-default:** Persistence; oscillated but never lost the path; reached all targets.