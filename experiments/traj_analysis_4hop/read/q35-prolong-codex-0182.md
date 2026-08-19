# q35-prolong-codex-0182  arm=prolong
TASK: Find the green banner landmark, then locate and find the dark oak button on the stone wall. Pass through the wall opening, mine magma blocks from the deposit, then build a bridge across the lava gap to reach the gold block on the far platform.
MILESTONE RULES (spawn-relative coords; x+ = east, z+ = south; Minecraft yaw: 0=south(+z), 90=west(-x), 180/-180=north(-z), -90=east(+x)):
  - find_green_banner: position_near_with_facing {"target": [4, 0, 5], "max_distance": 5, "facing_tolerance": 60, "coordinate_frame": "spawn_relative"}
  - find_dark_oak_button: position_near_with_facing {"target": [7, 1, 5], "max_distance": 5, "facing_tolerance": 60, "coordinate_frame": "spawn_relative"}
  - mine_magma_block: inventory_has {"item": "magma_block", "min_count": 1}
  - bridge_lava_gap: position_inside_box {"min": [19, -1, 1], "max": [25, 3, 9], "coordinate_frame": "spawn_relative"}
spawn_abs=(-3009.5, 71.0, -5572.5)  milestones_done(frame)={'find_green_banner': 9, 'find_dark_oak_button': 22}  esc_rejected_steps(n=0)=[]
PHASES (action-class runs; pos = spawn-relative x,z at start -> end):
  steps   1-  2 (  2) turn        (0.0,0.0)->(0.0,0.0) yaw -45->-45
  steps   3-  7 (  5) move        (0.1,0.1)->(0.8,0.8) yaw -45->-45
  steps   8-  8 (  1) use         (0.9,0.9)->(0.9,0.9) yaw -45->-45
  steps   9- 11 (  3) move        (1.0,1.0)->(1.4,1.4) yaw -45->-45
  steps  12- 17 (  6) mixed       (1.5,1.5)->(1.8,2.0) yaw -45->-55
  steps  18- 22 (  5) move        (1.9,2.1)->(2.7,2.7) yaw -55->-55
  steps  23- 23 (  1) turn        (2.8,2.8)->(2.8,2.8) yaw -55->-55
  steps  24- 58 ( 35) move        (3.0,2.9)->(6.2,7.7) yaw -55->-55
  steps  59- 59 (  1) turn        (6.2,7.7)->(6.2,7.7) yaw -10->-10
  steps  60- 64 (  5) move        (6.2,7.9)->(6.4,8.9) yaw -10->-10
  steps  65- 65 (  1) turn        (6.4,9.0)->(6.4,9.0) yaw -55->-55
  steps  66- 70 (  5) move        (6.5,9.2)->(7.3,9.8) yaw -55->-55
  steps  71- 71 (  1) turn        (7.4,9.9)->(7.4,9.9) yaw -55->-55
  steps  72- 76 (  5) move        (7.6,10.0)->(8.5,10.6) yaw -55->-55
  steps  77- 77 (  1) turn        (8.6,10.7)->(8.6,10.7) yaw -85->-85
  steps  78- 82 (  5) move        (8.8,10.8)->(9.8,10.9) yaw -85->-85
  steps  83- 83 (  1) turn        (10.0,10.9)->(10.0,10.9) yaw -100->-100
  steps  84- 88 (  5) move        (10.2,10.9)->(11.2,10.8) yaw -100->-100
  steps  89- 93 (  5) attack      (11.3,10.7)->(11.5,10.7) yaw -100->-100
  steps  94- 94 (  1) turn        (11.5,10.7)->(11.5,10.7) yaw -100->-100
  steps  95-104 ( 10) attack      (11.5,10.7)->(11.5,10.7) yaw -100->-100
  steps 105-105 (  1) turn        (11.5,10.7)->(11.5,10.7) yaw -120->-120
  steps 106-125 ( 20) attack      (11.5,10.7)->(11.5,10.7) yaw -120->-120
  steps 126-127 (  2) move        (11.5,10.6)->(11.4,10.5) yaw -120->-120
  steps 128-137 ( 10) attack      (11.4,10.4)->(11.3,10.3) yaw -120->-120
  steps 138-138 (  1) turn        (11.3,10.3)->(11.3,10.3) yaw -130->-130
  steps 139-148 ( 10) attack      (11.3,10.3)->(11.3,10.3) yaw -130->-130
  steps 149-149 (  1) turn        (11.3,10.3)->(11.3,10.3) yaw -130->-130
  steps 150-159 ( 10) attack      (11.3,10.3)->(11.3,10.3) yaw -130->-130
  steps 160-161 (  2) move        (11.4,10.3)->(11.5,10.2) yaw -130->-130
  steps 162-171 ( 10) attack      (11.6,10.1)->(11.6,10.1) yaw -130->-130
  steps 172-172 (  1) turn        (11.6,10.1)->(11.6,10.1) yaw -135->-135
  steps 173-182 ( 10) attack      (11.6,10.1)->(11.6,10.1) yaw -135->-135
  steps 183-183 (  1) turn        (11.6,10.1)->(11.6,10.1) yaw -135->-135
  steps 184-193 ( 10) attack      (11.6,10.1)->(11.6,10.1) yaw -135->-135
  steps 194-194 (  1) other       (11.6,10.1)->(11.6,10.1) yaw -135->-135
  steps 195-204 ( 10) attack      (11.6,10.1)->(11.6,10.1) yaw -135->-135
  steps 205-205 (  1) other       (11.6,10.1)->(11.6,10.1) yaw -135->-135
  steps 206-215 ( 10) attack      (11.6,10.1)->(11.6,10.1) yaw -135->-135
  steps 216-218 (  3) other       (11.6,10.1)->(11.6,10.1) yaw -135->-135
  steps 219-221 (  3) mixed       (11.6,10.1)->(11.6,10.1) yaw -135->-90
  steps 222-256 ( 35) move        (11.8,10.1)->(14.0,10.1) yaw -90->-90
  steps 257-257 (  1) turn        (14.0,10.1)->(14.0,10.1) yaw -70->-70
  steps 258-267 ( 10) move        (14.0,10.1)->(14.0,10.1) yaw -70->-70
  steps 268-277 ( 10) jump+move   (14.0,10.1)->(13.8,9.9) yaw -70->-70
  steps 278-278 (  1) turn        (13.8,9.9)->(13.8,9.9) yaw -40->-40
  steps 279-288 ( 10) move        (13.8,9.9)->(14.0,10.2) yaw -40->-40
  steps 289-293 (  5) jump+move   (14.0,10.2)->(13.9,10.1) yaw -40->-40
  steps 294-299 (  6) move        (13.9,10.1)->(13.8,9.8) yaw -40->-40
  steps 300-300 (  1) none        (13.8,9.7)->(13.8,9.7) yaw -40->-40

