# q35-prolong-codex-0603  arm=prolong
TASK: You are in a bedroom. Find the purple bed and mine the white carpet next to it. Then walk east through the doorways to find the red nether brick stairs in the middle room. Continue east to the far room and mine a quartz block.
MILESTONE RULES (spawn-relative coords; x+ = east, z+ = south; Minecraft yaw: 0=south(+z), 90=west(-x), 180/-180=north(-z), -90=east(+x)):
  - find_purple_bed: position_near_with_facing {"target": [0, 0, 6], "max_distance": 5, "facing_tolerance": 30, "coordinate_frame": "spawn_relative"}
  - mine_white_carpet: inventory_has {"item": "white_carpet", "min_count": 1}
  - find_red_nether_brick_stairs: position_near_with_facing {"target": [6, 0, 5], "max_distance": 5, "facing_tolerance": 45, "coordinate_frame": "spawn_relative"}
  - mine_quartz_block: inventory_has {"item": "quartz_block", "min_count": 1}
spawn_abs=(-3009.5, 71.0, -5567.5)  milestones_done(frame)={'mine_white_carpet': 42, 'mine_quartz_block': 253}  esc_rejected_steps(n=1)=[256]
PHASES (action-class runs; pos = spawn-relative x,z at start -> end):
  steps   1-  9 (  9) turn        (0.0,0.0)->(0.0,0.0) yaw -90->-110
  steps  10- 12 (  3) attack      (0.0,0.0)->(0.0,0.0) yaw -110->-110
  steps  13- 13 (  1) turn        (0.0,0.0)->(0.0,0.0) yaw -80->-80
  steps  14- 18 (  5) attack      (0.0,0.0)->(0.0,0.0) yaw -80->-80
  steps  19- 19 (  1) turn        (0.0,0.0)->(0.0,0.0) yaw -70->-70
  steps  20- 24 (  5) attack      (0.0,0.0)->(0.0,0.0) yaw -70->-70
  steps  25- 25 (  1) turn        (0.0,0.0)->(0.0,0.0) yaw -55->-55
  steps  26- 30 (  5) attack      (0.0,0.0)->(0.0,0.0) yaw -55->-55
  steps  31- 32 (  2) move        (0.1,0.1)->(0.2,0.1) yaw -55->-55
  steps  33- 37 (  5) attack      (0.3,0.2)->(0.3,0.2) yaw -55->-55
  steps  38- 38 (  1) turn        (0.3,0.2)->(0.3,0.2) yaw -65->-65
  steps  39- 43 (  5) attack      (0.3,0.2)->(0.3,0.2) yaw -65->-65
  steps  44- 44 (  1) turn        (0.3,0.2)->(0.3,0.2) yaw -55->-55
  steps  45- 49 (  5) attack      (0.3,0.2)->(0.3,0.2) yaw -55->-55
  steps  50- 51 (  2) turn        (0.3,0.2)->(0.3,0.2) yaw -55->-100
  steps  52- 66 ( 15) move        (0.5,0.2)->(3.8,-0.2) yaw -100->-100
  steps  67- 67 (  1) turn        (3.9,-0.2)->(3.9,-0.2) yaw -100->-100
  steps  68- 72 (  5) attack      (4.0,-0.2)->(4.0,-0.2) yaw -100->-100
  steps  73- 75 (  3) jump+move   (4.1,-0.2)->(4.3,-0.2) yaw -100->-100
  steps  76- 80 (  5) attack      (4.4,-0.3)->(4.6,-0.3) yaw -100->-100
  steps  81- 82 (  2) move        (4.7,-0.3)->(4.8,-0.3) yaw -100->-100
  steps  83- 87 (  5) attack      (4.9,-0.4)->(5.0,-0.4) yaw -100->-100
  steps  88- 88 (  1) turn        (5.0,-0.4)->(5.0,-0.4) yaw -90->-90
  steps  89- 93 (  5) attack      (5.0,-0.4)->(5.0,-0.4) yaw -90->-90
  steps  94- 95 (  2) move        (5.1,-0.4)->(5.3,-0.4) yaw -90->-90
  steps  96-100 (  5) attack      (5.4,-0.4)->(5.4,-0.4) yaw -90->-90
  steps 101-101 (  1) turn        (5.5,-0.4)->(5.5,-0.4) yaw -100->-100
  steps 102-106 (  5) attack      (5.5,-0.4)->(5.5,-0.4) yaw -100->-100
  steps 107-107 (  1) turn        (5.5,-0.4)->(5.5,-0.4) yaw -80->-80
  steps 108-117 ( 10) attack      (5.5,-0.4)->(5.5,-0.4) yaw -80->-80
  steps 118-120 (  3) move        (5.5,-0.4)->(5.9,-0.3) yaw -80->-80
  steps 121-130 ( 10) attack      (6.0,-0.3)->(6.1,-0.3) yaw -80->-80
  steps 131-131 (  1) turn        (6.1,-0.3)->(6.1,-0.3) yaw -75->-75
  steps 132-136 (  5) attack      (6.1,-0.3)->(6.1,-0.3) yaw -75->-75
  steps 137-137 (  1) turn        (6.1,-0.3)->(6.1,-0.3) yaw -65->-65
  steps 138-142 (  5) attack      (6.1,-0.3)->(6.1,-0.3) yaw -65->-65
  steps 143-143 (  1) turn        (6.1,-0.3)->(6.1,-0.3) yaw -85->-85
  steps 144-153 ( 10) attack      (6.1,-0.3)->(6.1,-0.3) yaw -85->-85
  steps 154-155 (  2) move        (6.2,-0.3)->(6.3,-0.2) yaw -85->-85
  steps 156-165 ( 10) attack      (6.4,-0.2)->(6.5,-0.2) yaw -85->-85
  steps 166-175 ( 10) attack+move (6.6,-0.2)->(8.3,-0.1) yaw -85->-85
  steps 176-235 ( 60) attack      (8.4,-0.1)->(8.9,-0.0) yaw -85->-85
  steps 236-245 ( 10) attack+move (9.0,-0.0)->(10.8,0.1) yaw -85->-85
  steps 246-255 ( 10) attack      (10.9,0.1)->(11.0,0.2) yaw -85->-85
  steps 256-256 (  1) ESC         (11.0,0.2)->(11.0,0.2) yaw -85->-85
  steps 257-259 (  3) turn        (11.0,0.2)->(11.0,0.2) yaw -115->125
  steps 260-299 ( 40) move        (11.1,0.2)->(15.2,2.2) yaw 125->125
  steps 300-300 (  1) none        (15.2,2.2)->(15.2,2.2) yaw -145->-145

