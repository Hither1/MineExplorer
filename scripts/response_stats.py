#!/usr/bin/env python3
"""What the model wrote back, per cell, from a cell's log: how long a step took, how big the
reply was, and how often the memory / hypotheses / plan were actually (re)sent -- the numbers
that tell a `full` cell from a `compact` one (see RESPONSE_STYLES in mc_agent/context.py) and
show whether a compact cell still maintains its state.

  .venv/bin/python scripts/response_stats.py outputs/log-c4h-default-vllm-0306.txt outputs/log-fast-*-0306.txt
"""
from __future__ import annotations

import json
import re
import statistics as st
import sys
from datetime import datetime

STEP_RE = re.compile(r"^(\S+ \S+) \| INFO .*--- Step (\d+)/(\d+) ---", re.M)
RESP_RE = re.compile(r"Raw LLM response \(attempt (\d)\):\n(.*?)\n\d{4}-\d\d-\d\d \d\d:\d\d:\d\d", re.S)


def _json_of(block: str):
    m = re.search(r"\{.*\}", block, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def stats(path: str) -> str:
    txt = open(path, errors="replace").read()
    steps = STEP_RE.findall(txt)
    times = [datetime.strptime(t.split(".")[0], "%Y-%m-%d %H:%M:%S") for t, _, _ in steps]
    dts = [(b - a).total_seconds() for a, b in zip(times, times[1:])]
    resps = RESP_RE.findall(txt)
    parsed = [(int(a), _json_of(b), b) for a, b in resps]
    ok = [d for _, d, _ in parsed if isinstance(d, dict) and "action" in d]
    retries = sum(1 for a, _, _ in parsed if a > 1)
    n = max(1, len(ok))
    mem = [d for d in ok if d.get("memory_update")]
    hyp = [d for d in ok if d.get("hypotheses")]
    plan = [d for d in ok if d.get("plan")]
    reply_chars = [len(b) for _, d, b in parsed if isinstance(d, dict)]
    thought_chars = [len(str(d.get("thought", ""))) for d in ok]
    mem_chars = [len(str(d.get("memory_update", ""))) for d in mem]
    one_line = sum(1 for _, d, b in parsed if isinstance(d, dict) and "\n" not in b.strip().strip("`").strip())
    ms = re.findall(r"Milestone '([^']+)' completed at step (\d+)", txt)
    name = path.rsplit("/", 1)[-1]
    out = (f"{name}: steps {len(steps)}, s/step med {st.median(dts):.1f} (p90 {sorted(dts)[int(0.9 * len(dts))]:.1f})"
           if dts else f"{name}: steps {len(steps)}")
    out += (f"; replies {len(parsed)} (retry {retries}, unparsed {len(parsed) - len(ok)}), one-line {100 * one_line / max(1, len(parsed)):.0f}%"
            f"; reply {st.median(reply_chars):.0f} chars, thought {st.median(thought_chars):.0f} chars"
            if parsed else "")
    if ok:
        out += (f"; memory sent {100 * len(mem) / n:.0f}% (med {st.median(mem_chars) if mem_chars else 0:.0f} chars)")
        if any("hypotheses" in d or "plan" in d for d in ok) or "hypothesis" in name:
            out += f", hypotheses sent {100 * len(hyp) / n:.0f}%, plan sent {100 * len(plan) / n:.0f}%"
    out += f"; milestones {len(ms)}: {', '.join(f'{m}@{s}' for m, s in ms)}"
    return out


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(stats(p))
