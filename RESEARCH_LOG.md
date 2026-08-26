# RESEARCH_LOG

## Now (2026-08-26 14:0x)

- **g56l154 campaign RUNNING** (since 12:00): worldmodel+prolong × all 154 4-hop scenes
  × 300 steps, hosted gpt-5.6-sol effort=low, one codex session per turn, parallel
  CONC=7+7. Detached (setsid): chain `scripts/chain_g56l154.sh`, log
  `outputs/log-g56l154-chain.txt`. ETA: wm ~Thu 06:00, prolong ~Thu 17:00.
- **default strict-7 solo rerun QUEUED**: watcher `scripts/g56l_default_solo_after154.sh`
  (setsid, log `outputs/log-g56l-default-solo-watch.txt`) fires when the chain log says
  "chain complete". First arm-3 attempt stopped 13:05 (contention-confounded, ledger).
- **a219 zombie-JVM reaper RUNNING** on 192.168.2.12 (setsid, 10-min rounds): mc_server
  close_env leaks busy JVMs; reaper kills `^java .*envPort=` with no ESTABLISHED conn on
  its port (tcp+tcp6) after 15-min grace. Log `outputs/log-a219-reaper.txt`; stop switch
  `outputs/a219-reaper.stop`. Root-cause server fix deferred to next sandbox downtime.
- **Monitors are harness background tasks and MAY BE RECLAIMED after a context
  compaction** (a sibling session lost its pre-compaction task tree exactly this way,
  ~13:08). After any compaction: re-arm three monitors — (1) tail chain154 log for
  `[chain154]|ABORT|Traceback`, (2) 2-hourly result counts, (3) 10-min health thresholds
  (local load>230/mem<40G; a219 load5>800/mem<100G/javas>35/reaper stale>25min/ssh
  down×2; cell-count-0 without a "finished" line). The setsid processes above survive
  compaction on their own.
- Sibling session (MCU-AgentBeats, socket 61207): dm4_plk1 on ports 9071/9081, display
  :171, local java envPort=12409, /var/tmp/mcu-codex-ruihan/dm4_plk1 — do not touch;
  it avoids a219 and my patterns.
- **Morning decisions for the user**: (1) default×154 disposition (measured ~2.4 min/step
  ⇒ 154 scenes infeasible hosted; recommend strict-7 column only), (2) rule-derived
  requirement rendering into the checklist (benchmark info-condition change, all arms or
  none), (3) full worldmodel-v2 numbers land inside g56l154 automatically (post-fix code).

## Log

- 08-26: g56l strict-7: wm 16/28 (pre-fix), prolong 15/28; wm trajectory analysis →
  five loss mechanisms → fixes 4c03041 (see experiments/BEHAVIOR_g56l_worldmodel.md).
  CS1 session policy decided (payload wall measured; MCU default). dab9698 audit port.
  Default arm stopped once (contention), solo rerun queued. a219 JVM leak found and
  reaped (load 819→232). g56l154 launched 12:00.