STEPS: step | rel_pos(x,y,z) yaw pitch | moved | per-milestone d=3D dist to target / f=facing error deg (* = rule satisfied this step; "-" = non-position rule) | action | T: thought (trunc) | M: memory (shown when changed, every ~25 steps) | H: hypothesis ops (new statements / status changes)
  1 | (0.0,0.0,0.0) yaw=-90 p=0 | mv=0.00 | find_purple_:d6.0/f90 mine_white_c:- find_red_net:d7.8/f40 mine_quartz_:- | {"camera":[0,-90]} [1/1]
      PLAN: Looking around the bedroom to locate the purple bed and white carpet. Currently turning to scan the room.
  2 | (0.0,0.0,0.0) yaw=180 p=0 | mv=0.00 | find_purple_:d6.0/f180 mine_white_c:- find_red_net:d7.8/f130 mine_quartz_:- | {"camera":[0,-90]} [1/1]
  3 | (0.0,0.0,0.0) yaw=90 p=0 | mv=0.00 | find_purple_:d6.0/f90 mine_white_c:- find_red_net:d7.8/f140 mine_quartz_:- | {"camera":[0,-90]} [1/1]
      PLAN: Continuing to scan the room by turning left to find the purple bed and white carpet. Currently at yaw=-180, turning to yaw=-270.
  4 | (0.0,0.0,0.0) yaw=180 p=0 | mv=0.00 | find_purple_:d6.0/f180 mine_white_c:- find_red_net:d7.8/f130 mine_quartz_:- | {"camera":[0,90]} [1/1]
      PLAN: Turning right to complete the room scan and locate the purple bed and white carpet. Should now be at yaw=0 (facing original direction).
  5 | (0.0,0.0,0.0) yaw=180 p=90 | mv=0.00 | find_purple_:d6.0/f180 mine_white_c:- find_red_net:d7.8/f130 mine_quartz_:- | {"camera":[90,0]} [1/1]
      PLAN: Looking down (pitch=90) to see the floor and locate the white carpet and bed that were visible in the initial frame.
  6 | (0.0,0.0,0.0) yaw=180 p=60 | mv=0.00 | find_purple_:d6.0/f180 mine_white_c:- find_red_net:d7.8/f130 mine_quartz_:- | {"camera":[-30,0]} [1/1]
      PLAN: Looking up slightly (pitch=60) to see the room layout and locate the purple bed while keeping the white carpet in view.
  7 | (0.0,0.0,0.0) yaw=-135 p=60 | mv=0.00 | find_purple_:d6.0/f135 mine_white_c:- find_red_net:d7.8/f85 mine_quartz_:- | {"camera":[0,45]} [1/1]
      PLAN: Turning right to scan the room and find the purple bed. Continuing to explore the bedroom layout.
  8 | (0.0,0.0,0.0) yaw=-90 p=60 | mv=0.00 | find_purple_:d6.0/f90 mine_white_c:- find_red_net:d7.8/f40 mine_quartz_:- | {"camera":[0,45]} [1/1]
      PLAN: Continuing to turn right to scan more of the room and locate the purple bed.
  9 | (0.0,0.0,0.0) yaw=-110 p=60 | mv=0.00 | find_purple_:d6.0/f110 mine_white_c:- find_red_net:d7.8/f60 mine_quartz_:- | {"camera":[0,-20]} [1/1]
      PLAN: Positioning to mine the white carpet next to the purple bed. Attacking the carpet block to mine it.
 10 | (0.0,0.0,0.0) yaw=-110 p=60 | mv=0.00 | find_purple_:d6.0/f110 mine_white_c:- find_red_net:d7.8/f60 mine_quartz_:- | {"attack":1} [1/3]
 11 | (0.0,0.0,0.0) yaw=-110 p=60 | mv=0.00 | find_purple_:d6.0/f110 mine_white_c:- find_red_net:d7.8/f60 mine_quartz_:- | {"attack":1} [2/3]
 12 | (0.0,0.0,0.0) yaw=-110 p=60 | mv=0.00 | find_purple_:d6.0/f110 mine_white_c:- find_red_net:d7.8/f60 mine_quartz_:- | {"attack":1} [3/3]
 13 | (0.0,0.0,0.0) yaw=-80 p=60 | mv=0.00 | find_purple_:d6.0/f80 mine_white_c:- find_red_net:d7.8/f30 mine_quartz_:- | {"camera":[0,30]} [1/1]
      PLAN: Repositioning to better target the white carpet and attacking it more aggressively to mine it.
 14 | (0.0,0.0,0.0) yaw=-80 p=60 | mv=0.00 | find_purple_:d6.0/f80 mine_white_c:- find_red_net:d7.8/f30 mine_quartz_:- | {"attack":1} [1/5]
 15 | (0.0,0.0,0.0) yaw=-80 p=60 | mv=0.00 | find_purple_:d6.0/f80 mine_white_c:- find_red_net:d7.8/f30 mine_quartz_:- | {"attack":1} [2/5]
 16 | (0.0,0.0,0.0) yaw=-80 p=60 | mv=0.00 | find_purple_:d6.0/f80 mine_white_c:- find_red_net:d7.8/f30 mine_quartz_:- | {"attack":1} [3/5]
 17 | (0.0,0.0,0.0) yaw=-80 p=60 | mv=0.00 | find_purple_:d6.0/f80 mine_white_c:- find_red_net:d7.8/f30 mine_quartz_:- | {"attack":1} [4/5]
 18 | (0.0,0.0,0.0) yaw=-80 p=60 | mv=0.00 | find_purple_:d6.0/f80 mine_white_c:- find_red_net:d7.8/f30 mine_quartz_:- | {"attack":1} [5/5]
 19 | (0.0,0.0,0.0) yaw=-70 p=60 | mv=0.00 | find_purple_:d6.0/f70 mine_white_c:- find_red_net:d7.8/f20 mine_quartz_:- | {"camera":[0,10]} [1/1]
      PLAN: Adjusting aim slightly to target the white carpet directly and continuing to attack it to mine it.
 20 | (0.0,0.0,0.0) yaw=-70 p=60 | mv=0.00 | find_purple_:d6.0/f70 mine_white_c:- find_red_net:d7.8/f20 mine_quartz_:- | {"attack":1} [1/5]
 21 | (0.0,0.0,0.0) yaw=-70 p=60 | mv=0.00 | find_purple_:d6.0/f70 mine_white_c:- find_red_net:d7.8/f20 mine_quartz_:- | {"attack":1} [2/5]
 22 | (0.0,0.0,0.0) yaw=-70 p=60 | mv=0.00 | find_purple_:d6.0/f70 mine_white_c:- find_red_net:d7.8/f20 mine_quartz_:- | {"attack":1} [3/5]
 23 | (0.0,0.0,0.0) yaw=-70 p=60 | mv=0.00 | find_purple_:d6.0/f70 mine_white_c:- find_red_net:d7.8/f20 mine_quartz_:- | {"attack":1} [4/5]
 24 | (0.0,0.0,0.0) yaw=-70 p=60 | mv=0.00 | find_purple_:d6.0/f70 mine_white_c:- find_red_net:d7.8/f20 mine_quartz_:- | {"attack":1} [5/5]
 25 | (0.0,0.0,0.0) yaw=-55 p=60 | mv=0.00 | find_purple_:d6.0/f55 mine_white_c:- find_red_net:d7.8/f5 mine_quartz_:- | {"camera":[0,15]} [1/1]
      PLAN: Adjusting view to target the white carpet block more directly and attacking to mine it.
 26 | (0.0,0.0,0.0) yaw=-55 p=60 | mv=0.00 | find_purple_:d6.0/f55 mine_white_c:- find_red_net:d7.8/f5 mine_quartz_:- | {"attack":1} [1/5]
 27 | (0.0,0.0,0.0) yaw=-55 p=60 | mv=0.00 | find_purple_:d6.0/f55 mine_white_c:- find_red_net:d7.8/f5 mine_quartz_:- | {"attack":1} [2/5]
 28 | (0.0,0.0,0.0) yaw=-55 p=60 | mv=0.00 | find_purple_:d6.0/f55 mine_white_c:- find_red_net:d7.8/f5 mine_quartz_:- | {"attack":1} [3/5]
 29 | (0.0,0.0,0.0) yaw=-55 p=60 | mv=0.00 | find_purple_:d6.0/f55 mine_white_c:- find_red_net:d7.8/f5 mine_quartz_:- | {"attack":1} [4/5]
 30 | (0.0,0.0,0.0) yaw=-55 p=60 | mv=0.00 | find_purple_:d6.0/f55 mine_white_c:- find_red_net:d7.8/f5 mine_quartz_:- | {"attack":1} [5/5]
 31 | (0.1,0.0,0.1) yaw=-55 p=60 | mv=0.10 | find_purple_:d5.9/f56 mine_white_c:- find_red_net:d7.7/f5 mine_quartz_:- | {"forward":1} [1/2]
      PLAN: Moving forward to get closer to the white carpet and attacking it to mine it.
 32 | (0.2,0.0,0.1) yaw=-55 p=60 | mv=0.15 | find_purple_:d5.9/f57 mine_white_c:- find_red_net:d7.6/f5 mine_quartz_:- | {"forward":1} [2/2]
 33 | (0.3,0.0,0.2) yaw=-55 p=60 | mv=0.08 | find_purple_:d5.8/f58 mine_white_c:- find_red_net:d7.5/f5 mine_quartz_:- | {"attack":1} [1/5]
 34 | (0.3,0.6,0.2) yaw=-55 p=60 | mv=0.05 | find_purple_:d5.8/f58 mine_white_c:- find_red_net:d7.5/f5 mine_quartz_:- | {"attack":1} [2/5]
 35 | (0.3,0.6,0.2) yaw=-55 p=60 | mv=0.02 | find_purple_:d5.8/f58 mine_white_c:- find_red_net:d7.4/f5 mine_quartz_:- | {"attack":1} [3/5]
 36 | (0.3,0.6,0.2) yaw=-55 p=60 | mv=0.01 | find_purple_:d5.8/f58 mine_white_c:- find_red_net:d7.4/f5 mine_quartz_:- | {"attack":1} [4/5]
 37 | (0.3,0.6,0.2) yaw=-55 p=60 | mv=0.01 | find_purple_:d5.8/f58 mine_white_c:- find_red_net:d7.4/f5 mine_quartz_:- | {"attack":1} [5/5]
 38 | (0.3,0.6,0.2) yaw=-65 p=60 | mv=0.00 | find_purple_:d5.8/f68 mine_white_c:- find_red_net:d7.4/f15 mine_quartz_:- | {"camera":[0,-10]} [1/1]
      PLAN: Adjusting view slightly to target the white carpet block and attacking it to mine it.
 39 | (0.3,0.6,0.2) yaw=-65 p=60 | mv=0.00 | find_purple_:d5.8/f68 mine_white_c:- find_red_net:d7.4/f15 mine_quartz_:- | {"attack":1} [1/5]
 40 | (0.3,0.6,0.2) yaw=-65 p=60 | mv=0.00 | find_purple_:d5.8/f68 mine_white_c:- find_red_net:d7.4/f15 mine_quartz_:- | {"attack":1} [2/5]
 41 | (0.3,0.6,0.2) yaw=-65 p=60 | mv=0.00 | find_purple_:d5.8/f68 mine_white_c:- find_red_net:d7.4/f15 mine_quartz_:- | {"attack":1} [3/5]
 42 | (0.3,0.6,0.2) yaw=-65 p=60 | mv=0.00 | find_purple_:d5.8/f68 mine_white_c:* find_red_net:d7.4/f15 mine_quartz_:- | {"attack":1} [4/5]
 43 | (0.3,0.6,0.2) yaw=-65 p=60 | mv=0.00 | find_purple_:d5.8/f68 mine_white_c:* find_red_net:d7.4/f15 mine_quartz_:- | {"attack":1} [5/5]
 44 | (0.3,0.6,0.2) yaw=-55 p=60 | mv=0.00 | find_purple_:d5.8/f58 mine_white_c:* find_red_net:d7.4/f5 mine_quartz_:- | {"camera":[0,10]} [1/1]
      PLAN: Adjusting view to target the white carpet block more directly and attacking to mine it.
 45 | (0.3,0.6,0.2) yaw=-55 p=60 | mv=0.00 | find_purple_:d5.8/f58 mine_white_c:* find_red_net:d7.4/f5 mine_quartz_:- | {"attack":1} [1/5]
 46 | (0.3,0.6,0.2) yaw=-55 p=60 | mv=0.00 | find_purple_:d5.8/f58 mine_white_c:* find_red_net:d7.4/f5 mine_quartz_:- | {"attack":1} [2/5]
 47 | (0.3,0.6,0.2) yaw=-55 p=60 | mv=0.00 | find_purple_:d5.8/f58 mine_white_c:* find_red_net:d7.4/f5 mine_quartz_:- | {"attack":1} [3/5]
 48 | (0.3,0.6,0.2) yaw=-55 p=60 | mv=0.00 | find_purple_:d5.8/f58 mine_white_c:* find_red_net:d7.4/f5 mine_quartz_:- | {"attack":1} [4/5]
 49 | (0.3,0.6,0.2) yaw=-55 p=60 | mv=0.00 | find_purple_:d5.8/f58 mine_white_c:* find_red_net:d7.4/f5 mine_quartz_:- | {"attack":1} [5/5]
 50 | (0.3,0.6,0.2) yaw=-55 p=30 | mv=0.00 | find_purple_:d5.8/f58 mine_white_c:* find_red_net:d7.4/f5 mine_quartz_:- | {"camera":[-30,0]} [1/1]
      PLAN: Looking up and turning to find the doorway to exit the bedroom and walk east toward the middle room with red nether brick stairs.
 51 | (0.3,0.6,0.2) yaw=-100 p=30 | mv=0.00 | find_purple_:d5.8/f103 mine_white_c:* find_red_net:d7.4/f50 mine_quartz_:- | {"camera":[0,-45]} [1/1]
 52 | (0.5,0.6,0.2) yaw=-100 p=30 | mv=0.13 | find_purple_:d5.8/f105 mine_white_c:* find_red_net:d7.3/f51 mine_quartz_:- | {"forward":1,"sprint":1} [1/5]
      PLAN: Moving forward through the middle room with the red nether brick stairs, continuing east toward the far room to find the quartz block.
 53 | (0.7,0.6,0.2) yaw=-100 p=30 | mv=0.20 | find_purple_:d5.9/f107 mine_white_c:* find_red_net:d7.2/f52 mine_quartz_:- | {"forward":1,"sprint":1} [2/5]
 54 | (0.9,0.5,0.1) yaw=-100 p=30 | mv=0.23 | find_purple_:d5.9/f109 mine_white_c:* find_red_net:d7.1/f54 mine_quartz_:- | {"forward":1,"sprint":1} [3/5]
 55 | (1.1,0.3,0.1) yaw=-100 p=30 | mv=0.15 | find_purple_:d6.0/f110 mine_white_c:* find_red_net:d7.0/f55 mine_quartz_:- | {"forward":1,"sprint":1} [4/5]
 56 | (1.2,0.1,0.1) yaw=-100 p=30 | mv=0.17 | find_purple_:d6.0/f112 mine_white_c:* find_red_net:d6.9/f56 mine_quartz_:- | {"forward":1,"sprint":1} [5/5]
 57 | (1.4,0.0,0.1) yaw=-100 p=30 | mv=0.18 | find_purple_:d6.1/f113 mine_white_c:* find_red_net:d6.8/f57 mine_quartz_:- | {"forward":1,"sprint":1} [1/10]
      PLAN: Continuing to move east through the middle room, past the red nether brick stairs, toward the far room to find the quartz block.
 58 | (1.7,0.0,0.0) yaw=-100 p=30 | mv=0.29 | find_purple_:d6.2/f116 mine_white_c:* find_red_net:d6.6/f59 mine_quartz_:- | {"forward":1,"sprint":1} [2/10]
 59 | (2.0,0.0,-0.0) yaw=-100 p=30 | mv=0.28 | find_purple_:d6.3/f118 mine_white_c:* find_red_net:d6.5/f61 mine_quartz_:- | {"forward":1,"sprint":1} [3/10]
 60 | (2.2,0.0,-0.1) yaw=-100 p=30 | mv=0.28 | find_purple_:d6.5/f120 mine_white_c:* find_red_net:d6.3/f63 mine_quartz_:- | {"forward":1,"sprint":1} [4/10]
 61 | (2.5,0.0,-0.1) yaw=-100 p=30 | mv=0.28 | find_purple_:d6.6/f122 mine_white_c:* find_red_net:d6.2/f66 mine_quartz_:- | {"forward":1,"sprint":1} [5/10]
 62 | (2.8,0.0,-0.2) yaw=-100 p=30 | mv=0.28 | find_purple_:d6.8/f124 mine_white_c:* find_red_net:d6.1/f68 mine_quartz_:- | {"forward":1,"sprint":1} [6/10]
 63 | (3.1,0.0,-0.2) yaw=-100 p=30 | mv=0.28 | find_purple_:d6.9/f126 mine_white_c:* find_red_net:d6.0/f71 mine_quartz_:- | {"forward":1,"sprint":1} [7/10]
 64 | (3.3,0.0,-0.2) yaw=-100 p=30 | mv=0.25 | find_purple_:d7.0/f128 mine_white_c:* find_red_net:d5.9/f73 mine_quartz_:- | {"forward":1,"sprint":1} [8/10]
 65 | (3.5,0.0,-0.2) yaw=-100 p=30 | mv=0.23 | find_purple_:d7.1/f130 mine_white_c:* find_red_net:d5.8/f75 mine_quartz_:- | {"forward":1,"sprint":1} [9/10]
 66 | (3.8,0.0,-0.2) yaw=-100 p=30 | mv=0.22 | find_purple_:d7.3/f131 mine_white_c:* find_red_net:d5.7/f77 mine_quartz_:- | {"forward":1,"sprint":1} [10/10]
 67 | (3.9,0.0,-0.2) yaw=-100 p=20 | mv=0.12 | find_purple_:d7.3/f132 mine_white_c:* find_red_net:d5.6/f78 mine_quartz_:- | {"camera":[-10,0]} [1/1]
      PLAN: Looking slightly up at the white block on top of the red nether brick stairs (likely the quartz block) and attacking it to mine it.
 68 | (4.0,0.0,-0.2) yaw=-100 p=20 | mv=0.07 | find_purple_:d7.4/f133 mine_white_c:* find_red_net:d5.6/f78 mine_quartz_:- | {"attack":1} [1/5]
 69 | (4.0,0.0,-0.2) yaw=-100 p=20 | mv=0.04 | find_purple_:d7.4/f133 mine_white_c:* find_red_net:d5.6/f79 mine_quartz_:- | {"attack":1} [2/5]
 70 | (4.0,0.0,-0.2) yaw=-100 p=20 | mv=0.02 | find_purple_:d7.4/f133 mine_white_c:* find_red_net:d5.6/f79 mine_quartz_:- | {"attack":1} [3/5]
 71 | (4.0,0.0,-0.2) yaw=-100 p=20 | mv=0.01 | find_purple_:d7.4/f133 mine_white_c:* find_red_net:d5.6/f79 mine_quartz_:- | {"attack":1} [4/5]
 72 | (4.0,0.0,-0.2) yaw=-100 p=20 | mv=0.01 | find_purple_:d7.4/f133 mine_white_c:* find_red_net:d5.6/f79 mine_quartz_:- | {"attack":1} [5/5]
 73 | (4.1,0.4,-0.2) yaw=-100 p=20 | mv=0.10 | find_purple_:d7.5/f134 mine_white_c:* find_red_net:d5.6/f80 mine_quartz_:- | {"forward":1,"jump":1} [1/3]
      PLAN: Moving forward and jumping to reach the quartz block on top of the stairs, then attacking it to mine it.
 74 | (4.2,0.8,-0.2) yaw=-100 p=20 | mv=0.07 | find_purple_:d7.5/f134 mine_white_c:* find_red_net:d5.6/f81 mine_quartz_:- | {"forward":1,"jump":1} [2/3]
 75 | (4.3,1.0,-0.2) yaw=-100 p=20 | mv=0.09 | find_purple_:d7.6/f134 mine_white_c:* find_red_net:d5.6/f82 mine_quartz_:- | {"forward":1,"jump":1} [3/3]
 76 | (4.4,1.2,-0.3) yaw=-100 p=20 | mv=0.08 | find_purple_:d7.7/f135 mine_white_c:* find_red_net:d5.6/f83 mine_quartz_:- | {"attack":1} [1/5]
 77 | (4.4,1.2,-0.3) yaw=-100 p=20 | mv=0.07 | find_purple_:d7.8/f135 mine_white_c:* find_red_net:d5.6/f83 mine_quartz_:- | {"attack":1} [2/5]
 78 | (4.5,1.1,-0.3) yaw=-100 p=20 | mv=0.07 | find_purple_:d7.8/f136 mine_white_c:* find_red_net:d5.6/f84 mine_quartz_:- | {"attack":1} [3/5]
 79 | (4.6,1.0,-0.3) yaw=-100 p=20 | mv=0.06 | find_purple_:d7.8/f136 mine_white_c:* find_red_net:d5.6/f85 mine_quartz_:- | {"attack":1} [4/5]
 80 | (4.6,0.7,-0.3) yaw=-100 p=20 | mv=0.05 | find_purple_:d7.8/f136 mine_white_c:* find_red_net:d5.5/f85 mine_quartz_:- | {"attack":1} [5/5]
 81 | (4.7,0.5,-0.3) yaw=-100 p=20 | mv=0.07 | find_purple_:d7.9/f137 mine_white_c:* find_red_net:d5.5/f86 mine_quartz_:- | {"forward":1} [1/2]
      PLAN: Moving forward to get closer to the quartz block and attacking it to mine it.
 82 | (4.8,1.0,-0.3) yaw=-100 p=20 | mv=0.16 | find_purple_:d8.0/f137 mine_white_c:* find_red_net:d5.6/f88 mine_quartz_:- | {"forward":1} [2/2]
 83 | (4.9,1.0,-0.4) yaw=-100 p=20 | mv=0.09 | find_purple_:d8.1/f138 mine_white_c:* find_red_net:d5.6/f89 mine_quartz_:- | {"attack":1} [1/5]
 84 | (5.0,1.0,-0.4) yaw=-100 p=20 | mv=0.05 | find_purple_:d8.1/f138 mine_white_c:* find_red_net:d5.6/f89 mine_quartz_:- | {"attack":1} [2/5]
 85 | (5.0,1.0,-0.4) yaw=-100 p=20 | mv=0.03 | find_purple_:d8.2/f138 mine_white_c:* find_red_net:d5.6/f89 mine_quartz_:- | {"attack":1} [3/5]
 86 | (5.0,1.0,-0.4) yaw=-100 p=20 | mv=0.01 | find_purple_:d8.2/f138 mine_white_c:* find_red_net:d5.5/f90 mine_quartz_:- | {"attack":1} [4/5]
 87 | (5.0,1.0,-0.4) yaw=-100 p=20 | mv=0.01 | find_purple_:d8.2/f138 mine_white_c:* find_red_net:d5.5/f90 mine_quartz_:- | {"attack":1} [5/5]
 88 | (5.0,1.0,-0.4) yaw=-90 p=20 | mv=0.00 | find_purple_:d8.2/f128 mine_white_c:* find_red_net:d5.5/f80 mine_quartz_:- | {"camera":[0,10]} [1/1]
      PLAN: Adjusting view to target the quartz block directly and attacking it to mine it.
 89 | (5.0,1.0,-0.4) yaw=-90 p=20 | mv=0.00 | find_purple_:d8.2/f128 mine_white_c:* find_red_net:d5.5/f80 mine_quartz_:- | {"attack":1} [1/5]
 90 | (5.0,1.0,-0.4) yaw=-90 p=20 | mv=0.00 | find_purple_:d8.2/f128 mine_white_c:* find_red_net:d5.5/f80 mine_quartz_:- | {"attack":1} [2/5]
 91 | (5.0,1.0,-0.4) yaw=-90 p=20 | mv=0.00 | find_purple_:d8.2/f128 mine_white_c:* find_red_net:d5.5/f80 mine_quartz_:- | {"attack":1} [3/5]
 92 | (5.0,1.0,-0.4) yaw=-90 p=20 | mv=0.00 | find_purple_:d8.2/f128 mine_white_c:* find_red_net:d5.5/f80 mine_quartz_:- | {"attack":1} [4/5]
 93 | (5.0,1.0,-0.4) yaw=-90 p=20 | mv=0.00 | find_purple_:d8.2/f128 mine_white_c:* find_red_net:d5.5/f80 mine_quartz_:- | {"attack":1} [5/5]
 94 | (5.1,1.0,-0.4) yaw=-90 p=20 | mv=0.10 | find_purple_:d8.2/f129 mine_white_c:* find_red_net:d5.5/f81 mine_quartz_:- | {"forward":1} [1/2]
      PLAN: Moving forward to get closer to the quartz block and attacking it to mine it.
 95 | (5.3,1.0,-0.4) yaw=-90 p=20 | mv=0.15 | find_purple_:d8.3/f130 mine_white_c:* find_red_net:d5.5/f82 mine_quartz_:- | {"forward":1} [2/2]
 96 | (5.4,1.0,-0.4) yaw=-90 p=20 | mv=0.08 | find_purple_:d8.4/f130 mine_white_c:* find_red_net:d5.5/f83 mine_quartz_:- | {"attack":1} [1/5]
 97 | (5.4,1.0,-0.4) yaw=-90 p=20 | mv=0.05 | find_purple_:d8.4/f130 mine_white_c:* find_red_net:d5.5/f84 mine_quartz_:- | {"attack":1} [2/5]
 98 | (5.4,1.0,-0.4) yaw=-90 p=20 | mv=0.02 | find_purple_:d8.4/f130 mine_white_c:* find_red_net:d5.5/f84 mine_quartz_:- | {"attack":1} [3/5]
 99 | (5.4,1.0,-0.4) yaw=-90 p=20 | mv=0.01 | find_purple_:d8.4/f131 mine_white_c:* find_red_net:d5.5/f84 mine_quartz_:- | {"attack":1} [4/5]
