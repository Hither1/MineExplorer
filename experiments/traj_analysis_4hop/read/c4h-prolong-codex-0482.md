# c4h-prolong-codex-0482  arm=prolong
TASK: Find the stone brick slabs on the ground near the stone structure. Go inside and mine the mossy cobblestone blocks. Then walk to the pink concrete wall and mine some pink concrete. Finally, go to the oak room and use the pink concrete to build a hidden room inside it.
MILESTONE RULES (spawn-relative coords; x+ = east, z+ = south; Minecraft yaw: 0=south(+z), 90=west(-x), 180/-180=north(-z), -90=east(+x)):
  - find_stone_brick_slab: position_near_with_facing {"target": [10, 0, 9], "max_distance": 8, "facing_tolerance": 60, "coordinate_frame": "spawn_relative"}
  - mine_mossy_cobblestone: inventory_has {"item": "mossy_cobblestone", "min_count": 1}
  - mine_pink_concrete: inventory_has {"item": "pink_concrete", "min_count": 1}
  - build_hidden_room: count_in_box_at_least {"kind": "block", "object": "pink_concrete", "min": [13, 0, -5], "max": [24, 5, 7], "min_count": 6, "coordinate_frame": "spawn_relative"}
spawn_abs=(-3009.5, 71.0, -5572.5)  milestones_done(frame)={'find_stone_brick_slab': 37}  esc_rejected_steps(n=0)=[]
PHASES (action-class runs; pos = spawn-relative x,z at start -> end):
  steps   1-  1 (  1) turn        (0.0,0.0)->(0.0,0.0) yaw -90->-90
  steps   2-  9 (  8) move        (0.1,0.0)->(1.9,0.0) yaw -90->-90
  steps  10- 10 (  1) turn        (2.1,0.0)->(2.1,0.0) yaw -135->-135
  steps  11- 16 (  6) move        (2.2,-0.1)->(3.2,-1.0) yaw -135->-135
  steps  17- 17 (  1) turn        (3.3,-1.1)->(3.3,-1.1) yaw -45->-45
  steps  18- 27 ( 10) move        (3.5,-1.0)->(5.2,0.6) yaw -45->-45
  steps  28- 29 (  2) turn        (5.3,0.7)->(5.3,0.7) yaw -45->-45
  steps  30- 41 ( 12) move        (5.5,0.8)->(7.1,2.4) yaw -45->-45
  steps  42- 44 (  3) mixed       (7.2,2.5)->(7.2,2.6) yaw -45->-45
  steps  45- 47 (  3) jump+move   (7.3,2.7)->(7.4,2.8) yaw -45->-45
  steps  48- 48 (  1) turn        (7.5,2.9)->(7.5,2.9) yaw -0->-0
  steps  49- 52 (  4) move        (7.5,2.9)->(7.7,3.2) yaw -0->-0
  steps  53- 54 (  2) turn        (7.7,3.3)->(7.8,3.4) yaw -0->-45
  steps  55- 58 (  4) jump+move   (7.8,3.5)->(8.1,3.9) yaw -45->-45
  steps  59- 59 (  1) turn        (8.1,4.0)->(8.1,4.0) yaw -45->-45
  steps  60- 63 (  4) attack      (8.2,4.1)->(8.4,4.3) yaw -45->-45
  steps  64- 64 (  1) turn        (8.4,4.3)->(8.4,4.3) yaw -45->-45
  steps  65- 67 (  3) move        (8.5,4.4)->(8.6,4.6) yaw -45->-45
  steps  68- 73 (  6) attack      (8.7,4.6)->(8.8,4.8) yaw -45->-45
  steps  74- 74 (  1) turn        (8.8,4.8)->(8.8,4.8) yaw -90->-90
  steps  75- 77 (  3) jump+move   (8.9,4.8)->(9.0,4.8) yaw -90->-90
  steps  78- 80 (  3) mixed       (9.1,4.8)->(9.3,4.8) yaw -45->-45
  steps  81- 85 (  5) attack      (9.4,4.9)->(9.6,4.9) yaw -45->-45
  steps  86- 86 (  1) turn        (9.7,4.9)->(9.7,4.9) yaw -0->-0
  steps  87- 89 (  3) jump+move   (9.7,5.1)->(9.8,5.2) yaw -0->-0
  steps  90- 95 (  6) attack      (9.8,5.3)->(9.9,5.6) yaw -0->-0
  steps  96- 96 (  1) turn        (9.9,5.7)->(9.9,5.7) yaw -0->-0
  steps  97-104 (  8) attack      (9.9,5.7)->(9.9,5.8) yaw -0->-0
  steps 105-105 (  1) turn        (9.9,5.8)->(9.9,5.8) yaw -30->-30
  steps 106-109 (  4) attack      (9.9,5.8)->(9.9,5.8) yaw -30->-30
  steps 110-110 (  1) turn        (9.9,5.8)->(9.9,5.8) yaw -0->-0
  steps 111-118 (  8) attack      (9.9,5.8)->(9.9,5.8) yaw -0->-0
  steps 119-119 (  1) turn        (9.9,5.8)->(9.9,5.8) yaw 20->20
  steps 120-123 (  4) attack      (9.9,5.8)->(9.9,5.8) yaw 20->20
  steps 124-124 (  1) turn        (9.9,5.8)->(9.9,5.8) yaw -0->-0
  steps 125-134 ( 10) attack      (9.9,5.8)->(9.9,5.8) yaw -0->-0
  steps 135-135 (  1) turn        (9.9,5.8)->(9.9,5.8) yaw -15->-15
  steps 136-140 (  5) attack      (9.9,5.8)->(9.9,5.8) yaw -15->-15
  steps 141-141 (  1) turn        (9.9,5.8)->(9.9,5.8) yaw -0->-0
  steps 142-153 ( 12) attack      (9.9,5.8)->(9.9,5.8) yaw -0->-0
  steps 154-154 (  1) turn        (9.9,5.8)->(9.9,5.8) yaw 10->10
  steps 155-180 ( 26) attack      (9.9,5.8)->(9.9,5.8) yaw 10->10
  steps 181-181 (  1) turn        (9.9,5.8)->(9.9,5.8) yaw -10->-10
  steps 182-189 (  8) attack      (9.9,5.8)->(9.9,5.8) yaw -10->-10
  steps 190-190 (  1) turn        (9.9,5.8)->(9.9,5.8) yaw -0->-0
  steps 191-210 ( 20) attack      (9.9,5.8)->(9.9,5.8) yaw -0->-0
  steps 211-211 (  1) turn        (9.9,5.8)->(9.9,5.8) yaw 10->10
  steps 212-239 ( 28) attack      (9.9,5.8)->(9.9,5.8) yaw 10->10
  steps 240-240 (  1) turn        (9.9,5.8)->(9.9,5.8) yaw -0->-0
  steps 241-250 ( 10) attack      (9.9,5.8)->(9.9,5.8) yaw -0->-0
  steps 251-255 (  5) move        (9.9,5.9)->(9.9,6.6) yaw -0->-0
  steps 256-265 ( 10) attack      (9.9,6.7)->(9.9,6.8) yaw -0->-0
  steps 266-266 (  1) turn        (9.9,6.8)->(9.9,6.8) yaw -15->-15
  steps 267-271 (  5) attack      (9.9,6.8)->(9.9,6.8) yaw -15->-15
  steps 272-272 (  1) turn        (9.9,6.8)->(9.9,6.8) yaw -0->-0
  steps 273-282 ( 10) attack      (9.9,6.8)->(9.9,6.8) yaw -0->-0
  steps 283-283 (  1) turn        (9.9,6.8)->(9.9,6.8) yaw 10->10
  steps 284-291 (  8) attack      (9.9,6.8)->(9.9,6.8) yaw 10->10
  steps 292-292 (  1) turn        (9.9,6.8)->(9.9,6.8) yaw -0->-0
  steps 293-299 (  7) attack      (9.9,6.8)->(9.9,6.8) yaw -0->-0
  steps 300-300 (  1) none        (9.9,6.8)->(9.9,6.8) yaw -0->-0