STEPS: step | rel_pos(x,y,z) yaw pitch | moved | per-milestone d=3D dist to target / f=facing error deg (* = rule satisfied this step; "-" = non-position rule) | action | T: thought (trunc) | M: memory (shown when changed, every ~25 steps) | H: hypothesis ops (new statements / status changes)
  1 | (0.0,0.0,0.0) yaw=-45 p=0 | mv=0.00 | find_green_b:d6.4/f6 find_dark_oa:d8.7/f9 mine_magma_b:- bridge_lava_:d19.0 | {"camera":[0,-45]} [1/1]
      PLAN: Turn left to face the stone wall with the green banner, then look around to locate the dark oak button on the wall.
  2 | (0.0,0.0,0.0) yaw=-45 p=-10 | mv=0.00 | find_green_b:d6.4/f6 find_dark_oa:d8.7/f9 mine_magma_b:- bridge_lava_:d19.0 | {"camera":[-10,0]} [1/1]
  3 | (0.1,0.0,0.1) yaw=-45 p=-10 | mv=0.13 | find_green_b:d6.3/f6 find_dark_oa:d8.5/f10 mine_magma_b:- bridge_lava_:d18.9 | {"forward":1,"sprint":1} [1/5]
      PLAN: Move forward toward the stone wall with the button, then use the button to open the passage through the wall.
  4 | (0.2,0.0,0.2) yaw=-45 p=-10 | mv=0.20 | find_green_b:d6.1/f7 find_dark_oa:d8.3/f10 mine_magma_b:- bridge_lava_:d18.8 | {"forward":1,"sprint":1} [2/5]
  5 | (0.4,0.0,0.4) yaw=-45 p=-10 | mv=0.23 | find_green_b:d5.8/f7 find_dark_oa:d8.1/f10 mine_magma_b:- bridge_lava_:d18.6 | {"forward":1,"sprint":1} [3/5]
  6 | (0.6,0.0,0.6) yaw=-45 p=-10 | mv=0.26 | find_green_b:d5.6/f7 find_dark_oa:d7.9/f10 mine_magma_b:- bridge_lava_:d18.4 | {"forward":1,"sprint":1} [4/5]
  7 | (0.8,0.0,0.8) yaw=-45 p=-10 | mv=0.27 | find_green_b:d5.3/f8 find_dark_oa:d7.6/f11 mine_magma_b:- bridge_lava_:d18.2 | {"forward":1,"sprint":1} [5/5]
  8 | (0.9,0.0,0.9) yaw=-45 p=-10 | mv=0.15 | find_green_b:d5.2/f8 find_dark_oa:d7.5/f11 mine_magma_b:- bridge_lava_:d18.1 | {"use":1} [1/1]
  9 | (1.0,0.0,1.0) yaw=-45 p=-10 | mv=0.21 | find_green_b:d5.0/f8* find_dark_oa:d7.3/f11 mine_magma_b:- bridge_lava_:d18.0 | {"forward":1} [1/3]
      PLAN: Move closer to the button on the stone wall, adjust camera angle slightly upward to aim at it, then press the button to open the passage.
 10 | (1.2,0.0,1.2) yaw=-45 p=-10 | mv=0.24 | find_green_b:d4.7/f9* find_dark_oa:d7.0/f12 mine_magma_b:- bridge_lava_:d17.8 | {"forward":1} [2/3]
 11 | (1.4,0.0,1.4) yaw=-45 p=-10 | mv=0.26 | find_green_b:d4.5/f9* find_dark_oa:d6.8/f12 mine_magma_b:- bridge_lava_:d17.6 | {"forward":1} [3/3]
 12 | (1.5,0.0,1.5) yaw=-45 p=-5 | mv=0.14 | find_green_b:d4.3/f9* find_dark_oa:d6.6/f12 mine_magma_b:- bridge_lava_:d17.5 | {"camera":[5,0]} [1/1]
 13 | (1.5,0.0,1.5) yaw=-45 p=-5 | mv=0.08 | find_green_b:d4.3/f10* find_dark_oa:d6.6/f13 mine_magma_b:- bridge_lava_:d17.5 | {"use":1} [1/1]
 14 | (1.6,0.0,1.6) yaw=-25 p=-5 | mv=0.04 | find_green_b:d4.2/f10* find_dark_oa:d6.5/f33 mine_magma_b:- bridge_lava_:d17.4 | {"camera":[0,20]} [1/1]
      PLAN: Look around the stone wall to find the opening or passage that should appear after pressing the button, then move through it.
 15 | (1.6,0.0,1.7) yaw=-25 p=-5 | mv=0.15 | find_green_b:d4.1/f11* find_dark_oa:d6.4/f33 mine_magma_b:- bridge_lava_:d17.4 | {"forward":1} [1/2]
 16 | (1.7,0.0,1.9) yaw=-25 p=-5 | mv=0.21 | find_green_b:d3.9/f11* find_dark_oa:d6.2/f34 mine_magma_b:- bridge_lava_:d17.3 | {"forward":1} [2/2]
 17 | (1.8,0.0,2.0) yaw=-55 p=-5 | mv=0.11 | find_green_b:d3.8/f19* find_dark_oa:d6.1/f5 mine_magma_b:- bridge_lava_:d17.2 | {"camera":[0,-30]} [1/1]
      PLAN: Turn left to look along the stone wall and find the opening/passage, then move toward it.
 18 | (1.9,0.0,2.1) yaw=-55 p=-5 | mv=0.18 | find_green_b:d3.6/f19* find_dark_oa:d6.0/f5 mine_magma_b:- bridge_lava_:d17.1 | {"forward":1,"sprint":1} [1/5]
 19 | (2.1,0.0,2.2) yaw=-55 p=-5 | mv=0.23 | find_green_b:d3.4/f20* find_dark_oa:d5.7/f6 mine_magma_b:- bridge_lava_:d16.9 | {"forward":1,"sprint":1} [2/5]
 20 | (2.3,0.0,2.4) yaw=-55 p=-5 | mv=0.25 | find_green_b:d3.1/f21* find_dark_oa:d5.5/f6 mine_magma_b:- bridge_lava_:d16.7 | {"forward":1,"sprint":1} [3/5]
 21 | (2.5,0.0,2.6) yaw=-55 p=-5 | mv=0.26 | find_green_b:d2.9/f23* find_dark_oa:d5.2/f7 mine_magma_b:- bridge_lava_:d16.5 | {"forward":1,"sprint":1} [4/5]
 22 | (2.7,0.0,2.7) yaw=-55 p=-5 | mv=0.27 | find_green_b:d2.6/f26* find_dark_oa:d5.0/f7* mine_magma_b:- bridge_lava_:d16.3 | {"forward":1,"sprint":1} [5/5]
 23 | (2.8,0.0,2.8) yaw=-55 p=-10 | mv=0.15 | find_green_b:d2.5/f27* find_dark_oa:d4.8/f7* mine_magma_b:- bridge_lava_:d16.2 | {"camera":[-5,0]} [1/1]
      PLAN: Look down slightly to aim at the opening below the button, then move forward through the passage.
 24 | (3.0,0.0,2.9) yaw=-55 p=-10 | mv=0.21 | find_green_b:d2.3/f29* find_dark_oa:d4.6/f7* mine_magma_b:- bridge_lava_:d16.0 | {"forward":1,"sprint":1} [1/5]
 25 | (3.2,0.0,3.1) yaw=-55 p=-10 | mv=0.24 | find_green_b:d2.1/f33 find_dark_oa:d4.4/f8* mine_magma_b:- bridge_lava_:d15.8 | {"forward":1,"sprint":1} [2/5]
 26 | (3.4,0.0,3.2) yaw=-55 p=-10 | mv=0.26 | find_green_b:d1.9/f37 find_dark_oa:d4.1/f8* mine_magma_b:- bridge_lava_:d15.6 | {"forward":1,"sprint":1} [3/5]
 27 | (3.6,0.0,3.4) yaw=-55 p=-10 | mv=0.27 | find_green_b:d1.7/f42 find_dark_oa:d3.9/f9* mine_magma_b:- bridge_lava_:d15.4 | {"forward":1,"sprint":1} [4/5]
 28 | (3.9,0.0,3.5) yaw=-55 p=-10 | mv=0.27 | find_green_b:d1.5/f49 find_dark_oa:d3.6/f10* mine_magma_b:- bridge_lava_:d15.1 | {"forward":1,"sprint":1} [5/5]
 29 | (4.1,0.0,3.7) yaw=-55 p=-10 | mv=0.28 | find_green_b:d1.3/f58 find_dark_oa:d3.4/f11* mine_magma_b:- bridge_lava_:d14.9 | {"forward":1,"sprint":1} [1/5]
      PLAN: Continue moving forward through the one-block opening in the stone wall to reach the area behind it.
 30 | (4.3,0.0,3.8) yaw=-55 p=-10 | mv=0.28 | find_green_b:d1.2/f70 find_dark_oa:d3.1/f12* mine_magma_b:- bridge_lava_:d14.7 | {"forward":1,"sprint":1} [2/5]
 31 | (4.5,0.0,4.0) yaw=-55 p=-10 | mv=0.28 | find_green_b:d1.1/f83 find_dark_oa:d2.8/f13* mine_magma_b:- bridge_lava_:d14.5 | {"forward":1,"sprint":1} [3/5]
 32 | (4.8,0.0,4.2) yaw=-55 p=-10 | mv=0.28 | find_green_b:d1.1/f97 find_dark_oa:d2.6/f14* mine_magma_b:- bridge_lava_:d14.2 | {"forward":1,"sprint":1} [4/5]
 33 | (5.0,0.0,4.3) yaw=-55 p=-10 | mv=0.28 | find_green_b:d1.2/f111 find_dark_oa:d2.3/f16* mine_magma_b:- bridge_lava_:d14.0 | {"forward":1,"sprint":1} [5/5]
 34 | (5.2,0.0,4.5) yaw=-55 p=-10 | mv=0.28 | find_green_b:d1.3/f122 find_dark_oa:d2.1/f19* mine_magma_b:- bridge_lava_:d13.8 | {"forward":1,"sprint":1} [1/5]
      PLAN: Move forward through the one-block opening in the stone wall to enter the area behind it where the magma blocks should be.
 35 | (5.5,0.0,4.6) yaw=-55 p=-10 | mv=0.28 | find_green_b:d1.5/f131 find_dark_oa:d1.9/f22* mine_magma_b:- bridge_lava_:d13.5 | {"forward":1,"sprint":1} [2/5]
 36 | (5.7,0.0,4.8) yaw=-55 p=-10 | mv=0.28 | find_green_b:d1.7/f138 find_dark_oa:d1.7/f26* mine_magma_b:- bridge_lava_:d13.3 | {"forward":1,"sprint":1} [3/5]
 37 | (5.9,0.0,5.0) yaw=-55 p=-10 | mv=0.28 | find_green_b:d1.9/f144 find_dark_oa:d1.5/f33 mine_magma_b:- bridge_lava_:d13.1 | {"forward":1,"sprint":1} [4/5]
 38 | (6.1,0.0,5.1) yaw=-55 p=-10 | mv=0.28 | find_green_b:d2.1/f148 find_dark_oa:d1.3/f43 mine_magma_b:- bridge_lava_:d12.9 | {"forward":1,"sprint":1} [5/5]
 39 | (6.2,0.0,5.3) yaw=-55 p=-10 | mv=0.17 | find_green_b:d2.2/f152 find_dark_oa:d1.3/f54 mine_magma_b:- bridge_lava_:d12.8 | {"forward":1,"sprint":1} [1/5]
      PLAN: Continue moving forward through the passage to exit the wall and reach the area with magma blocks.
 40 | (6.2,0.0,5.4) yaw=-55 p=-10 | mv=0.14 | find_green_b:d2.2/f156 find_dark_oa:d1.3/f63 mine_magma_b:- bridge_lava_:d12.8 | {"forward":1,"sprint":1} [2/5]
 41 | (6.2,0.0,5.6) yaw=-55 p=-10 | mv=0.13 | find_green_b:d2.3/f159 find_dark_oa:d1.4/f70 mine_magma_b:- bridge_lava_:d12.8 | {"forward":1,"sprint":1} [3/5]
 42 | (6.2,0.0,5.7) yaw=-55 p=-10 | mv=0.13 | find_green_b:d2.3/f162 find_dark_oa:d1.5/f76 mine_magma_b:- bridge_lava_:d12.8 | {"forward":1,"sprint":1} [4/5]
 43 | (6.2,0.0,5.8) yaw=-55 p=-10 | mv=0.13 | find_green_b:d2.3/f165 find_dark_oa:d1.5/f81 mine_magma_b:- bridge_lava_:d12.8 | {"forward":1,"sprint":1} [5/5]
 44 | (6.2,0.0,5.9) yaw=-55 p=-10 | mv=0.13 | find_green_b:d2.4/f168 find_dark_oa:d1.6/f85 mine_magma_b:- bridge_lava_:d12.8 | {"forward":1,"sprint":1} [1/5]
      PLAN: Continue moving forward to exit the narrow passage and reach the area with magma blocks.
 45 | (6.2,0.0,6.1) yaw=-55 p=-10 | mv=0.12 | find_green_b:d2.4/f171 find_dark_oa:d1.7/f88 mine_magma_b:- bridge_lava_:d12.8 | {"forward":1,"sprint":1} [2/5]
 46 | (6.2,0.0,6.2) yaw=-55 p=-10 | mv=0.12 | find_green_b:d2.5/f173 find_dark_oa:d1.8/f91 mine_magma_b:- bridge_lava_:d12.8 | {"forward":1,"sprint":1} [3/5]
 47 | (6.2,0.0,6.3) yaw=-55 p=-10 | mv=0.12 | find_green_b:d2.6/f176 find_dark_oa:d1.8/f94 mine_magma_b:- bridge_lava_:d12.8 | {"forward":1,"sprint":1} [4/5]
 48 | (6.2,0.0,6.4) yaw=-55 p=-10 | mv=0.12 | find_green_b:d2.6/f178 find_dark_oa:d1.9/f96 mine_magma_b:- bridge_lava_:d12.8 | {"forward":1,"sprint":1} [5/5]
 49 | (6.2,0.0,6.6) yaw=-55 p=-10 | mv=0.12 | find_green_b:d2.7/f180 find_dark_oa:d2.0/f98 mine_magma_b:- bridge_lava_:d12.8 | {"forward":1,"sprint":1} [1/5]
      PLAN: Continue moving forward to exit the passage and reach the magma block area.
 50 | (6.2,0.0,6.7) yaw=-55 p=-10 | mv=0.12 | find_green_b:d2.8/f177 find_dark_oa:d2.1/f100 mine_magma_b:- bridge_lava_:d12.8 | {"forward":1,"sprint":1} [2/5]
 51 | (6.2,0.0,6.8) yaw=-55 p=-10 | mv=0.12 | find_green_b:d2.9/f176 find_dark_oa:d2.2/f101 mine_magma_b:- bridge_lava_:d12.8 | {"forward":1,"sprint":1} [3/5]
 52 | (6.2,0.0,6.9) yaw=-55 p=-10 | mv=0.12 | find_green_b:d2.9/f174 find_dark_oa:d2.3/f103 mine_magma_b:- bridge_lava_:d12.8 | {"forward":1,"sprint":1} [4/5]
 53 | (6.2,0.0,7.1) yaw=-55 p=-10 | mv=0.12 | find_green_b:d3.0/f172 find_dark_oa:d2.4/f104 mine_magma_b:- bridge_lava_:d12.8 | {"forward":1,"sprint":1} [5/5]
 54 | (6.2,0.0,7.2) yaw=-55 p=-10 | mv=0.12 | find_green_b:d3.1/f170 find_dark_oa:d2.5/f105 mine_magma_b:- bridge_lava_:d12.8 | {"forward":1,"sprint":1} [1/5]
      PLAN: Continue moving forward to fully exit the passage and reach the area with magma blocks.
 55 | (6.2,0.0,7.3) yaw=-55 p=-10 | mv=0.12 | find_green_b:d3.2/f169 find_dark_oa:d2.6/f106 mine_magma_b:- bridge_lava_:d12.8 | {"forward":1,"sprint":1} [2/5]
 56 | (6.2,0.0,7.4) yaw=-55 p=-10 | mv=0.12 | find_green_b:d3.3/f167 find_dark_oa:d2.7/f107 mine_magma_b:- bridge_lava_:d12.8 | {"forward":1,"sprint":1} [3/5]
 57 | (6.2,0.0,7.6) yaw=-55 p=-10 | mv=0.12 | find_green_b:d3.4/f166 find_dark_oa:d2.9/f108 mine_magma_b:- bridge_lava_:d12.8 | {"forward":1,"sprint":1} [4/5]
 58 | (6.2,0.0,7.7) yaw=-55 p=-10 | mv=0.12 | find_green_b:d3.5/f164 find_dark_oa:d3.0/f108 mine_magma_b:- bridge_lava_:d12.8 | {"forward":1,"sprint":1} [5/5]
 59 | (6.2,0.0,7.7) yaw=-10 p=-10 | mv=0.07 | find_green_b:d3.5/f151 find_dark_oa:d3.0/f154 mine_magma_b:- bridge_lava_:d12.8 | {"camera":[0,45]} [1/1]
      PLAN: Look around to find the magma block deposit, then move toward it to mine the blocks.
 60 | (6.2,0.0,7.9) yaw=-10 p=-10 | mv=0.16 | find_green_b:d3.7/f153 find_dark_oa:d3.2/f155 mine_magma_b:- bridge_lava_:d12.8 | {"forward":1,"sprint":1} [1/5]
 61 | (6.3,0.0,8.1) yaw=-10 p=-10 | mv=0.22 | find_green_b:d3.9/f154 find_dark_oa:d3.4/f157 mine_magma_b:- bridge_lava_:d12.7 | {"forward":1,"sprint":1} [2/5]
 62 | (6.3,0.0,8.4) yaw=-10 p=-10 | mv=0.25 | find_green_b:d4.1/f156 find_dark_oa:d3.6/f158 mine_magma_b:- bridge_lava_:d12.7 | {"forward":1,"sprint":1} [3/5]
 63 | (6.3,0.0,8.6) yaw=-10 p=-10 | mv=0.26 | find_green_b:d4.3/f157 find_dark_oa:d3.8/f160 mine_magma_b:- bridge_lava_:d12.7 | {"forward":1,"sprint":1} [4/5]
 64 | (6.4,0.0,8.9) yaw=-10 p=-10 | mv=0.27 | find_green_b:d4.6/f158 find_dark_oa:d4.1/f161 mine_magma_b:- bridge_lava_:d12.6 | {"forward":1,"sprint":1} [5/5]
 65 | (6.4,0.0,9.0) yaw=-55 p=-10 | mv=0.15 | find_green_b:d4.7/f156 find_dark_oa:d4.2/f117 mine_magma_b:- bridge_lava_:d12.6 | {"camera":[0,-45]} [1/1]
      PLAN: Turn left and move forward to search for the magma block deposit in the area.
 66 | (6.5,0.0,9.2) yaw=-55 p=-10 | mv=0.19 | find_green_b:d4.9/f156 find_dark_oa:d4.3/f119 mine_magma_b:- bridge_lava_:d12.5 | {"forward":1,"sprint":1} [1/5]
 67 | (6.7,0.0,9.3) yaw=-55 p=-10 | mv=0.23 | find_green_b:d5.1/f157 find_dark_oa:d4.5/f121 mine_magma_b:- bridge_lava_:d12.3 | {"forward":1,"sprint":1} [2/5]
 68 | (6.9,0.0,9.5) yaw=-55 p=-10 | mv=0.25 | find_green_b:d5.4/f158 find_dark_oa:d4.6/f124 mine_magma_b:- bridge_lava_:d12.1 | {"forward":1,"sprint":1} [3/5]
 69 | (7.1,0.0,9.7) yaw=-55 p=-10 | mv=0.27 | find_green_b:d5.6/f159 find_dark_oa:d4.8/f126 mine_magma_b:- bridge_lava_:d11.9 | {"forward":1,"sprint":1} [4/5]
 70 | (7.3,0.0,9.8) yaw=-55 p=-10 | mv=0.27 | find_green_b:d5.9/f160 find_dark_oa:d4.9/f129 mine_magma_b:- bridge_lava_:d11.7 | {"forward":1,"sprint":1} [5/5]
 71 | (7.4,0.0,9.9) yaw=-55 p=20 | mv=0.15 | find_green_b:d6.0/f160 find_dark_oa:d5.0/f130 mine_magma_b:- bridge_lava_:d11.6 | {"camera":[30,0]} [1/1]
      PLAN: Look down and move forward to search for magma blocks on the ground or nearby lava area.
 72 | (7.6,0.0,10.0) yaw=-55 p=20 | mv=0.21 | find_green_b:d6.2/f161 find_dark_oa:d5.2/f132 mine_magma_b:- bridge_lava_:d11.4 | {"forward":1,"sprint":1} [1/5]
 73 | (7.8,0.0,10.2) yaw=-55 p=20 | mv=0.24 | find_green_b:d6.4/f161 find_dark_oa:d5.3/f134 mine_magma_b:- bridge_lava_:d11.2 | {"forward":1,"sprint":1} [2/5]
 74 | (8.0,0.0,10.3) yaw=-55 p=20 | mv=0.26 | find_green_b:d6.7/f162 find_dark_oa:d5.5/f136 mine_magma_b:- bridge_lava_:d11.1 | {"forward":1,"sprint":1} [3/5]
 75 | (8.2,0.0,10.5) yaw=-55 p=20 | mv=0.27 | find_green_b:d6.9/f163 find_dark_oa:d5.7/f138 mine_magma_b:- bridge_lava_:d10.9 | {"forward":1,"sprint":1} [4/5]
 76 | (8.5,0.0,10.6) yaw=-55 p=20 | mv=0.27 | find_green_b:d7.2/f163 find_dark_oa:d5.9/f140 mine_magma_b:- bridge_lava_:d10.7 | {"forward":1,"sprint":1} [5/5]
 77 | (8.6,0.0,10.7) yaw=-85 p=20 | mv=0.15 | find_green_b:d7.3/f134 find_dark_oa:d6.0/f111 mine_magma_b:- bridge_lava_:d10.5 | {"camera":[0,-30]} [1/1]
      PLAN: Turn left to face the lava area and look for the magma block deposit near the lava.
 78 | (8.8,0.0,10.8) yaw=-85 p=20 | mv=0.20 | find_green_b:d7.5/f135 find_dark_oa:d6.1/f112 mine_magma_b:- bridge_lava_:d10.4 | {"forward":1,"sprint":1} [1/5]
 79 | (9.0,0.0,10.8) yaw=-85 p=20 | mv=0.24 | find_green_b:d7.7/f136 find_dark_oa:d6.2/f114 mine_magma_b:- bridge_lava_:d10.1 | {"forward":1,"sprint":1} [2/5]
 80 | (9.3,0.0,10.9) yaw=-85 p=20 | mv=0.26 | find_green_b:d7.9/f137 find_dark_oa:d6.4/f116 mine_magma_b:- bridge_lava_:d9.9 | {"forward":1,"sprint":1} [3/5]
 81 | (9.5,0.0,10.9) yaw=-85 p=20 | mv=0.27 | find_green_b:d8.1/f138 find_dark_oa:d6.5/f118 mine_magma_b:- bridge_lava_:d9.6 | {"forward":1,"sprint":1} [4/5]
 82 | (9.8,0.0,10.9) yaw=-85 p=20 | mv=0.27 | find_green_b:d8.3/f140 find_dark_oa:d6.6/f120 mine_magma_b:- bridge_lava_:d9.4 | {"forward":1,"sprint":1} [5/5]
 83 | (10.0,0.0,10.9) yaw=-100 p=20 | mv=0.15 | find_green_b:d8.4/f125 find_dark_oa:d6.7/f107 mine_magma_b:- bridge_lava_:d9.2 | {"camera":[0,-15]} [1/1]
      PLAN: Move closer to the magma blocks next to the lava, then mine them with the diamond pickaxe.
 84 | (10.2,0.0,10.9) yaw=-100 p=20 | mv=0.21 | find_green_b:d8.5/f126 find_dark_oa:d6.8/f108 mine_magma_b:- bridge_lava_:d9.0 | {"forward":1,"sprint":1} [1/3]
 85 | (10.4,0.0,10.9) yaw=-100 p=20 | mv=0.24 | find_green_b:d8.7/f127 find_dark_oa:d6.9/f110 mine_magma_b:- bridge_lava_:d8.8 | {"forward":1,"sprint":1} [2/3]
 86 | (10.7,0.0,10.8) yaw=-100 p=20 | mv=0.26 | find_green_b:d8.9/f129 find_dark_oa:d7.0/f112 mine_magma_b:- bridge_lava_:d8.5 | {"forward":1,"sprint":1} [3/3]
 87 | (10.9,0.0,10.8) yaw=-100 p=20 | mv=0.27 | find_green_b:d9.0/f130 find_dark_oa:d7.1/f114 mine_magma_b:- bridge_lava_:d8.3 | {"forward":1} [1/2]
      PLAN: Move closer to the magma blocks and start mining them with the diamond pickaxe.
 88 | (11.2,0.0,10.8) yaw=-100 p=20 | mv=0.27 | find_green_b:d9.2/f131 find_dark_oa:d7.2/f116 mine_magma_b:- bridge_lava_:d8.0 | {"forward":1} [2/2]
 89 | (11.3,0.0,10.7) yaw=-100 p=20 | mv=0.15 | find_green_b:d9.3/f132 find_dark_oa:d7.3/f117 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [1/5]
 90 | (11.4,0.0,10.7) yaw=-100 p=20 | mv=0.08 | find_green_b:d9.4/f132 find_dark_oa:d7.3/f118 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [2/5]
 91 | (11.5,0.0,10.7) yaw=-100 p=20 | mv=0.04 | find_green_b:d9.4/f133 find_dark_oa:d7.3/f118 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [3/5]
 92 | (11.5,0.0,10.7) yaw=-100 p=20 | mv=0.02 | find_green_b:d9.4/f133 find_dark_oa:d7.3/f118 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [4/5]
 93 | (11.5,0.0,10.7) yaw=-100 p=20 | mv=0.01 | find_green_b:d9.4/f133 find_dark_oa:d7.3/f118 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [5/5]
 94 | (11.5,0.0,10.7) yaw=-100 p=30 | mv=0.01 | find_green_b:d9.4/f133 find_dark_oa:d7.3/f118 mine_magma_b:- bridge_lava_:d7.7 | {"camera":[10,0]} [1/1]
      PLAN: Look down at the magma blocks and continue mining them with the diamond pickaxe.
 95 | (11.5,0.0,10.7) yaw=-100 p=30 | mv=0.00 | find_green_b:d9.4/f133 find_dark_oa:d7.3/f118 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [1/10]
 96 | (11.5,0.0,10.7) yaw=-100 p=30 | mv=0.00 | find_green_b:d9.4/f133 find_dark_oa:d7.3/f118 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [2/10]
 97 | (11.5,0.0,10.7) yaw=-100 p=30 | mv=0.00 | find_green_b:d9.4/f133 find_dark_oa:d7.3/f118 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [3/10]
 98 | (11.5,0.0,10.7) yaw=-100 p=30 | mv=0.00 | find_green_b:d9.4/f133 find_dark_oa:d7.3/f118 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [4/10]
 99 | (11.5,0.0,10.7) yaw=-100 p=30 | mv=0.00 | find_green_b:d9.4/f133 find_dark_oa:d7.3/f118 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [5/10]