100 | (5.4,1.0,-0.4) yaw=-90 p=20 | mv=0.01 | find_purple_:d8.4/f131 mine_white_c:* find_red_net:d5.5/f84 mine_quartz_:- | {"attack":1} [5/5]
101 | (5.5,1.0,-0.4) yaw=-100 p=20 | mv=0.00 | find_purple_:d8.4/f141 mine_white_c:* find_red_net:d5.5/f94 mine_quartz_:- | {"camera":[0,-10]} [1/1]
      PLAN: Adjusting view to target the quartz block directly and attacking it to mine it.
102 | (5.5,1.0,-0.4) yaw=-100 p=20 | mv=0.00 | find_purple_:d8.4/f141 mine_white_c:* find_red_net:d5.5/f94 mine_quartz_:- | {"attack":1} [1/5]
103 | (5.5,1.0,-0.4) yaw=-100 p=20 | mv=0.00 | find_purple_:d8.4/f141 mine_white_c:* find_red_net:d5.5/f94 mine_quartz_:- | {"attack":1} [2/5]
104 | (5.5,1.0,-0.4) yaw=-100 p=20 | mv=0.00 | find_purple_:d8.4/f141 mine_white_c:* find_red_net:d5.5/f94 mine_quartz_:- | {"attack":1} [3/5]
105 | (5.5,1.0,-0.4) yaw=-100 p=20 | mv=0.00 | find_purple_:d8.4/f141 mine_white_c:* find_red_net:d5.5/f94 mine_quartz_:- | {"attack":1} [4/5]
106 | (5.5,1.0,-0.4) yaw=-100 p=20 | mv=0.00 | find_purple_:d8.4/f141 mine_white_c:* find_red_net:d5.5/f94 mine_quartz_:- | {"attack":1} [5/5]
107 | (5.5,1.0,-0.4) yaw=-80 p=20 | mv=0.00 | find_purple_:d8.4/f121 mine_white_c:* find_red_net:d5.5/f74 mine_quartz_:- | {"camera":[0,20]} [1/1]
      PLAN: Turning right to target the quartz block and attacking it to mine it.
