#!/usr/bin/env bash
# Run a snapshot of a script instead of the script itself.
#
# bash reads a script incrementally as it executes, so editing a file that a Slurm
# job is running corrupts that job -- silently, at whatever offset the interpreter
# has reached. It has happened twice here: once via a cross-filesystem `mv` that
# truncated the inode, once via a plain in-place edit that left a running job to die
# on `unexpected EOF while looking for matching '"'` after its results were already
# written. Both produced runs that had to be thrown away.
#
# Copying into the run's own artifact directory makes the running job immune to
# later edits, and leaves the exact code that ran next to the results it produced.
#
# Usage: scripts/snapshot_exec.sh <script> [args...]
set -euo pipefail

SCRIPT=$1; shift
DEST_DIR=${ART_DIR:-${TMPDIR:-/tmp}}/script-snapshot
mkdir -p "$DEST_DIR"
SNAP="$DEST_DIR/$(basename "$SCRIPT")"
cp "$SCRIPT" "$SNAP"
chmod +x "$SNAP"
echo "running snapshot: $SNAP (from $SCRIPT)"
exec bash "$SNAP" "$@"
