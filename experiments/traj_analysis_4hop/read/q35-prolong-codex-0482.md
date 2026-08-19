# q35-prolong-codex-0482  arm=prolong
TASK: Find the stone brick slabs on the ground near the stone structure. Go inside and mine the mossy cobblestone blocks. Then walk to the pink concrete wall and mine some pink concrete. Finally, go to the oak room and use the pink concrete to build a hidden room inside it.
MILESTONE RULES (spawn-relative coords; x+ = east, z+ = south; Minecraft yaw: 0=south(+z), 90=west(-x), 180/-180=north(-z), -90=east(+x)):
  - find_stone_brick_slab: position_near_with_facing {"target": [10, 0, 9], "max_distance": 8, "facing_tolerance": 60, "coordinate_frame": "spawn_relative"}
  - mine_mossy_cobblestone: inventory_has {"item": "mossy_cobblestone", "min_count": 1}
  - mine_pink_concrete: inventory_has {"item": "pink_concrete", "min_count": 1}
  - build_hidden_room: count_in_box_at_least {"kind": "block", "object": "pink_concrete", "min": [13, 0, -5], "max": [24, 5, 7], "min_count": 6, "coordinate_frame": "spawn_relative"}
spawn_abs=(-3009.5, 71.0, -5572.5)  milestones_done(frame)={'find_stone_brick_slab': 22}  esc_rejected_steps(n=0)=[]
PHASES (action-class runs; pos = spawn-relative x,z at start -> end):
  steps   1-  1 (  1) turn        (0.0,0.0)->(0.0,0.0) yaw -45->-45
  steps   2- 32 ( 31) move        (0.1,0.1)->(5.9,5.9) yaw -45->-45
  steps  33- 33 (  1) turn        (6.0,6.0)->(6.0,6.0) yaw -65->-65
  steps  34- 41 (  8) move        (6.2,6.1)->(7.9,7.0) yaw -65->-65
  steps  42- 45 (  4) turn        (8.0,7.0)->(8.2,7.1) yaw -35->-5
  steps  46- 48 (  3) move        (8.2,7.2)->(8.2,7.2) yaw -5->-5
  steps  49- 53 (  5) turn        (8.2,7.2)->(8.2,7.2) yaw 85->-95
  steps  54- 56 (  3) mixed       (8.3,7.2)->(8.6,7.2) yaw -95->-5
  steps  57- 79 ( 23) attack      (8.6,7.2)->(8.7,7.2) yaw -5->-5
  steps  80- 80 (  1) turn        (8.7,7.2)->(8.7,7.2) yaw 175->175
  steps  81- 85 (  5) move        (8.7,7.0)->(8.6,6.1) yaw 175->175
  steps  86- 90 (  5) turn        (8.6,5.9)->(8.6,5.8) yaw -95->-95
  steps  91- 95 (  5) move        (8.7,5.8)->(9.6,5.7) yaw -95->-95
  steps  96- 97 (  2) turn        (9.8,5.7)->(9.9,5.7) yaw -5->-95
  steps  98-100 (  3) move        (10.0,5.6)->(10.5,5.6) yaw -95->-95
  steps 101-102 (  2) turn        (10.6,5.6)->(10.7,5.6) yaw -5->175
  steps 103-107 (  5) move        (10.7,5.5)->(10.7,4.6) yaw 175->175
  steps 108-108 (  1) turn        (10.7,4.4)->(10.7,4.4) yaw 85->85
  steps 109-173 ( 65) move        (10.7,4.3)->(-7.0,5.6) yaw 85->85
  steps 174-174 (  1) turn        (-7.1,5.6)->(-7.1,5.6) yaw -5->-5
  steps 175-184 ( 10) attack      (-7.2,5.6)->(-7.3,5.6) yaw -5->-5
  steps 185-186 (  2) other       (-7.3,5.6)->(-7.3,5.6) yaw -5->-5
  steps 187-191 (  5) attack      (-7.3,5.6)->(-7.3,5.6) yaw -5->-5
  steps 192-192 (  1) other       (-7.3,5.6)->(-7.3,5.6) yaw -5->-5
  steps 193-222 ( 30) attack      (-7.3,5.6)->(-7.3,5.6) yaw -5->-5
  steps 223-225 (  3) mixed       (-7.3,5.6)->(-7.3,5.6) yaw -5->-5
  steps 226-235 ( 10) move        (-7.3,5.6)->(-7.3,5.6) yaw -5->-5
  steps 236-237 (  2) mixed       (-7.3,5.6)->(-7.3,5.6) yaw -5->175
  steps 238-247 ( 10) move        (-7.3,5.5)->(-7.5,3.1) yaw 175->175
  steps 248-248 (  1) turn        (-7.5,3.0)->(-7.5,3.0) yaw -95->-95
  steps 249-299 ( 51) move        (-7.4,2.9)->(6.4,1.6) yaw -95->-95
  steps 300-300 (  1) none        (6.7,1.6)->(6.7,1.6) yaw -95->-95