108 | (5.5,1.0,-0.4) yaw=-80 p=20 | mv=0.00 | find_purple_:d8.4/f121 mine_white_c:* find_red_net:d5.5/f74 mine_quartz_:- | {"attack":1} [1/5]
109 | (5.5,1.0,-0.4) yaw=-80 p=20 | mv=0.00 | find_purple_:d8.4/f121 mine_white_c:* find_red_net:d5.5/f74 mine_quartz_:- | {"attack":1} [2/5]
110 | (5.5,1.0,-0.4) yaw=-80 p=20 | mv=0.00 | find_purple_:d8.4/f121 mine_white_c:* find_red_net:d5.5/f74 mine_quartz_:- | {"attack":1} [3/5]
111 | (5.5,1.0,-0.4) yaw=-80 p=20 | mv=0.00 | find_purple_:d8.4/f121 mine_white_c:* find_red_net:d5.5/f74 mine_quartz_:- | {"attack":1} [4/5]
112 | (5.5,1.0,-0.4) yaw=-80 p=20 | mv=0.00 | find_purple_:d8.4/f121 mine_white_c:* find_red_net:d5.5/f74 mine_quartz_:- | {"attack":1} [5/5]
113 | (5.5,1.0,-0.4) yaw=-80 p=20 | mv=0.00 | find_purple_:d8.4/f121 mine_white_c:* find_red_net:d5.5/f74 mine_quartz_:- | {"attack":1} [1/5]
      PLAN: Continuing to attack the quartz block to mine it.