STEPS: step | rel_pos(x,y,z) yaw pitch | moved | per-milestone d=3D dist to target / f=facing error deg (* = rule satisfied this step; "-" = non-position rule) | action | T: thought (trunc) | M: memory (shown when changed, every ~25 steps) | H: hypothesis ops (new statements / status changes)
  1 | (0.0,0.0,0.0) yaw=-90 p=0 | mv=0.00 | find_stone_b:d13.5/f42 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,-90]} [1/1]
      PLAN: Turn west toward the stone structure and sprint toward it to find the stone brick slabs on the ground, then reassess from the new view.
  2 | (0.1,0.0,0.0) yaw=-90 p=0 | mv=0.13 | find_stone_b:d13.4/f42 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/8]
  3 | (0.3,0.0,0.0) yaw=-90 p=0 | mv=0.20 | find_stone_b:d13.2/f43 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/8]
  4 | (0.6,0.0,0.0) yaw=-90 p=0 | mv=0.23 | find_stone_b:d13.0/f44 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/8]
  5 | (0.8,0.0,0.0) yaw=-90 p=0 | mv=0.26 | find_stone_b:d12.9/f44 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [4/8]
  6 | (1.1,0.0,0.0) yaw=-90 p=0 | mv=0.27 | find_stone_b:d12.7/f45 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [5/8]
  7 | (1.4,0.0,0.0) yaw=-90 p=0 | mv=0.27 | find_stone_b:d12.5/f46 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [6/8]
  8 | (1.6,0.0,0.0) yaw=-90 p=0 | mv=0.28 | find_stone_b:d12.3/f47 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [7/8]
  9 | (1.9,0.0,0.0) yaw=-90 p=0 | mv=0.28 | find_stone_b:d12.1/f48 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [8/8]
 10 | (2.1,0.0,0.0) yaw=-135 p=0 | mv=0.15 | find_stone_b:d12.0/f94 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,-45]} [1/1]
 11 | (2.2,0.0,-0.1) yaw=-135 p=0 | mv=0.20 | find_stone_b:d12.0/f94 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/6]
 12 | (2.4,0.0,-0.2) yaw=-135 p=0 | mv=0.23 | find_stone_b:d11.9/f96 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/6]
 13 | (2.6,0.0,-0.4) yaw=-135 p=0 | mv=0.25 | find_stone_b:d12.0/f97 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/6]
 14 | (2.8,0.0,-0.6) yaw=-135 p=0 | mv=0.27 | find_stone_b:d12.0/f98 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [4/6]
 15 | (3.0,0.0,-0.8) yaw=-135 p=0 | mv=0.27 | find_stone_b:d12.0/f99 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [5/6]
 16 | (3.2,0.0,-1.0) yaw=-135 p=0 | mv=0.28 | find_stone_b:d12.1/f101 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [6/6]
 17 | (3.3,0.0,-1.1) yaw=-45 p=0 | mv=0.15 | find_stone_b:d12.1/f11 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,90]} [1/1]
      PLAN: Turn to face east (toward the stone structure seen in the first frame) and sprint toward it, then look down to spot the stone brick slabs on the ground.
 18 | (3.5,0.0,-1.0) yaw=-45 p=0 | mv=0.15 | find_stone_b:d12.0/f12 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [1/10]
 19 | (3.6,0.0,-0.9) yaw=-45 p=0 | mv=0.20 | find_stone_b:d11.8/f12 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [2/10]
 20 | (3.8,0.0,-0.8) yaw=-45 p=0 | mv=0.24 | find_stone_b:d11.6/f13 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [3/10]
 21 | (4.0,0.0,-0.6) yaw=-45 p=0 | mv=0.26 | find_stone_b:d11.3/f13 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [4/10]
 22 | (4.2,0.0,-0.4) yaw=-45 p=0 | mv=0.27 | find_stone_b:d11.1/f13 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [5/10]
 23 | (4.4,0.0,-0.2) yaw=-45 p=0 | mv=0.27 | find_stone_b:d10.8/f14 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [6/10]
 24 | (4.6,0.0,-0.0) yaw=-45 p=0 | mv=0.28 | find_stone_b:d10.5/f14 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [7/10]
 25 | (4.8,0.0,0.2) yaw=-45 p=0 | mv=0.28 | find_stone_b:d10.3/f14 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [8/10]
 26 | (5.0,0.0,0.4) yaw=-45 p=0 | mv=0.28 | find_stone_b:d10.0/f15 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [9/10]
 27 | (5.2,0.0,0.6) yaw=-45 p=0 | mv=0.28 | find_stone_b:d9.7/f15 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"sprint":1} [10/10]
 28 | (5.3,0.0,0.7) yaw=-45 p=20 | mv=0.15 | find_stone_b:d9.6/f16 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[20,0]} [1/1]
 29 | (5.3,0.0,0.7) yaw=-45 p=0 | mv=0.08 | find_stone_b:d9.5/f16 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[-20,0]} [1/1]
      PLAN: Level the camera and walk forward toward the stone slab platform at the base of the stone structure, then look down and begin mining.
 30 | (5.5,0.0,0.8) yaw=-45 p=0 | mv=0.14 | find_stone_b:d9.4/f16 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/12]
 31 | (5.6,0.0,0.9) yaw=-45 p=0 | mv=0.18 | find_stone_b:d9.2/f16 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/12]
 32 | (5.7,0.0,1.1) yaw=-45 p=0 | mv=0.19 | find_stone_b:d9.0/f17 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [3/12]
 33 | (5.9,0.0,1.2) yaw=-45 p=0 | mv=0.20 | find_stone_b:d8.8/f17 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [4/12]
 34 | (6.0,0.0,1.4) yaw=-45 p=0 | mv=0.21 | find_stone_b:d8.6/f17 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [5/12]
 35 | (6.2,0.0,1.5) yaw=-45 p=0 | mv=0.21 | find_stone_b:d8.4/f18 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [6/12]
 36 | (6.3,0.0,1.7) yaw=-45 p=0 | mv=0.21 | find_stone_b:d8.2/f18 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [7/12]
 37 | (6.5,0.0,1.8) yaw=-45 p=0 | mv=0.21 | find_stone_b:d8.0/f19* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [8/12]
 38 | (6.6,0.0,2.0) yaw=-45 p=0 | mv=0.22 | find_stone_b:d7.8/f19* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [9/12]
 39 | (6.8,0.0,2.1) yaw=-45 p=0 | mv=0.22 | find_stone_b:d7.6/f20* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [10/12]
 40 | (6.9,0.0,2.3) yaw=-45 p=0 | mv=0.22 | find_stone_b:d7.4/f20* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [11/12]
 41 | (7.1,0.0,2.4) yaw=-45 p=0 | mv=0.22 | find_stone_b:d7.2/f21* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [12/12]
 42 | (7.2,0.0,2.5) yaw=-45 p=15 | mv=0.12 | find_stone_b:d7.1/f21* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[15,0]} [1/1]
 43 | (7.2,0.0,2.6) yaw=-45 p=15 | mv=0.06 | find_stone_b:d7.0/f21* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/2]
 44 | (7.2,0.0,2.6) yaw=-45 p=15 | mv=0.04 | find_stone_b:d7.0/f22* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/2]
 45 | (7.3,0.4,2.7) yaw=-45 p=15 | mv=0.12 | find_stone_b:d6.9/f22* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"jump":1} [1/3]
      PLAN: Jump up onto the stone slab platform, turn right to face the mossy cobblestone on the wall, walk closer, then look down at it to prepare mining.
 46 | (7.4,0.8,2.7) yaw=-45 p=15 | mv=0.08 | find_stone_b:d6.8/f22* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"jump":1} [2/3]
 47 | (7.4,1.0,2.8) yaw=-45 p=15 | mv=0.10 | find_stone_b:d6.8/f22* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"jump":1} [3/3]
 48 | (7.5,1.2,2.9) yaw=-0 p=15 | mv=0.09 | find_stone_b:d6.7/f22* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,45]} [1/1]
 49 | (7.5,1.2,2.9) yaw=-0 p=15 | mv=0.09 | find_stone_b:d6.7/f22* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/4]
 50 | (7.6,1.3,3.0) yaw=-0 p=15 | mv=0.10 | find_stone_b:d6.6/f22* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/4]
 51 | (7.6,1.2,3.1) yaw=-0 p=15 | mv=0.11 | find_stone_b:d6.4/f22* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [3/4]
 52 | (7.7,1.0,3.2) yaw=-0 p=15 | mv=0.12 | find_stone_b:d6.3/f22* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [4/4]
 53 | (7.7,0.8,3.3) yaw=-0 p=35 | mv=0.11 | find_stone_b:d6.1/f22* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[20,0]} [1/1]
 54 | (7.8,0.5,3.4) yaw=-45 p=15 | mv=0.10 | find_stone_b:d6.0/f23* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[-20,-45]} [1/1]
      PLAN: Turn to face the mossy cobblestone wall, hop up onto the platform toward it, then attack to mine the mossy cobblestone blocks.
 55 | (7.8,0.1,3.5) yaw=-45 p=15 | mv=0.11 | find_stone_b:d5.9/f23* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"jump":1} [1/4]
 56 | (7.9,0.0,3.6) yaw=-45 p=15 | mv=0.12 | find_stone_b:d5.8/f23* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"jump":1} [2/4]
 57 | (8.0,0.4,3.8) yaw=-45 p=15 | mv=0.20 | find_stone_b:d5.6/f24* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"jump":1} [3/4]
 58 | (8.1,0.8,3.9) yaw=-45 p=15 | mv=0.13 | find_stone_b:d5.5/f24* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"jump":1} [4/4]
 59 | (8.1,1.0,4.0) yaw=-45 p=25 | mv=0.12 | find_stone_b:d5.4/f25* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[10,0]} [1/1]
 60 | (8.2,1.2,4.1) yaw=-45 p=25 | mv=0.11 | find_stone_b:d5.4/f25* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/4]
 61 | (8.3,1.2,4.2) yaw=-45 p=25 | mv=0.10 | find_stone_b:d5.3/f25* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/4]
 62 | (8.3,1.3,4.2) yaw=-45 p=25 | mv=0.09 | find_stone_b:d5.2/f26* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/4]
 63 | (8.4,1.2,4.3) yaw=-45 p=25 | mv=0.08 | find_stone_b:d5.1/f26* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/4]
 64 | (8.4,1.0,4.3) yaw=-45 p=15 | mv=0.07 | find_stone_b:d5.0/f26* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[-10,0]} [1/1]
      PLAN: Step closer to the mossy cobblestone wall and attack repeatedly to mine the blocks.
 65 | (8.5,0.8,4.4) yaw=-45 p=15 | mv=0.09 | find_stone_b:d4.9/f26* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/3]
 66 | (8.5,0.5,4.5) yaw=-45 p=15 | mv=0.10 | find_stone_b:d4.8/f27* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/3]
 67 | (8.6,0.1,4.6) yaw=-45 p=15 | mv=0.11 | find_stone_b:d4.6/f27* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [3/3]
 68 | (8.7,0.0,4.6) yaw=-45 p=15 | mv=0.10 | find_stone_b:d4.6/f28* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/6]
 69 | (8.7,0.0,4.7) yaw=-45 p=15 | mv=0.09 | find_stone_b:d4.5/f28* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/6]
 70 | (8.8,0.0,4.7) yaw=-45 p=15 | mv=0.05 | find_stone_b:d4.4/f29* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/6]
 71 | (8.8,0.0,4.8) yaw=-45 p=15 | mv=0.03 | find_stone_b:d4.4/f29* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/6]
 72 | (8.8,0.0,4.8) yaw=-45 p=15 | mv=0.01 | find_stone_b:d4.4/f29* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/6]
 73 | (8.8,0.0,4.8) yaw=-45 p=15 | mv=0.01 | find_stone_b:d4.4/f29* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [6/6]
 74 | (8.8,0.0,4.8) yaw=-90 p=15 | mv=0.00 | find_stone_b:d4.4/f74 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,-45]} [1/1]
      PLAN: Turn right to face the mossy cobblestone wall, jump up onto the platform toward it, then attack to mine the mossy cobblestone.
 75 | (8.9,0.4,4.8) yaw=-90 p=15 | mv=0.10 | find_stone_b:d4.4/f75 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"jump":1} [1/3]
 76 | (9.0,0.8,4.8) yaw=-90 p=15 | mv=0.07 | find_stone_b:d4.4/f76 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"jump":1} [2/3]
 77 | (9.0,1.0,4.8) yaw=-90 p=15 | mv=0.09 | find_stone_b:d4.4/f77 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"jump":1} [3/3]
 78 | (9.1,1.2,4.8) yaw=-45 p=15 | mv=0.08 | find_stone_b:d4.5/f33 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,45]} [1/1]
 79 | (9.2,1.2,4.8) yaw=-45 p=15 | mv=0.09 | find_stone_b:d4.5/f34 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/2]
 80 | (9.3,1.3,4.8) yaw=-45 p=15 | mv=0.10 | find_stone_b:d4.4/f35 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/2]
 81 | (9.4,1.2,4.9) yaw=-45 p=15 | mv=0.09 | find_stone_b:d4.4/f37 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/5]
 82 | (9.5,1.0,4.9) yaw=-45 p=15 | mv=0.08 | find_stone_b:d4.3/f38 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/5]
 83 | (9.5,0.8,4.9) yaw=-45 p=15 | mv=0.07 | find_stone_b:d4.2/f38 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/5]
 84 | (9.6,0.5,4.9) yaw=-45 p=15 | mv=0.07 | find_stone_b:d4.1/f39 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/5]
 85 | (9.6,0.1,4.9) yaw=-45 p=15 | mv=0.06 | find_stone_b:d4.1/f40 mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/5]
 86 | (9.7,0.0,4.9) yaw=-0 p=15 | mv=0.05 | find_stone_b:d4.1/f4* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,45]} [1/1]
      PLAN: Face the mossy cobblestone wall, jump up onto the platform against it, then attack repeatedly to mine the mossy cobblestone blocks.
 87 | (9.7,0.4,5.1) yaw=-0 p=15 | mv=0.12 | find_stone_b:d4.0/f4* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"jump":1} [1/3]
 88 | (9.8,0.8,5.1) yaw=-0 p=15 | mv=0.08 | find_stone_b:d3.9/f3* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"jump":1} [2/3]
 89 | (9.8,1.0,5.2) yaw=-0 p=15 | mv=0.10 | find_stone_b:d3.9/f3* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1,"jump":1} [3/3]
 90 | (9.8,1.2,5.3) yaw=-0 p=15 | mv=0.09 | find_stone_b:d3.9/f3* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/6]
 91 | (9.8,1.2,5.4) yaw=-0 p=15 | mv=0.08 | find_stone_b:d3.8/f3* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/6]
 92 | (9.9,1.3,5.5) yaw=-0 p=15 | mv=0.07 | find_stone_b:d3.8/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/6]
 93 | (9.9,1.2,5.5) yaw=-0 p=15 | mv=0.07 | find_stone_b:d3.7/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/6]
 94 | (9.9,1.0,5.6) yaw=-0 p=15 | mv=0.06 | find_stone_b:d3.6/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/6]
 95 | (9.9,0.8,5.6) yaw=-0 p=15 | mv=0.05 | find_stone_b:d3.5/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [6/6]
 96 | (9.9,0.5,5.7) yaw=-0 p=-0 | mv=0.05 | find_stone_b:d3.4/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[-15,0]} [1/1]
      PLAN: Aim at the mossy cobblestone and attack repeatedly to mine it, then adjust aim to cover more of the mossy area.
 97 | (9.9,0.5,5.7) yaw=-0 p=-0 | mv=0.05 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/8]
 98 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.02 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/8]
 99 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.01 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/8]
