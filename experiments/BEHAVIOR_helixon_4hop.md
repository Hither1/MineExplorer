# How the three agents actually behave on the strict 4-hop set (trajectory analysis)

Companion to [RESULTS_helixon_4hop.md](RESULTS_helixon_4hop.md) and
[RESULTS_helixon_4hop_qwen35.md](RESULTS_helixon_4hop_qwen35.md). Those two files report
scores (default×vllm 10/28 → 11/28, hypothesis×vllm 10/28 → 10/28, prolong×codex 12/28 →
14/28 across Qwen3.8-27B → Qwen3.5-27B). This file asks a different question: **what does
each arm actually do, step by step, and which mechanisms lose the hops?** The purpose is
to find each arm's *systematic* problems and the fixes they imply — not to re-rank the
arms (n = 1 seed per cell; nothing here separates arm from seed).

Data: the 42 cells of the two campaigns (`outputs/c4h-*` = Qwen3.8-27B, `outputs/q35-*` =
Qwen3.5-27B; 3 arms × 7 scenes × 2 checkpoints), parsed from the runner logs (per-step
`player_pos`, `rules_passed`, the full LLM reply), PRO-LONG's `logs.txt` and codex event
streams, and the hypothesis DAGs. Parser: `scripts/analyze_4hop_traj.py` (per-cell
digests + `summary.csv`); every claim below cites steps that can be found in the digest of
the named cell. Seven per-scene reports (one bounded reader per scene, all six cells of a
scene compared side by side) fed the synthesis; where a reader's claim was checked against
the raw data and did not hold, it was dropped.

## 0. What the trajectories say (summary)

1. **The score gaps are small, the behavioural differences are not.** The same handful
   of mechanisms lose the hops in every arm; the arms differ mainly in *which* of them
   bites first. Ranked by hops lost across the 42 cells:
   1. **Mining / tool / aiming** — the first unachieved hop is an `inventory_has` rule in
      16 of 42 cells (5 default, 5 hypothesis, 6 prolong). Exactly one cell in the whole
      campaign ever put a mined block into its inventory (q35 prolong 0603: white carpet at
      step 42, quartz at 253). Nobody mined magma, mossy cobblestone, pink concrete or six
      purple concrete.
   2. **Compass / yaw confusion** — every prolong cell on 0311 (both checkpoints) and c4h
      hypothesis 0311 walked *west* into the natural forest looking for "the river to the
      east"; c4h prolong 0182 sprinted south past the whole course. The Qwen3.8 analyzer
      states a yaw→compass mapping 24 times in its briefings and 23 of them are wrong
      (it believes 0 = north, 90 = east; Minecraft: 0 = south, 90 = west, −90 = east).
   3. **False completion and belief lock-in** — the direct arms write "successfully mined
      X" into memory in 9 of 16 mining-scene cells with nothing in the inventory
      (q35 default 0763 after a *single* attack tick, step 18→19), then press ESC:
      default 152 presses / 151 rejected, hypothesis 320 / 318 (202 in one cell), i.e. up
      to two thirds of a cell's budget spent on a rejected ESC. PRO-LONG has the mirror
      problem: it does not notice the *verified* line — c4h 0306 finished 4/4 at step 52
      and paced the corridor for 248 more steps.
   4. **The harness's own movement hints (direct arms only)** — the 8-step "you are
      circling" warning fires on 56–62 % of all steps and the "You have NOT moved …
      likely blocked" line on 20–36 %; 44–71 % of camera-only steps are followed by an
      "I'm stuck" thought, and 25–38 % of all "stuck" thoughts occur while the player is
      moving ≥ 0.15 blocks/tick. In water (0311, 0726) the thresholds misfire on legitimate
      slow progress and both direct arms turned back from the bank.
   5. **Decision granularity** — PRO-LONG's `repeat` programs make it 2–3× faster to the
      first hops (median hop-1 at step 10.5 vs 29.5 default / 17.5 hypothesis, artefact
      hops excluded) and let it swim (0726: 4/4 and 3/4 vs 0/4, 0/4 on Qwen3.8), but
      blind 15–20-tick programs plus `tail`-only log reading make it overshoot and pace,
      and on Qwen3.5 it re-plans every 3–6 steps.
   6. **Benchmark defects** that cap several scenes independently of the agent (§4):
      0603 targets shifted 5 blocks by `/tp`; 0311's hunts pre-satisfied and its "river"
      a raised, flooding water layer with the natural world 5 blocks west of spawn; 0763's
      pen rule counting purple concrete, not fences; 0726's seagrass rule = facing a point
      under water within ±22.5°; 0182's hops 3–4 need mining + a 7-block lava bridge in
      what is left of 300 ticks.