114 | (5.5,1.0,-0.4) yaw=-80 p=20 | mv=0.00 | find_purple_:d8.4/f121 mine_white_c:* find_red_net:d5.5/f74 mine_quartz_:- | {"attack":1} [2/5]
115 | (5.5,1.0,-0.4) yaw=-80 p=20 | mv=0.00 | find_purple_:d8.4/f121 mine_white_c:* find_red_net:d5.5/f74 mine_quartz_:- | {"attack":1} [3/5]
116 | (5.5,1.0,-0.4) yaw=-80 p=20 | mv=0.00 | find_purple_:d8.4/f121 mine_white_c:* find_red_net:d5.5/f74 mine_quartz_:- | {"attack":1} [4/5]
117 | (5.5,1.0,-0.4) yaw=-80 p=20 | mv=0.00 | find_purple_:d8.4/f121 mine_white_c:* find_red_net:d5.5/f74 mine_quartz_:- | {"attack":1} [5/5]
118 | (5.5,1.0,-0.4) yaw=-80 p=20 | mv=0.10 | find_purple_:d8.5/f121 mine_white_c:* find_red_net:d5.5/f75 mine_quartz_:- | {"forward":1} [1/3]
      PLAN: Moving forward to get closer to the quartz block and attacking it to mine it.
119 | (5.7,1.0,-0.3) yaw=-80 p=20 | mv=0.15 | find_purple_:d8.6/f122 mine_white_c:* find_red_net:d5.4/f77 mine_quartz_:- | {"forward":1} [2/3]
120 | (5.9,1.0,-0.3) yaw=-80 p=20 | mv=0.18 | find_purple_:d8.7/f123 mine_white_c:* find_red_net:d5.4/f79 mine_quartz_:- | {"forward":1} [3/3]
121 | (6.0,1.0,-0.3) yaw=-80 p=20 | mv=0.10 | find_purple_:d8.7/f124 mine_white_c:* find_red_net:d5.4/f80 mine_quartz_:- | {"attack":1} [1/5]
122 | (6.0,1.0,-0.3) yaw=-80 p=20 | mv=0.05 | find_purple_:d8.8/f124 mine_white_c:* find_red_net:d5.4/f80 mine_quartz_:- | {"attack":1} [2/5]
123 | (6.1,1.0,-0.3) yaw=-80 p=20 | mv=0.03 | find_purple_:d8.8/f124 mine_white_c:* find_red_net:d5.4/f81 mine_quartz_:- | {"attack":1} [3/5]
124 | (6.1,1.0,-0.3) yaw=-80 p=20 | mv=0.02 | find_purple_:d8.8/f124 mine_white_c:* find_red_net:d5.4/f81 mine_quartz_:- | {"attack":1} [4/5]
125 | (6.1,1.0,-0.3) yaw=-80 p=20 | mv=0.01 | find_purple_:d8.8/f124 mine_white_c:* find_red_net:d5.4/f81 mine_quartz_:- | {"attack":1} [5/5]
126 | (6.1,1.0,-0.3) yaw=-80 p=20 | mv=0.00 | find_purple_:d8.8/f124 mine_white_c:* find_red_net:d5.4/f81 mine_quartz_:- | {"attack":1} [1/5]
      PLAN: Attacking the quartz block to mine it.
127 | (6.1,1.0,-0.3) yaw=-80 p=20 | mv=0.00 | find_purple_:d8.8/f124 mine_white_c:* find_red_net:d5.4/f81 mine_quartz_:- | {"attack":1} [2/5]
128 | (6.1,1.0,-0.3) yaw=-80 p=20 | mv=0.00 | find_purple_:d8.8/f124 mine_white_c:* find_red_net:d5.4/f81 mine_quartz_:- | {"attack":1} [3/5]
129 | (6.1,1.0,-0.3) yaw=-80 p=20 | mv=0.00 | find_purple_:d8.8/f124 mine_white_c:* find_red_net:d5.4/f81 mine_quartz_:- | {"attack":1} [4/5]
130 | (6.1,1.0,-0.3) yaw=-80 p=20 | mv=0.00 | find_purple_:d8.8/f124 mine_white_c:* find_red_net:d5.4/f81 mine_quartz_:- | {"attack":1} [5/5]
131 | (6.1,1.0,-0.3) yaw=-75 p=20 | mv=0.00 | find_purple_:d8.8/f119 mine_white_c:* find_red_net:d5.4/f76 mine_quartz_:- | {"camera":[0,5]} [1/1]
      PLAN: Adjusting view slightly to target the quartz block and attacking it to mine it.
132 | (6.1,1.0,-0.3) yaw=-75 p=20 | mv=0.00 | find_purple_:d8.8/f119 mine_white_c:* find_red_net:d5.4/f76 mine_quartz_:- | {"attack":1} [1/5]
133 | (6.1,1.0,-0.3) yaw=-75 p=20 | mv=0.00 | find_purple_:d8.8/f119 mine_white_c:* find_red_net:d5.4/f76 mine_quartz_:- | {"attack":1} [2/5]
134 | (6.1,1.0,-0.3) yaw=-75 p=20 | mv=0.00 | find_purple_:d8.8/f119 mine_white_c:* find_red_net:d5.4/f76 mine_quartz_:- | {"attack":1} [3/5]
135 | (6.1,1.0,-0.3) yaw=-75 p=20 | mv=0.00 | find_purple_:d8.8/f119 mine_white_c:* find_red_net:d5.4/f76 mine_quartz_:- | {"attack":1} [4/5]
136 | (6.1,1.0,-0.3) yaw=-75 p=20 | mv=0.00 | find_purple_:d8.8/f119 mine_white_c:* find_red_net:d5.4/f76 mine_quartz_:- | {"attack":1} [5/5]
137 | (6.1,1.0,-0.3) yaw=-65 p=20 | mv=0.00 | find_purple_:d8.8/f109 mine_white_c:* find_red_net:d5.4/f66 mine_quartz_:- | {"camera":[0,10]} [1/1]
      PLAN: Adjusting view to target the quartz block more directly and attacking it to mine it.
138 | (6.1,1.0,-0.3) yaw=-65 p=20 | mv=0.00 | find_purple_:d8.8/f109 mine_white_c:* find_red_net:d5.4/f66 mine_quartz_:- | {"attack":1} [1/5]
139 | (6.1,1.0,-0.3) yaw=-65 p=20 | mv=0.00 | find_purple_:d8.8/f109 mine_white_c:* find_red_net:d5.4/f66 mine_quartz_:- | {"attack":1} [2/5]
140 | (6.1,1.0,-0.3) yaw=-65 p=20 | mv=0.00 | find_purple_:d8.8/f109 mine_white_c:* find_red_net:d5.4/f66 mine_quartz_:- | {"attack":1} [3/5]
141 | (6.1,1.0,-0.3) yaw=-65 p=20 | mv=0.00 | find_purple_:d8.8/f109 mine_white_c:* find_red_net:d5.4/f66 mine_quartz_:- | {"attack":1} [4/5]
142 | (6.1,1.0,-0.3) yaw=-65 p=20 | mv=0.00 | find_purple_:d8.8/f109 mine_white_c:* find_red_net:d5.4/f66 mine_quartz_:- | {"attack":1} [5/5]
143 | (6.1,1.0,-0.3) yaw=-85 p=20 | mv=0.00 | find_purple_:d8.8/f129 mine_white_c:* find_red_net:d5.4/f86 mine_quartz_:- | {"camera":[0,-20]} [1/1]
      PLAN: Turning left to target the quartz block and attacking it to mine it.
