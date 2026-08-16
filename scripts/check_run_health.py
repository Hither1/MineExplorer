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

    # Not every run is an episode. A model server has no steps, no player and no
    # milestones, so every invariant below would report its absence as a problem --
    # and an alert that cries wolf on healthy infrastructure is how the real ones get
    # ignored.
    if not states and not loop_steps and "eval_benchmark" not in text:
        notes.append("not an episode run (no benchmark loop); invariants skipped")
        return verdict, notes
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
                # Two very different causes, and conflating them wastes the alert. If
                # the environment is answering and states keep arriving, the actions
                # are landing and it is the agent that has stopped -- a result, not a
                # defect. Only silence from the environment means the run is invalid.
                if lost:
                    flag("BROKEN", f"player has not moved in {len(window)} steps and "
                                   f"the environment is failing")
                else:
                    flag("WARN", f"player has not moved in {len(window)} steps; the "
                                 f"environment is healthy, so the agent has stalled")

    # The stall has a signature worth naming: a model that believes it succeeded, will
    # not press ESC because nothing verified it, and returns an empty action "to
    # preserve the successful state". gpt-5.6 spent 150 steps that way on 0802.
    empty = len(re.findall(r'"action":\s*\{\}', text))
    if empty >= 20:
        notes.append(f"empty_actions={empty}")
        flag("WARN", f"agent returned an empty action {empty} times; it has given up "
                     f"without ending the episode")

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
        # Three separate questions, which a single steps-per-turn ratio conflated --
        # it counted retried turns in the denominator and then blamed the queue for
        # the model's short plans. The runner logs every plan it queues, so each can
        # be asked directly.
        planned = [int(m) for m in re.findall(r"queued \d+ entries = (\d+) steps", text)]
        executed = states[-1][0]
        if planned:
            mean_plan = sum(planned) / len(planned)
            notes.append(f"plans={len(planned)} mean_plan_steps={mean_plan:.1f} "
                         f"planned_total={sum(planned)} executed={executed}")
            # 1. Is the queue delivering what was planned?
            if sum(planned) - executed > 10:
                flag("BROKEN", f"{sum(planned)} steps were planned but only {executed} "
                               f"reached the world; the queue is dropping them")
            # 2. Is the mechanism even in use? One-step plans make PRO-LONG an
            #    expensive per-step agent -- a result about the model, not a defect.
            elif len(planned) >= 5 and mean_plan < 1.5:
                flag("WARN", f"the analyzer plans {mean_plan:.1f} steps at a time, so "
                             f"PRO-LONG's one-analysis-many-steps property is absent")
        # 3. How many turns yield nothing? Retries make this invisible in the raw
        #    call count: 15 turns produced 8 plans while only 3 logged a failure.
        barren = calls - len(planned)
        if calls >= 8 and barren / calls > 0.4:
            flag("WARN", f"{barren} of {calls} analyzer turns produced no usable plan")

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