100 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.01 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/8]
101 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/8]
102 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [6/8]
103 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [7/8]
104 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [8/8]
105 | (9.9,0.5,5.8) yaw=-30 p=-0 | mv=0.00 | find_stone_b:d3.3/f29* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,-30]} [1/1]
106 | (9.9,0.5,5.8) yaw=-30 p=-0 | mv=0.00 | find_stone_b:d3.3/f29* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/4]
107 | (9.9,0.5,5.8) yaw=-30 p=-0 | mv=0.00 | find_stone_b:d3.3/f29* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/4]
108 | (9.9,0.5,5.8) yaw=-30 p=-0 | mv=0.00 | find_stone_b:d3.3/f29* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/4]
109 | (9.9,0.5,5.8) yaw=-30 p=-0 | mv=0.00 | find_stone_b:d3.3/f29* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/4]
110 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,30]} [1/1]
      PLAN: Turn right to face the mossy cobblestone wall directly and attack repeatedly to mine the mossy cobblestone blocks.
111 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/8]
112 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/8]
113 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/8]
114 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/8]
115 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/8]
116 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [6/8]
117 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [7/8]
118 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [8/8]
119 | (9.9,0.5,5.8) yaw=20 p=-0 | mv=0.00 | find_stone_b:d3.3/f21* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,20]} [1/1]
120 | (9.9,0.5,5.8) yaw=20 p=-0 | mv=0.00 | find_stone_b:d3.3/f21* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/4]
121 | (9.9,0.5,5.8) yaw=20 p=-0 | mv=0.00 | find_stone_b:d3.3/f21* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/4]
122 | (9.9,0.5,5.8) yaw=20 p=-0 | mv=0.00 | find_stone_b:d3.3/f21* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/4]
123 | (9.9,0.5,5.8) yaw=20 p=-0 | mv=0.00 | find_stone_b:d3.3/f21* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/4]
124 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,-20]} [1/1]
      PLAN: Turn left to face the mossy cobblestone and attack repeatedly to mine it, then adjust aim to cover more of the mossy area.