144 | (6.1,1.0,-0.3) yaw=-85 p=20 | mv=0.00 | find_purple_:d8.8/f129 mine_white_c:* find_red_net:d5.4/f86 mine_quartz_:- | {"attack":1} [1/5]
145 | (6.1,1.0,-0.3) yaw=-85 p=20 | mv=0.00 | find_purple_:d8.8/f129 mine_white_c:* find_red_net:d5.4/f86 mine_quartz_:- | {"attack":1} [2/5]
146 | (6.1,1.0,-0.3) yaw=-85 p=20 | mv=0.00 | find_purple_:d8.8/f129 mine_white_c:* find_red_net:d5.4/f86 mine_quartz_:- | {"attack":1} [3/5]
147 | (6.1,1.0,-0.3) yaw=-85 p=20 | mv=0.00 | find_purple_:d8.8/f129 mine_white_c:* find_red_net:d5.4/f86 mine_quartz_:- | {"attack":1} [4/5]
148 | (6.1,1.0,-0.3) yaw=-85 p=20 | mv=0.00 | find_purple_:d8.8/f129 mine_white_c:* find_red_net:d5.4/f86 mine_quartz_:- | {"attack":1} [5/5]
149 | (6.1,1.0,-0.3) yaw=-85 p=20 | mv=0.00 | find_purple_:d8.8/f129 mine_white_c:* find_red_net:d5.4/f86 mine_quartz_:- | {"attack":1} [1/5]
      PLAN: Continuing to attack the quartz block to mine it.
150 | (6.1,1.0,-0.3) yaw=-85 p=20 | mv=0.00 | find_purple_:d8.8/f129 mine_white_c:* find_red_net:d5.4/f86 mine_quartz_:- | {"attack":1} [2/5]
151 | (6.1,1.0,-0.3) yaw=-85 p=20 | mv=0.00 | find_purple_:d8.8/f129 mine_white_c:* find_red_net:d5.4/f86 mine_quartz_:- | {"attack":1} [3/5]
152 | (6.1,1.0,-0.3) yaw=-85 p=20 | mv=0.00 | find_purple_:d8.8/f129 mine_white_c:* find_red_net:d5.4/f86 mine_quartz_:- | {"attack":1} [4/5]
153 | (6.1,1.0,-0.3) yaw=-85 p=20 | mv=0.00 | find_purple_:d8.8/f129 mine_white_c:* find_red_net:d5.4/f86 mine_quartz_:- | {"attack":1} [5/5]
154 | (6.2,1.0,-0.3) yaw=-85 p=20 | mv=0.10 | find_purple_:d8.9/f130 mine_white_c:* find_red_net:d5.4/f87 mine_quartz_:- | {"forward":1} [1/2]
      PLAN: Moving forward to get closer to the quartz block and attacking it to mine it.
155 | (6.3,1.0,-0.2) yaw=-85 p=20 | mv=0.15 | find_purple_:d8.9/f130 mine_white_c:* find_red_net:d5.3/f89 mine_quartz_:- | {"forward":1} [2/2]
156 | (6.4,1.0,-0.2) yaw=-85 p=20 | mv=0.08 | find_purple_:d9.0/f131 mine_white_c:* find_red_net:d5.3/f90 mine_quartz_:- | {"attack":1} [1/5]
157 | (6.5,1.0,-0.2) yaw=-85 p=20 | mv=0.05 | find_purple_:d9.0/f131 mine_white_c:* find_red_net:d5.3/f90 mine_quartz_:- | {"attack":1} [2/5]
158 | (6.5,1.0,-0.2) yaw=-85 p=20 | mv=0.02 | find_purple_:d9.0/f131 mine_white_c:* find_red_net:d5.3/f90 mine_quartz_:- | {"attack":1} [3/5]
159 | (6.5,1.0,-0.2) yaw=-85 p=20 | mv=0.01 | find_purple_:d9.1/f131 mine_white_c:* find_red_net:d5.3/f90 mine_quartz_:- | {"attack":1} [4/5]
160 | (6.5,1.0,-0.2) yaw=-85 p=20 | mv=0.01 | find_purple_:d9.1/f131 mine_white_c:* find_red_net:d5.3/f91 mine_quartz_:- | {"attack":1} [5/5]
161 | (6.5,1.0,-0.2) yaw=-85 p=20 | mv=0.00 | find_purple_:d9.1/f131 mine_white_c:* find_red_net:d5.3/f91 mine_quartz_:- | {"attack":1} [1/5]
      PLAN: Attacking the quartz block to mine it.
162 | (6.5,1.0,-0.2) yaw=-85 p=20 | mv=0.00 | find_purple_:d9.1/f131 mine_white_c:* find_red_net:d5.3/f91 mine_quartz_:- | {"attack":1} [2/5]
163 | (6.5,1.0,-0.2) yaw=-85 p=20 | mv=0.00 | find_purple_:d9.1/f131 mine_white_c:* find_red_net:d5.3/f91 mine_quartz_:- | {"attack":1} [3/5]
164 | (6.5,1.0,-0.2) yaw=-85 p=20 | mv=0.00 | find_purple_:d9.1/f131 mine_white_c:* find_red_net:d5.3/f91 mine_quartz_:- | {"attack":1} [4/5]
165 | (6.5,1.0,-0.2) yaw=-85 p=20 | mv=0.00 | find_purple_:d9.1/f131 mine_white_c:* find_red_net:d5.3/f91 mine_quartz_:- | {"attack":1} [5/5]
166 | (6.6,1.0,-0.2) yaw=-85 p=20 | mv=0.10 | find_purple_:d9.1/f132 mine_white_c:* find_red_net:d5.4/f92 mine_quartz_:- | {"forward":1,"attack":1} [1/10]
      PLAN: Moving forward while attacking the quartz block to mine it.
167 | (6.8,1.0,-0.2) yaw=-85 p=20 | mv=0.15 | find_purple_:d9.2/f132 mine_white_c:* find_red_net:d5.4/f93 mine_quartz_:- | {"forward":1,"attack":1} [2/10]
168 | (6.9,1.0,-0.2) yaw=-85 p=20 | mv=0.18 | find_purple_:d9.4/f133 mine_white_c:* find_red_net:d5.4/f95 mine_quartz_:- | {"forward":1,"attack":1} [3/10]
169 | (7.1,1.0,-0.2) yaw=-85 p=20 | mv=0.20 | find_purple_:d9.5/f134 mine_white_c:* find_red_net:d5.4/f97 mine_quartz_:- | {"forward":1,"attack":1} [4/10]
170 | (7.3,1.0,-0.2) yaw=-85 p=20 | mv=0.21 | find_purple_:d9.6/f135 mine_white_c:* find_red_net:d5.4/f100 mine_quartz_:- | {"forward":1,"attack":1} [5/10]
171 | (7.5,1.0,-0.1) yaw=-85 p=20 | mv=0.21 | find_purple_:d9.8/f136 mine_white_c:* find_red_net:d5.5/f102 mine_quartz_:- | {"forward":1,"attack":1} [6/10]
172 | (7.8,1.0,-0.1) yaw=-85 p=20 | mv=0.21 | find_purple_:d9.9/f137 mine_white_c:* find_red_net:d5.5/f104 mine_quartz_:- | {"forward":1,"attack":1} [7/10]
173 | (8.0,1.0,-0.1) yaw=-85 p=20 | mv=0.21 | find_purple_:d10.1/f138 mine_white_c:* find_red_net:d5.6/f106 mine_quartz_:- | {"forward":1,"attack":1} [8/10]
174 | (8.2,0.9,-0.1) yaw=-85 p=20 | mv=0.21 | find_purple_:d10.2/f138 mine_white_c:* find_red_net:d5.6/f108 mine_quartz_:- | {"forward":1,"attack":1} [9/10]
175 | (8.3,0.8,-0.1) yaw=-85 p=20 | mv=0.14 | find_purple_:d10.3/f139 mine_white_c:* find_red_net:d5.6/f110 mine_quartz_:- | {"forward":1,"attack":1} [10/10]
176 | (8.4,0.5,-0.1) yaw=-85 p=20 | mv=0.12 | find_purple_:d10.4/f139 mine_white_c:* find_red_net:d5.6/f111 mine_quartz_:- | {"attack":1} [1/10]
      PLAN: Attacking the quartz block to mine it.
177 | (8.6,0.2,-0.1) yaw=-85 p=20 | mv=0.11 | find_purple_:d10.5/f140 mine_white_c:* find_red_net:d5.7/f112 mine_quartz_:- | {"attack":1} [2/10]
178 | (8.7,0.0,-0.0) yaw=-85 p=20 | mv=0.10 | find_purple_:d10.6/f140 mine_white_c:* find_red_net:d5.7/f113 mine_quartz_:- | {"attack":1} [3/10]
179 | (8.8,0.0,-0.0) yaw=-85 p=20 | mv=0.09 | find_purple_:d10.6/f140 mine_white_c:* find_red_net:d5.7/f114 mine_quartz_:- | {"attack":1} [4/10]
180 | (8.8,0.0,-0.0) yaw=-85 p=20 | mv=0.05 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f114 mine_quartz_:- | {"attack":1} [5/10]
181 | (8.8,0.0,-0.0) yaw=-85 p=20 | mv=0.03 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f114 mine_quartz_:- | {"attack":1} [6/10]
182 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.02 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [7/10]
183 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.01 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [8/10]
184 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [9/10]
185 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [10/10]
186 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [1/10]
      PLAN: Continuing to attack the quartz block to finish mining it.