100 | (11.5,0.0,10.7) yaw=-100 p=30 | mv=0.00 | find_green_b:d9.4/f133 find_dark_oa:d7.3/f118 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [6/10]
101 | (11.5,0.0,10.7) yaw=-100 p=30 | mv=0.00 | find_green_b:d9.4/f133 find_dark_oa:d7.3/f118 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [7/10]
102 | (11.5,0.0,10.7) yaw=-100 p=30 | mv=0.00 | find_green_b:d9.4/f133 find_dark_oa:d7.3/f118 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [8/10]
103 | (11.5,0.0,10.7) yaw=-100 p=30 | mv=0.00 | find_green_b:d9.4/f133 find_dark_oa:d7.3/f118 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [9/10]
104 | (11.5,0.0,10.7) yaw=-100 p=30 | mv=0.00 | find_green_b:d9.4/f133 find_dark_oa:d7.3/f118 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [10/10]
105 | (11.5,0.0,10.7) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.4/f113 find_dark_oa:d7.3/f98 mine_magma_b:- bridge_lava_:d7.7 | {"camera":[0,-20]} [1/1]
      PLAN: Turn left to face the magma blocks next to the lava and mine them with the diamond pickaxe.
106 | (11.5,0.0,10.7) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.4/f113 find_dark_oa:d7.3/f98 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [1/10]
107 | (11.5,0.0,10.7) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.4/f113 find_dark_oa:d7.3/f98 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [2/10]
108 | (11.5,0.0,10.7) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.4/f113 find_dark_oa:d7.3/f98 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [3/10]
109 | (11.5,0.0,10.7) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.4/f113 find_dark_oa:d7.3/f98 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [4/10]
110 | (11.5,0.0,10.7) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.4/f113 find_dark_oa:d7.3/f98 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [5/10]
111 | (11.5,0.0,10.7) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.4/f113 find_dark_oa:d7.3/f98 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [6/10]
112 | (11.5,0.0,10.7) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.4/f113 find_dark_oa:d7.3/f98 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [7/10]
113 | (11.5,0.0,10.7) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.4/f113 find_dark_oa:d7.3/f98 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [8/10]
114 | (11.5,0.0,10.7) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.4/f113 find_dark_oa:d7.3/f98 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [9/10]
115 | (11.5,0.0,10.7) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.4/f113 find_dark_oa:d7.3/f98 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [10/10]
116 | (11.5,0.0,10.7) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.4/f113 find_dark_oa:d7.3/f98 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [1/10]
      PLAN: Continue mining the magma block with the diamond pickaxe.