125 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/10]
126 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/10]
127 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/10]
128 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/10]
129 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/10]
130 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [6/10]
131 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [7/10]
132 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [8/10]
133 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [9/10]
134 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [10/10]
135 | (9.9,0.5,5.8) yaw=-15 p=-0 | mv=0.00 | find_stone_b:d3.3/f14* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,-15]} [1/1]
136 | (9.9,0.5,5.8) yaw=-15 p=-0 | mv=0.00 | find_stone_b:d3.3/f14* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/5]
137 | (9.9,0.5,5.8) yaw=-15 p=-0 | mv=0.00 | find_stone_b:d3.3/f14* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/5]
138 | (9.9,0.5,5.8) yaw=-15 p=-0 | mv=0.00 | find_stone_b:d3.3/f14* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/5]
139 | (9.9,0.5,5.8) yaw=-15 p=-0 | mv=0.00 | find_stone_b:d3.3/f14* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/5]
140 | (9.9,0.5,5.8) yaw=-15 p=-0 | mv=0.00 | find_stone_b:d3.3/f14* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/5]
141 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,15]} [1/1]
      PLAN: Turn right to face the mossy cobblestone directly and attack repeatedly to mine the mossy cobblestone blocks.
142 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/12]
143 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/12]
144 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/12]
145 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/12]
146 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/12]
147 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [6/12]
148 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [7/12]
149 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [8/12]
150 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [9/12]
151 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [10/12]
152 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [11/12]
153 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [12/12]
154 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,10]} [1/1]
155 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/6]
156 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/6]
157 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/6]
158 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/6]
159 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/6]
160 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [6/6]
161 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/20]
      PLAN: Attack the mossy cobblestone directly to mine it, then adjust aim to cover the remaining mossy blocks.
