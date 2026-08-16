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
# The whole scripts/ directory is copied, not just the named file: these scripts
# call each other through "$(dirname "$BASH_SOURCE")/sibling.sh", and a lone copy
# resolves that to a snapshot directory where the sibling does not exist. A run died
# that way (`start_minecraft_arm64.sh: No such file or directory`) before the
# directory-level copy replaced the single-file one.
#
# Usage: scripts/snapshot_exec.sh <script> [args...]
set -euo pipefail

SCRIPT=$1; shift
SRC_DIR=$(cd "$(dirname "$SCRIPT")" && pwd)
DEST_DIR=${ART_DIR:-${TMPDIR:-/tmp}}/script-snapshot

# Copy once per run. Nested use -- the outer wrapper invoking this again for the
# inner script -- must not re-copy, or it would overwrite the very file the outer
# bash is still reading and reintroduce the corruption this script exists to prevent.
if [[ ! -f "$DEST_DIR/.snapshot-complete" ]]; then
  mkdir -p "$DEST_DIR"
  cp -r "$SRC_DIR/." "$DEST_DIR/"
  touch "$DEST_DIR/.snapshot-complete"
  echo "snapshotted $SRC_DIR -> $DEST_DIR"
fi

# A snapshotted script sits under artifacts/runs/<id>/script-snapshot/, so computing
# the repo root from its own location yields the run directory instead of the repo.
# The real root is known here, so pass it on: the server's discovery file was written
# to artifacts/runs/<id>/artifacts/servers/ before this existed.
export MINEEXPLORER_ROOT=${MINEEXPLORER_ROOT:-$(cd "$SRC_DIR/.." && pwd)}

SNAP="$DEST_DIR/$(basename "$SCRIPT")"
chmod +x "$SNAP"
echo "running snapshot: $SNAP (from $SCRIPT)"
exec bash "$SNAP" "$@"