STEPS: step | rel_pos(x,y,z) yaw pitch | moved | per-milestone d=3D dist to target / f=facing error deg (* = rule satisfied this step; "-" = non-position rule) | action | T: thought (trunc) | M: memory (shown when changed, every ~25 steps) | H: hypothesis ops (new statements / status changes)
  1 | (0.0,0.0,0.0) yaw=-45 p=0 | mv=0.00 | find_stone_b:d13.5/f3 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,-45]} [1/1]
      PLAN: Turn left toward the stone structure and move forward to locate the stone brick slabs on the ground. Then enter the structure to mine mossy cobblestone blocks.
  2 | (0.1,0.0,0.1) yaw=-45 p=0 | mv=0.13 | find_stone_b:d13.3/f3 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/5]
  3 | (0.2,0.0,0.2) yaw=-45 p=0 | mv=0.20 | find_stone_b:d13.1/f3 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/5]
  4 | (0.4,0.0,0.4) yaw=-45 p=0 | mv=0.23 | find_stone_b:d12.9/f3 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/5]
  5 | (0.6,0.0,0.6) yaw=-45 p=0 | mv=0.26 | find_stone_b:d12.6/f3 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [4/5]
  6 | (0.8,0.0,0.8) yaw=-45 p=0 | mv=0.27 | find_stone_b:d12.4/f3 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [5/5]
  7 | (1.0,0.0,1.0) yaw=-45 p=0 | mv=0.27 | find_stone_b:d12.1/f3 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/10]
      PLAN: Move forward toward the stone structure entrance to enter it and find the mossy cobblestone blocks to mine.
  8 | (1.2,0.0,1.2) yaw=-45 p=0 | mv=0.28 | find_stone_b:d11.8/f3 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/10]
  9 | (1.4,0.0,1.4) yaw=-45 p=0 | mv=0.28 | find_stone_b:d11.5/f4 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/10]
 10 | (1.5,0.0,1.5) yaw=-45 p=0 | mv=0.28 | find_stone_b:d11.3/f4 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [4/10]
 11 | (1.7,0.0,1.7) yaw=-45 p=0 | mv=0.28 | find_stone_b:d11.0/f4 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [5/10]
 12 | (1.9,0.0,1.9) yaw=-45 p=0 | mv=0.28 | find_stone_b:d10.7/f4 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [6/10]
 13 | (2.1,0.0,2.1) yaw=-45 p=0 | mv=0.28 | find_stone_b:d10.4/f4 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [7/10]
 14 | (2.3,0.0,2.3) yaw=-45 p=0 | mv=0.28 | find_stone_b:d10.1/f4 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [8/10]
 15 | (2.5,0.0,2.5) yaw=-45 p=0 | mv=0.28 | find_stone_b:d9.9/f4 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [9/10]
 16 | (2.7,0.0,2.7) yaw=-45 p=0 | mv=0.28 | find_stone_b:d9.6/f4 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [10/10]
 17 | (2.9,0.0,2.9) yaw=-45 p=0 | mv=0.28 | find_stone_b:d9.3/f4 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/5]
      PLAN: Move forward to enter the stone structure and locate the mossy cobblestone blocks inside.
 18 | (3.1,0.0,3.1) yaw=-45 p=0 | mv=0.28 | find_stone_b:d9.0/f4 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/5]
 19 | (3.3,0.0,3.3) yaw=-45 p=0 | mv=0.28 | find_stone_b:d8.8/f5 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/5]
 20 | (3.5,0.0,3.5) yaw=-45 p=0 | mv=0.28 | find_stone_b:d8.5/f5 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [4/5]
 21 | (3.7,0.0,3.7) yaw=-45 p=0 | mv=0.28 | find_stone_b:d8.2/f5 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [5/5]
 22 | (3.9,0.0,3.9) yaw=-45 p=0 | mv=0.28 | find_stone_b:d7.9/f5* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/5]
      PLAN: Continue moving forward to enter the stone structure and find the mossy cobblestone blocks inside.
 23 | (4.1,0.0,4.1) yaw=-45 p=0 | mv=0.28 | find_stone_b:d7.6/f5* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/5]
 24 | (4.3,0.0,4.3) yaw=-45 p=0 | mv=0.28 | find_stone_b:d7.4/f6* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/5]
 25 | (4.5,0.0,4.5) yaw=-45 p=0 | mv=0.28 | find_stone_b:d7.1/f6* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [4/5]
 26 | (4.7,0.0,4.7) yaw=-45 p=0 | mv=0.28 | find_stone_b:d6.8/f6* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [5/5]
 27 | (4.9,0.0,4.9) yaw=-45 p=0 | mv=0.28 | find_stone_b:d6.5/f6* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/3]
      PLAN: Move forward to enter the stone structure and find the mossy cobblestone blocks inside.
 28 | (5.1,0.0,5.1) yaw=-45 p=0 | mv=0.28 | find_stone_b:d6.2/f7* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/3]
 29 | (5.3,0.0,5.3) yaw=-45 p=0 | mv=0.28 | find_stone_b:d6.0/f7* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/3]
 30 | (5.5,0.0,5.5) yaw=-45 p=0 | mv=0.28 | find_stone_b:d5.7/f7* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/3]
 31 | (5.7,0.0,5.7) yaw=-45 p=0 | mv=0.28 | find_stone_b:d5.4/f8* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/3]
 32 | (5.9,0.0,5.9) yaw=-45 p=0 | mv=0.28 | find_stone_b:d5.1/f8* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/3]
 33 | (6.0,0.0,6.0) yaw=-65 p=0 | mv=0.15 | find_stone_b:d5.0/f12* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,-20]} [1/1]
      PLAN: Turn left slightly and move forward to enter the stone structure and find the mossy cobblestone blocks inside.
 34 | (6.2,0.0,6.1) yaw=-65 p=0 | mv=0.21 | find_stone_b:d4.8/f12* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/3]
 35 | (6.4,0.0,6.2) yaw=-65 p=0 | mv=0.24 | find_stone_b:d4.5/f12* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/3]
 36 | (6.6,0.0,6.4) yaw=-65 p=0 | mv=0.26 | find_stone_b:d4.3/f13* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/3]
 37 | (6.9,0.0,6.5) yaw=-65 p=0 | mv=0.27 | find_stone_b:d4.0/f14* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/5]
      PLAN: Move forward to enter the stone structure and find the mossy cobblestone blocks inside.
 38 | (7.1,0.0,6.6) yaw=-65 p=0 | mv=0.27 | find_stone_b:d3.7/f15* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/5]
 39 | (7.4,0.5,6.7) yaw=-65 p=0 | mv=0.28 | find_stone_b:d3.5/f16* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/5]
 40 | (7.6,0.5,6.8) yaw=-65 p=0 | mv=0.28 | find_stone_b:d3.2/f17* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [4/5]
 41 | (7.9,0.5,7.0) yaw=-65 p=0 | mv=0.28 | find_stone_b:d3.0/f19* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [5/5]
 42 | (8.0,0.5,7.0) yaw=-35 p=0 | mv=0.15 | find_stone_b:d2.8/f10* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,30]} [1/1]
      PLAN: Look around inside the stone structure to find the mossy cobblestone blocks that need to be mined.
 43 | (8.1,0.5,7.1) yaw=-5 p=0 | mv=0.08 | find_stone_b:d2.8/f39 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,30]} [1/1]
 44 | (8.1,0.5,7.1) yaw=175 p=0 | mv=0.05 | find_stone_b:d2.7/f141 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,180]} [1/1]
      PLAN: Turn around to see the other side of the stone structure interior and locate the mossy cobblestone blocks.
 45 | (8.2,0.5,7.1) yaw=-5 p=0 | mv=0.02 | find_stone_b:d2.7/f39 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,180]} [1/1]
      PLAN: Turn back toward the stone structure and move forward to re-enter it, then look for mossy cobblestone blocks.
 46 | (8.2,0.5,7.2) yaw=-5 p=0 | mv=0.12 | find_stone_b:d2.6/f40 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/3]
 47 | (8.2,0.5,7.2) yaw=-5 p=0 | mv=0.02 | find_stone_b:d2.6/f40 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/3]
 48 | (8.2,0.5,7.2) yaw=-5 p=0 | mv=0.02 | find_stone_b:d2.6/f40 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/3]
 49 | (8.2,0.5,7.2) yaw=85 p=0 | mv=0.01 | find_stone_b:d2.6/f129 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,90]} [1/1]
      PLAN: Look around inside the stone structure to find the mossy cobblestone blocks that need to be mined.
 50 | (8.2,0.5,7.2) yaw=175 p=0 | mv=0.01 | find_stone_b:d2.6/f141 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,90]} [1/1]
      PLAN: Look around and up inside the stone structure to find the mossy cobblestone blocks that need to be mined.
 51 | (8.2,0.5,7.2) yaw=175 p=-30 | mv=0.00 | find_stone_b:d2.6/f141 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[-30,0]} [1/1]
 52 | (8.2,0.5,7.2) yaw=175 p=0 | mv=0.00 | find_stone_b:d2.6/f141 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[30,0]} [1/1]
      PLAN: Look down and around inside the stone structure to find the mossy cobblestone blocks on the floor or walls.
 53 | (8.2,0.5,7.2) yaw=-95 p=0 | mv=0.00 | find_stone_b:d2.6/f51 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,90]} [1/1]
 54 | (8.3,0.5,7.2) yaw=-95 p=0 | mv=0.10 | find_stone_b:d2.5/f52 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/2]
      PLAN: Move forward inside the stone structure to examine the walls and floor for mossy cobblestone blocks.
 55 | (8.5,0.5,7.2) yaw=-95 p=0 | mv=0.15 | find_stone_b:d2.4/f55 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/2]
 56 | (8.6,0.5,7.2) yaw=-5 p=0 | mv=0.08 | find_stone_b:d2.4/f33 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,90]} [1/1]
      PLAN: Turn right to examine the back wall of the stone structure for mossy cobblestone blocks.
 57 | (8.6,0.5,7.2) yaw=-5 p=0 | mv=0.05 | find_stone_b:d2.3/f32 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/5]
      PLAN: Mine the mossy cobblestone blocks on the back wall of the stone structure using the pickaxe.
 58 | (8.6,0.5,7.2) yaw=-5 p=0 | mv=0.02 | find_stone_b:d2.3/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/5]
 59 | (8.7,0.5,7.2) yaw=-5 p=0 | mv=0.01 | find_stone_b:d2.3/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/5]
 60 | (8.7,0.5,7.2) yaw=-5 p=0 | mv=0.01 | find_stone_b:d2.3/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/5]
 61 | (8.7,0.5,7.2) yaw=-5 p=0 | mv=0.00 | find_stone_b:d2.3/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/5]
 62 | (8.7,0.5,7.2) yaw=-5 p=0 | mv=0.00 | find_stone_b:d2.3/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/5]
      PLAN: Continue mining the mossy cobblestone blocks to collect them.
 63 | (8.7,0.5,7.2) yaw=-5 p=0 | mv=0.00 | find_stone_b:d2.3/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/5]
 64 | (8.7,0.5,7.2) yaw=-5 p=0 | mv=0.00 | find_stone_b:d2.3/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/5]
 65 | (8.7,0.5,7.2) yaw=-5 p=0 | mv=0.00 | find_stone_b:d2.3/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/5]
 66 | (8.7,0.5,7.2) yaw=-5 p=0 | mv=0.00 | find_stone_b:d2.3/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/5]
 67 | (8.7,0.5,7.2) yaw=-5 p=0 | mv=0.00 | find_stone_b:d2.3/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/5]
 68 | (8.7,0.5,7.2) yaw=-5 p=0 | mv=0.00 | find_stone_b:d2.3/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/5]
 69 | (8.7,0.5,7.2) yaw=-5 p=0 | mv=0.00 | find_stone_b:d2.3/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/5]
 70 | (8.7,0.5,7.2) yaw=-5 p=0 | mv=0.00 | find_stone_b:d2.3/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/5]
 71 | (8.7,0.5,7.2) yaw=-5 p=0 | mv=0.00 | find_stone_b:d2.3/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/5]
 72 | (8.7,0.5,7.2) yaw=-5 p=0 | mv=0.00 | find_stone_b:d2.3/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/5]
      PLAN: Continue mining the mossy cobblestone blocks to collect enough for the task.
 73 | (8.7,0.5,7.2) yaw=-5 p=0 | mv=0.00 | find_stone_b:d2.3/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/5]
 74 | (8.7,0.5,7.2) yaw=-5 p=0 | mv=0.00 | find_stone_b:d2.3/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/5]
 75 | (8.7,0.5,7.2) yaw=-5 p=0 | mv=0.00 | find_stone_b:d2.3/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/5]
 76 | (8.7,0.5,7.2) yaw=-5 p=0 | mv=0.00 | find_stone_b:d2.3/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/5]
 77 | (8.7,0.5,7.2) yaw=-5 p=0 | mv=0.00 | find_stone_b:d2.3/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/3]
      PLAN: Mine a few more mossy cobblestone blocks, then exit the stone structure and walk to the pink concrete wall to mine pink concrete.
 78 | (8.7,0.5,7.2) yaw=-5 p=0 | mv=0.00 | find_stone_b:d2.3/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/3]
 79 | (8.7,0.5,7.2) yaw=-5 p=0 | mv=0.00 | find_stone_b:d2.3/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/3]
 80 | (8.7,0.5,7.2) yaw=175 p=0 | mv=0.00 | find_stone_b:d2.3/f149 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,180]} [1/1]
      PLAN: Exit the stone structure and walk toward the pink concrete wall to mine pink concrete blocks.
 81 | (8.7,0.5,7.0) yaw=175 p=0 | mv=0.13 | find_stone_b:d2.4/f151 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/5]
 82 | (8.6,0.5,6.8) yaw=175 p=0 | mv=0.20 | find_stone_b:d2.6/f153 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/5]
 83 | (8.6,0.5,6.6) yaw=175 p=0 | mv=0.23 | find_stone_b:d2.8/f155 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/5]
 84 | (8.6,0.5,6.4) yaw=175 p=0 | mv=0.26 | find_stone_b:d3.0/f157 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [4/5]
 85 | (8.6,0.5,6.1) yaw=175 p=0 | mv=0.27 | find_stone_b:d3.3/f159 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [5/5]
 86 | (8.6,0.5,5.9) yaw=-95 p=0 | mv=0.15 | find_stone_b:d3.4/f70 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,90]} [1/1]
      PLAN: Turn right to locate the pink concrete wall and move toward it to mine pink concrete blocks.
 87 | (8.6,0.5,5.9) yaw=-5 p=0 | mv=0.08 | find_stone_b:d3.5/f20* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,90]} [1/1]
      PLAN: Turn right again to locate the pink concrete wall.
 88 | (8.6,0.5,5.8) yaw=-95 p=0 | mv=0.04 | find_stone_b:d3.5/f70 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,-90]} [1/1]
      PLAN: Turn left to locate the pink concrete wall.
 89 | (8.6,0.5,5.8) yaw=-5 p=0 | mv=0.02 | find_stone_b:d3.6/f19* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,90]} [1/1]
      PLAN: Turn right to locate the pink concrete wall.
 90 | (8.6,0.5,5.8) yaw=-95 p=0 | mv=0.01 | find_stone_b:d3.6/f71 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,-90]} [1/1]
      PLAN: Exit the stone structure and move forward to locate the pink concrete wall.
 91 | (8.7,0.5,5.8) yaw=-95 p=0 | mv=0.13 | find_stone_b:d3.5/f73 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/5]
 92 | (8.9,0.5,5.7) yaw=-95 p=0 | mv=0.20 | find_stone_b:d3.5/f76 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/5]
 93 | (9.1,0.5,5.7) yaw=-95 p=0 | mv=0.24 | find_stone_b:d3.4/f80 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/5]
 94 | (9.4,0.5,5.7) yaw=-95 p=0 | mv=0.26 | find_stone_b:d3.4/f84 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [4/5]
 95 | (9.6,0.5,5.7) yaw=-95 p=0 | mv=0.27 | find_stone_b:d3.4/f89 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [5/5]
 96 | (9.8,0.5,5.7) yaw=-5 p=0 | mv=0.15 | find_stone_b:d3.4/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,90]} [1/1]
      PLAN: Turn right to locate the pink concrete wall.
 97 | (9.9,0.5,5.7) yaw=-95 p=0 | mv=0.08 | find_stone_b:d3.4/f92 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,-90]} [1/1]
      PLAN: Exit the stone structure and move forward to locate the pink concrete wall.
 98 | (10.0,0.5,5.6) yaw=-95 p=0 | mv=0.17 | find_stone_b:d3.4/f95 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/3]
 99 | (10.2,0.5,5.6) yaw=-95 p=0 | mv=0.22 | find_stone_b:d3.4/f99 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/3]
