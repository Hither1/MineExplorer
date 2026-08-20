#!/usr/bin/env bash
# Independent 06:15 stop for the q35a sprint.
#
# append_only_sprint.sh's own `past()` compares "$(date +%H%M)" arithmetically, and bash reads
# a leading-zero literal as octal: after midnight "0008" is not valid octal, so the test errors
# out and returns false. It happens to still fire at 06:15 (both sides parse as octal 0615=397)
# and from 06:20 on, but a deadline should not rest on that coincidence. The running shell has
# already defined `past()` in memory and has not yet read the file's last three lines, so
# editing the script now would be both useless and unsafe -- hence a separate process.
#
# Killing the launchers is all this does. In-flight cells are left to land on their own, and
# the sprint's own watchdog then sees "both launchers exited", breaks, and writes the summary.
#
#   setsid nohup bash tasks/<task>/deadline_enforcer.sh > outputs/log-q35a-enforcer.txt 2>&1 &
set -uo pipefail
cd /datapool/data3/storage/ruihan/data_share/jh/Collab/MineExplorer
STOP_EPOCH=$(date -d '2026-08-21 06:15:00' +%s)
say() { echo "[enforcer] $(date '+%m-%d %H:%M:%S') $*"; }
say "armed for $(date -d @$STOP_EPOCH '+%m-%d %H:%M:%S')"
# Wait for the clock, NOT for the launchers. The first version exited as soon as it saw no
# launcher, which was true during the a230 outage -- and would have left a post-outage resume
# with no stop at all, since resume_after_a230.sh only checks the deadline while it is still
# waiting for the host.
while [ "$(date +%s)" -lt "$STOP_EPOCH" ]; do sleep 60; done
h=$(find outputs -path '*q35a-hypothesis-vllm-append-only*' -name result.json | wc -l)
d=$(find outputs -path '*q35a-default-vllm-append-only*'    -name result.json | wc -l)
say "deadline: hypothesis $h, default $d -- killing launchers, leaving cells to land"
for pid in $(pgrep -f '^bash scripts/launch_4hop\.sh$'); do say "kill $pid"; kill "$pid" 2>/dev/null; done
sleep 5
say "launchers left: $(pgrep -cf '^bash scripts/launch_4hop\.sh$')"