117 | (11.5,0.0,10.7) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.4/f113 find_dark_oa:d7.3/f98 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [2/10]
118 | (11.5,0.0,10.7) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.4/f113 find_dark_oa:d7.3/f98 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [3/10]
119 | (11.5,0.0,10.7) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.4/f113 find_dark_oa:d7.3/f98 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [4/10]
120 | (11.5,0.0,10.7) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.4/f113 find_dark_oa:d7.3/f98 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [5/10]
121 | (11.5,0.0,10.7) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.4/f113 find_dark_oa:d7.3/f98 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [6/10]
122 | (11.5,0.0,10.7) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.4/f113 find_dark_oa:d7.3/f98 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [7/10]
123 | (11.5,0.0,10.7) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.4/f113 find_dark_oa:d7.3/f98 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [8/10]
124 | (11.5,0.0,10.7) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.4/f113 find_dark_oa:d7.3/f98 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [9/10]
125 | (11.5,0.0,10.7) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.4/f113 find_dark_oa:d7.3/f98 mine_magma_b:- bridge_lava_:d7.7 | {"attack":1} [10/10]
126 | (11.5,0.0,10.6) yaw=-120 p=30 | mv=0.10 | find_green_b:d9.3/f113 find_dark_oa:d7.2/f98 mine_magma_b:- bridge_lava_:d7.7 | {"left":1} [1/2]
      PLAN: Strafe left to get closer to the magma block and continue mining it with the diamond pickaxe.