2. **Arm profiles.** *default*: per-tick re-decision, no yaw, no inventory; its single
   memory string locks in wrong beliefs; it thrashes on the hints; ESC-spams when it
   believes it is done or "permanently stuck". *hypothesis*: identical loop plus a DAG
   that never changes an action; the DAG mostly restates the hop list or documents
   motor-level confusion; it re-confirms false hypotheses at 1.0 one step after the
   harness demotes them; more tokens, more ESC spam on Qwen3.5. *prolong*: fast, coarse,
   commits to programs; but the "programmatic memory" is unused (0 note files in 14
   workspaces, 6 `view_image` calls, 465 `tail` calls vs 20 `grep` over 496 turns,
   `grep MILESTONE` in 3 turns of one checkpoint), the compass labels are wrong, it cannot see its own hotbar,
   and it plans mining without aim feedback.
3. **What to fix first** (§5): (a) surface inventory / held item / block-under-crosshair
   and per-hop verification as text (all arms); (b) a compass legend + yaw for the direct
   arms; (c) recalibrate or gate the movement hints; (d) tell every arm how ticks, mining
   and swimming work; (e) for PRO-LONG, put the milestone state and a parsed state summary
   in every turn's prompt instead of hoping for `grep`; (f) repair the four defective
   scenes before spending seeds.

## 1. What each arm sees and does (mechanics that matter for the reading)

- One env step = one game tick: sprinting covers ~0.28 blocks/step, walking ~0.21, water
  ~0.1. 300 steps ≈ 15 s of game time. Turning costs a step; mining needs the attack key
  held on consecutive ticks while the crosshair is on the block (carpet ≤ 5 ticks, quartz
  ~3 with a diamond pickaxe, purple concrete ~7 with a pickaxe / ~54 by hand or with a
  fence).
- **default**: task text; a ≤ 200-word memory it rewrites every step; the last 20
  frames (320×180) each captioned with the previous thought/action; text hints: pitch,
  "moved X blocks since last step (now x=,z=)" or "You have NOT moved … likely blocked",
  the 8-step net-displacement "circling" warning when < 1 block, spawn distance, and a
  task-level "The environment has NOT verified the task as complete yet". No yaw, no
  inventory, no held item, no per-hop feedback.
- **hypothesis**: the same plus its DAG (≤ 8 shown) and 2–5-step plan; it must emit
  hypothesis ops and a plan each step; the DAG is advisory. `on_esc_rejected` demotes
  "confirmed" nodes to active/0.5.
- **prolong**: a Codex agent that gets an append-only `logs.txt` ([STATE] pos/pitch/yaw/
  moved per tick, its own [PLAN]s, a [MILESTONE] line only when the task-level
  verification message changes, [NOTE]s), the current 640×360 frame attached, a persistent
  workspace, and writes `actions.json` (≤ 15 entries × repeat ≤ 20, ≤ 40 steps/turn). It
  sees numeric yaw but no compass legend; no inventory. The first frame of every episode
  (all arms) is the 128×128 reset observation, later frames are 640×360.

## 2. Behaviour profile (14 cells per arm, both checkpoints)

