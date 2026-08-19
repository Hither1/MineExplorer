#!/usr/bin/env python3
"""What a codex-driven step costs, from the cell logs and the rollouts codex itself wrote.

  .venv/bin/python scripts/codex_cost.py --prefix c4h --arm default [--outputs ../MineExplorer/outputs]
  .venv/bin/python scripts/codex_cost.py --prefix q35 --arm prolong

Both codex-driven arms turned out to be decode-bound at the server's per-request rate (measured
2026-08-19: answered `default x codex` calls generate 1172-1450 tokens in 38-48 s = 29-30 tok/s,
the same rate the direct arms see with 2-3 requests running), so what this prints is mostly
"how many tokens does this arm make the model generate per step, and how long is it made to
wait". A call that hits the ceiling is not hung: it has produced 3.0-3.5k tokens when cut.

Per arm it reports: step and call/turn times, requests and tokens per call/turn, which tools the
model reached for, the share of the call spent executing them, and -- for an arm with a ceiling
-- what a different ceiling would have cost in wall time and in answered calls turned into
no-ops. See experiments/EVAL_LATENCY_helixon.md section 7.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import re
import statistics as st
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TS = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+)")
ROLLOUT_TS = re.compile(r"rollout-(\d{4}-\d\d-\d\dT\d\d-\d\d-\d\d)-")


def _q(xs, p):
    return sorted(xs)[min(len(xs) - 1, int(p * len(xs)))] if xs else float("nan")


def parse_log(path: Path):
    """(step times, [(call start, duration, hit_ceiling)], [turn durations])."""
    steps, calls, turns = [], [], []
    t_step = t_call = t_turn = None
    for line in open(path, errors="replace"):
        m = TS.match(line)
        if not m:
            continue
        t = dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S.%f")
        if "--- Step " in line:
            if t_step:
                steps.append((t - t_step).total_seconds())
            t_step = t
        # Order matters: the ceiling line is ALSO a "[CodexProvider] call N ..." line.
        if t_call and ("Raw LLM response" in line or "timed out after" in line):
            calls.append((t_call, (t - t_call).total_seconds(), "timed out after" in line))
            t_call = None
        elif "[CodexProvider] call " in line and "timed out" not in line:
            t_call = t
        if "[codex] turn " in line:
            t_turn = t
        elif t_turn and "queued" in line:
            turns.append((t - t_turn).total_seconds())
            t_turn = None
    return steps, calls, turns


def parse_rollout(path: str):
    """(requests, input, cached, output) per turn in this rollout, plus tool counts/time."""
    out, cur, prev = [], None, (0, 0, 0)
    tools, tool_time, pend = Counter(), 0.0, None
    for line in open(path, errors="replace"):
        try:
            d = json.loads(line)
        except Exception:
            continue
        pl = d.get("payload") or {}
        kind = pl.get("type")
        t = dt.datetime.strptime(d["timestamp"][:23], "%Y-%m-%dT%H:%M:%S.%f") if d.get("timestamp") else None
        if kind == "task_started":
            if cur:
                out.append(cur)
            cur = [0, 0, 0, 0]
        elif kind == "token_count" and cur is not None:
            u = ((pl.get("info") or {}).get("total_token_usage") or {})
            now = (u.get("input_tokens", 0), u.get("cached_input_tokens", 0), u.get("output_tokens", 0))
            delta = tuple(a - b for a, b in zip(now, prev))
            prev = now
            cur[0] += 1
            cur[1] += delta[0]
            cur[2] += delta[1]
            cur[3] += delta[2]
        elif kind == "function_call":
            name = pl.get("name", "?")
            args = str(pl.get("arguments", ""))
            if name == "exec_command":
                name = "exec:PIL" if ("PIL" in args or "Image" in args) else (
                    "exec:echo" if '"cmd": "echo' in args else "exec:other")
            tools[name] += 1
            pend = t
        elif kind == "function_call_output" and pend and t:
            tool_time += (t - pend).total_seconds()
            pend = None
    if cur:
        out.append(cur)
    return out, tools, tool_time


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="c4h")
    ap.add_argument("--arm", default="default", choices=("default", "hypothesis", "prolong"))
    ap.add_argument("--ceilings", default="45,60,75,90", help="what-if ceilings, seconds")
    ap.add_argument("--outputs", default=str(ROOT / "outputs"),
                    help="outputs directory holding the cells (another worktree's is fine)")
    args = ap.parse_args()

    steps, calls, turns = [], [], []
    out_dir = Path(args.outputs)
    for f in sorted(out_dir.glob(f"log-{args.prefix}-{args.arm}-codex-*.txt")):
        s, c, t = parse_log(f)
        steps += s
        calls += c
        turns += t
    if not steps:
        print(f"no logs matching {out_dir}/log-{args.prefix}-{args.arm}-codex-*.txt")
        return 1

    print(f"{args.prefix} {args.arm} x codex: {len(steps)} steps, med {st.median(steps):.0f}s (p90 {_q(steps, .9):.0f}s)")
    if turns:
        print(f"  codex turns {len(turns)} = one per {len(steps)/len(turns):.0f} steps, med {st.median(turns):.0f}s "
              f"(p90 {_q(turns, .9):.0f}s) -> ~{sum(turns)/len(steps):.1f}s of model time per step "
              f"({100*sum(turns)/sum(steps):.0f}% of the arm's wall)")
    if calls:
        ans = [d for _, d, to in calls if not to]
        ceil = [d for _, d, to in calls if to]
        total = sum(ans) + sum(ceil)
        print(f"  provider calls {len(calls)} = {len(calls)/len(steps):.2f}/step; answered {len(ans)} "
              f"med {st.median(ans):.0f}s p90 {_q(ans, .9):.0f}s"
              + (f"; ceiling {len(ceil)} ({100*len(ceil)/len(calls):.0f}% of calls, "
                 f"{100*sum(ceil)/total:.0f}% of call time)" if ceil else ""))
        if ceil:
            for cut in [int(x) for x in args.ceilings.split(",")]:
                new = sum(min(d, cut) for d in ans) + len(ceil) * cut
                lost = sum(1 for d in ans if d > cut)
                print(f"    ceiling {cut:3d}s -> call time {100*new/total:3.0f}% of today, "
                      f"{lost} answered calls ({100*lost/len(ans):.0f}%) would become no-ops")

    rollouts = glob.glob(str(out_dir / f"{args.prefix}-{args.arm}-codex-*/**/rollout-*.jsonl"), recursive=True)
    per_turn, tools, tool_time = [], Counter(), 0.0
    for f in rollouts:
        t, tl, tt = parse_rollout(f)
        per_turn += t
        tools += tl
        tool_time += tt
    if per_turn:
        n = len(per_turn)
        inp = [t[1] for t in per_turn]
        cac = [t[2] for t in per_turn]
        print(f"  rollouts: {n} turns | requests/turn med {st.median([t[0] for t in per_turn]):.0f} "
              f"(p90 {_q([t[0] for t in per_turn], .9):.0f}) | input tok/turn med {st.median(inp):.0f} "
              f"(cached {100*sum(cac)/max(1, sum(inp)):.0f}%) | OUTPUT tok/turn med {st.median([t[3] for t in per_turn]):.0f} "
              f"(p90 {_q([t[3] for t in per_turn], .9):.0f})")
        print(f"  tools/turn: " + ", ".join(f"{k} {v/n:.1f}" for k, v in tools.most_common(6))
              + f" | tool execution {tool_time/n:.1f}s per turn")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
