"""Collate every finished scene result into one comparison table.

Reads result.json wherever eval_benchmark wrote it and labels each run by the three
axes that actually vary: agent architecture, model, and how the model is reached.
Milestones are reported per scene rather than pooled, because the scenes differ
sharply in how much they demand -- 0313's first hop needs 0.56 blocks of movement
while 0802's single milestone needs ~4.5 -- so a pooled percentage hides the signal.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def label(run_id: str) -> tuple[str, str, str]:
    """(agent, model, path) inferred from the run slug the launcher recorded."""
    r = run_id.lower()
    agent = "prolong" if "prolong" in r else "hypothesis" if "hypothesis" in r else "default"
    model = "gpt-5.6" if "gpt56" in r else "Qwen3.5-27B"
    path = "vllm" if "vllm" in r or ("codex" not in r and "prolong" not in r) else "codex"
    return agent, model, path


def load_invalid() -> dict[str, str]:
    """Runs whose numbers exist but do not measure what they claim."""
    path = ROOT / "artifacts" / "INVALID_RUNS.txt"
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        prefix, _, reason = line.partition("  ")
        out[prefix.strip()] = reason.strip()
    return out


def main() -> int:
    invalid = load_invalid()
    skipped: list[tuple[str, str]] = []
    rows = []
    for f in sorted(ROOT.glob("artifacts/runs/*/results/*/*/*/result.json")):
        run_id = f.parts[len(ROOT.parts) + 2]
        bad = next((r for p, r in invalid.items() if run_id.startswith(p)), None)
        if bad:
            if (run_id, bad) not in skipped:
                skipped.append((run_id, bad))
            continue
        scene = f.parent.name
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        agent, model, path = label(run_id)
        ms = d.get("milestone_status", [])
        hits = [m["milestone_id"] for m in ms if m.get("completed")]
        rows.append({
            "run": run_id, "scene": scene, "agent": agent, "model": model, "path": path,
            "steps": d.get("total_steps", 0), "term": d.get("termination_reason", ""),
            "done": d.get("milestones_completed", 0),
            "track": d.get("milestones_trackable", 0),
            "hits": hits,
        })

    if skipped:
        print(f"excluded {len(skipped)} invalidated run(s):")
        for run_id, reason in skipped:
            print(f"  {run_id[:44]:44s} {reason}")
        print()
    if not rows:
        print("no valid results yet")
        return 0

    print(f"{'agent':11s} {'model':12s} {'path':6s} {'scene':6s} {'steps':>5s} "
          f"{'term':15s} {'score':>6s}  milestones hit")
    print("-" * 100)
    for r in sorted(rows, key=lambda r: (r["scene"], r["agent"], r["model"], r["path"])):
        print(f"{r['agent']:11s} {r['model']:12s} {r['path']:6s} {r['scene']:6s} "
              f"{r['steps']:5d} {r['term']:15s} {r['done']:2d}/{r['track']:<3d}  "
              f"{','.join(r['hits']) or '-'}")

    print()
    print("per-configuration totals (scenes pooled, read with the caveat above):")
    agg: dict[tuple, list[int]] = {}
    for r in rows:
        k = (r["agent"], r["model"], r["path"])
        a = agg.setdefault(k, [0, 0, 0])
        a[0] += r["done"]; a[1] += r["track"]; a[2] += 1
    for (agent, model, path), (done, track, n) in sorted(agg.items()):
        pct = f"{100 * done / track:.0f}%" if track else "n/a"
        print(f"  {agent:11s} {model:12s} {path:6s}  {done}/{track} ({pct}) over {n} scene(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
