# RESEARCH_LOG

## Now (2026-08-27 11:1x)

- **worldmodel v2 landed (cddc4a8)**, from the 77-scene autopsy (4 subagent tracks +
  direct transcript counts over all 80 workspaces / 1750 turns): face_pixel/approach
  pixel aiming (38/40 unmet mine hops never broke their target), goal_check.json with
  real enforcement (ABANDONED render + testing-refusal + keep-one-live), plan-identity
  guard (3rd identical no-progress plan refused -> forced induction), stale binding
  (no re-test, no evidence-less revival), endgame induction anchor (<=70 steps),
  spatial.md frame pointers. selftest 101/0.
- **User-approved plan**: smoke 0106 -> strict-7 v2 (7 scenes ONLY, low CONC, resource
  monitoring per user order) -> compare vs g56l strict-7 v1. Full-154 resume and
  rule-shape rendering stay user decisions.
- Sandbox restarted 10:59 (boot ~10 min: MineStudio copy on fuse-overlayfs), reap
  patch verified present after restart. Kill switch removed 11:09 after confirming no
  surviving campaign processes. Smoke g56m-smoke-worldmodel-codex-0106 launched 11:09
  with WM_BRAIN_DIR=<scratch> (brain write-path test). Monitors: cell log + a219
  load/mem/JVM/alive (alert thresholds 160 load / 100G / 12 JVMs).
- **Smoke PASSED on mechanisms** (11:45): 17 act + 6 induction, 0 failed/silent, all
  6 inductions wrote goal_check.json (final: 3 craft hops abandoned @284, focus
  mine_crafting_table), endgame anchor fired at 230, spatial.md carries frame
  pointers IN THE WILD (even for a retired false candidate), brain exported 3 docs.
  Score 0/4 (v1: 1/4) -- loss = pressed under the crafting table, attacks could not
  land (1 mine_block in 300 steps); GUI never opened because the mine hop gated it.
- **g56m strict-7: concurrency is NOT viable at tonight's ambient load** (box load
  71 -> 240 from other users; our slice stays 48 cores nice 10). The sandbox
  serialises create/reset; at CONC=4 the queue blew the 120s create timeout (0726,
  0182 dead 11:49-50 -- fix 708dc86: create timeout 600, MC_CREATE_TIMEOUT), then at
  load ~240 even 600s x3 reset attempts died (0306/0603/0726 second wave 12:17-25).
  Error results quarantined under outputs/g56m-failed-quarantine/. **Serial tail
  driver armed** (scratchpad/serial_tail.sh -> outputs/log-g56m-serial-tail.txt):
  waits for in-flight evals to drain, quarantines error schemas, clean-restarts the
  sandbox when sessions>2, then runs every missing scene at CONC=1. The smoke (one
  cell, load 130-180) worked end-to-end, so serial is the reliable regime tonight.
  4 cells (0311/0482/0182/0763) still fighting when the driver was armed 12:29.

## Previous (2026-08-27 02:3x)

- **ALL CAMPAIGNS STOPPED by user order** ("先都停掉", executed 02:21-02:23 from a219):
  kill switch `outputs/.campaign-stop` (run_cell.sh exits before account/sandbox — remove
  the file to re-enable cells), mineexplorer container stopped, Minecraft JVMs 0, reaper
  stopped (flag + kill). Full mechanism and verification in RUN_LEDGER
  20260827-022200-g56l154-user-stop.
- **a218 leftovers CLEANED (02:5x, by the resident session — its Claude runs ON a218 and
  needed no sshd)**: chain_g56l154, both launchers (SIGCONT+kill for the frozen 19205),
  the default-solo watcher, and 3 draining eval cells all killed; the session's three
  monitors (health v4, hang guard, chain watch) stopped. a218's sshd being down remains
  a host issue for the user, but no campaign process survives anywhere.
- Background task (this session) parks tonight's error results into
  `outputs/g56l154-failed-20260827/` once the a218 launcher drains.
- **State at stop**: strict-7 wm 16/28, prolong 15/28, default never ran; g56l154 wm 50
  valid (creditable 93/181 = 51.4%, 4 scenes all-done), prolong 7 valid (frozen since
  20:35). Resume protocol: rm `outputs/.campaign-stop`, run
  `/datapool/data3/storage/ruihan/.podman/restart-mc-a219.sh`, relaunch the chain —
  scenes with a result.json skip as always.
- Sibling-topology correction (from mcu-agentbeats-e4, 08-27 00:2x): its dm4_plk1 runs
  on a214 (192.168.1.64), NOT a218/a219; nothing of its is live on a219. Protected set
  unchanged: dm4_plk1, ports 9071/9081, display :171, java envPort=12409.
- **Decisions for the user**: (1) whether/when to resume g56l154 at all, (2) default
  disposition (strict-7 column only is still the recommendation), (3) rule-derived
  requirement rendering into the checklist (info-condition change, all arms or none),
  (4) a218 recovery + leftover-process cleanup.

## Log

- 08-26: g56l strict-7: wm 16/28 (pre-fix), prolong 15/28; wm trajectory analysis →
  five loss mechanisms → fixes 4c03041 (see experiments/BEHAVIOR_g56l_worldmodel.md).
  CS1 session policy decided (payload wall measured; MCU default). dab9698 audit port.
  Default arm stopped once (contention), solo rerun queued. a219 JVM leak found and
  reaped (load 819→232). g56l154 launched 12:00.
- 08-27: user-ordered full stop 02:21-02:23 (kill switch + container stop + reaper off);
  a218 sshd down, its chain/launcher/watcher leftovers inert against the switch. Ledger
  20260827-022200. wm 154-set frozen at 50 valid (93/181 creditable).
- 08-27: four wm method fixes landed (2a18d8d, from the 77-scene post-fix analysis):
  GUI cursor regime (plan flush + tight caps + prompt line), binding goal-check triage,
  model-written executable skills (procedures/*.json), WM_BRAIN_DIR cross-episode brain.
  selftest 72/72; real-episode smoke pending sandbox restart.