100 | (10.5,0.5,5.6) yaw=-95 p=0 | mv=0.25 | find_stone_b:d3.5/f103 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/3]
101 | (10.6,0.5,5.6) yaw=-5 p=0 | mv=0.14 | find_stone_b:d3.5/f15* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,90]} [1/1]
      PLAN: Turn right to locate the pink concrete wall.
102 | (10.7,0.5,5.6) yaw=175 p=0 | mv=0.07 | find_stone_b:d3.5/f163 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,180]} [1/1]
      PLAN: Exit the stone structure and move forward to locate the pink concrete wall.
103 | (10.7,0.5,5.5) yaw=175 p=0 | mv=0.13 | find_stone_b:d3.7/f163 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/5]
104 | (10.7,0.5,5.3) yaw=175 p=0 | mv=0.20 | find_stone_b:d3.9/f164 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/5]
105 | (10.7,0.5,5.0) yaw=175 p=0 | mv=0.24 | find_stone_b:d4.1/f165 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/5]
106 | (10.7,0.4,4.8) yaw=175 p=0 | mv=0.26 | find_stone_b:d4.3/f166 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [4/5]
107 | (10.7,0.3,4.6) yaw=175 p=0 | mv=0.17 | find_stone_b:d4.5/f166 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [5/5]
108 | (10.7,0.0,4.4) yaw=85 p=0 | mv=0.15 | find_stone_b:d4.6/f76 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,-90]} [1/1]
      PLAN: Turn left to locate the pink concrete wall.