| | default | hypothesis | prolong |
|---|---|---|---|
| milestones (of 56) | 21 | 20 | 26 |
| steps used (mean/cell) | 288 | 279 | 272 |
| median hop-1 / hop-2 step (cells that reached it; 0763 hop 1 and 0603 position hops excluded) | 29.5 / 108 | 17.5 / 79.5 | **10.5 / 34.5** |
| median path length per cell (blocks) | 36 | 41 | 20 |
| median max distance from spawn | 9.8 | 11.7 | 14.9 |
| stuck ticks (< 0.05 blocks), median fraction | 0.24 | 0.20 | 0.37 (mostly standing still to attack) |
| action mix: move / turn-only / turn+move / jump+move / attack (% of steps) | 55 / 16 / 5 / 7 / 11 | 53 / 17 / 4 / 6 / 8 | 42 / 7 / 0 / 14 / 34 |
| ESC pressed / rejected | 152 / 151 | 320 / 318 | 13 / 13 |
| analyzer turns (steps per turn) | – | – | 176 c4h (11.1), 320 q35 (5.8) |
| "stuck/blocked" thoughts (share of steps; share of those while moving ≥ 0.15/tick) | 66 % / 31 % (c4h), 41 % / 29 % (q35) | 78 % / 38 %, 25 % / 25 % | rare: 4–5 turns per checkpoint claim "blocked" while moving normally, all in natural forest |
| cells with a false "mined X" statement in memory/thought (of 8 mining-scene cells) | 4 | 5 | 0 in [PLAN]s; briefings claim it twice on 0482 |
| workspace notes / view_image / `grep MILESTONE` | – | – | 0 files in 14 workspaces / 6 calls / 3 turns (all q35) |

Per-scene hop frames (arm columns c4h then q35; −1 = never):

| scene | c4h default | c4h hypothesis | c4h prolong | q35 default | q35 hypothesis | q35 prolong |
|---|---|---|---|---|---|---|
| 0182 | 7,112,-1,-1 | 8,38,-1,-1 | -1,-1,-1,-1 | 28,216,-1,-1 | -1,-1,-1,-1 | 9,22,-1,-1 |
| 0306 | 10,41,57,135 | 7,15,46,106 | 6,14,20,52 | 6,16,21,-1 | 6,38,23,194 | 6,14,20,55 |
| 0311 | 31,-1,·,· | -1,-1,·,· | -1,-1,·,· | 104,-1,·,· | 34,-1,·,· | -1,-1,·,· |
| 0482 | 66,-1,-1,-1 | 27,-1,-1,-1 | 37,-1,-1,-1 | -1,-1,-1,-1 | 246,-1,-1,-1 | 22,-1,-1,-1 |
| 0603 | -1,-1,-1,-1 | -1,-1,264*,-1 | 38*,-1,-1,-1 | -1,-1,-1,-1 | -1,-1,51*,-1 | -1,**42**,-1,**253** |
| 0726 | -1,-1,-1,-1 | -1,-1,-1,-1 | 12,63,157,81 | 52,108,135,-1 | -1,158,-1,-1 | -1,62,78,99 |
| 0763 | 1,51,-1,-1 | 3,234,-1,-1 | 1,27,-1,-1 | 1,165,-1,-1 | 1,121,-1,-1 | 1,220,-1,-1 |

`*` = fired only because of the 0603 target shift (§4). 0311's hunt hops are excluded (pre-satisfied).

## 3. The systematic problems, with evidence

### 3.1 Mining, tool selection and aiming (all arms; the largest single loss)

