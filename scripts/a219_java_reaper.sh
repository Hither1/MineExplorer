#!/usr/bin/env bash
# Reap zombie Minecraft JVMs on the a219 sandbox host.
#
# Why: mc_server's close_env pops the session and calls MinecraftSim.close(), returns
# "released" -- and the instance's java keeps running and BUSY (~2 cores each, the
# server tick loop spins without a client). Measured 2026-08-26 14:0x mid-g56l154:
# 53 java procs for 14 active cells, 40 of them zombies, a219 load 789/255 almost
# entirely ours. One zombie is born per finished episode, so a 154x2 campaign would
# accumulate ~300 by morning.
#
# Discriminator (validated 13 established / 40 not, matching the 14 live cells): an
# ACTIVE instance has an ESTABLISHED TCP connection on its --envPort (java is
# IPv6-dual-stack: /proc/<pid>/net/tcp6 carries it); a zombie's port has no peer.
# /list_sessions cannot be the source -- under campaign load the endpoint starves
# (>45s no response, measured).
#
# Safety:
#   - only javas older than GRACE (a booting JVM has no connection yet; creates take
#     1-4 min normally, the grace is 15);
#   - kills by PID (java + its xvfb-run wrapper tree), never by port pattern -- freed
#     zombie ports get reused by live instances (seen: two javas on 9143);
#   - stop switch: touch outputs/a219-reaper.stop (shared fs) and the loop exits;
#   - DRY=1 prints what it would kill and touches nothing.
#
# Run from the repo root ON a219 (same /datapool mount):
#   setsid nohup bash scripts/a219_java_reaper.sh > /dev/null 2>&1 &
set -uo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
LOG="$ROOT/outputs/log-a219-reaper.txt"
STOP="$ROOT/outputs/a219-reaper.stop"
GRACE=${GRACE:-900}
DRY=${DRY:-0}
log() { echo "[reaper] $(date '+%m-%d %H:%M:%S') $*" >> "$LOG"; }

log "started on $(hostname) DRY=$DRY GRACE=${GRACE}s"
while [ ! -f "$STOP" ]; do
  reaped=0; kept=0
  for p in $(pgrep -f "^java .*envPort="); do
    age=$(ps -o etimes= -p "$p" 2>/dev/null | tr -d ' '); [ -z "$age" ] && continue
    port=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null | grep -o "envPort=[0-9]*" | cut -d= -f2)
    [ -z "$port" ] && continue
    hex=$(printf "%04X" "$port")
    n=$(cat "/proc/$p/net/tcp" "/proc/$p/net/tcp6" 2>/dev/null | awk -v h=":$hex" '$2 ~ h && $4 == "01"' | wc -l)
    if [ "$n" -gt 0 ] || [ "$age" -lt "$GRACE" ]; then kept=$((kept+1)); continue; fi
    # zombie: kill the xvfb-run wrapper tree when there is one, else just the java
    ppid=$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' ')
    victims="$p"
    if [ -n "$ppid" ] && grep -qa "xvfb-run" "/proc/$ppid/cmdline" 2>/dev/null; then
      victims="$ppid $(pgrep -P "$ppid" | tr '\n' ' ') $p"
    fi
    if [ "$DRY" = "1" ]; then
      log "DRY would-kill pid=$p port=$port age_min=$((age/60)) tree=[$victims]"
    else
      kill -9 $victims 2>/dev/null
      log "killed pid=$p port=$port age_min=$((age/60)) tree=[$victims]"
    fi
    reaped=$((reaped+1))
  done
  log "round done: reaped=$reaped kept=$kept load=$(cut -d' ' -f1 /proc/loadavg)"
  [ "$DRY" = "1" ] && { log "dry run: single round only"; break; }
  sleep 600
done
log "stopped ($([ -f "$STOP" ] && echo stop-file || echo dry-exit))"