109 | (10.7,0.0,4.3) yaw=85 p=0 | mv=0.14 | find_stone_b:d4.7/f77 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/10]
      PLAN: Move forward toward the pink concrete wall to mine pink concrete blocks.
110 | (10.5,0.0,4.2) yaw=85 p=0 | mv=0.19 | find_stone_b:d4.8/f79 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/10]
111 | (10.3,0.0,4.2) yaw=85 p=0 | mv=0.22 | find_stone_b:d4.9/f82 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/10]
112 | (10.0,0.0,4.1) yaw=85 p=0 | mv=0.24 | find_stone_b:d4.9/f84 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [4/10]
113 | (9.8,0.0,4.1) yaw=85 p=0 | mv=0.26 | find_stone_b:d4.9/f87 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [5/10]
114 | (9.5,0.0,4.1) yaw=85 p=0 | mv=0.27 | find_stone_b:d4.9/f91 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [6/10]
115 | (9.2,0.0,4.2) yaw=85 p=0 | mv=0.27 | find_stone_b:d4.9/f94 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [7/10]
116 | (9.0,0.0,4.2) yaw=85 p=0 | mv=0.28 | find_stone_b:d4.9/f97 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [8/10]
117 | (8.7,0.0,4.2) yaw=85 p=0 | mv=0.28 | find_stone_b:d5.0/f100 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [9/10]
118 | (8.4,0.0,4.2) yaw=85 p=0 | mv=0.28 | find_stone_b:d5.0/f103 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [10/10]
119 | (8.1,0.0,4.3) yaw=85 p=0 | mv=0.28 | find_stone_b:d5.1/f106 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/5]
      PLAN: Move forward to get right up to the pink concrete wall, then mine some pink concrete blocks.