127 | (11.4,0.0,10.5) yaw=-120 p=30 | mv=0.15 | find_green_b:d9.2/f113 find_dark_oa:d7.1/f99 mine_magma_b:- bridge_lava_:d7.8 | {"left":1} [2/2]
128 | (11.4,0.0,10.4) yaw=-120 p=30 | mv=0.08 | find_green_b:d9.1/f114 find_dark_oa:d7.0/f99 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [1/10]
129 | (11.3,0.0,10.4) yaw=-120 p=30 | mv=0.05 | find_green_b:d9.1/f114 find_dark_oa:d7.0/f99 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [2/10]
130 | (11.3,0.0,10.4) yaw=-120 p=30 | mv=0.02 | find_green_b:d9.1/f114 find_dark_oa:d6.9/f99 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [3/10]
131 | (11.3,0.0,10.3) yaw=-120 p=30 | mv=0.01 | find_green_b:d9.1/f114 find_dark_oa:d6.9/f99 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [4/10]
132 | (11.3,0.0,10.3) yaw=-120 p=30 | mv=0.01 | find_green_b:d9.0/f114 find_dark_oa:d6.9/f99 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [5/10]
133 | (11.3,0.0,10.3) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.0/f114 find_dark_oa:d6.9/f99 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [6/10]
134 | (11.3,0.0,10.3) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.0/f114 find_dark_oa:d6.9/f99 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [7/10]
135 | (11.3,0.0,10.3) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.0/f114 find_dark_oa:d6.9/f99 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [8/10]
136 | (11.3,0.0,10.3) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.0/f114 find_dark_oa:d6.9/f99 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [9/10]
137 | (11.3,0.0,10.3) yaw=-120 p=30 | mv=0.00 | find_green_b:d9.0/f114 find_dark_oa:d6.9/f99 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [10/10]
138 | (11.3,0.0,10.3) yaw=-130 p=30 | mv=0.00 | find_green_b:d9.0/f104 find_dark_oa:d6.9/f89 mine_magma_b:- bridge_lava_:d7.8 | {"camera":[0,-10]} [1/1]
      PLAN: Aim directly at the magma block and continue mining it with the diamond pickaxe.
139 | (11.3,0.0,10.3) yaw=-130 p=30 | mv=0.00 | find_green_b:d9.0/f104 find_dark_oa:d6.9/f89 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [1/10]
140 | (11.3,0.0,10.3) yaw=-130 p=30 | mv=0.00 | find_green_b:d9.0/f104 find_dark_oa:d6.9/f89 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [2/10]
141 | (11.3,0.0,10.3) yaw=-130 p=30 | mv=0.00 | find_green_b:d9.0/f104 find_dark_oa:d6.9/f89 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [3/10]
142 | (11.3,0.0,10.3) yaw=-130 p=30 | mv=0.00 | find_green_b:d9.0/f104 find_dark_oa:d6.9/f89 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [4/10]
143 | (11.3,0.0,10.3) yaw=-130 p=30 | mv=0.00 | find_green_b:d9.0/f104 find_dark_oa:d6.9/f89 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [5/10]
144 | (11.3,0.0,10.3) yaw=-130 p=30 | mv=0.00 | find_green_b:d9.0/f104 find_dark_oa:d6.9/f89 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [6/10]
145 | (11.3,0.0,10.3) yaw=-130 p=30 | mv=0.00 | find_green_b:d9.0/f104 find_dark_oa:d6.9/f89 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [7/10]
146 | (11.3,0.0,10.3) yaw=-130 p=30 | mv=0.00 | find_green_b:d9.0/f104 find_dark_oa:d6.9/f89 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [8/10]
147 | (11.3,0.0,10.3) yaw=-130 p=30 | mv=0.00 | find_green_b:d9.0/f104 find_dark_oa:d6.9/f89 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [9/10]
148 | (11.3,0.0,10.3) yaw=-130 p=30 | mv=0.00 | find_green_b:d9.0/f104 find_dark_oa:d6.9/f89 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [10/10]
149 | (11.3,0.0,10.3) yaw=-130 p=25 | mv=0.00 | find_green_b:d9.0/f104 find_dark_oa:d6.9/f89 mine_magma_b:- bridge_lava_:d7.8 | {"camera":[-5,0]} [1/1]
      PLAN: Look up slightly to aim at the magma block and continue mining it with the diamond pickaxe.
150 | (11.3,0.0,10.3) yaw=-130 p=25 | mv=0.00 | find_green_b:d9.0/f104 find_dark_oa:d6.9/f89 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [1/10]
151 | (11.3,0.0,10.3) yaw=-130 p=25 | mv=0.00 | find_green_b:d9.0/f104 find_dark_oa:d6.9/f89 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [2/10]
152 | (11.3,0.0,10.3) yaw=-130 p=25 | mv=0.00 | find_green_b:d9.0/f104 find_dark_oa:d6.9/f89 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [3/10]
153 | (11.3,0.0,10.3) yaw=-130 p=25 | mv=0.00 | find_green_b:d9.0/f104 find_dark_oa:d6.9/f89 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [4/10]
154 | (11.3,0.0,10.3) yaw=-130 p=25 | mv=0.00 | find_green_b:d9.0/f104 find_dark_oa:d6.9/f89 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [5/10]
155 | (11.3,0.0,10.3) yaw=-130 p=25 | mv=0.00 | find_green_b:d9.0/f104 find_dark_oa:d6.9/f89 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [6/10]
156 | (11.3,0.0,10.3) yaw=-130 p=25 | mv=0.00 | find_green_b:d9.0/f104 find_dark_oa:d6.9/f89 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [7/10]
157 | (11.3,0.0,10.3) yaw=-130 p=25 | mv=0.00 | find_green_b:d9.0/f104 find_dark_oa:d6.9/f89 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [8/10]
158 | (11.3,0.0,10.3) yaw=-130 p=25 | mv=0.00 | find_green_b:d9.0/f104 find_dark_oa:d6.9/f89 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [9/10]
159 | (11.3,0.0,10.3) yaw=-130 p=25 | mv=0.00 | find_green_b:d9.0/f104 find_dark_oa:d6.9/f89 mine_magma_b:- bridge_lava_:d7.8 | {"attack":1} [10/10]
160 | (11.4,0.0,10.3) yaw=-130 p=25 | mv=0.10 | find_green_b:d9.1/f104 find_dark_oa:d6.9/f90 mine_magma_b:- bridge_lava_:d7.7 | {"forward":1} [1/2]
      PLAN: Move closer to the magma blocks and continue mining them with the diamond pickaxe.