162 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/20]
163 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/20]
164 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/20]
165 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/20]
166 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [6/20]
167 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [7/20]
168 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [8/20]
169 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [9/20]
170 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [10/20]
171 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [11/20]
172 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [12/20]
173 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [13/20]
174 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [14/20]
175 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [15/20]
176 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [16/20]
177 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [17/20]
178 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [18/20]
179 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [19/20]
180 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [20/20]
181 | (9.9,0.5,5.8) yaw=-10 p=-0 | mv=0.00 | find_stone_b:d3.3/f9* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,-20]} [1/1]
182 | (9.9,0.5,5.8) yaw=-10 p=-0 | mv=0.00 | find_stone_b:d3.3/f9* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/8]
183 | (9.9,0.5,5.8) yaw=-10 p=-0 | mv=0.00 | find_stone_b:d3.3/f9* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/8]
184 | (9.9,0.5,5.8) yaw=-10 p=-0 | mv=0.00 | find_stone_b:d3.3/f9* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/8]
185 | (9.9,0.5,5.8) yaw=-10 p=-0 | mv=0.00 | find_stone_b:d3.3/f9* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/8]
186 | (9.9,0.5,5.8) yaw=-10 p=-0 | mv=0.00 | find_stone_b:d3.3/f9* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/8]
187 | (9.9,0.5,5.8) yaw=-10 p=-0 | mv=0.00 | find_stone_b:d3.3/f9* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [6/8]
188 | (9.9,0.5,5.8) yaw=-10 p=-0 | mv=0.00 | find_stone_b:d3.3/f9* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [7/8]
189 | (9.9,0.5,5.8) yaw=-10 p=-0 | mv=0.00 | find_stone_b:d3.3/f9* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [8/8]
190 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,10]} [1/1]
      PLAN: Turn slightly right to put the crosshair on the mossy cobblestone, then attack repeatedly to mine it.