120 | (7.9,0.0,4.3) yaw=85 p=0 | mv=0.28 | find_stone_b:d5.2/f109 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/5]
121 | (7.6,0.0,4.3) yaw=85 p=0 | mv=0.28 | find_stone_b:d5.3/f112 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/5]
122 | (7.3,0.0,4.3) yaw=85 p=0 | mv=0.28 | find_stone_b:d5.4/f115 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [4/5]
123 | (7.0,0.0,4.4) yaw=85 p=0 | mv=0.28 | find_stone_b:d5.5/f118 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [5/5]
124 | (6.7,0.0,4.4) yaw=85 p=0 | mv=0.28 | find_stone_b:d5.7/f120 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/5]
125 | (6.5,0.0,4.4) yaw=85 p=0 | mv=0.28 | find_stone_b:d5.8/f123 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/5]
126 | (6.2,0.0,4.4) yaw=85 p=0 | mv=0.28 | find_stone_b:d6.0/f125 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/5]
127 | (5.9,0.0,4.5) yaw=85 p=0 | mv=0.28 | find_stone_b:d6.1/f127 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [4/5]
128 | (5.6,0.0,4.5) yaw=85 p=0 | mv=0.28 | find_stone_b:d6.3/f129 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [5/5]
129 | (5.3,0.0,4.5) yaw=85 p=0 | mv=0.28 | find_stone_b:d6.5/f131 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/3]
130 | (5.1,0.0,4.5) yaw=85 p=0 | mv=0.28 | find_stone_b:d6.7/f133 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/3]
131 | (4.8,0.0,4.5) yaw=85 p=0 | mv=0.28 | find_stone_b:d6.9/f135 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/3]
132 | (4.5,0.0,4.6) yaw=85 p=0 | mv=0.28 | find_stone_b:d7.1/f136 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/2]
133 | (4.2,0.0,4.6) yaw=85 p=0 | mv=0.28 | find_stone_b:d7.3/f138 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/2]
134 | (3.9,0.0,4.6) yaw=85 p=0 | mv=0.28 | find_stone_b:d7.5/f139 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/2]
135 | (3.7,0.0,4.6) yaw=85 p=0 | mv=0.28 | find_stone_b:d7.7/f141 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/2]
136 | (3.4,0.0,4.7) yaw=85 p=0 | mv=0.28 | find_stone_b:d7.9/f142 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/2]
137 | (3.1,0.0,4.7) yaw=85 p=0 | mv=0.28 | find_stone_b:d8.1/f143 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/2]
138 | (2.8,0.0,4.7) yaw=85 p=0 | mv=0.28 | find_stone_b:d8.4/f144 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/2]
139 | (2.5,0.0,4.7) yaw=85 p=0 | mv=0.28 | find_stone_b:d8.6/f145 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/2]
140 | (2.3,0.0,4.8) yaw=85 p=0 | mv=0.28 | find_stone_b:d8.8/f146 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/2]
141 | (2.0,0.0,4.8) yaw=85 p=0 | mv=0.28 | find_stone_b:d9.1/f147 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/2]
142 | (1.7,0.0,4.8) yaw=85 p=0 | mv=0.28 | find_stone_b:d9.3/f148 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/2]
143 | (1.4,0.0,4.8) yaw=85 p=0 | mv=0.28 | find_stone_b:d9.5/f149 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/2]
144 | (1.1,0.0,4.9) yaw=85 p=0 | mv=0.28 | find_stone_b:d9.8/f150 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/2]
145 | (0.9,0.0,4.9) yaw=85 p=0 | mv=0.28 | find_stone_b:d10.0/f151 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/2]
146 | (0.6,0.0,4.9) yaw=85 p=0 | mv=0.28 | find_stone_b:d10.3/f152 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/2]
147 | (0.3,0.0,4.9) yaw=85 p=0 | mv=0.28 | find_stone_b:d10.5/f152 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/2]
148 | (0.0,0.0,5.0) yaw=85 p=0 | mv=0.28 | find_stone_b:d10.8/f153 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/2]
149 | (-0.3,0.0,5.0) yaw=85 p=0 | mv=0.28 | find_stone_b:d11.0/f154 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/2]
150 | (-0.5,0.0,5.0) yaw=85 p=0 | mv=0.28 | find_stone_b:d11.3/f154 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/2]
151 | (-0.8,0.0,5.0) yaw=85 p=0 | mv=0.28 | find_stone_b:d11.5/f155 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/2]
152 | (-1.1,0.0,5.1) yaw=85 p=0 | mv=0.28 | find_stone_b:d11.8/f155 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/2]
153 | (-1.4,0.0,5.1) yaw=85 p=0 | mv=0.28 | find_stone_b:d12.0/f156 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/2]
154 | (-1.6,0.0,5.1) yaw=85 p=0 | mv=0.28 | find_stone_b:d12.3/f157 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/2]
155 | (-1.9,0.0,5.1) yaw=85 p=0 | mv=0.28 | find_stone_b:d12.5/f157 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/2]
156 | (-2.2,0.0,5.2) yaw=85 p=0 | mv=0.28 | find_stone_b:d12.8/f158 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/2]
157 | (-2.5,0.0,5.2) yaw=85 p=0 | mv=0.28 | find_stone_b:d13.1/f158 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/2]
158 | (-2.8,0.0,5.2) yaw=85 p=0 | mv=0.28 | find_stone_b:d13.3/f158 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/2]
159 | (-3.0,0.0,5.2) yaw=85 p=0 | mv=0.28 | find_stone_b:d13.6/f159 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/2]
160 | (-3.3,0.0,5.3) yaw=85 p=0 | mv=0.28 | find_stone_b:d13.8/f159 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/2]
161 | (-3.6,0.0,5.3) yaw=85 p=0 | mv=0.28 | find_stone_b:d14.1/f160 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/2]
162 | (-3.9,0.0,5.3) yaw=85 p=0 | mv=0.28 | find_stone_b:d14.4/f160 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/2]
163 | (-4.2,0.0,5.3) yaw=85 p=0 | mv=0.28 | find_stone_b:d14.6/f160 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/2]
164 | (-4.4,0.0,5.4) yaw=85 p=0 | mv=0.28 | find_stone_b:d14.9/f161 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/2]
165 | (-4.7,0.0,5.4) yaw=85 p=0 | mv=0.28 | find_stone_b:d15.2/f161 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/2]
166 | (-5.0,0.0,5.4) yaw=85 p=0 | mv=0.28 | find_stone_b:d15.4/f162 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/2]
167 | (-5.3,0.0,5.4) yaw=85 p=0 | mv=0.28 | find_stone_b:d15.7/f162 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/2]
168 | (-5.6,0.0,5.5) yaw=85 p=0 | mv=0.28 | find_stone_b:d16.0/f162 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/2]
169 | (-5.8,0.0,5.5) yaw=85 p=0 | mv=0.28 | find_stone_b:d16.2/f162 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/2]
170 | (-6.1,0.0,5.5) yaw=85 p=0 | mv=0.28 | find_stone_b:d16.5/f163 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/2]
171 | (-6.4,0.0,5.5) yaw=85 p=0 | mv=0.28 | find_stone_b:d16.8/f163 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/2]
172 | (-6.7,0.0,5.6) yaw=85 p=0 | mv=0.28 | find_stone_b:d17.0/f163 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/2]
173 | (-7.0,0.0,5.6) yaw=85 p=0 | mv=0.28 | find_stone_b:d17.3/f164 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/2]
174 | (-7.1,0.0,5.6) yaw=-5 p=0 | mv=0.15 | find_stone_b:d17.4/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,-90]} [1/1]
      PLAN: Turn left to face the pink concrete wall, then mine some pink concrete blocks.