- Only q35 prolong 0603 ever mined anything. Its successful attempts show what it takes:
  carpet at pitch 60°, standing 1 block away, `attack ×5` twice with a small yaw
  correction in between (steps 31–42); quartz only after it stopped adjusting the camera,
  walked `forward+attack ×10` up to the block and then held `attack ×10` (steps 236–253:
  the block broke on the 8th consecutive tick). Everything else failed on one of three
  things:
  - **Wrong tool / can't read the hotbar.** 0763: the pickaxe is in slot 3 behind fence
    (1) and gate (2). c4h prolong looked at the inventory screen, chose `hotbar.2`, and
    hit purple concrete with a fence gate for ~170 steps (turns 9–16, steps 69–210, 20-tick
    attack streaks, "the hotbar still shows Oak Fence Gate selected"); one block broke at
    step 231 after `hotbar.3`. 0182 q35 prolong *had* the pickaxe selected, mined at the
    wrong aim for 100 steps, then read the inventory screenshot as "cobblestone in slot 1,
    a shield in slot 2, no pickaxe" (turn 31, step 217) — the frame shows a diamond pickaxe
    in slot 1 (checked) — deselected it with `hotbar.2/3`, and set off to craft a stone
    pickaxe from trees. No direct-arm cell in 0763/0482 issued a hotbar action at all.
  - **Aim without feedback.** The agents guess pitch/yaw and get no signal about what the
    crosshair is on. c4h prolong 0482 stood inside the hut and hit the stone-brick walls
    left and right of the mossy blocks for 200 attack ticks ("I've been hitting the right
    stone brick wall", turn 15); c4h prolong 0603 attacked the red stairs' top surface at
    x≈8.9 believing it was the quartz (turns 22–30); c4h default 0603 tried the carpet at
    pitch 40° from 0.2 blocks (steps 6–7) and gave up after 2 ticks.
  - **Ticks are not held.** Direct arms typically attack for 1–3 consecutive steps then
    re-decide (default max attack streak 0–16 across cells; hypothesis 0–19); PRO-LONG's
    programs hold 5–20 ticks but the analyzer often interleaves camera moves between
    bursts, restarting the block.
- Consequence for hop chains: 0482 (mossy → pink → build), 0763 (6 concrete → pen), 0182
  (magma → bridge), 0603 (carpet, quartz) all stall at the first mining hop; the building
  hops were never even reachable.

### 3.2 Compass / yaw / "which way is east"

- The task texts use compass words ("river to the east", "walk east through the
  doorways", "far platform"), the checker's targets are absolute, and no arm is told the
  yaw convention. PRO-LONG sees `yaw=` and labels it wrong: c4h analyzers state 0 = north,
  −90 = west, 180 = south (0182 turn 2: "facing west (yaw=−90)"; 0306 turn 6: "facing
  north (yaw=0)"), q35: "Turn east (yaw=90)" (0311 turn 1). Result: 0311 c4h prolong
  ended 17 blocks west of spawn, q35 prolong 43 blocks west, having "found the river" in the
  natural forest (turn 8: "Excellent! I can see the river now!" at rel (−14.7, −11.4)); 0182
  c4h prolong turned back to yaw 0 ("face north") and sprinted 27 blocks south past the
  banner (min distance 4.0 at step 22 while facing 90° away), then fell into a natural
  ravine for 130 steps.
- Direct arms have no yaw and must infer heading from x/z deltas; c4h hypothesis 0311
  wrote "Turned east (yaw+90)" at step 2 and spent 300 steps cutting trees westward; q35
  default 0306 turned 90° at step 8 and never got back on the corridor axis (3/4).
  c4h default 0311 got it right only after 20 steps of trial (turned to −90 at step 20).

### 3.3 False completion, "seeing = finding", and ESC behaviour

- The checker requires proximity + facing (or an inventory change); the agents treat
  *seeing* the object, or *issuing* the action, as completion, and there is no per-hop
  feedback to correct them. q35 hypothesis 0306 pressed ESC at step 13 ("I have visually
  confirmed all sub-goals … the orange banner is clearly visible at the end of the
  corridor", 3 blocks from spawn) and 69 more times before it finally walked to the
  banner at 194. q35 default 0763 step 18 `attack ×1` → step 19 "I have successfully mined
  the purple concrete block", then tried to build the pen for 280 steps. q35 hypothesis
  0603 step 98: "The visual evidence shows the block has broken", memory "Mined white
  carpet (h2). Mined red nether brick stairs (h3)", 202 ESC presses to step 300 while
  reading "NOT verified" every step ("I have exhausted all physical actions").
- **The memory / DAG lock the error in.** Once "mined X" is in the memory string it is
  copied forward every step (9 of 16 direct-arm mining cells; up to 297 steps in one cell);
  the hypothesis agent re-confirms the same nodes at confidence 1.0 one step after
  `on_esc_rejected` demoted them (0603 steps 98–100). Nothing in either loop asks "which
  hop could be unverified, and how would I check?".
- The other ESC mode is **giving up**: c4h default 0311 (84 presses from step 172,
  "permanently stuck in this river channel"), c4h default 0182 (17, "collision loop for
  170 steps"). Under the hint protocol a rejected ESC is a wasted tick.
- PRO-LONG almost never presses ESC (13 presses in 14 cells) and pays the opposite price:
  c4h 0306 verified 4/4 at step 52; the [MILESTONE] "HAS verified" line was written to
  logs.txt once and scrolled out of the `tail -40` window within a turn; the analyzer never
  grepped for it and paced the corridor south↔north five times to step 300 (turns 7–26,
  "I can see the orange banner ahead … let me continue forward to reach the chamber").
  q35 0306 is the counter-example: it ran `grep MILESTONE` at turn 7 and pressed ESC at 56.

### 3.4 The movement hints (direct arms): a hint that mostly cries wolf

- The "NOT moved … you are likely blocked by terrain" line is emitted whenever the tick's
  displacement is < 0.05, i.e. also after every camera-only step; the "circling" warning
  whenever the 8-step net displacement is < 1 block, i.e. during any scan, any mining, any
  water crossing. Measured over the 28 direct-arm cells: circling warning present on 56–62 %
  of steps, NOT-moved on 20–36 %; only 5–13 % of steps are a real block (a move action
  that produced no displacement).
- The models believe it: 44–71 % of camera-only steps are followed by an "I'm stuck"
  thought; c4h default 0182 step 29 "stuck for 20+ steps … trees are blocking my path" on
  a bare stone platform; c4h default 0306 steps 3–6 "BARELY MOVING – only 0.3 blocks from
  spawn after 2 sprint steps. May be blocked" (it was sprinting normally at 0.2–0.28/tick)
  → strafes and camera turns instead of walking down the corridor. The narrative then
  drives evasive actions (jump, back, strafe, "one full turn") that pull the agent off the
  target: at the 0311 river bank q35 hypothesis (steps 48–66) read the < 1-block/8-step
  warning as "colliding with a vertical bank", backed off, turned, and then believed it had
  crossed ("I have successfully crossed the river and am now on the plains", step 69, at
  x = 5.7 heading south-west; it never entered the water again). PRO-LONG, which sees the
  raw per-tick `moved=` and is told only that "0.00 repeatedly means blocked", makes this
  mistake in 4–5 turns per checkpoint, all in the natural forest.
- Related: no arm is told the movement scale (0.2–0.28 blocks/tick), so "moved 0.28
  blocks" reads as failure to both the direct arms and the Qwen3.5 analyzer ("moved=0.28
  is very low, suggesting I'm blocked", 0311 turn 2).

### 3.5 Decision granularity: per-tick re-decision vs. programs

- PRO-LONG commits to `forward+sprint ×10–20` and reaches hop 1/2/3 of 0306 at 6/14/20 on
  both checkpoints; the direct arms need 10/41/57 (c4h default) — the corridor is straight.
  In 0726 the c4h direct arms never entered the water (default drifted west to x = −5.2 and
  stood there 220 steps; hypothesis mined the bank block and wedged itself), while c4h
  prolong swam across with repeated `forward+sprint+jump` blocks (steps 34–88) and finished
  4/4 by 159; q35 default did cross but needed 100 steps of thrash at the bank.
- The cost of programs: 15-tick sprints overshoot rooms (0306 c4h: exits into the forest
  every pass), and turns are coarse (±45–90°), so a facing rule of ±22.5° is met by
  accident (0726 q35 prolong within 5 blocks of the seagrass point for 107 steps, never
  facing it; c4h got it at step 12 with yaw −20°). On Qwen3.5 the analyzer re-plans every
  3–6 steps (0482: 92 turns, the last 19 verbatim "I've moved closer to the oak room …")
  — programs without the commitment.

### 3.6 Memory: what each mechanism actually retains

- *default*: the memory string is rewritten every step and mirrors the current thought;
  it carries the hop list well (0306, 0763 memories list the four hops correctly) but also
  carries every wrong belief forward (§3.3), and it never contains yaw, inventory or which
  hop is verified because it was never given them.
- *hypothesis*: the DAG grows to 26–75 nodes on Qwen3.8 (median confidence 0.1–0.3) and
  4–37 on Qwen3.5 (0.5–1.0). Four nodes are the hop scaffolding created at step 1 in every
  cell; most of the rest are motor-level ("There is a low block or subtle obstacle at
  ground level blocking forward movement", 0482) or restated goals; confidence is not
  updated against outcomes (0311 c4h h12 "breaking tree trunks will clear a path" stays
  0.65 through 46 attack ticks with no progress). No cell shows the DAG choosing an action
  the memory-only agent would not have chosen; the one place it helped (0311 q35 diagnosing
  turn+move coupling, h14) is a prompt rule restated, not a discovery.
- *prolong*: the intended mechanism — parse the log programmatically, keep notes, revisit
  frames — did not happen: 610 `cat > actions.json`, 465 `tail`, 20 `grep`, 0 note files,
  6 `view_image`. What carries state is the resumed codex conversation (all previous
  briefings and tail dumps), which is why it re-reads "the chamber is ahead" and repeats
  itself once the conversation is full of it.

## 4. Benchmark / harness defects found on the way (fix before more seeds)

- **0603 — every position rule is off by 5 blocks.** The scene's last command
  `/tp @p ~0 ~1 ~5` moves the player before spawn is recorded, so `find_purple_bed`
  (target rel (0,0,6)) is 3 blocks *outside* the bedroom's south wall while the bed is 1
  block in front of the player at spawn ("I can see a purple bed in the bottom center of
  the screen", c4h default step 3, distance-to-target 6.0). The three "hits" (c4h prolong
  38, c4h hypothesis 264, q35 hypothesis 51) are agents standing near a south wall facing
  south. Only the two inventory hops measure anything.
- **0311 — the platform is 30×30 but spawn is 5 blocks from its west edge**, so the
  natural forest fills the view to the west/south, the "river" is a 1-block layer of
  source water placed at y = 0 on top of the ground (surface above the banks, spreading as
  flowing water over both sides), and c4h default sank to y ≈ −0.5 at x ≈ 9 and could not
  leave for 250 steps (steps 45–300; sand collapse or current — inference). Hunts are
  pre-satisfied (known). No arm reached the plains.
- **0763 — `build_animal_pen` counts ≥ 6 *purple_concrete* blocks in the grassy box**;
  the task text says "using the oak fences in your inventory". Hop 4 cannot be earned by
  following the text.
- **0726 — `find_seagrass` = distance ≤ 5 to a point *in* the channel and facing it within
  ±22.5°**; an agent swimming straight across at yaw 0 passes it facing 60–150° away (four
  cells within distance, never facing).
- **0182 — hops 3–4 need a pickaxe (slot 1), a mined magma block and a 7-block cobblestone
  bridge**; with ~250 ticks left after the button, no cell got past mining (see §3.1). The
  natural world begins 5 blocks from the platform on three sides.
- **Harness**: the first frame of every episode is the 128×128 reset observation (later
  frames 640×360); the milestone hint is task-level only; the movement-hint thresholds are
  land-sprint thresholds (§3.4); `validate_action` silently turns sprint/sneak-without-
  direction into a no-op (rare: 4 default, 14 hypothesis steps).

## 5. What the evidence says to change, and how to test it cheaply

Ordered by hops that would plausibly be recovered; each is a small change to
`eval_benchmark.py` hints / the prompts / `prolong_mc/prompts.py`, testable on 1–2 scenes
× 1 seed before any campaign.

1. **Give every arm the game state it is blind to, as text** (the runner already has it in
   `info`): hotbar contents + selected slot + held item; inventory deltas ("+1
   white_carpet"); the block under the crosshair and its break progress if the sandbox
   can report it (else at least "attack ticks held on the same block: n"); numeric yaw
   with a legend ("yaw −90 = east (+x)"). Test: 0763 + 0603 with default and prolong —
   does anyone select slot 3 in < 20 steps, does the carpet get mined?
2. **Per-hop verification feedback under the hint protocol** ("hop 1 find_granite:
   verified at step 10; hop 2: not yet"). This is what the agents keep guessing at; it
   removes the "seeing = finding" and "action = outcome" errors and most ESC spam, and it
   is what the [MILESTONE] line already almost is. Note it changes the benchmark's
   "implicit" contract, so it is an arm/protocol variant, not a patch — but the paper's
   no-hint protocol already differs from what these campaigns ran.
3. **Recalibrate the movement hints**: emit "NOT moved" only after a *movement* action;
   scale the 8-step circling threshold to the action mix (or suppress it when the last 8
   actions were mostly turns/attacks or when the player is in water); state the movement
   scale ("sprint ≈ 0.28 blocks per step"). Test: 0306 + 0726 default — stuck-thoughts
   after turn-only steps should fall from ~65 % toward zero and the water crossing should
   happen.
4. **Mechanics one-liners in all prompts**: how many ticks a block takes and that the
   attack key must be held on consecutive steps aimed at the block; that swimming is
   forward+jump; that pitch ~60° is needed for a block at your feet; that a "find" hop
   means walk up to (≤ 3–5 blocks) and look at the object.
5. **PRO-LONG specific**: put the milestone state and a parsed summary of the last N
   [STATE] lines (position, yaw→compass, net displacement, held item) into every turn's
   prompt instead of relying on the analyzer to grep; cap `repeat` for `forward` when a
   target is within a few blocks or add a "turn to face (x,z)" primitive; require an
   inventory read before the first mining program. Test: 0306 c4h should ESC at ~56 like
   q35; 0311 should go east.
6. **hypothesis specific**: either drop the DAG or make it do work — bind each hop's node
   to the per-hop verification (2) so a "confirmed" that the environment contradicts is
   forced to refuted with a reason, and stop the agent from re-confirming at 1.0 in the
   next step; forbid ESC while any hop node is unverified.
7. **Scenes**: re-record spawn after `/tp` (or drop the tp) in 0603; make 0763's pen rule
   count fences; give 0311 and 0182 a wider platform and a river that is below grade;
   loosen 0726's seagrass rule to position-only or widen the tolerance; add a static
   screen for gravity blocks / fluids placed above grade.

The order of the arms is unlikely to change from (1)–(4) alone — they help every arm —
but the *ceiling* would: today 16 of 42 cells stop at a mining hop and 6 more at a compass
error, and both are fixable at the harness/prompt level rather than the model level.

## 6. Files

- Digests, per-scene reports and the metrics table used here: `experiments/traj_analysis_4hop/`
  (`read/*.md`, `prolong/*.md`, `summary.csv`, `scene_reports/scene-*.md`, `scenes.txt`,
  `README.md` with the digest format and conventions); regenerate the digests and the
  table with `python scripts/analyze_4hop_traj.py experiments/traj_analysis_4hop`.
- Chinese version of this write-up: `BEHAVIOR_helixon_4hop.zh.md`.
- Raw evidence: `outputs/log-c4h-*.txt`, `outputs/log-q35-*.txt`,
  `outputs/*-prolong-codex-*/*/4-hop/*/prolong_workspace/logs.txt` and
  `codex_turns/turn_*.events.jsonl`, `outputs/*-hypothesis-vllm-*/*/4-hop/*/hypothesis_graph.json`;
  the committed traces in `experiments/trajectories/`.
