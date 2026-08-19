Now I have sufficient evidence. Let me create the comprehensive analysis.

---

## Scene 0726 Trajectory Analysis Report

### A. Per-Cell Analysis

#### **c4h-default-vllm** (Qwen3.8 checkpoint, direct vLLM arm)
**Scores:** 0/4 milestones (none reached, 300 steps, 77.6% stuck fraction)

**Hop timeline:**
- find_seagrass: Closest approach d=3.74 at step 19; never satisfied
- swim_across_channel: Closest d=2.28 at step 135; never entered water box
- find_diamond_block: Closest d=8.7 at step 20; never satisfied
- find_soul_campfire: Closest d=11.33 at step 19; never satisfied

**What it believed vs. ground truth:**
- Step 1-9: "I can see water channel...need to jump to get into water." (Thought sprint+jump would work; actually bank is too high and agent stuck on grass edge)
- Step 19-30: "I am completely stuck at water's edge facing North. I need to strafe left...to find a lower section of bank." (Correctly diagnosed stuck state but misidentified cause)
- Step 49: "I have successfully cleared the foliage and am now in the water." (FALSE—still on bank, frame is solid green; agent wedged in terrain)
- Step 77+: "I have been stuck in water for many steps, barely moving. I am facing North with dense dark oak foliage ahead blocking my path." (Actually still at water's EDGE, never entered channel; at x=-5.2, z=6.2, which is WEST of spawn, not in the water zone z=7..9)

**Primary blocker:** **N (navigation-motor)** – stuck on bank terrain, unable to break through water's edge via sprint+jump at z~6. The bank geometry presents a collision barrier; the agent tried every axis (forward, strafe left/right, jumping) from one position but never found an entry vector. Compounded with **P (perception)** – unable to interpret "You have NOT moved" / circling warnings; thought attacking foliage would help.

**Secondary codes:** **D (direction/compass)** – turned 90° east at step 20 then walked away from water, eventually ending up at x=-5.2 (5 blocks west of spawn).

**Memory quality:** Degraded by step ~50; agent still claims to be "in water" at step 49 and beyond despite being on bank. No recovery from initial error.

---

#### **c4h-hypothesis-vllm** (Qwen3.8 checkpoint, DAG-planning arm)
**Scores:** 0/4 milestones (300 steps, 27.4% stuck fraction, 0 ESC presses)

**Hop timeline:**
- find_seagrass: Closest d=4.02 at step 24; never satisfied (within dist but facing off by ~124°)
- swim_across_channel: Closest d=2.16 at step 47; never entered water box
- find_diamond_block: Closest d=8.95 at step 24; never satisfied
- find_soul_campfire: Closest d=11.59 at step 24; never satisfied

**What it believed:**
- Step 1: "I need to decompose task into sub-goals: 1) find seagrass...2) swim...3) find diamond block...4) locate soul campfire...5) end episode." (Correct plan frame)
- Step 7: h1 confirmed at 0.95 confidence: "Seagrass is visible in water channel ahead." (True)
- Step 39-45: "Mining the block directly in front of me will create a step down into the water." (Hypothesis h8 at 0.75 confidence; actually mined and got stuck in collision at step 50)
- Step 50+: "I am stuck inside a block or against a collision barrier at the water's edge...I need to try a different movement vector to un-wedge." (Correct diagnosis; attempted back/left/right/forward)
- Step 58: h10 at 0.4: "Moving away from the water (forward after 180-degree turn) will un-wedge me from the collision state." (Correct; hypothesis guided recovery)

**Primary blocker:** **N (navigation-motor)** – same water-entry bank collision as c4h-default, but hypothesis-guided attempts to mine the blocking block and reverse out of wedge. Despite h8 (mine block) reaching 0.95 confidence by step 46, this did not solve the core problem: the agent still could not reach water even after mining.

**Secondary codes:** **M (memory/context corruption)** – hypothesis cache shows 10 statements at step 50 but agent state description contradicts them ("h9:conf:0.95 I can now walk or jump into the water" yet next step fails to do so).

**Did DAG change outcome?** No. Hypothesis nodes h5-h10 correctly identified stuck state and mining strategy but could not overcome the underlying navigation constraint. The vLLM arm was given the same blocked water entry and additional planning structure did not unlock it.

**Key difference from default:** Hypothesis spent fewer total steps (~62 unique x,z positions vs. default's wandering to x=-5) and stayed more local, but both failed to enter water.

---

#### **c4h-prolong-codex** (Qwen3.8 checkpoint, Codex-planning arm with logs)
**Scores:** 4/4 milestones (12, 63, 157, 81 steps respectively, 159 total steps, 28.5% stuck fraction, 0 ESC rejections)

**Hop timeline:**
- find_seagrass: ✓ step 12 (within 5 blocks, facing ±22.5°)
- swim_across_channel: ✓ step 63 (entered z=7..9 box)
- find_diamond_block: ✓ step 157 (within 4 blocks, facing within tol)
- find_soul_campfire: ✓ step 81 (within 5 blocks, facing within tol)

**Movement quality:** Smooth progression: steps 1–33 crossed from spawn (0,0,0) to mid-water (1.3, 3.6); steps 34–78 swam/jumped to far shore, reached diamond zone by step 71 (d=3.8); steps 79–87 final approach to campfire; steps 88–159 fine-tuning position under shelter with camera adjustments and attempted use/interact actions.

**What it believed:**
- Step 1 (PLAN): "Turn slightly left to face the water channel directly, then sprint forward toward water's edge to look for seagrass." (Correct)
- Step 8 (MSG): "I can see seagrass in the water...Let me look down slightly and continue forward." (Perception correct)
- Step 34 (MSG): "I can see the diamond block and dark oak shelter on far shore. Let me jump to get into water." (Correct identification)
- Step 79 (MSG): "I'm on the shore now...I can see the soul campfire right in front of me." (Correct)
- Step 87-111: Repeated waits for "milestone verification" while stationary; correctly identified all hops reached but unclear why verification was delayed.

**Turn granularity:** Coarse but effective. Large turns (e.g., camera yaw ±90° at steps 52, 101, 107) separated by sprint+jump sequences. No fine 5-10° adjustments until steps 93+.

**Log usage:** Prolong's tail -50/-30/-20/-15 commands (turns 1–32) show it read recent state but **did not grep or parse for specific milestones**. Planner relied on visual frame + current STATE line (pos, yaw, pitch) and distance metrics in observation. No evidence of extracting "[MILESTONE]" lines from logs.

**ESC handling:** Zero rejections. At step 159 (turn 32), recognized "milestone has been triggered" from environment message and sent ESC=1 to exit. Correct termination logic.

**Swimming program:** Steps 8–63 used repeated `forward+sprint` entries with repeat counts (5–15 ticks per plan block), interspersed with `jump` entries for buoyancy. Effective incremental program structure allowed continuous progress despite ~0.1 blocks/step water drag.

---

#### **q35-default-vllm** (Qwen3.5 checkpoint, direct vLLM arm)
**Scores:** 3/4 milestones (52, 108, 135, missed campfire, 300 steps, 26.8% stuck fraction, 4 ESC rejections at steps 117–119, 131)

**Hop timeline:**
- find_seagrass: ✓ step 52 (within 5 blocks; facing error 154.4° but within 45° tol for position_near_with_facing rule → counting as success; then faced away but that didn't revoke milestone)
- swim_across_channel: ✓ step 108 (inside z=7..9 box after swimming/jumping from ~z=4 at step 40)
- find_diamond_block: ✓ step 135 (within 4 blocks at step 135; min_dist=3.96)
- find_soul_campfire: ✗ (closest d=6.2 at step 138, just outside 5-block radius; never satisfied)

**What it believed:**
- Step 1-24: "I am stuck at water's edge...The water is directly ahead, but I cannot enter it." (Correct diagnosis by step 11; correctly tried jump+forward combos)
- Step 24: "I have successfully turned 90 degrees to face along the shoreline. I am currently stuck in a loop at the water's edge." (Identified circling pattern; turned to strafe)
- Step 37: "I have successfully exited the water and am now on the shore, standing right next to the diamond block." (FALSE: still in water at z=4.8 per position log; frame shows forest but water still present; agent hallucinated exit)
- Step 52 (seagrass milestone reached): Agent did not acknowledge or update plan after seagrass milestone fired; continued assuming it was pending.
- Step 108 (swim milestone reached): "I have successfully crossed the water channel and am on the far shore." (Correct)
- Step 135 (diamond milestone reached): Agent did not acknowledge; continued moving east along channel at z~8 (still in water box!) searching for campfire.
- Step 138-142: "The diamond block is visible to my left...The shelter with the soul campfire is visible just ahead and slightly to the right." (True visually but too far away d=6.2; agent veering away from campfire zone as it swims eastward up the channel)

**Primary blocker for campfire (hop 4):** **P (perception) + G (goal/hop management)**. Agent reached ~d=6.2 at step 138 (slightly outside 5-block threshold) then made a critical error: instead of adjusting direction toward shelter at (5,0,14), it continued swimming EAST along the channel for ~100 steps (to ~x=15 at steps 150–254), drifting away from target. The memory log shows no acknowledge of campfire's location; agent pursued a false target (perceived shelter structure to the right) and swam past the true campfire zone.

**Secondary code:** **N (navigation-motor)** – water drag made fine-grained steering difficult; agent applied turn+move pairs but achieved only ~3 blocks net eastward per 10 steps once in the channel.

**ESC behavior:** Pressed ESC 4 times at steps 117–119 (believing swim was done) and step 131. All were rejected because only 3/4 milestones had fired at that point.

---

#### **q35-hypothesis-vllm** (Qwen3.5 checkpoint, DAG-planning arm)
**Scores:** 1/4 milestones (swim at 158; missed seagrass, diamond, campfire; 300 steps, 20.4% stuck, 35 ESC rejections)

**Hop timeline:**
- find_seagrass: ✗ (closest d=4.67 at step 14, within dist but never facing satisfied; steps later no longer within distance)
- swim_across_channel: ✓ step 158 (entered z=7..9 box after lengthy circling)
- find_diamond_block: ✗ (closest d=8.32 at step 177, far away)
- find_soul_campfire: ✗ (closest d=6.56 at step 187, outside range)

**What it believed:**
- Step 1: Hypothesis nodes h1–h4 created: "Seagrass visible," "Diamond block on far shore," "Soul campfire present," "Narrow enough to swim." (Correct goals)
- Step 24: "I am completely stuck at water's edge...The environment warning confirms I am circling back on myself." (Correct diagnosis; h6 at 0.5 confidence: "Clear path if I move along shoreline.")
- Step 50: h9 at 0.8: "I can now walk or jump into the water from my current position." (Attempted mining block; after 5 attack steps, assumed block gone but actually still wedged)
- Step 57: "I am stuck inside a block or against collision barrier at water's edge...I need to turn 180° and move backward." (Correct recovery strategy; h10 at 0.4)
- Step 99–135: Repeatedly pressed ESC expecting task done; rejected 35 times. Agent was at z~5.2 (barely in water), far from completion.
- Step 158 (swim milestone finally triggered): Agent had drifted to z~6.3, inside the z=7..9 box. Hypothesis did not update; agent pressed ESC 35 more times at steps 99–163 (only first batch shown; log truncated).

**Primary blocker:** **G (goal/hop management) + N (navigation-motor)**. Agent got stuck on water-entry bank (same as others) but, unlike default/prolong, developed a false belief that the hop was complete. After step 99 (believed swim was done), issued 35 ESC presses in a tight loop (steps 99–163 concentrated at steps 99–163 per reject log), blocking progress. The hypothesis system recorded h9 (can enter water) but never confirmed success; environment never sent "[MILESTONE]" line for seagrass/diamond/campfire, yet agent kept trying to exit.

**Why 35 ESC rejections?** Each rejection forces re-planning and re-execution, but agent had no new model of its actual position or blockage. It looped attempting ESC → rejection → next thought: "I must be missing something; let me turn and try again" → ESC → reject. The vLLM generated `{"ESC": 1}` action without waiting for environment feedback that task was incomplete.

---

#### **q35-prolong-codex** (Qwen3.5 checkpoint, Codex-planning arm with logs)
**Scores:** 3/4 milestones (swim 62, diamond 78, campfire 99; missed seagrass; 300 steps, 15.1% stuck, 12 ESC rejections at steps 125, 128, 140, 153, 156, 159, 161, 163, ...)

**Hop timeline:**
- find_seagrass: ✗ (within 5 blocks for 107 steps starting at step 10; facing error min 93.7° at step 74, never ≤22.5°; 107 steps within distance but 107 ALSO steps with facing bad)
- swim_across_channel: ✓ step 62 (entered z=7..9 box, sustained ~20 steps inside)
- find_diamond_block: ✓ step 78 (within 4 blocks, facing ~86° error at min point)
- find_soul_campfire: ✓ step 99 (within 5 blocks, facing within tol)

**Movement quality:** Steps 1–45 swam forward into water; steps 46–62 crossed channel with turns to angle ±45°; steps 63–114 approached far shore and intermediate turns (yaw -45° → 75° → -30° → etc.); steps 115–160+ circled shelter area, repeatedly turned to acquire campfire bearing, made 12 ESC attempts.

**What it believed:**
- Step 1 (PLAN): "Swim forward across water channel to reach far shore, locate diamond block, find soul campfire under dark oak shelter." (Correct)
- Steps 1–62: Smooth execution; planner reported "I'm in the water...seagrass visible" and "about to exit" with good visual confirmation.
- Step 62: Crossed into zone but immediate note: "close to the far shore - I can see the diamond block and soul campfire clearly." (Actually at z=7.0, just entered box; not yet on shore; campfire not visible yet but was correctly identified as next target)
- Step 78 (diamond milestone fired): "I can see the diamond block right in front of me...Let me turn left to face the diamond block." (Correct, diamond acquired)
- Step 81: (campfire milestone should have fired here per summary, but...)
- Step 102–120: Attempted multiple camera angles (yaw turns ±30°, ±60°, ±90°, ±120°) to view campfire and diamond simultaneously; PLAN text shows "Turn left/right to look for the soul campfire." Campfire reached its minimum distance of 0.91 at step 160; milestone fired at step 99 but planner didn't acknowledge until much later.
- Step 120–135: Looped with noop actions (camera-only turns), increasing pitch angle from 5° to 35°, then waited stationary.
- Step 125+: Began ESC presses; rejected 12 times (environment sent rejection message). Planner issued 12 ESC commands despite milestone having fired at step 99; unclear why it kept trying to exit.

**Seagrass blocking factor — benchmark/checker artifact?** Agent was within 5 blocks for 107 consecutive steps (10–116), with min distance 1.45 at step 74. However, facing error never dropped below 93.7° (at step 74 when d_min occurred). The milestone rule requires distance ≤5 AND facing error ≤22.5° (i.e., ±22.5° tolerance, which is facing_tol_half = 22.5). At every step the agent was within distance, it faced 93.7°–154.4° away from the seagrass point (2,0,7). **This suggests the agent never aligned its yaw to face the seagrass point.** The logic is sound (you must look at the object to "find" it), but prolong never issued a turn-toward-seagrass command; it navigated by forward+jump primarily, maintaining yaw -45° to -20° while moving. The seagrass point is roughly at yaw 0° (south) from spawn, so reaching it while moving northeast/southwest (yaw ±45°) meant always looking away from it.

**Turn granularity:** Coarser at start (step 1–6 only camera adjustments, yaw fixed); at steps 46–62 issued large 45° camera yaw shifts. By steps 115+, attempted finer ±30° and ±60° increments. Last 20 steps (140+) showed diminishing returns: repeated same camera angle, pressed ESC, reset.

**Log usage:** Like c4h-prolong, used tail -20/-15/-50 to read recent logs; no grep for "MILESTONE". Planner briefings show it read "[STATE]" position and yaw, inferred milestone status from environment message text (e.g., "The milestone has been triggered! The environment has verified...") only in the c4h case; q35-prolong does not show such explicit reads in its MSG lines.

**ESC handling:** Unlike c4h-prolong (0 rejections), q35-prolong received 12 ESC rejections at steps 125–163. After each rejection, planner re-issued a new turn/camera command and tried again. No recovery strategy; agent did not update its understanding of which milestones were done.

---

### B. Cross-Arm Comparison for Scene 0726

**Score Summary:**
| Arm | Qwen3.8 | Qwen3.5 |
|---|---|---|
| default | 0/4 | 3/4 |
| hypothesis | 0/4 | 1/4 |
| prolong | 4/4 | 3/4 |

**Why default Qwen3.8 crashed entirely but Qwen3.5 default got 3/4:**

Both hit the same water-entry bank collision at z≈6–6.5 (outside the z=7..9 swimming zone). However:
- **c4h-default** interpreted circling/stuck warnings as "try different directions from the same spot" and ended up west at x=-5.2, z=6.2 (5 blocks from spawn, opposite side). Gave up navigation at step ~90 and then circled in place with attack actions for 200+ steps.
- **q35-default** was more persistent: tried to strafe along the bank eastward, eventually stumbled into the water at z=7+ around step 24 (after ~40 steps of difficult exits). Once in water, swam effectively using jump+forward combos, reached seagrass by step 52, crossed channel by step 108, and found diamond by step 135. Failed only the final campfire hop due to drifting eastward.

**Root cause difference:** q35-default's strafe-along-bank strategy randomly found a viable entry point; c4h-default's west-ward turn (step 20) was catastrophic and irrecoverable.

---

**Why hypothesis performed worse than default:**

- **c4h-hypothesis:** DAG planning overhead added complexity (10 hypothesis nodes by step 50) but did not unlock water entry. Hypothesis-guided mining strategy (h8) consumed 5 steps (45–50) attacking block, but block was not the root blocker (terrain geometry was). Ended with same bank collision.
- **q35-hypothesis:** Had even worse outcome (1/4 vs. default's 3/4): after reaching vicinity of seagrass at step 12–24, never faced it; entered water somehow by step 158 but lost 140 steps to ESC-loop (steps 99–163). The DAG node for seagrass ("Seagrass visible...") reached 0.95 confidence but milestone never fired because facing was never satisfied. ESC rejection loop (35 times) created a belief cascade: "if ESC was rejected, I must not be done with seagrass yet" → spin → try ESC again → reject → repeat. No fallback to a re-plan.

---

**Why prolong outperformed direct arms:**

- **c4h-prolong: 4/4 (perfect)** — Codex planner issued well-formed sequential programs (tail -50 logs, write actions.json with 5–15-step blocks). Visual frame + state line were sufficient. No hypothesis overhead. Smooth forward+sprint+jump swimming (steps 1–78) and incremental camera turns (steps 79–159) for final positioning. Correctly recognized milestone firing ("The milestone has been triggered!") and exited via ESC.
- **q35-prolong: 3/4 (partial)** — Better than q35-hypothesis (1/4) but worse than c4h-prolong. Success on swim, diamond, campfire but failed seagrass facing rule (107 steps within distance, never facing the point). The issue: planner never issued a "turn to face seagrass" command. It sprinted forward and jumped; yaw remained -45° to -20° instead of rotating to face the water point at yaw ≈0°. ESC-rejection loop at steps 125+ suggests planner was confused by campfire milestone firing (step 99) but still receiving rejections (campfire was reached, but seagrass+diamond rules were not yet all satisfied at first ESC attempt).

---

**Real bottleneck:** Water-entry bank terrain collision and its handling.
- **Default arms** relied on trial-and-error (turn, strafe, jump) until stumbling into a viable entry direction or giving up.
- **Hypothesis arms** added DAG reasoning but no new motor primitives; mining and backup strategies didn't solve the underlying collision.
- **Prolong arms** benefited from structured planning (explicit action blocks) and visual feedback per turn, allowing incremental progress (swim forward → see progress → update plan → next block). No ESC until 100+ steps of sustained forward motion proved progress.

**Facing rule bottleneck (seagrass):** Both prolong arms struggled with the seagrass facing rule (±22.5°) despite being within 5 blocks for >100 steps. The rule is strict and requires deliberate yaw alignment. c4h-prolong happened to satisfy it early (step 12) with a fortuitous camera/yaw combo; q35-prolong never did. DAG planning did not help q35-hypothesis here; the vLLM never recognized that facing was the blocker and issued a targeted turn command.

---

### C. Concrete Fix Hypotheses

#### **For c4h-default:**
1. **Motor primitive:** Add a "water-entry detection" routine that, upon detecting "You have NOT moved" / circling for 8+ steps while adjacent to water, issues a sequence of timed high-jumps (jump+look_down+forward) rather than sustained forward pressure. **Citation:** Steps 6–40 spent ~35 steps on forward/sprint/jump at z=1.2–4.0, all failed to break the 1-block bank. Structured jump sequences (turn aside, jump high, land in water, recover forward) were never attempted.
2. **Observation enhancement:** Provide agent with explicit "water ahead" indicator (pixel-based or distance-to-water-surface), not just visual. **Citation:** Step 49 agent hallucinated being "in water" despite frame being solid green terrain. A ground-truth water-proximity signal would disambiguate in-water vs. at-edge.
3. **Direction/compass:** Provide yaw + compass. Agent turned 90° east (step 20) without understanding it was moving away from goal. **Citation:** Steps 20–87 agent wandered to x=-5.2, then gave up. A compass ("water to the north") would have prevented westward drift.

#### **For c4h-hypothesis:**
1. **Hypothesis validation:** Require hypothesis confidence to drop if predicted action fails for 3+ steps. h8 ("mining will create step down") reached 0.95 by step 46 but mining did not help; hypothesis should have revoked h8 by step 53 and triggered re-plan. **Citation:** Steps 45–63 agent mined block and got wedged in terrain; h8 persisted at 0.75 through step 48 despite zero progress.
2. **Motor recovery:** Add a "escape wedge" macro: on 0-movement for 5 consecutive steps, issue back+jump commands to create separation, then re-evaluate yaw. **Citation:** Steps 50–62 agent was stuck inside terrain/block and issued back/left/right/jump but never coordinated them into a coherent retreat.

#### **For c4h-prolong:**
✓ **Already optimal.** No fixes needed for this scene. Turn granularity could be finer (±5° instead of ±20–45°) for final campfire alignment, but was not necessary.

#### **For q35-default:**
1. **Swimming mechanics documentation:** Agents should be told "sprint in water is ineffective; use forward+jump repeatedly" or implement an automatic swim-forward-jump behavior when in water (z-box). **Citation:** Steps 1–24 agent tried forward+sprint, barely moved. Once it switched to jump+forward around step 5–10, progress increased to ~0.3–0.4 blocks/step.
2. **Milestone feedback per hop:** Provide explicit "hop N complete: find_seagrass done" message, not just aggregate task status. Agent reached diamond (step 135) but continued swimming eastward without acknowledging diamond or realizing campfire was behind it. **Citation:** Steps 135–174 agent was at (3.2, 8.0) (near diamond zone) but moved to (5.6, 7.4) then (16.1, 10.2), drifting away. If agent had heard "find_diamond_block: DONE," it might have adjusted direction.
3. **Direction hints in water:** When in water, provide "campfire bearing: southeast" or similar. **Citation:** Step 138 agent was at (3.3, 8.0) with campfire at (5, 0, 14), distance 6.2; agent drifted to (15.9, 7.7) by step 254 (off course by ~11 blocks).

#### **For q35-hypothesis:**
1. **ESC throttling:** Reject ESC if fewer than all milestones have been reached within the last 20 steps. **Citation:** Steps 99–163 agent pressed ESC 35 times despite only 1 milestone (swim) being close to firing. Every ESC rejection should trigger "milestone status" check in hypothesis DAG; if any milestone shows d > max_distance or steps_with_facing_bad > 0, suppress ESC and re-plan.
2. **Facing rule debugging:** Add explicit log line "seagrass facing rule: distance=X, facing_error=Y, within_distance=<bool>, facing_ok=<bool>, satisfied=<bool>." **Citation:** Step 12 hypothesis correctly believed h1 ("Seagrass visible, confidence 0.95") but never acknowledged the facing constraint; agent assumed the position rule was sufficient.
3. **Hypothesis pruning:** On ESC rejection, zero-out confidence for all hypotheses older than 20 steps. **Citation:** Step 99+ h1 ("Seagrass visible") was still present in state but h4/h6 (about water width and clear entry paths) were outdated; they cluttered the decision space.

#### **For q35-prolong:**
1. **Seagrass yaw alignment:** After reaching within-5-blocks distance, add a turn-to-face-target sub-plan. **Citation:** Steps 10–116 agent was within 5 blocks for 107 consecutive steps but facing error ranged 93.7°–154.4°, never ≤22.5°. A 20-step sub-plan "rotate yaw from -45° toward seagrass at yaw 0° in 5-degree increments" would have been ~16 steps to rotate 80° and likely satisfied the rule.
2. **Milestone-done acknowledgment:** When environment sends "[MILESTONE] find_X done", explicitly update PLAN to "move to next hop." **Citation:** Step 99 campfire milestone fired but agent issued ESC at step 125 anyway; the 26-step gap shows planner didn't register the completion. A clear "Milestone find_soul_campfire COMPLETE" message in briefing would have prevented ESC-loop.
3. **Turn precision in shelter:** For hops 3–4 (diamond and campfire, both within shelter), issue ±15° incremental camera yaw between action blocks instead of ±45°. **Citation:** Steps 101–160 agent issued large turns (yaw 40° → -50° → -120° → 60° → etc.) and spent 60 steps locating items that were ≤5 blocks away but out of view due to occlusion by shelter structure.

---

### D. Evidence Table

| Cell | Primary Code | Secondary Codes | 3 Most Telling Step Citations |
|---|---|---|---|
| **c4h-default** | N (stuck on bank) | P (thought wedged in water); D (walked west) | 20 (turned 90° east), 49 (claimed "in water" but green-frame), 300 (capped out at x=-5.2, z=6.2) |
| **c4h-hypothesis** | N (bank collision) | M (h8 mining didn't help); G (thought mining fixed it) | 45–50 (mining attempt), 50 (wedged in collision), 62 (attempted escape via backup/strafe) |
| **c4h-prolong** | — (success) | — | 12 (seagrass found), 63 (swim), 157 (diamond reached) |
| **q35-default** | P + G (drifted east) | N (water drag) | 52 (seagrass OK), 135 (diamond reached), 138 (campfire min d=6.2 then moved away) |
| **q35-hypothesis** | G (ESC loop) | P (never faced seagrass); M (h1 stuck at confident but unsatisfied) | 12 (h1 "seagrass visible" 0.95), 99 (ESC attempt), 135 (35 rejects, still trying) |
| **q35-prolong** | P (facing rule, seagrass) | G (12 ESC rejections after 99); N (water navigation) | 62 (swim OK), 74 (seagrass min d=1.45 but facing 93.7°), 99 (campfire milestone, ESC not recognized) |

---

### Benchmark / Checker Artifacts

**Scene 0726 seagrass facing rule (±22.5°):** The position target [2,0,7] is **in the water itself** at z=7 (water zone z=6..9). Every agent that tried to face this point while navigating through water (especially while moving diagonally northeast/southwest) ended up swimming past it or couldn't stably align. The facing_tolerance of ±22.5° is strict; even c4h-prolong's step-12 success appears to be a coincidental yaw alignment (-20°) that happened to fall within tolerance as it swam diagonally. This is borderline but defensible: finding seagrass requires looking at it, not just swimming through its vicinity.

**No other detected artifacts.** swim_across_channel (position_inside_box z=7..9) is well-formed; diamond and campfire targets are on shore and clearly distinguishable.

---

### Summary Observations

**Central mechanism-driven difference:** Water entry and swimming strategy.
- Agents that stumbled into a viable entry direction (q35-default via strafe, c4h-prolong via structured forward+jump blocks) succeeded at hops 1–3.
- Agents stuck on the initial bank (c4h-default, c4h-hypothesis) or in an ESC-loop belief failure (q35-hypothesis) could not recover.
- Prolong's structured action-block planning with visual feedback per turn enabled iterative progress; direct vLLM arms had no mechanism to detect and adapt to repeated 0-movement signals.

**Secondary bottleneck:** Milestone facing rules (seagrass, diamond, campfire all require facing ±22.5°).
- c4h-prolong satisfied seagrass early by chance.
- q35-prolong and all q35 variants either never aimed at seagrass or never realized facing was the requirement.
- Direct vLLMs did not issue targeted "turn to face" commands; they relied on forward+strafe momentum to align.

---

**End of Report**