175 | (-7.2,0.0,5.6) yaw=-5 p=0 | mv=0.08 | find_stone_b:d17.5/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/5]
      PLAN: Mine the pink concrete blocks to collect some pink concrete.
176 | (-7.2,0.0,5.6) yaw=-5 p=0 | mv=0.05 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/5]
177 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.02 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/5]
178 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.01 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/5]
179 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.01 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/5]
180 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/5]
      PLAN: Continue mining the pink concrete blocks to collect them.
181 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/5]
182 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/5]
183 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/5]
184 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/5]
185 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"inventory":1} [1/1]
      PLAN: Check inventory to confirm I have pink concrete, then navigate to the oak room to build a hidden room.
186 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"inventory":1} [1/1]
      PLAN: Close inventory and continue mining pink concrete blocks to collect them.
187 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/5]
188 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/5]
189 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/5]
190 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/5]
191 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/5]
192 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"inventory":1} [1/1]
      PLAN: Close the inventory and continue mining pink concrete blocks to collect them.
193 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/5]
      PLAN: Continue mining pink concrete blocks to collect them.
194 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/5]
195 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/5]
196 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/5]
197 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/5]
198 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/5]
199 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/5]
200 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/5]
201 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/5]
202 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/5]
203 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/5]
204 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/5]
205 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/5]
206 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/5]
207 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/5]
208 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/5]
209 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/5]
210 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/5]
211 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/5]
212 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/5]
213 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/5]
214 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/5]
215 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/5]
216 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/5]
217 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/5]
218 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/5]
219 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/5]
220 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/5]
221 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/5]
222 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/5]
223 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"inventory":1} [1/1]
      PLAN: Check inventory to see what items I have collected, then determine the next steps for building the hidden room.
