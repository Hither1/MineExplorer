# RESEARCH_LOG

## Now (2026-08-27 02:3x)

- **ALL CAMPAIGNS STOPPED by user order** ("先都停掉", executed 02:21-02:23 from a219):
  kill switch `outputs/.campaign-stop` (run_cell.sh exits before account/sandbox — remove
  the file to re-enable cells), mineexplorer container stopped, Minecraft JVMs 0, reaper
  stopped (flag + kill). Full mechanism and verification in RUN_LEDGER
  20260827-022200-g56l154-user-stop.
- **a218 (192.168.2.11), the campaign control host, has sshd DOWN** (verified from a219
  and by the sibling session; user side reports a218 掉线). Its leftover processes —
  chain_g56l154, the SIGSTOPped prolong launcher (pid 19205), the default-solo watcher —
  are INERT (the wm launcher drains against the kill switch; the chain then blocks
  forever on the frozen prolong launcher; any future watcher launch dies on the switch).
  When a218's sshd returns, finish the cleanup with one process-group kill each:
  `kill -- -$(ps -o pgid= -p $(pgrep -f chain_g56l154.sh) | tr -d ' ')` (CONT+KILL the
  stopped member too) and the same for `g56l_default_solo_after154`.
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