161 | (11.5,0.0,10.2) yaw=-130 p=25 | mv=0.15 | find_green_b:d9.1/f105 find_dark_oa:d6.9/f91 mine_magma_b:- bridge_lava_:d7.6 | {"forward":1} [2/2]
162 | (11.6,0.0,10.1) yaw=-130 p=25 | mv=0.08 | find_green_b:d9.1/f106 find_dark_oa:d6.9/f92 mine_magma_b:- bridge_lava_:d7.5 | {"attack":1} [1/10]
163 | (11.6,0.0,10.1) yaw=-130 p=25 | mv=0.05 | find_green_b:d9.1/f106 find_dark_oa:d6.9/f92 mine_magma_b:- bridge_lava_:d7.5 | {"attack":1} [2/10]
164 | (11.6,0.0,10.1) yaw=-130 p=25 | mv=0.02 | find_green_b:d9.1/f106 find_dark_oa:d6.9/f92 mine_magma_b:- bridge_lava_:d7.5 | {"attack":1} [3/10]
165 | (11.6,0.0,10.1) yaw=-130 p=25 | mv=0.01 | find_green_b:d9.2/f106 find_dark_oa:d6.9/f92 mine_magma_b:- bridge_lava_:d7.5 | {"attack":1} [4/10]
166 | (11.6,0.0,10.1) yaw=-130 p=25 | mv=0.01 | find_green_b:d9.2/f106 find_dark_oa:d6.9/f92 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [5/10]
167 | (11.6,0.0,10.1) yaw=-130 p=25 | mv=0.00 | find_green_b:d9.2/f106 find_dark_oa:d6.9/f92 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [6/10]
168 | (11.6,0.0,10.1) yaw=-130 p=25 | mv=0.00 | find_green_b:d9.2/f106 find_dark_oa:d6.9/f92 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [7/10]
169 | (11.6,0.0,10.1) yaw=-130 p=25 | mv=0.00 | find_green_b:d9.2/f106 find_dark_oa:d6.9/f92 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [8/10]
170 | (11.6,0.0,10.1) yaw=-130 p=25 | mv=0.00 | find_green_b:d9.2/f106 find_dark_oa:d6.9/f92 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [9/10]
171 | (11.6,0.0,10.1) yaw=-130 p=25 | mv=0.00 | find_green_b:d9.2/f106 find_dark_oa:d6.9/f92 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [10/10]
172 | (11.6,0.0,10.1) yaw=-135 p=25 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"camera":[0,-5]} [1/1]
      PLAN: Aim directly at the magma block and continue mining it with the diamond pickaxe.
173 | (11.6,0.0,10.1) yaw=-135 p=25 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [1/10]
174 | (11.6,0.0,10.1) yaw=-135 p=25 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [2/10]
175 | (11.6,0.0,10.1) yaw=-135 p=25 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [3/10]
176 | (11.6,0.0,10.1) yaw=-135 p=25 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [4/10]
177 | (11.6,0.0,10.1) yaw=-135 p=25 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [5/10]
178 | (11.6,0.0,10.1) yaw=-135 p=25 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [6/10]
179 | (11.6,0.0,10.1) yaw=-135 p=25 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [7/10]
180 | (11.6,0.0,10.1) yaw=-135 p=25 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [8/10]
181 | (11.6,0.0,10.1) yaw=-135 p=25 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [9/10]
182 | (11.6,0.0,10.1) yaw=-135 p=25 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [10/10]
183 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"camera":[-10,0]} [1/1]
      PLAN: Look down at the magma blocks and continue mining them with the diamond pickaxe.
184 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [1/10]
185 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [2/10]
186 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [3/10]
187 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [4/10]
188 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [5/10]
189 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [6/10]
190 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [7/10]
191 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [8/10]
192 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [9/10]
193 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [10/10]
194 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"hotbar.2":1} [1/1]
      PLAN: Select the diamond pickaxe from the hotbar (slot 2) and continue mining the magma blocks.
195 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [1/10]
196 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [2/10]
197 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [3/10]
198 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [4/10]
199 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [5/10]
200 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [6/10]
201 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [7/10]
202 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [8/10]
203 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [9/10]
204 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [10/10]
205 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"hotbar.3":1} [1/1]
      PLAN: Try selecting slot 3 for the diamond pickaxe and continue mining the magma blocks.
206 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [1/10]
207 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [2/10]
208 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [3/10]
209 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [4/10]
210 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [5/10]
211 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [6/10]
212 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [7/10]
213 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [8/10]
214 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [9/10]
215 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"attack":1} [10/10]
216 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"inventory":1} [1/1]
      PLAN: Open the inventory to find the diamond pickaxe location.
217 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"inventory":1} [1/1]
      PLAN: Close the inventory and craft a stone pickaxe using the cobblestone I have.
218 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"inventory":1} [1/1]
      PLAN: Close the inventory and look around for wood/trees to gather for crafting sticks and a pickaxe.
219 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"camera":[0,30]} [1/1]
220 | (11.6,0.0,10.1) yaw=-135 p=15 | mv=0.00 | find_green_b:d9.2/f101 find_dark_oa:d6.9/f87 mine_magma_b:- bridge_lava_:d7.4 | {"inventory":1} [1/1]
      PLAN: Close the inventory to return to the game view.
221 | (11.6,0.0,10.1) yaw=-90 p=15 | mv=0.00 | find_green_b:d9.2/f146 find_dark_oa:d6.9/f132 mine_magma_b:- bridge_lava_:d7.4 | {"camera":[0,45]} [1/1]
      PLAN: Turn right and move toward the trees to gather wood for crafting a pickaxe.
222 | (11.8,0.0,10.1) yaw=-90 p=15 | mv=0.13 | find_green_b:d9.3/f147 find_dark_oa:d7.0/f133 mine_magma_b:- bridge_lava_:d7.3 | {"forward":1,"sprint":1} [1/10]
223 | (12.0,0.0,10.1) yaw=-90 p=15 | mv=0.20 | find_green_b:d9.4/f148 find_dark_oa:d7.2/f134 mine_magma_b:- bridge_lava_:d7.1 | {"forward":1,"sprint":1} [2/10]
224 | (12.2,0.0,10.1) yaw=-90 p=15 | mv=0.23 | find_green_b:d9.6/f148 find_dark_oa:d7.3/f136 mine_magma_b:- bridge_lava_:d6.9 | {"forward":1,"sprint":1} [3/10]
225 | (12.4,0.0,10.1) yaw=-90 p=15 | mv=0.26 | find_green_b:d9.8/f149 find_dark_oa:d7.5/f137 mine_magma_b:- bridge_lava_:d6.6 | {"forward":1,"sprint":1} [4/10]
226 | (12.7,0.0,10.1) yaw=-90 p=15 | mv=0.27 | find_green_b:d10.1/f150 find_dark_oa:d7.7/f138 mine_magma_b:- bridge_lava_:d6.4 | {"forward":1,"sprint":1} [5/10]
227 | (13.0,0.0,10.1) yaw=-90 p=15 | mv=0.27 | find_green_b:d10.3/f151 find_dark_oa:d7.9/f140 mine_magma_b:- bridge_lava_:d6.1 | {"forward":1,"sprint":1} [6/10]
228 | (13.3,0.0,10.1) yaw=-90 p=15 | mv=0.28 | find_green_b:d10.6/f151 find_dark_oa:d8.1/f141 mine_magma_b:- bridge_lava_:d5.8 | {"forward":1,"sprint":1} [7/10]
229 | (13.5,0.0,10.1) yaw=-90 p=15 | mv=0.28 | find_green_b:d10.8/f152 find_dark_oa:d8.3/f142 mine_magma_b:- bridge_lava_:d5.6 | {"forward":1,"sprint":1} [8/10]
230 | (13.8,0.0,10.1) yaw=-90 p=15 | mv=0.28 | find_green_b:d11.0/f153 find_dark_oa:d8.6/f143 mine_magma_b:- bridge_lava_:d5.3 | {"forward":1,"sprint":1} [9/10]
231 | (14.1,-0.1,10.1) yaw=-90 p=15 | mv=0.28 | find_green_b:d11.3/f153 find_dark_oa:d8.8/f145 mine_magma_b:- bridge_lava_:d5.0 | {"forward":1,"sprint":1} [10/10]
232 | (14.2,-0.2,10.1) yaw=-90 p=15 | mv=0.10 | find_green_b:d11.4/f154 find_dark_oa:d8.9/f145 mine_magma_b:- bridge_lava_:d4.9 | {"forward":1,"sprint":1} [1/10]
      PLAN: Continue moving toward the trees to gather wood for crafting.