224 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"inventory":1} [1/1]
      PLAN: Close inventory, turn toward the oak room, and move forward to reach it. Then check if there are pink concrete blocks inside that I can use to build the hidden room.
225 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,90]} [1/1]
226 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/10]
227 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/10]
228 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/10]
229 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [4/10]
230 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [5/10]
231 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [6/10]
232 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [7/10]
233 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [8/10]
234 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [9/10]
235 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [10/10]
236 | (-7.3,0.0,5.6) yaw=-5 p=0 | mv=0.00 | find_stone_b:d17.6/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"inventory":1} [1/1]
      PLAN: Close the inventory and then navigate to the oak room to check for pink concrete blocks.
237 | (-7.3,0.0,5.6) yaw=175 p=0 | mv=0.00 | find_stone_b:d17.6/f106 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,180]} [1/1]
      PLAN: Turn around and move forward toward the oak room to check for pink concrete blocks inside.
238 | (-7.3,0.0,5.5) yaw=175 p=0 | mv=0.13 | find_stone_b:d17.7/f107 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/10]
239 | (-7.3,0.0,5.3) yaw=175 p=0 | mv=0.20 | find_stone_b:d17.7/f107 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/10]
240 | (-7.3,0.0,5.0) yaw=175 p=0 | mv=0.23 | find_stone_b:d17.8/f108 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/10]
241 | (-7.4,0.0,4.8) yaw=175 p=0 | mv=0.26 | find_stone_b:d17.9/f109 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [4/10]
242 | (-7.4,0.0,4.5) yaw=175 p=0 | mv=0.27 | find_stone_b:d18.0/f109 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [5/10]
243 | (-7.4,0.0,4.3) yaw=175 p=0 | mv=0.27 | find_stone_b:d18.0/f110 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [6/10]
244 | (-7.4,0.0,4.0) yaw=175 p=0 | mv=0.28 | find_stone_b:d18.1/f111 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [7/10]
245 | (-7.5,0.0,3.7) yaw=175 p=0 | mv=0.28 | find_stone_b:d18.2/f112 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [8/10]
246 | (-7.5,0.0,3.4) yaw=175 p=0 | mv=0.28 | find_stone_b:d18.4/f113 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [9/10]
247 | (-7.5,0.0,3.1) yaw=175 p=0 | mv=0.28 | find_stone_b:d18.5/f114 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [10/10]
248 | (-7.5,0.0,3.0) yaw=-95 p=0 | mv=0.15 | find_stone_b:d18.5/f24 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,90]} [1/1]
      PLAN: Look around to locate the oak room (wooden structure).
249 | (-7.4,0.0,2.9) yaw=-95 p=0 | mv=0.15 | find_stone_b:d18.4/f24 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/10]
      PLAN: Move forward toward the oak room to enter it and check for pink concrete blocks inside.
250 | (-7.2,0.0,2.8) yaw=-95 p=0 | mv=0.20 | find_stone_b:d18.3/f25 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/10]
251 | (-7.0,0.0,2.8) yaw=-95 p=0 | mv=0.24 | find_stone_b:d18.1/f25 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/10]
252 | (-6.7,0.0,2.8) yaw=-95 p=0 | mv=0.26 | find_stone_b:d17.9/f25 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [4/10]
253 | (-6.5,0.0,2.7) yaw=-95 p=0 | mv=0.27 | find_stone_b:d17.6/f26 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [5/10]
254 | (-6.2,0.0,2.7) yaw=-95 p=0 | mv=0.27 | find_stone_b:d17.4/f26 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [6/10]
255 | (-5.9,0.0,2.7) yaw=-95 p=0 | mv=0.28 | find_stone_b:d17.1/f27 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [7/10]
256 | (-5.6,0.0,2.6) yaw=-95 p=0 | mv=0.28 | find_stone_b:d16.9/f27 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [8/10]
257 | (-5.4,0.0,2.6) yaw=-95 p=0 | mv=0.28 | find_stone_b:d16.6/f28 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [9/10]
258 | (-5.1,0.0,2.6) yaw=-95 p=0 | mv=0.28 | find_stone_b:d16.4/f28 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [10/10]
259 | (-4.8,0.0,2.6) yaw=-95 p=0 | mv=0.28 | find_stone_b:d16.1/f29 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/5]
      PLAN: Move forward to enter the oak room and check for pink concrete blocks inside.
