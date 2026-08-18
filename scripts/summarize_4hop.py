"""One table for the strict 4-hop campaign: scene x arm, from the cells' own files.

Reads outputs/<prefix>-<agent>-<channel>-<scene>/Qwen3.8-27B/4-hop/<scene>/result.json,
the cell log (wall clock, which server, model calls) and, for the codex arm, the
rollout the vision audit points at (requests and tokens, codex's own accounting; per
thread it is cumulative, so the last request's figures are the thread's totals).

    python scripts/summarize_4hop.py [--prefix c4h] [--md]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TS = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+)")


def wall_and_server(log: Path) -> tuple[str, str, int]:
    first = last = None
    server = ""
    calls = 0
    if not log.exists():
        return "", "", 0
    for line in log.read_text(errors="replace").splitlines():
        m = TS.match(line)
        if m:
            t = dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S.%f")
            first = first or t
            last = t
        if "Connected to vLLM server at" in line or "endpoint=" in line:
            mm = re.search(r"(http://[\d.]+:\d+)", line)
            if mm:
                server = mm.group(1).rsplit(":", 1)[1]
        if "Querying vLLM" in line or ("[codex] turn" in line and "model=" in line):
            calls += 1
    wall = f"{(last - first).total_seconds() / 60:.0f}m" if first and last else ""
    return wall, server, calls


def rollout_cost(audit: Path) -> tuple[int, int, int]:
    """(requests, input tokens, output tokens) from the rollout's token_count events."""
    if not audit.exists():
        return 0, 0, 0
    src = json.loads(audit.read_text()).get("vision_audit_source")
    if not src or not Path(src).exists():
        return 0, 0, 0
    reqs = 0
    total_in = total_out = 0
    for line in Path(src).read_text(errors="replace").splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        pl = e.get("payload") or {}
        if e.get("type") == "event_msg" and pl.get("type") == "token_count":
            lu = (pl.get("info") or {}).get("last_token_usage") or {}
            if lu.get("input_tokens"):
                reqs += 1
                total_in += lu["input_tokens"]
                total_out += lu.get("output_tokens", 0)
    return reqs, total_in, total_out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="c4h")
    ap.add_argument("--md", action="store_true", help="markdown table")
    args = ap.parse_args()

    rows = []
    for res in sorted(ROOT.glob(f"outputs/{args.prefix}-*/Qwen3.8-27B/4-hop/*/result.json")):
        j = json.loads(res.read_text())
        tag = res.parts[-5]
        agent, channel = j["agent_mode"], j["provider"]
        scene = j["scene_id"]
        wall, server, calls = wall_and_server(ROOT / "outputs" / f"log-{tag}.txt")
        frames = [m["frame_completed"] for m in j["milestone_status"]]
        reqs = tin = tout = 0
        if channel == "codex":
            reqs, tin, tout = rollout_cost(res.parent / "prolong_vision_audit.json")
        rows.append(dict(
            scene=scene, arm=f"{agent}x{channel}", ms=f"{j['milestones_completed']}/{j['milestones_trackable']}",
            steps=j["total_steps"], end=j["termination_reason"], frames=",".join(str(f) for f in frames),
            wall=wall, server=server, calls=calls, reqs=reqs, tok_in=tin, tok_out=tout,
            sandboxed=j.get("codex_sandboxed", "-"),
        ))
    rows.sort(key=lambda r: (r["scene"], r["arm"]))
    cols = ["scene", "arm", "ms", "steps", "end", "frames", "wall", "server", "calls", "reqs", "tok_in", "tok_out", "sandboxed"]
    if args.md:
        print("| " + " | ".join(cols) + " |")
        print("|" + "---|" * len(cols))
        for r in rows:
            print("| " + " | ".join(str(r[c]) for c in cols) + " |")
    else:
        widths = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in cols} if rows else {c: len(c) for c in cols}
        print("  ".join(c.ljust(widths[c]) for c in cols))
        for r in rows:
            print("  ".join(str(r[c]).ljust(widths[c]) for c in cols))
    # per-arm totals
    for arm in sorted({r["arm"] for r in rows}):
        sub = [r for r in rows if r["arm"] == arm]
        done = sum(int(r["ms"].split("/")[0]) for r in sub)
        total = sum(int(r["ms"].split("/")[1]) for r in sub)
        full = sum(1 for r in sub if r["ms"].split("/")[0] == r["ms"].split("/")[1])
        print(f"{arm}: {len(sub)} scenes, milestones {done}/{total}, all-done scenes {full}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
