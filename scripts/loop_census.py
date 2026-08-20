"""How much of each arm's episode is spent going nowhere.

One definition applied to all three arms, taken from the only per-step record they all write
(`_run_benchmark:521 ... step=N player_pos={x,y,z,pitch,yaw}`), so nothing here depends on how
an arm talks to the model:

  frozen      consecutive steps with a byte-identical pose -- position AND camera unchanged,
              i.e. the step did nothing observable at all. Reported as the share of steps
              inside a frozen run of >= 5, and the longest such run.
  stalled     steps that moved the player < 0.25 blocks. A superset of frozen: it includes
              spinning the camera on the spot, which is not idle but is not progress either.
  revisit     share of steps whose (round(x), round(z)) block was already visited earlier in
              the episode. High revisit with low frozen is the pacing/circling loop.
  coverage    distinct blocks visited / steps. The same signal read the other way.
  tortuosity  path length / net displacement. 1.0 is a straight line; large means the walking
              did not get anywhere.

`prolong` also has an arm-specific loop that these cannot see, because it happens before any
action reaches the environment: the analyzer retrying a plan the 1024-token cap keeps
truncating. That is counted separately from the `wrote no actions.json` lines.

    python scripts/loop_census.py [--prefix q35a] [--arms a,b,c] [--shared] [--md]
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import statistics as st
from collections import defaultdict
from math import dist
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSE = re.compile(r"step=(\d+) player_pos=(\{[^}]*\})")
NOACT = re.compile(r"wrote no actions\.json")
TURN = re.compile(r"\[codex\] turn (\d+) model=")


def arm_label(j: dict) -> str:
    layout, style = j.get("prompt_layout", "legacy"), j.get("response_style", "full")
    variant = [v for v in (layout if layout != "legacy" else "", style if style != "full" else "") if v]
    return f"{j['agent_mode']}x{j['provider']}" + (f"[{','.join(variant)}]" if variant else "")


def trace(log: Path) -> list[tuple]:
    out = []
    if not log.exists():
        return out
    with log.open(errors="replace") as fh:
        for line in fh:
            m = POSE.search(line)
            if m:
                try:
                    d = ast.literal_eval(m.group(2))
                except Exception:
                    continue
                out.append((d["x"], d["y"], d["z"], d.get("pitch", 0.0), d.get("yaw", 0.0)))
    return out


def census(poses: list[tuple]) -> dict | None:
    n = len(poses)
    if n < 10:
        return None
    frozen_runs, run = [], 1
    for a, b in zip(poses, poses[1:]):
        run = run + 1 if a == b else (frozen_runs.append(run), 1)[1]
    frozen_runs.append(run)
    frozen_steps = sum(r for r in frozen_runs if r >= 5)
    steps = [dist(a[:3], b[:3]) for a, b in zip(poses, poses[1:])]
    stalled = sum(1 for s in steps if s < 0.25)
    cells, seen, revisit = [], set(), 0
    for p in poses:
        c = (round(p[0]), round(p[2]))
        if c in seen:
            revisit += 1
        seen.add(c)
        cells.append(c)
    path = sum(steps)
    net = dist(poses[0][:3], poses[-1][:3])
    return dict(steps=n,
                frozen=100 * frozen_steps / n, frozen_max=max(frozen_runs),
                stalled=100 * stalled / max(n - 1, 1),
                revisit=100 * revisit / n,
                coverage=len(seen) / n,
                tort=path / net if net > 0.5 else float("inf"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="q35a")
    ap.add_argument("--model", default="Qwen3.5-27B")
    ap.add_argument("--arms", default="")
    ap.add_argument("--shared", action="store_true", help="restrict to the scenes every arm has")
    ap.add_argument("--md", action="store_true")
    args = ap.parse_args()

    cells: dict[str, dict[str, Path]] = defaultdict(dict)
    for res in ROOT.glob(f"outputs/{args.prefix}-*/*/4-hop/*/result.json"):
        j = json.loads(res.read_text())
        if args.model and j.get("model") != args.model:
            continue
        cells[arm_label(j)][j["scene_id"]] = ROOT / "outputs" / f"log-{res.parts[-5]}.txt"
    if args.arms:
        want = [a.strip() for a in args.arms.split(",")]
        missing = [a for a in want if a not in cells]
        if missing:
            print("no such arm(s):", missing, "\navailable:", sorted(cells)); return 1
        cells = {a: cells[a] for a in want}
    arms = sorted(cells, key=lambda a: -len(cells[a]))
    scope = set.intersection(*(set(cells[a]) for a in arms)) if args.shared else None

    cols = ["arm", "cells", "frozen %", "longest frozen", "stalled %", "revisit %", "coverage", "tortuosity"]
    rows = []
    for a in arms:
        rs = [census(trace(lg)) for s, lg in sorted(cells[a].items()) if scope is None or s in scope]
        rs = [r for r in rs if r]
        if not rs:
            continue
        med = lambda k: st.median([r[k] for r in rs])
        finite = [r["tort"] for r in rs if r["tort"] != float("inf")]
        rows.append([a, str(len(rs)),
                     f"{med('frozen'):.1f}", f"{max(r['frozen_max'] for r in rs)}",
                     f"{med('stalled'):.1f}", f"{med('revisit'):.1f}",
                     f"{med('coverage'):.2f}",
                     f"{st.median(finite):.1f}" if finite else "-"])
    if args.md:
        print("| " + " | ".join(cols) + " |"); print("|" + "---|" * len(cols))
        for r in rows:
            print("| " + " | ".join(r) + " |")
    else:
        w = [max(len(c), *(len(r[i]) for r in rows)) for i, c in enumerate(cols)]
        print("  ".join(c.ljust(w[i]) for i, c in enumerate(cols)))
        for r in rows:
            print("  ".join(r[i].ljust(w[i]) for i in range(len(cols))))
    print("\n(medians over cells; 'longest frozen' is the worst single run in the arm)")

    # prolong's pre-environment loop, which the pose trace cannot see.
    for a in arms:
        if not a.startswith("prolong"):
            continue
        turns = wasted = loops = 0
        for s, lg in sorted(cells[a].items()):
            if scope is not None and s not in scope:
                continue
            txt = lg.read_text(errors="replace") if lg.exists() else ""
            t, w = len(TURN.findall(txt)), len(NOACT.findall(txt))
            turns += t; wasted += w
            if t and w / t > 0.5:
                loops += 1
        if turns:
            print(f"\n{a} analyzer loop (invisible to the pose trace): {wasted}/{turns} turns "
                  f"({100*wasted/turns:.1f} %) produced no action; {loops} cell(s) spent >50 % of "
                  f"their turns that way.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