187 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [2/10]
188 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [3/10]
189 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [4/10]
190 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [5/10]
191 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [6/10]
192 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [7/10]
193 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [8/10]
194 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [9/10]
195 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [10/10]
196 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [1/10]
197 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [2/10]
198 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [3/10]
199 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [4/10]
200 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [5/10]
201 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [6/10]
202 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [7/10]
203 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [8/10]
204 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [9/10]
205 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [10/10]
206 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [1/10]
207 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [2/10]
208 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [3/10]
209 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [4/10]
210 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [5/10]
211 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [6/10]
212 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [7/10]
213 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [8/10]
214 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [9/10]
215 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [10/10]
216 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [1/10]
217 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [2/10]
218 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [3/10]
219 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [4/10]
220 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [5/10]
221 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [6/10]
222 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [7/10]
223 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [8/10]
224 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [9/10]
225 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [10/10]
226 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [1/10]
227 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [2/10]
228 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [3/10]
229 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [4/10]
230 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [5/10]
231 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [6/10]
232 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [7/10]
233 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [8/10]
234 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [9/10]
235 | (8.9,0.0,-0.0) yaw=-85 p=20 | mv=0.00 | find_purple_:d10.7/f141 mine_white_c:* find_red_net:d5.8/f115 mine_quartz_:- | {"attack":1} [10/10]
236 | (9.0,0.0,-0.0) yaw=-85 p=20 | mv=0.10 | find_purple_:d10.8/f141 mine_white_c:* find_red_net:d5.8/f116 mine_quartz_:- | {"forward":1,"attack":1} [1/10]
      PLAN: Moving forward while attacking the quartz block to mine it.
237 | (9.1,0.0,-0.0) yaw=-85 p=20 | mv=0.15 | find_purple_:d10.9/f142 mine_white_c:* find_red_net:d5.9/f117 mine_quartz_:- | {"forward":1,"attack":1} [2/10]
238 | (9.3,0.0,0.0) yaw=-85 p=20 | mv=0.18 | find_purple_:d11.1/f142 mine_white_c:* find_red_net:d6.0/f118 mine_quartz_:- | {"forward":1,"attack":1} [3/10]
239 | (9.5,0.0,0.0) yaw=-85 p=20 | mv=0.20 | find_purple_:d11.2/f143 mine_white_c:* find_red_net:d6.1/f120 mine_quartz_:- | {"forward":1,"attack":1} [4/10]
240 | (9.7,0.0,0.0) yaw=-85 p=20 | mv=0.21 | find_purple_:d11.4/f143 mine_white_c:* find_red_net:d6.2/f122 mine_quartz_:- | {"forward":1,"attack":1} [5/10]
241 | (9.9,0.0,0.1) yaw=-85 p=20 | mv=0.21 | find_purple_:d11.5/f144 mine_white_c:* find_red_net:d6.3/f123 mine_quartz_:- | {"forward":1,"attack":1} [6/10]
242 | (10.1,0.0,0.1) yaw=-85 p=20 | mv=0.21 | find_purple_:d11.7/f145 mine_white_c:* find_red_net:d6.4/f125 mine_quartz_:- | {"forward":1,"attack":1} [7/10]
243 | (10.3,0.0,0.1) yaw=-85 p=20 | mv=0.21 | find_purple_:d11.9/f145 mine_white_c:* find_red_net:d6.5/f126 mine_quartz_:- | {"forward":1,"attack":1} [8/10]
244 | (10.5,0.0,0.1) yaw=-85 p=20 | mv=0.21 | find_purple_:d12.1/f146 mine_white_c:* find_red_net:d6.7/f128 mine_quartz_:- | {"forward":1,"attack":1} [9/10]
245 | (10.8,0.0,0.1) yaw=-85 p=20 | mv=0.22 | find_purple_:d12.3/f146 mine_white_c:* find_red_net:d6.8/f129 mine_quartz_:- | {"forward":1,"attack":1} [10/10]
246 | (10.9,0.0,0.1) yaw=-85 p=20 | mv=0.12 | find_purple_:d12.3/f147 mine_white_c:* find_red_net:d6.9/f130 mine_quartz_:- | {"attack":1} [1/10]
      PLAN: Continuing to attack the quartz block to finish mining it.
247 | (10.9,0.0,0.2) yaw=-85 p=20 | mv=0.06 | find_purple_:d12.4/f147 mine_white_c:* find_red_net:d6.9/f131 mine_quartz_:- | {"attack":1} [2/10]
248 | (11.0,0.0,0.2) yaw=-85 p=20 | mv=0.04 | find_purple_:d12.4/f147 mine_white_c:* find_red_net:d6.9/f131 mine_quartz_:- | {"attack":1} [3/10]
249 | (11.0,0.0,0.2) yaw=-85 p=20 | mv=0.02 | find_purple_:d12.4/f147 mine_white_c:* find_red_net:d7.0/f131 mine_quartz_:- | {"attack":1} [4/10]
250 | (11.0,0.0,0.2) yaw=-85 p=20 | mv=0.01 | find_purple_:d12.5/f147 mine_white_c:* find_red_net:d7.0/f131 mine_quartz_:- | {"attack":1} [5/10]
251 | (11.0,0.0,0.2) yaw=-85 p=20 | mv=0.01 | find_purple_:d12.5/f147 mine_white_c:* find_red_net:d7.0/f131 mine_quartz_:- | {"attack":1} [6/10]
252 | (11.0,0.0,0.2) yaw=-85 p=20 | mv=0.00 | find_purple_:d12.5/f147 mine_white_c:* find_red_net:d7.0/f131 mine_quartz_:- | {"attack":1} [7/10]
253 | (11.0,0.0,0.2) yaw=-85 p=20 | mv=0.00 | find_purple_:d12.5/f147 mine_white_c:* find_red_net:d7.0/f131 mine_quartz_:* | {"attack":1} [8/10]
254 | (11.0,0.0,0.2) yaw=-85 p=20 | mv=0.00 | find_purple_:d12.5/f147 mine_white_c:* find_red_net:d7.0/f131 mine_quartz_:* | {"attack":1} [9/10]
255 | (11.0,0.0,0.2) yaw=-85 p=20 | mv=0.00 | find_purple_:d12.5/f147 mine_white_c:* find_red_net:d7.0/f131 mine_quartz_:* | {"attack":1} [10/10]
256 | (11.0,0.0,0.2) yaw=-85 p=20 | mv=0.00 | find_purple_:d12.5/f147 mine_white_c:* find_red_net:d7.0/f131 mine_quartz_:* | {"ESC":1} [1/1]
      PLAN: Ending the episode with ESC=1 since all task requirements have been completed: found purple bed, mined white carpet, walked east through doorways past red nether brick stairs, and mined the quartz block.
      NOTE: ESC was rejected at step 256 (1x): the environment has not verified the task as complete. Keep working.
257 | (11.0,0.0,0.2) yaw=-115 p=20 | mv=0.00 | find_purple_:d12.5/f177 mine_white_c:* find_red_net:d7.0/f161 mine_quartz_:* | {"camera":[0,-30]} [1/1]
      PLAN: Looking around the room to see if there's another quartz block to mine or something else I'm missing.
258 | (11.0,0.0,0.2) yaw=-145 p=20 | mv=0.00 | find_purple_:d12.5/f153 mine_white_c:* find_red_net:d7.0/f169 mine_quartz_:* | {"camera":[0,-30]} [1/1]
259 | (11.0,0.0,0.2) yaw=125 p=20 | mv=0.00 | find_purple_:d12.5/f63 mine_white_c:* find_red_net:d7.0/f79 mine_quartz_:* | {"camera":[0,-90]} [1/1]
      PLAN: Turning to see the full room layout and check if there's anything else I need to do.
260 | (11.1,0.0,0.2) yaw=125 p=20 | mv=0.10 | find_purple_:d12.5/f63 mine_white_c:* find_red_net:d7.0/f78 mine_quartz_:* | {"back":1,"sprint":1} [1/10]
      PLAN: Walking back to the bedroom to verify the white carpet was mined and check if there's anything else I need to do.