260 | (-4.5,0.0,2.5) yaw=-95 p=0 | mv=0.28 | find_stone_b:d15.9/f29 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/5]
261 | (-4.2,0.0,2.5) yaw=-95 p=0 | mv=0.28 | find_stone_b:d15.6/f29 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/5]
262 | (-4.0,0.0,2.5) yaw=-95 p=0 | mv=0.28 | find_stone_b:d15.4/f30 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [4/5]
263 | (-3.7,0.0,2.5) yaw=-95 p=0 | mv=0.28 | find_stone_b:d15.2/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [5/5]
264 | (-3.4,0.0,2.4) yaw=-95 p=0 | mv=0.28 | find_stone_b:d14.9/f31 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/5]
265 | (-3.1,0.0,2.4) yaw=-95 p=0 | mv=0.28 | find_stone_b:d14.7/f32 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/5]
266 | (-2.8,0.0,2.4) yaw=-95 p=0 | mv=0.28 | find_stone_b:d14.4/f32 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/5]
267 | (-2.6,0.0,2.4) yaw=-95 p=0 | mv=0.28 | find_stone_b:d14.2/f33 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [4/5]
268 | (-2.3,0.0,2.3) yaw=-95 p=0 | mv=0.28 | find_stone_b:d14.0/f33 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [5/5]
269 | (-2.0,0.0,2.3) yaw=-95 p=0 | mv=0.28 | find_stone_b:d13.7/f34 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/3]
270 | (-1.7,0.0,2.3) yaw=-95 p=0 | mv=0.28 | find_stone_b:d13.5/f35 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/3]
271 | (-1.4,0.0,2.3) yaw=-95 p=0 | mv=0.28 | find_stone_b:d13.3/f35 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/3]
272 | (-1.2,0.0,2.2) yaw=-95 p=0 | mv=0.28 | find_stone_b:d13.0/f36 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/3]
273 | (-0.9,0.0,2.2) yaw=-95 p=0 | mv=0.28 | find_stone_b:d12.8/f37 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/3]
274 | (-0.6,0.0,2.2) yaw=-95 p=0 | mv=0.28 | find_stone_b:d12.6/f38 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/3]
275 | (-0.3,0.0,2.2) yaw=-95 p=0 | mv=0.28 | find_stone_b:d12.4/f38 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/2]
276 | (-0.0,0.0,2.1) yaw=-95 p=0 | mv=0.28 | find_stone_b:d12.2/f39 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/2]
277 | (0.2,0.0,2.1) yaw=-95 p=0 | mv=0.28 | find_stone_b:d11.9/f40 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/2]
278 | (0.5,0.0,2.1) yaw=-95 p=0 | mv=0.28 | find_stone_b:d11.7/f41 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/2]
279 | (0.8,0.0,2.1) yaw=-95 p=0 | mv=0.28 | find_stone_b:d11.5/f42 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/2]
280 | (1.1,0.0,2.1) yaw=-95 p=0 | mv=0.28 | find_stone_b:d11.3/f43 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/2]
281 | (1.4,0.0,2.0) yaw=-95 p=0 | mv=0.28 | find_stone_b:d11.1/f44 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/2]
282 | (1.6,0.0,2.0) yaw=-95 p=0 | mv=0.28 | find_stone_b:d10.9/f45 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/2]
283 | (1.9,0.0,2.0) yaw=-95 p=0 | mv=0.28 | find_stone_b:d10.7/f46 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/2]
284 | (2.2,0.0,2.0) yaw=-95 p=0 | mv=0.28 | find_stone_b:d10.5/f47 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/2]
285 | (2.5,0.0,1.9) yaw=-95 p=0 | mv=0.28 | find_stone_b:d10.3/f48 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/2]
286 | (2.8,0.0,1.9) yaw=-95 p=0 | mv=0.28 | find_stone_b:d10.1/f49 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/2]
287 | (3.0,0.0,1.9) yaw=-95 p=0 | mv=0.28 | find_stone_b:d10.0/f51 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/2]
288 | (3.3,0.0,1.9) yaw=-95 p=0 | mv=0.28 | find_stone_b:d9.8/f52 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/2]
289 | (3.6,0.0,1.8) yaw=-95 p=0 | mv=0.28 | find_stone_b:d9.6/f53 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/2]
290 | (3.9,0.0,1.8) yaw=-95 p=0 | mv=0.28 | find_stone_b:d9.5/f55 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/2]
291 | (4.1,0.0,1.8) yaw=-95 p=0 | mv=0.28 | find_stone_b:d9.3/f56 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/2]
292 | (4.4,0.0,1.8) yaw=-95 p=0 | mv=0.28 | find_stone_b:d9.1/f57 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/2]
293 | (4.7,0.0,1.7) yaw=-95 p=0 | mv=0.28 | find_stone_b:d9.0/f59 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/2]
294 | (5.0,0.0,1.7) yaw=-95 p=0 | mv=0.28 | find_stone_b:d8.8/f60 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/2]
295 | (5.3,0.0,1.7) yaw=-95 p=0 | mv=0.28 | find_stone_b:d8.7/f62 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/2]
296 | (5.5,0.0,1.7) yaw=-95 p=0 | mv=0.28 | find_stone_b:d8.6/f64 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/2]
297 | (5.8,0.0,1.6) yaw=-95 p=0 | mv=0.28 | find_stone_b:d8.5/f65 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/2]
298 | (6.1,0.0,1.6) yaw=-95 p=0 | mv=0.28 | find_stone_b:d8.4/f67 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/2]
299 | (6.4,0.0,1.6) yaw=-95 p=0 | mv=0.28 | find_stone_b:d8.2/f69 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/2]
300 | (6.7,0.0,1.6) yaw=-95 p=0 | mv=0.28 | find_stone_b:d8.2/f71 mine_mossy_c:- mine_pink_co:- build_hidden:- | None [None/None]