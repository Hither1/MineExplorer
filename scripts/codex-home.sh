#!/usr/bin/env bash
# Build an isolated CODEX_HOME for one experiment arm and print the exports for it.
#
#   eval "$(scripts/codex-home.sh prolong-codex)"
#
# Ported from MCU-AgentBeats scripts/codex-home.sh (merge-agentbeats-main), where each
# of the four problems below was measured on a live campaign. The `codex` on PATH here
# is a wrapper that forces CODEX_HOME to the account runtime-home and symlinks the
# account's global files into whatever home it is given; this script redirects it to a
# per-arm home the wrapper cannot contaminate. Verified against this host's wrapper
# (~/.local/bin/codex): it honors CODEX_RUNTIME_HOME and CODEX_SQLITE_DIR, and its
# link_or_replace skips any target that already exists as a real file.
#
#   1. A shared thread store gets corrupted. Six arms against one
#      thread_history sqlite ended in "database disk image is malformed", which broke
#      `codex exec resume` host-wide and forced CODEX_SESSION_MAX_TURNS=1 -- no
#      conversation memory -- for the whole campaign. Per-arm CODEX_SQLITE_DIR keeps
#      one arm's corruption from reaching another.
#
#   2. Copied credentials race. Every copy of an OAuth auth.json carries the same
#      single-use refresh token; the second arm to refresh gets "your refresh token was
#      already used" and every later turn 401s. auth.json is therefore a symlink to one
#      live credential, never a copy.
#
#   3. The account's personal instructions ride along. The wrapper symlinks
#      ~/.codex/{AGENTS.md,lessons.md,RTK.md,config.toml} and the skills/memories/plugins
#      roots into the home, and codex prepends them to every turn ahead of the agent's
#      own system prompt. `--ignore-user-config` does not cover them. Empty real files
#      defeat the symlink step, which skips a target that already exists.
#
#   4. Codex refuses to create its PATH-alias helper binaries under /tmp. /var/tmp is
#      the same partition, survives boots, and does not trigger the refusal. It must be
#      a local disk: sqlite locking fails on network filesystems.
#
# This script deliberately does NOT export CODEX_HOME itself: prolong_mc's find_rollout
# resolves the rollout path as codex_home kwarg -> $CODEX_HOME -> <workspace>.codexhome
# -> wrapper home, and a blanket CODEX_HOME export would shadow the per-episode homes
# that prolong_mc/codex_sandbox.sh actually writes rollouts to. The wrapper path is
# covered by CODEX_RUNTIME_HOME; sandboxed calls bypass the wrapper entirely.
#
# Deviation from the MCU original: that script rebuilds the home unconditionally,
# because it runs once per arm launch. Here run_cell.sh evals it once per CELL and many
# cells of one arm run concurrently, so the build is idempotent behind an atomic lock:
# the first cell builds, the rest reuse. Set MC_CODEX_HOME_REBUILD=1 to force a clean
# rebuild (do it while no cell of that arm is running -- it removes the thread store).
#
# Overrides: MC_CODEX_ROOT (location; must be a local disk), MC_CODEX_AUTH (credential
# to share; read through a symlink so refreshes stay in one place).
set -euo pipefail

ARM="${1:?usage: codex-home.sh <arm-name>}"
ROOT="${MC_CODEX_ROOT:-/var/tmp/mineexplorer-codex-$(id -un)}"
HOME_DIR="$ROOT/$ARM"
SQLITE_DIR="$HOME_DIR/sqlite"
READY="$HOME_DIR/.ready"
LOCK="$ROOT/.build-$ARM.lock"

# Credential resolution. Local arms authenticate with the dummy env key and need no
# credential at all, so a missing auth.json is a warning, not an error. The first
# candidate is the repo's own master eval home (codex_sandbox.sh's CODEX_EVAL_HOME
# convention); the others are where the wrapper keeps the account credential.
AUTH="${MC_CODEX_AUTH:-}"
if [ -z "$AUTH" ]; then
    for cand in "$HOME/.codex-eval/auth.json" "$HOME/.codex/runtime-home/auth.json" \
                "$HOME/.codex/auth.json"; do
        if [ -e "$cand" ]; then AUTH="$cand"; break; fi
    done
fi
if [ -n "$AUTH" ] && [ ! -e "$AUTH" ]; then
    echo "codex-home.sh: MC_CODEX_AUTH points at $AUTH but it does not exist." >&2
    exit 1
fi
if [ -z "$AUTH" ]; then
    echo "codex-home.sh: no credential found; building $ARM without auth.json" >&2
    echo "  (fine for dummy-key local arms; set MC_CODEX_AUTH for hosted runs)." >&2
fi

build() {
    rm -rf "$HOME_DIR"
    mkdir -p "$SQLITE_DIR"
    # 700: /var/tmp is world-readable and this host is multi-user. The credential is a
    # symlink to a 600 file so it was never exposed, but the thread store holds full
    # conversations, which are the run's data.
    chmod 700 "$HOME_DIR" "$SQLITE_DIR"
    [ -n "$AUTH" ] && ln -s "$AUTH" "$HOME_DIR/auth.json"
    for f in AGENTS.md lessons.md RTK.md config.toml; do : > "$HOME_DIR/$f"; done
    for d in agents rules skills skills.disabled memories plugins; do mkdir -p "$HOME_DIR/$d"; done
    touch "$READY"
}

mkdir -p "$ROOT"
if [ "${MC_CODEX_HOME_REBUILD:-0}" = "1" ] || [ ! -e "$READY" ]; then
    if mkdir "$LOCK" 2>/dev/null; then
        trap 'rmdir "$LOCK"' EXIT
        # Re-check under the lock: a concurrent cell may have finished the build
        # between our marker test and winning the lock.
        if [ "${MC_CODEX_HOME_REBUILD:-0}" = "1" ] || [ ! -e "$READY" ]; then
            build
        fi
        rmdir "$LOCK"
        trap - EXIT
    else
        # Another cell is building; wait for its marker rather than racing it.
        for _ in $(seq 1 100); do
            [ -e "$READY" ] && break
            sleep 0.2
        done
        if [ ! -e "$READY" ]; then
            echo "codex-home.sh: timed out waiting for $HOME_DIR build (stale $LOCK?)" >&2
            exit 1
        fi
    fi
fi

echo "export CODEX_RUNTIME_HOME=$HOME_DIR"
echo "export CODEX_SQLITE_DIR=$SQLITE_DIR"