191 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/20]
192 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/20]
193 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/20]
194 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/20]
195 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/20]
196 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [6/20]
197 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [7/20]
198 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [8/20]
199 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [9/20]
200 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [10/20]
201 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [11/20]
202 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [12/20]
203 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [13/20]
204 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [14/20]
205 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [15/20]
206 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [16/20]
207 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [17/20]
208 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [18/20]
209 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [19/20]
210 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [20/20]
211 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,10]} [1/1]
212 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/8]
213 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/8]
214 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/8]
215 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/8]
216 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/8]
217 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [6/8]
218 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [7/8]
219 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [8/8]
220 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/20]
      PLAN: Attack the mossy cobblestone directly until it breaks, then adjust aim left to mine the rest of the mossy area.
221 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/20]
222 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/20]
223 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/20]
224 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/20]
225 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [6/20]
226 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [7/20]
227 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [8/20]
228 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [9/20]
229 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [10/20]
230 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [11/20]
231 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [12/20]
232 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [13/20]
233 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [14/20]
234 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [15/20]
235 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [16/20]
236 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [17/20]
237 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [18/20]
238 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [19/20]
239 | (9.9,0.5,5.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d3.3/f11* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [20/20]
240 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,-10]} [1/1]
241 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/10]
242 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/10]
243 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/10]
244 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/10]
245 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/10]
246 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [6/10]
247 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [7/10]
248 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [8/10]
249 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [9/10]
250 | (9.9,0.5,5.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d3.3/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [10/10]
251 | (9.9,0.5,5.9) yaw=-0 p=-0 | mv=0.10 | find_stone_b:d3.2/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [1/5]
      PLAN: Walk forward to get within reach of the mossy cobblestone wall, then attack to mine it, and sweep left to cover more of the mossy area.
252 | (9.9,0.5,6.0) yaw=-0 p=-0 | mv=0.15 | find_stone_b:d3.0/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [2/5]
253 | (9.9,0.5,6.2) yaw=-0 p=-0 | mv=0.18 | find_stone_b:d2.8/f1* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [3/5]
254 | (9.9,0.5,6.4) yaw=-0 p=-0 | mv=0.20 | find_stone_b:d2.6/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [4/5]
255 | (9.9,0.5,6.6) yaw=-0 p=-0 | mv=0.21 | find_stone_b:d2.4/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"forward":1} [5/5]
256 | (9.9,0.5,6.7) yaw=-0 p=-0 | mv=0.11 | find_stone_b:d2.3/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/10]
257 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.06 | find_stone_b:d2.3/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/10]
258 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.03 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/10]
259 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.02 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/10]
260 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.01 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/10]
261 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.01 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [6/10]
262 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [7/10]
263 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [8/10]
264 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [9/10]
265 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [10/10]
266 | (9.9,0.5,6.8) yaw=-15 p=-0 | mv=0.00 | find_stone_b:d2.2/f13* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,-15]} [1/1]
267 | (9.9,0.5,6.8) yaw=-15 p=-0 | mv=0.00 | find_stone_b:d2.2/f13* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/5]
268 | (9.9,0.5,6.8) yaw=-15 p=-0 | mv=0.00 | find_stone_b:d2.2/f13* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/5]
269 | (9.9,0.5,6.8) yaw=-15 p=-0 | mv=0.00 | find_stone_b:d2.2/f13* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/5]
270 | (9.9,0.5,6.8) yaw=-15 p=-0 | mv=0.00 | find_stone_b:d2.2/f13* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/5]
271 | (9.9,0.5,6.8) yaw=-15 p=-0 | mv=0.00 | find_stone_b:d2.2/f13* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/5]
272 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,15]} [1/1]
      PLAN: Attack the mossy cobblestone directly to mine more blocks, then sweep right to cover the rest of the mossy area.
