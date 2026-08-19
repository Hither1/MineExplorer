# 4-hop trajectory analysis — digests, per-scene reports, metrics

Derived from `outputs/` by `python scripts/analyze_4hop_traj.py experiments/traj_analysis_4hop` (do not
hand-edit `read/`, `prolong/`, `summary.csv`); synthesis in `../BEHAVIOR_helixon_4hop.md` (English)
and `../BEHAVIOR_helixon_4hop.zh.md` (Chinese). `scene_reports/scene-<id>.md` are the seven bounded
per-scene readings (one reader per scene, all six cells side by side) that fed the synthesis; the
synthesis re-checked their key claims against the digests and dropped what did not hold, so prefer the
synthesis where they disagree. `scenes.txt` is the dump of the seven scene definitions.

Data root: this directory.

Cells: `<prefix>-<arm>-<channel>-<scene>` where prefix `c4h` = Qwen3.8-27B (2026-08-18/19 campaign),
`q35` = Qwen3.5-27B (2026-08-19 repeat). Arms: `default-vllm`, `hypothesis-vllm`, `prolong-codex`.
Scenes: 0182 0306 0311 0482 0603 0726 0763. 42 cells total. One seed per cell, 300-step cap.

Files
- `read/<cell>.md` — per-step digest for every cell (all three arms). Header = task text, milestone rules,
  which milestones fired at which frame, ESC-rejected steps, then a PHASES table (runs of the same action
  class with spawn-relative start/end position), then one block per step:
  `step | rel_pos(x,y,z) yaw pitch | moved | <per-milestone d=3D distance to target / f=facing error°, * if rule
  satisfied> | action | T: thought | M: memory (only when changed & ~every 25 steps) | H: hypothesis ops`.
  For prolong cells the "action" is the queued program entry `{...} [tick i/N]` and `PLAN:` is the analyzer's
  [PLAN] text when a new turn starts; `NOTE:` are runner notes (e.g. ESC rejected).
- `prolong/<cell>.md` — for the 14 prolong cells: one section per analyzer turn (`## turn k @ step s`),
  the shell commands it ran (`tail -40 logs.txt`, `WRITE actions.json: {...}`), and every agent message
  (the briefing text). This is the analyzer's reasoning — read it together with `read/`.
- `summary.csv` — per-cell metrics (stuck fraction, path length, action-class counts, ESC presses/rejections,
  turns per prolong cell, per-milestone min distance / facing error / steps-within-distance-but-facing-wrong ...).
- `scenes.txt` — the 7 scene definitions (task text, layout commands, milestone rules, design notes).

Coordinate conventions (important for judging "went the wrong way")
- Spawn-relative: +x = EAST, -x = WEST, +z = SOUTH, -z = NORTH. Player spawns facing yaw 0 = SOUTH (+z) in every scene. Minecraft yaw: 0 = south(+z), 90 = west(-x), ±180 = north(-z), -90 = east(+x).
  So "turn to face east" = yaw -90 = camera [0,-90] (turn LEFT from yaw 0), NOT [0,+90].
- One env step = one game tick. Sprinting forward moves ~0.28 blocks/step, walking ~0.2. 300 steps ≈ 15 s of
  game time ≈ at most ~80 blocks of straight sprinting. Turning costs a step. Mining a block needs the attack key
  held for consecutive ticks while aiming at the block; switching steps to camera/moving resets progress.
- Position rules use 3D distance incl. y (targets are at y=+1 for wall items, +0 for floor items) and the yaw
  facing error must be ≤ facing_tolerance/2. Inventory rules need the item actually in inventory (mined block
  picked up). count_in_box rules query blocks/mobs inside a box.

What each arm receives every step (so you can judge what it *could* have known)
- default: task text; its own long-term memory (a ≤200-word string it rewrites each step); the last 20 frames
  (320x180 downscaled) each captioned with the previous thought+action; ground-truth text lines: pitch;
  "moved X blocks since last step (now x=,z=)"; "You have NOT moved" warning; 8-step net-displacement warning;
  distance from spawn; and a task-level line "The environment has NOT verified the task as complete yet"
  (it never says which hop is done). No yaw, no inventory/held item, no compass, no per-hop feedback.
- hypothesis: identical to default plus its own hypothesis DAG (up to 8 shown) and 2-5 step plan, and it must
  emit hypothesis updates + plan each step. Advisory only — never overrides the action.
- prolong: a Codex CLI agent (Qwen3.x through the Codex harness, thinking off) that gets an append-only
  `logs.txt` ([STATE] pos/pitch/yaw/moved per tick, its own [PLAN]s, [MILESTONE] line only when the task-level
  verification message changes, [NOTE]s), the CURRENT frame attached (640x360), a persistent workspace, and
  writes `actions.json` = 1-15 entries × repeat ≤20, ≤40 steps per turn. It sees yaw (numeric) but has no
  compass legend either; no inventory info.

Known benchmark/checker artifacts found so far (treat these as scene defects, not agent behaviour)
- 0603: the scene's last command `/tp @p ~0 ~1 ~5` moves the player 5 blocks +z BEFORE spawn is recorded, so all
  spawn-relative position targets are shifted 5 blocks south of the real objects. `find_purple_bed` target is
  ~3 blocks outside the room's south wall (the bed is actually ~1 block directly south of the player at spawn; the doorway east is at rel x=+2, z=0..1, i.e. to the player's LEFT when facing south);
  `find_red_nether_brick_stairs` is likewise 2 blocks outside room 2. The two inventory hops (white carpet,
  quartz block) are unaffected. Any "find_purple_bed" credit is an artifact of standing near the south wall facing south.
- 0311: `hunt_rabbit` / `hunt_donkey` are `count_in_box_at_most` and were already satisfied at spawn (mobs not
  counted in the box), so they are excluded — ceiling is 2/4. `find_river` requires being within 5 blocks of
  spawn-relative (10,0,0) i.e. 10 blocks EAST (+x) and facing it; `find_plains` = x ≥ 15 (east of the river).
  Spawn is on a 30x30 flat platform (x −5..25); WEST of x=−5 is natural terrain (forest, natural rivers).
- 0763: `build_animal_pen` counts ≥6 *purple_concrete* blocks placed in the grassy box, not oak fences — following
  the task text ("using the oak fences") cannot satisfy it; hop 3 needs 6 purple concrete mined (18 available).
  Inventory: slot1 oak_fence×16, slot2 oak_fence_gate×2, slot3 diamond_pickaxe.
- 0482: `build_hidden_room` = ≥6 pink concrete blocks inside the oak room's box; needs pink concrete mined first
  (iron pickaxe in slot 1). `find_stone_brick_slab` has an 8-block radius (easy).
- 0182: `mine_magma_block` needs a magma block in inventory (diamond pickaxe given, cobblestone×64 given);
  `bridge_lava_gap` = standing on the far platform box (x ≥ 19). The lava gap is x 14..20 (7 wide).
- 0726: `find_seagrass` needs distance ≤5 to (2,0,7) which is IN the water channel (z 6..9), facing tol ±22.5°;
  `swim_across_channel` = being inside the box z 7..9 (i.e. in the water); diamond block at (3,0,12) on the far
  shore, campfire (5,0,14).
- 0306: linear corridor: granite z2-5, bricks z6-10 (banner at (0,1,9) on the west wall), oak chamber z11-15
  (orange banner at (5,0,14)). All four rules are position+facing.