233 | (14.2,-0.5,10.1) yaw=-90 p=15 | mv=0.00 | find_green_b:d11.4/f154 find_dark_oa:d8.9/f145 mine_magma_b:- bridge_lava_:d4.9 | {"forward":1,"sprint":1} [2/10]
234 | (14.2,-0.8,10.1) yaw=-90 p=15 | mv=0.00 | find_green_b:d11.4/f154 find_dark_oa:d9.0/f145 mine_magma_b:- bridge_lava_:d4.9 | {"forward":1,"sprint":1} [3/10]
235 | (14.2,-1.0,10.1) yaw=-90 p=15 | mv=0.00 | find_green_b:d11.4/f154 find_dark_oa:d9.0/f145 mine_magma_b:- bridge_lava_:d4.9 | {"forward":1,"sprint":1} [4/10]
236 | (14.2,-1.0,10.1) yaw=-90 p=15 | mv=0.00 | find_green_b:d11.4/f154 find_dark_oa:d9.0/f145 mine_magma_b:- bridge_lava_:d4.9 | {"forward":1,"sprint":1} [5/10]
237 | (14.2,-1.0,10.1) yaw=-90 p=15 | mv=0.00 | find_green_b:d11.4/f154 find_dark_oa:d9.0/f145 mine_magma_b:- bridge_lava_:d4.9 | {"forward":1,"sprint":1} [6/10]
238 | (14.2,-1.0,10.1) yaw=-90 p=15 | mv=0.00 | find_green_b:d11.4/f154 find_dark_oa:d9.0/f145 mine_magma_b:- bridge_lava_:d4.9 | {"forward":1,"sprint":1} [7/10]
239 | (14.2,-1.0,10.1) yaw=-90 p=15 | mv=0.00 | find_green_b:d11.4/f154 find_dark_oa:d9.0/f145 mine_magma_b:- bridge_lava_:d4.9 | {"forward":1,"sprint":1} [8/10]
240 | (14.2,-1.0,10.1) yaw=-90 p=15 | mv=0.00 | find_green_b:d11.4/f154 find_dark_oa:d9.0/f145 mine_magma_b:- bridge_lava_:d4.9 | {"forward":1,"sprint":1} [9/10]
241 | (14.2,-1.0,10.1) yaw=-90 p=15 | mv=0.00 | find_green_b:d11.4/f154 find_dark_oa:d9.0/f145 mine_magma_b:- bridge_lava_:d4.9 | {"forward":1,"sprint":1} [10/10]
242 | (14.2,-1.0,10.1) yaw=-90 p=15 | mv=0.00 | find_green_b:d11.4/f154 find_dark_oa:d9.0/f145 mine_magma_b:- bridge_lava_:d4.9 | {"forward":1,"sprint":1} [1/10]
      PLAN: Continue moving toward the trees to gather wood for crafting a pickaxe.
243 | (14.2,-1.0,10.1) yaw=-90 p=15 | mv=0.00 | find_green_b:d11.4/f154 find_dark_oa:d9.0/f145 mine_magma_b:- bridge_lava_:d4.9 | {"forward":1,"sprint":1} [2/10]
244 | (14.2,-1.0,10.1) yaw=-90 p=15 | mv=0.00 | find_green_b:d11.4/f154 find_dark_oa:d9.0/f145 mine_magma_b:- bridge_lava_:d4.9 | {"forward":1,"sprint":1} [3/10]
245 | (14.2,-1.0,10.1) yaw=-90 p=15 | mv=0.00 | find_green_b:d11.4/f154 find_dark_oa:d9.0/f145 mine_magma_b:- bridge_lava_:d4.9 | {"forward":1,"sprint":1} [4/10]
246 | (14.2,-1.0,10.1) yaw=-90 p=15 | mv=0.00 | find_green_b:d11.4/f154 find_dark_oa:d9.0/f145 mine_magma_b:- bridge_lava_:d4.9 | {"forward":1,"sprint":1} [5/10]
247 | (14.2,-1.0,10.1) yaw=-90 p=15 | mv=0.00 | find_green_b:d11.4/f154 find_dark_oa:d9.0/f145 mine_magma_b:- bridge_lava_:d4.9 | {"forward":1,"sprint":1} [6/10]
248 | (14.2,-1.0,10.1) yaw=-90 p=15 | mv=0.00 | find_green_b:d11.4/f154 find_dark_oa:d9.0/f145 mine_magma_b:- bridge_lava_:d4.9 | {"forward":1,"sprint":1} [7/10]
249 | (14.2,-1.0,10.1) yaw=-90 p=15 | mv=0.00 | find_green_b:d11.4/f154 find_dark_oa:d9.0/f145 mine_magma_b:- bridge_lava_:d4.9 | {"forward":1,"sprint":1} [8/10]
250 | (14.2,-1.0,10.1) yaw=-90 p=15 | mv=0.00 | find_green_b:d11.4/f154 find_dark_oa:d9.0/f145 mine_magma_b:- bridge_lava_:d4.9 | {"forward":1,"sprint":1} [9/10]
251 | (14.2,-1.0,10.1) yaw=-90 p=15 | mv=0.01 | find_green_b:d11.4/f154 find_dark_oa:d9.0/f145 mine_magma_b:- bridge_lava_:d4.9 | {"forward":1,"sprint":1} [10/10]
252 | (14.2,-1.0,10.1) yaw=-90 p=15 | mv=0.02 | find_green_b:d11.4/f154 find_dark_oa:d9.0/f145 mine_magma_b:- bridge_lava_:d4.9 | {"back":1,"sprint":1} [1/5]
      PLAN: Back away from the lava and turn toward the trees to gather wood safely.
253 | (14.2,-1.0,10.1) yaw=-90 p=15 | mv=0.03 | find_green_b:d11.4/f153 find_dark_oa:d9.0/f145 mine_magma_b:- bridge_lava_:d5.0 | {"back":1,"sprint":1} [2/5]
254 | (14.1,-1.0,10.1) yaw=-90 p=15 | mv=0.03 | find_green_b:d11.4/f153 find_dark_oa:d9.0/f145 mine_magma_b:- bridge_lava_:d5.0 | {"back":1,"sprint":1} [3/5]
255 | (14.1,-1.0,10.1) yaw=-90 p=15 | mv=0.04 | find_green_b:d11.3/f153 find_dark_oa:d8.9/f144 mine_magma_b:- bridge_lava_:d5.0 | {"back":1,"sprint":1} [4/5]
256 | (14.0,-1.0,10.1) yaw=-90 p=15 | mv=0.04 | find_green_b:d11.3/f153 find_dark_oa:d8.9/f144 mine_magma_b:- bridge_lava_:d5.1 | {"back":1,"sprint":1} [5/5]
257 | (14.0,-1.0,10.1) yaw=-70 p=15 | mv=0.02 | find_green_b:d11.3/f173 find_dark_oa:d8.9/f164 mine_magma_b:- bridge_lava_:d5.1 | {"camera":[0,20]} [1/1]
258 | (14.0,-1.0,10.1) yaw=-70 p=15 | mv=0.03 | find_green_b:d11.2/f173 find_dark_oa:d8.9/f164 mine_magma_b:- bridge_lava_:d5.1 | {"back":1,"sprint":1} [1/5]
      PLAN: Back away from the lava area and move toward the trees to gather wood.
259 | (14.0,-1.0,10.1) yaw=-70 p=15 | mv=0.03 | find_green_b:d11.2/f173 find_dark_oa:d8.8/f164 mine_magma_b:- bridge_lava_:d5.1 | {"back":1,"sprint":1} [2/5]
260 | (13.9,-1.0,10.1) yaw=-70 p=15 | mv=0.04 | find_green_b:d11.2/f173 find_dark_oa:d8.8/f164 mine_magma_b:- bridge_lava_:d5.2 | {"back":1,"sprint":1} [3/5]
261 | (13.9,-1.0,10.1) yaw=-70 p=15 | mv=0.02 | find_green_b:d11.2/f173 find_dark_oa:d8.8/f164 mine_magma_b:- bridge_lava_:d5.2 | {"back":1,"sprint":1} [4/5]
262 | (13.9,-1.0,10.0) yaw=-70 p=15 | mv=0.03 | find_green_b:d11.1/f173 find_dark_oa:d8.8/f164 mine_magma_b:- bridge_lava_:d5.2 | {"back":1,"sprint":1} [5/5]
263 | (13.9,-1.0,10.1) yaw=-70 p=15 | mv=0.01 | find_green_b:d11.1/f173 find_dark_oa:d8.8/f164 mine_magma_b:- bridge_lava_:d5.2 | {"forward":1,"sprint":1} [1/5]
264 | (13.9,-1.0,10.1) yaw=-70 p=15 | mv=0.02 | find_green_b:d11.2/f173 find_dark_oa:d8.8/f164 mine_magma_b:- bridge_lava_:d5.2 | {"forward":1,"sprint":1} [2/5]
265 | (13.9,-1.0,10.1) yaw=-70 p=15 | mv=0.03 | find_green_b:d11.2/f173 find_dark_oa:d8.8/f164 mine_magma_b:- bridge_lava_:d5.2 | {"forward":1,"sprint":1} [3/5]
266 | (14.0,-1.0,10.1) yaw=-70 p=15 | mv=0.03 | find_green_b:d11.2/f173 find_dark_oa:d8.9/f164 mine_magma_b:- bridge_lava_:d5.2 | {"forward":1,"sprint":1} [4/5]
267 | (14.0,-1.0,10.1) yaw=-70 p=15 | mv=0.04 | find_green_b:d11.3/f173 find_dark_oa:d8.9/f164 mine_magma_b:- bridge_lava_:d5.1 | {"forward":1,"sprint":1} [5/5]
268 | (14.0,-0.6,10.1) yaw=-70 p=15 | mv=0.00 | find_green_b:d11.2/f173 find_dark_oa:d8.8/f164 mine_magma_b:- bridge_lava_:d5.1 | {"back":1,"jump":1,"sprint":1} [1/5]
      PLAN: Jump backward to escape the lava and get to safety.