261 | (11.2,0.0,0.3) yaw=125 p=20 | mv=0.14 | find_purple_:d12.6/f62 mine_white_c:* find_red_net:d7.0/f77 mine_quartz_:* | {"back":1,"sprint":1} [2/10]
262 | (11.2,0.0,0.4) yaw=125 p=20 | mv=0.10 | find_purple_:d12.5/f62 mine_white_c:* find_red_net:d6.9/f76 mine_quartz_:* | {"back":1,"sprint":1} [3/10]
263 | (11.2,0.0,0.5) yaw=125 p=20 | mv=0.11 | find_purple_:d12.5/f61 mine_white_c:* find_red_net:d6.9/f76 mine_quartz_:* | {"back":1,"sprint":1} [4/10]
264 | (11.2,0.0,0.6) yaw=125 p=20 | mv=0.12 | find_purple_:d12.4/f61 mine_white_c:* find_red_net:d6.8/f75 mine_quartz_:* | {"back":1,"sprint":1} [5/10]
265 | (11.2,0.0,0.8) yaw=125 p=20 | mv=0.12 | find_purple_:d12.4/f60 mine_white_c:* find_red_net:d6.7/f74 mine_quartz_:* | {"back":1,"sprint":1} [6/10]
266 | (11.2,0.0,0.9) yaw=125 p=20 | mv=0.12 | find_purple_:d12.3/f60 mine_white_c:* find_red_net:d6.6/f73 mine_quartz_:* | {"back":1,"sprint":1} [7/10]
267 | (11.2,0.0,1.0) yaw=125 p=20 | mv=0.12 | find_purple_:d12.3/f59 mine_white_c:* find_red_net:d6.6/f73 mine_quartz_:* | {"back":1,"sprint":1} [8/10]
268 | (11.2,0.0,1.1) yaw=125 p=20 | mv=0.12 | find_purple_:d12.2/f59 mine_white_c:* find_red_net:d6.5/f72 mine_quartz_:* | {"back":1,"sprint":1} [9/10]
269 | (11.2,0.0,1.2) yaw=125 p=20 | mv=0.12 | find_purple_:d12.2/f58 mine_white_c:* find_red_net:d6.4/f71 mine_quartz_:* | {"back":1,"sprint":1} [10/10]
270 | (11.2,0.0,1.4) yaw=125 p=20 | mv=0.12 | find_purple_:d12.1/f57 mine_white_c:* find_red_net:d6.3/f70 mine_quartz_:* | {"back":1,"sprint":1} [1/10]
      PLAN: Continuing to walk back to the bedroom to verify the white carpet was mined.
271 | (11.2,0.0,1.5) yaw=125 p=20 | mv=0.12 | find_purple_:d12.1/f57 mine_white_c:* find_red_net:d6.3/f69 mine_quartz_:* | {"back":1,"sprint":1} [2/10]
272 | (11.2,0.0,1.6) yaw=125 p=20 | mv=0.12 | find_purple_:d12.0/f56 mine_white_c:* find_red_net:d6.2/f68 mine_quartz_:* | {"back":1,"sprint":1} [3/10]
273 | (11.2,0.0,1.7) yaw=125 p=20 | mv=0.12 | find_purple_:d12.0/f56 mine_white_c:* find_red_net:d6.1/f67 mine_quartz_:* | {"back":1,"sprint":1} [4/10]
274 | (11.3,0.0,1.9) yaw=125 p=20 | mv=0.15 | find_purple_:d12.0/f55 mine_white_c:* find_red_net:d6.1/f66 mine_quartz_:* | {"back":1,"sprint":1} [5/10]
275 | (11.4,0.0,2.0) yaw=125 p=20 | mv=0.18 | find_purple_:d12.1/f54 mine_white_c:* find_red_net:d6.2/f64 mine_quartz_:* | {"back":1,"sprint":1} [6/10]
276 | (11.6,0.0,2.1) yaw=125 p=20 | mv=0.19 | find_purple_:d12.2/f54 mine_white_c:* find_red_net:d6.3/f62 mine_quartz_:* | {"back":1,"sprint":1} [7/10]
277 | (11.7,0.0,2.2) yaw=125 p=20 | mv=0.18 | find_purple_:d12.3/f53 mine_white_c:* find_red_net:d6.4/f61 mine_quartz_:* | {"back":1,"sprint":1} [8/10]
278 | (11.9,0.0,2.2) yaw=125 p=20 | mv=0.17 | find_purple_:d12.5/f53 mine_white_c:* find_red_net:d6.5/f60 mine_quartz_:* | {"back":1,"sprint":1} [9/10]
279 | (12.1,0.0,2.2) yaw=125 p=20 | mv=0.17 | find_purple_:d12.6/f52 mine_white_c:* find_red_net:d6.7/f60 mine_quartz_:* | {"back":1,"sprint":1} [10/10]
280 | (12.2,0.0,2.2) yaw=125 p=20 | mv=0.17 | find_purple_:d12.8/f52 mine_white_c:* find_red_net:d6.8/f59 mine_quartz_:* | {"back":1,"sprint":1} [1/10]
281 | (12.4,0.0,2.2) yaw=125 p=20 | mv=0.18 | find_purple_:d13.0/f52 mine_white_c:* find_red_net:d7.0/f59 mine_quartz_:* | {"back":1,"sprint":1} [2/10]
282 | (12.6,0.0,2.2) yaw=125 p=20 | mv=0.18 | find_purple_:d13.1/f52 mine_white_c:* find_red_net:d7.2/f58 mine_quartz_:* | {"back":1,"sprint":1} [3/10]
283 | (12.8,0.0,2.2) yaw=125 p=20 | mv=0.18 | find_purple_:d13.3/f52 mine_white_c:* find_red_net:d7.3/f58 mine_quartz_:* | {"back":1,"sprint":1} [4/10]
284 | (12.9,0.0,2.2) yaw=125 p=20 | mv=0.18 | find_purple_:d13.5/f51 mine_white_c:* find_red_net:d7.5/f57 mine_quartz_:* | {"back":1,"sprint":1} [5/10]
285 | (13.1,0.0,2.2) yaw=125 p=20 | mv=0.18 | find_purple_:d13.6/f51 mine_white_c:* find_red_net:d7.6/f56 mine_quartz_:* | {"back":1,"sprint":1} [6/10]
286 | (13.3,0.0,2.2) yaw=125 p=20 | mv=0.18 | find_purple_:d13.8/f51 mine_white_c:* find_red_net:d7.8/f56 mine_quartz_:* | {"back":1,"sprint":1} [7/10]
287 | (13.5,0.0,2.2) yaw=125 p=20 | mv=0.18 | find_purple_:d14.0/f51 mine_white_c:* find_red_net:d8.0/f56 mine_quartz_:* | {"back":1,"sprint":1} [8/10]
288 | (13.6,0.0,2.2) yaw=125 p=20 | mv=0.18 | find_purple_:d14.2/f51 mine_white_c:* find_red_net:d8.1/f55 mine_quartz_:* | {"back":1,"sprint":1} [9/10]
289 | (13.8,0.0,2.2) yaw=125 p=20 | mv=0.18 | find_purple_:d14.3/f50 mine_white_c:* find_red_net:d8.3/f55 mine_quartz_:* | {"back":1,"sprint":1} [10/10]
290 | (14.0,0.0,2.2) yaw=125 p=20 | mv=0.18 | find_purple_:d14.5/f50 mine_white_c:* find_red_net:d8.5/f54 mine_quartz_:* | {"back":1,"sprint":1} [1/10]
291 | (14.2,0.0,2.2) yaw=125 p=20 | mv=0.18 | find_purple_:d14.7/f50 mine_white_c:* find_red_net:d8.6/f54 mine_quartz_:* | {"back":1,"sprint":1} [2/10]
292 | (14.3,0.0,2.2) yaw=125 p=20 | mv=0.18 | find_purple_:d14.8/f50 mine_white_c:* find_red_net:d8.8/f54 mine_quartz_:* | {"back":1,"sprint":1} [3/10]
293 | (14.5,0.0,2.2) yaw=125 p=20 | mv=0.18 | find_purple_:d15.0/f50 mine_white_c:* find_red_net:d9.0/f53 mine_quartz_:* | {"back":1,"sprint":1} [4/10]
294 | (14.7,0.0,2.2) yaw=125 p=20 | mv=0.18 | find_purple_:d15.2/f49 mine_white_c:* find_red_net:d9.1/f53 mine_quartz_:* | {"back":1,"sprint":1} [5/10]
295 | (14.9,0.0,2.2) yaw=125 p=20 | mv=0.18 | find_purple_:d15.4/f49 mine_white_c:* find_red_net:d9.3/f53 mine_quartz_:* | {"back":1,"sprint":1} [6/10]
296 | (15.1,0.0,2.2) yaw=125 p=20 | mv=0.18 | find_purple_:d15.5/f49 mine_white_c:* find_red_net:d9.5/f52 mine_quartz_:* | {"back":1,"sprint":1} [7/10]
297 | (15.2,0.0,2.2) yaw=125 p=20 | mv=0.15 | find_purple_:d15.7/f49 mine_white_c:* find_red_net:d9.6/f52 mine_quartz_:* | {"back":1,"sprint":1} [8/10]
298 | (15.2,0.0,2.2) yaw=125 p=20 | mv=0.00 | find_purple_:d15.7/f49 mine_white_c:* find_red_net:d9.6/f52 mine_quartz_:* | {"back":1,"sprint":1} [9/10]
299 | (15.2,0.0,2.2) yaw=125 p=20 | mv=0.00 | find_purple_:d15.7/f49 mine_white_c:* find_red_net:d9.6/f52 mine_quartz_:* | {"back":1,"sprint":1} [10/10]
300 | (15.2,0.0,2.2) yaw=-145 p=20 | mv=0.00 | find_purple_:d15.7/f139 mine_white_c:* find_red_net:d9.6/f142 mine_quartz_:* | None [None/None]