273 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/10]
274 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/10]
275 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/10]
276 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/10]
277 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/10]
278 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [6/10]
279 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [7/10]
280 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [8/10]
281 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [9/10]
282 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [10/10]
283 | (9.9,0.5,6.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d2.2/f12* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,10]} [1/1]
284 | (9.9,0.5,6.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d2.2/f12* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/8]
285 | (9.9,0.5,6.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d2.2/f12* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/8]
286 | (9.9,0.5,6.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d2.2/f12* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/8]
287 | (9.9,0.5,6.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d2.2/f12* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/8]
288 | (9.9,0.5,6.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d2.2/f12* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/8]
289 | (9.9,0.5,6.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d2.2/f12* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [6/8]
290 | (9.9,0.5,6.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d2.2/f12* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [7/8]
291 | (9.9,0.5,6.8) yaw=10 p=-0 | mv=0.00 | find_stone_b:d2.2/f12* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [8/8]
292 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"camera":[0,-10]} [1/1]
      PLAN: Sweep left to face the remaining mossy cobblestone and attack to mine it, continuing to clear the mossy blocks.
293 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [1/10]
294 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [2/10]
295 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [3/10]
296 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [4/10]
297 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [5/10]
298 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [6/10]
299 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | {"attack":1} [7/10]
300 | (9.9,0.5,6.8) yaw=-0 p=-0 | mv=0.00 | find_stone_b:d2.2/f2* mine_mossy_c:- mine_pink_co:- build_hidden:- | None [None/None]