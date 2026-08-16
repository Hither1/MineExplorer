"""Detect runs that are burning time without producing a valid experiment.

Every systematic failure this project has hit looked healthy from the outside: the
step counter advanced, the log scrolled, the job stayed RUNNING. What gave each of
them away was an invariant nobody was checking -- the player never moved, or the
analyzer produced a plan once in fifty turns. This encodes those invariants so a
broken run is caught in minutes instead of at the walltime limit.

Usage: python scripts/check_run_health.py <run-dir> [<run-dir> ...]
Exit code is non-zero if any run is BROKEN.
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

STATE_RE = re.compile(
    r"step=(\d+) player_pos=\{'x': ([-\d.]+), 'y': ([-\d.]+), 'z': ([-\d.]+)"
)
# The episode loop's own counter, which advances even when the environment refuses
# the action. The gap between the two is the tell.
LOOP_STEP_RE = re.compile(r"--- Step (\d+)/(\d+) ---")


def check(run_dir: Path) -> tuple[str, list[str]]:
    log = run_dir / "stdout.log"
    if not log.exists():
        return "UNKNOWN", ["no stdout.log yet"]
    text = log.read_text(errors="replace")
    notes, verdict = [], "OK"

    # Invariants are per scene. A job runs several scenes into one log, and the step
    # counter restarts at each while the model-call count keeps climbing, so measuring
    # across the whole file made steps-per-turn collapse the moment scene two began:
    # a healthy PRO-LONG run reporting "0.32 steps per analyzer turn, queue not
    # working" at the exact step its queue was working fine.
    scenes = re.split(r"\[\d+/\d+\] (\d{4})\n", text)
    if len(scenes) > 1:
        current_scene = scenes[-2]
        text = scenes[-1]
        notes.append(f"scene={current_scene}")

    def flag(level: str, msg: str) -> None:
        nonlocal verdict
        notes.append(f"{level}: {msg}")
        if level == "BROKEN" or (level == "WARN" and verdict == "OK"):
            verdict = level

    # A dead sandbox session does not stop the episode: env.step exhausts its retries,
    # the loop logs the failure and moves to the next step, and the step counter climbs
    # for hours over a world that is no longer being acted on. One run reached step 83
    # this way with 316 session errors and looked, from the counter alone, healthy.
    lost = len(re.findall(r"env\.step failed|session '[^']+' not found", text))
    loop_steps = [int(m.group(1)) for m in LOOP_STEP_RE.finditer(text)]
    if lost:
        notes.append(f"env_step_failures={lost}")
        if lost > 10:
            flag("BROKEN", f"{lost} env.step failures; the sandbox session is gone")

    states = [(int(m.group(1)), float(m.group(2)), float(m.group(4)))
              for m in STATE_RE.finditer(text)]
    if loop_steps:
        notes.append(f"loop_steps={loop_steps[-1]}")
        # Every executed step reports state. Counter far ahead of state means the
        # actions are not landing, whatever the reason.
        if loop_steps[-1] >= 20 and len(states) < loop_steps[-1] / 2:
            flag("BROKEN",
                 f"loop reached step {loop_steps[-1]} but only {len(states)} states "
                 f"were reported; actions are not reaching the world")
    if not states:
        flag("WARN", "no per-step state lines yet")
    else:
        steps = states[-1][0]
        notes.append(f"steps={steps}")
        # Moving is the only proof the actions are reaching the world. A swallowed
        # prompt once produced 73 steps at a frozen spawn position.
        window = states[-40:]
        if len(window) >= 20:
            span = max(
                math.dist((a[1], a[2]), (b[1], b[2]))
                for a in window for b in window[-1:]
            )
            notes.append(f"displacement_last_{len(window)}={span:.2f}")
            if span < 0.5:
                flag("BROKEN", f"player has not moved in {len(window)} steps")

    calls = len(re.findall(r"\[CodexProvider\] call|\[codex\] turn", text))
    if calls:
        notes.append(f"model_calls={calls}")
    failures = len(re.findall(r"produced no message|produced no actions\.json", text))
    if failures:
        rate = failures / max(calls, 1)
        notes.append(f"failed_calls={failures} ({rate:.0%})")
        if rate > 0.3:
            flag("BROKEN", f"{rate:.0%} of model calls produce nothing")

    # PRO-LONG's whole point is that one analysis covers many steps. A ratio near or
    # below 1 means the plan queue is not working and the mechanism is absent.
    if "ProlongAgent" in text and states and calls:
        ratio = states[-1][0] / calls
        notes.append(f"steps_per_turn={ratio:.2f}")
        if calls >= 5 and ratio < 1.5:
            flag("BROKEN", f"only {ratio:.2f} steps per analyzer turn; queue not working")

    # An episode the agent ends in a handful of steps produced a score, but not an
    # answer: nothing about memory or navigation is observable in three steps. Qwen
    # does this in every non-PRO-LONG cell, so it is a property of the arm, not a
    # crash -- WARN, and read the number in the ledger's terms.
    for m in re.finditer(r"Episode finished \(agent_esc\)", text):
        at = [s[0] for s in states if s[0]]
        ended_at = max(at) if at else 0
        if ended_at < 20:
            flag("WARN", f"episode ended by agent ESC after ~{ended_at} steps")

    if re.search(r"unexpected argument|Traceback \(most recent", text):
        last = re.findall(r"^\w*Error.*$|^error: .*$", text, re.M)
        if last:
            flag("WARN", f"errors present, last: {last[-1][:100]}")

    for done in run_dir.parent.parent.rglob("result.json"):
        if run_dir.name in str(done):
            notes.append(f"result: {done.parent.name}")
    return verdict, notes


def main(argv: list[str]) -> int:
    worst = 0
    for arg in argv:
        d = Path(arg)
        verdict, notes = check(d)
        print(f"[{verdict:7s}] {d.name}")
        for n in notes:
            print(f"           {n}")
        if verdict == "BROKEN":
            worst = 1
    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