269 | (14.0,-0.3,10.1) yaw=-70 p=15 | mv=0.02 | find_green_b:d11.2/f173 find_dark_oa:d8.7/f164 mine_magma_b:- bridge_lava_:d5.1 | {"back":1,"jump":1,"sprint":1} [2/5]
270 | (13.9,-0.0,10.1) yaw=-70 p=15 | mv=0.04 | find_green_b:d11.2/f173 find_dark_oa:d8.7/f164 mine_magma_b:- bridge_lava_:d5.2 | {"back":1,"jump":1,"sprint":1} [3/5]
271 | (13.9,-0.1,10.1) yaw=-70 p=15 | mv=0.02 | find_green_b:d11.1/f173 find_dark_oa:d8.7/f164 mine_magma_b:- bridge_lava_:d5.2 | {"back":1,"jump":1,"sprint":1} [4/5]
272 | (13.9,-0.2,10.1) yaw=-70 p=15 | mv=0.04 | find_green_b:d11.1/f173 find_dark_oa:d8.6/f164 mine_magma_b:- bridge_lava_:d5.2 | {"back":1,"jump":1,"sprint":1} [5/5]
273 | (13.8,-0.3,10.0) yaw=-70 p=15 | mv=0.05 | find_green_b:d11.1/f173 find_dark_oa:d8.6/f164 mine_magma_b:- bridge_lava_:d5.3 | {"back":1,"jump":1,"sprint":1} [1/5]
      PLAN: Continue jumping backward to escape the lava area completely.
274 | (13.8,-0.6,10.0) yaw=-70 p=15 | mv=0.05 | find_green_b:d11.0/f173 find_dark_oa:d8.6/f164 mine_magma_b:- bridge_lava_:d5.3 | {"back":1,"jump":1,"sprint":1} [2/5]
275 | (13.8,-0.9,10.0) yaw=-70 p=15 | mv=0.03 | find_green_b:d11.0/f173 find_dark_oa:d8.6/f164 mine_magma_b:- bridge_lava_:d5.3 | {"back":1,"jump":1,"sprint":1} [3/5]
276 | (13.8,-1.0,10.0) yaw=-70 p=15 | mv=0.03 | find_green_b:d11.0/f173 find_dark_oa:d8.7/f164 mine_magma_b:- bridge_lava_:d5.3 | {"back":1,"jump":1,"sprint":1} [4/5]
277 | (13.8,-1.0,9.9) yaw=-70 p=15 | mv=0.02 | find_green_b:d11.0/f173 find_dark_oa:d8.6/f164 mine_magma_b:- bridge_lava_:d5.3 | {"back":1,"jump":1,"sprint":1} [5/5]
278 | (13.8,-1.0,9.9) yaw=-40 p=15 | mv=0.01 | find_green_b:d11.0/f157 find_dark_oa:d8.6/f166 mine_magma_b:- bridge_lava_:d5.3 | {"camera":[0,30]} [1/1]
      PLAN: Turn right and move toward the trees to gather wood for crafting a pickaxe.
279 | (13.8,-1.0,9.9) yaw=-40 p=15 | mv=0.02 | find_green_b:d11.0/f157 find_dark_oa:d8.6/f166 mine_magma_b:- bridge_lava_:d5.3 | {"forward":1,"sprint":1} [1/10]
280 | (13.8,-1.0,10.0) yaw=-40 p=15 | mv=0.03 | find_green_b:d11.1/f157 find_dark_oa:d8.7/f166 mine_magma_b:- bridge_lava_:d5.3 | {"forward":1,"sprint":1} [2/10]
281 | (13.9,-1.0,10.0) yaw=-40 p=15 | mv=0.03 | find_green_b:d11.1/f157 find_dark_oa:d8.7/f166 mine_magma_b:- bridge_lava_:d5.2 | {"forward":1,"sprint":1} [3/10]
282 | (13.9,-1.0,10.0) yaw=-40 p=15 | mv=0.03 | find_green_b:d11.1/f157 find_dark_oa:d8.7/f166 mine_magma_b:- bridge_lava_:d5.2 | {"forward":1,"sprint":1} [4/10]
283 | (13.9,-1.0,10.0) yaw=-40 p=15 | mv=0.03 | find_green_b:d11.1/f157 find_dark_oa:d8.8/f166 mine_magma_b:- bridge_lava_:d5.2 | {"forward":1,"sprint":1} [5/10]
284 | (13.9,-1.0,10.1) yaw=-40 p=15 | mv=0.04 | find_green_b:d11.2/f157 find_dark_oa:d8.8/f166 mine_magma_b:- bridge_lava_:d5.2 | {"forward":1,"sprint":1} [6/10]
285 | (13.9,-1.0,10.1) yaw=-40 p=15 | mv=0.04 | find_green_b:d11.2/f157 find_dark_oa:d8.8/f166 mine_magma_b:- bridge_lava_:d5.2 | {"forward":1,"sprint":1} [7/10]
286 | (14.0,-1.0,10.1) yaw=-40 p=15 | mv=0.04 | find_green_b:d11.2/f157 find_dark_oa:d8.9/f166 mine_magma_b:- bridge_lava_:d5.2 | {"forward":1,"sprint":1} [8/10]
287 | (14.0,-1.0,10.2) yaw=-40 p=15 | mv=0.04 | find_green_b:d11.3/f157 find_dark_oa:d8.9/f166 mine_magma_b:- bridge_lava_:d5.2 | {"forward":1,"sprint":1} [9/10]
288 | (14.0,-1.0,10.2) yaw=-40 p=15 | mv=0.04 | find_green_b:d11.3/f157 find_dark_oa:d8.9/f167 mine_magma_b:- bridge_lava_:d5.1 | {"forward":1,"sprint":1} [10/10]
289 | (14.0,-0.6,10.2) yaw=-40 p=15 | mv=0.00 | find_green_b:d11.3/f157 find_dark_oa:d8.9/f167 mine_magma_b:- bridge_lava_:d5.1 | {"back":1,"jump":1,"sprint":1} [1/5]
      PLAN: Jump backward to escape the fire and lava area completely.
290 | (14.0,-0.3,10.2) yaw=-40 p=15 | mv=0.02 | find_green_b:d11.3/f157 find_dark_oa:d8.8/f166 mine_magma_b:- bridge_lava_:d5.1 | {"back":1,"jump":1,"sprint":1} [2/5]
291 | (14.0,-0.0,10.1) yaw=-40 p=15 | mv=0.04 | find_green_b:d11.2/f157 find_dark_oa:d8.7/f166 mine_magma_b:- bridge_lava_:d5.2 | {"back":1,"jump":1,"sprint":1} [3/5]
292 | (14.0,-0.1,10.1) yaw=-40 p=15 | mv=0.02 | find_green_b:d11.2/f157 find_dark_oa:d8.7/f166 mine_magma_b:- bridge_lava_:d5.2 | {"back":1,"jump":1,"sprint":1} [4/5]
293 | (13.9,-0.2,10.1) yaw=-40 p=15 | mv=0.04 | find_green_b:d11.2/f157 find_dark_oa:d8.7/f166 mine_magma_b:- bridge_lava_:d5.2 | {"back":1,"jump":1,"sprint":1} [5/5]
294 | (13.9,-0.3,10.1) yaw=-40 p=15 | mv=0.05 | find_green_b:d11.1/f157 find_dark_oa:d8.7/f166 mine_magma_b:- bridge_lava_:d5.2 | {"back":1,"sprint":1} [1/5]
      PLAN: Continue moving backward away from the lava area to ensure I'm safe from fire.
295 | (13.9,-0.6,10.0) yaw=-40 p=15 | mv=0.07 | find_green_b:d11.1/f157 find_dark_oa:d8.6/f166 mine_magma_b:- bridge_lava_:d5.2 | {"back":1,"sprint":1} [2/5]
296 | (13.8,-0.9,9.9) yaw=-40 p=15 | mv=0.08 | find_green_b:d11.0/f157 find_dark_oa:d8.6/f166 mine_magma_b:- bridge_lava_:d5.3 | {"back":1,"sprint":1} [3/5]
297 | (13.8,-1.0,9.9) yaw=-40 p=15 | mv=0.07 | find_green_b:d11.0/f156 find_dark_oa:d8.6/f166 mine_magma_b:- bridge_lava_:d5.3 | {"back":1,"sprint":1} [4/5]
298 | (13.8,-1.0,9.8) yaw=-40 p=15 | mv=0.05 | find_green_b:d11.0/f156 find_dark_oa:d8.6/f165 mine_magma_b:- bridge_lava_:d5.3 | {"back":1,"sprint":1} [5/5]
299 | (13.8,-1.0,9.8) yaw=-40 p=15 | mv=0.04 | find_green_b:d10.9/f156 find_dark_oa:d8.5/f165 mine_magma_b:- bridge_lava_:d5.3 | {"back":1,"sprint":1} [1/5]
      PLAN: Continue moving backward to ensure I'm completely away from the lava area.
300 | (13.8,-1.0,9.7) yaw=-40 p=15 | mv=0.03 | find_green_b:d10.9/f156 find_dark_oa:d8.5/f165 mine_magma_b:- bridge_lava_:d5.3 | None [None/None]