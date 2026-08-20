"""Task success rate and milestone success rate for the arms on the scenes they share.

Two levels, and the presatisfied milestones make each of them ambiguous in the same way:

  TSR  strict     all_milestones_done as the harness records it, i.e. completed == trackable.
                  `trackable` counts spawn-satisfied milestones, and eval_benchmark.py never
                  puts one in `completed` (it is excluded by construction), so ANY scene with
                  a spawn-satisfied milestone is unwinnable under this definition.
       achievable completed == total - presatisfied: the agent earned everything it could.
                  (`(completed + presat) == total` is the same test, so the MSR-style
                  convention adds no third task-level number.)

  MSR  strict     completed / trackable
       ceiling    completed / (total - presatisfied)
       msr        (completed + presatisfied) / total

    python scripts/tsr_msr_table.py [--prefix q35a] [--model Qwen3.5-27B] [--arms a,b,c] [--md]
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def arm_label(j: dict) -> str:
    layout, style = j.get("prompt_layout", "legacy"), j.get("response_style", "full")
    variant = [v for v in (layout if layout != "legacy" else "", style if style != "full" else "") if v]
    return f"{j['agent_mode']}x{j['provider']}" + (f"[{','.join(variant)}]" if variant else "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="q35a")
    ap.add_argument("--model", default="Qwen3.5-27B")
    ap.add_argument("--arms", default="")
    ap.add_argument("--md", action="store_true")
    args = ap.parse_args()

    cells: dict[str, dict[str, dict]] = defaultdict(dict)
    for res in ROOT.glob(f"outputs/{args.prefix}-*/*/4-hop/*/result.json"):
        j = json.loads(res.read_text())
        if args.model and j.get("model") != args.model:
            continue
        cells[arm_label(j)][j["scene_id"]] = j
    if args.arms:
        want = [a.strip() for a in args.arms.split(",")]
        missing = [a for a in want if a not in cells]
        if missing:
            print("no such arm(s):", missing, "\navailable:", sorted(cells)); return 1
        cells = {a: cells[a] for a in want}
    arms = sorted(cells, key=lambda a: -len(cells[a]))
    common = sorted(set.intersection(*(set(cells[a]) for a in arms)))
    print(f"# {args.model}, prefix {args.prefix}, {len(common)} shared scenes\n")

    cols = ["arm", "TSR strict", "TSR achievable", "MSR strict", "MSR ceiling", "MSR msr"]
    rows = []
    for a in arms:
        sub = [cells[a][s] for s in common]
        n = len(sub)
        tsr_s = sum(1 for c in sub if c["all_milestones_done"])
        tsr_a = sum(1 for c in sub if c["milestones_completed"] == c["milestones_total"] - c["milestones_presatisfied"])
        comp = sum(c["milestones_completed"] for c in sub)
        trk = sum(c["milestones_trackable"] for c in sub)
        tot = sum(c["milestones_total"] for c in sub)
        pre = sum(c["milestones_presatisfied"] for c in sub)
        rows.append([a,
                     f"{tsr_s}/{n} = {100*tsr_s/n:.1f}%",
                     f"{tsr_a}/{n} = {100*tsr_a/n:.1f}%",
                     f"{comp}/{trk} = {100*comp/trk:.1f}%",
                     f"{comp}/{tot-pre} = {100*comp/(tot-pre):.1f}%",
                     f"{comp+pre}/{tot} = {100*(comp+pre)/tot:.1f}%"])
    if args.md:
        print("| " + " | ".join(cols) + " |"); print("|" + "---|" * len(cols))
        for r in rows:
            print("| " + " | ".join(r) + " |")
    else:
        w = [max(len(c), *(len(r[i]) for r in rows)) for i, c in enumerate(cols)]
        print("  ".join(c.ljust(w[i]) for i, c in enumerate(cols)))
        for r in rows:
            print("  ".join(r[i].ljust(w[i]) for i in range(len(cols))))

    scenes_with_presat = sum(1 for s in common if cells[arms[0]][s]["milestones_presatisfied"] > 0)
    print(f"\n{scenes_with_presat}/{len(common)} shared scenes carry at least one spawn-satisfied "
          f"milestone and are therefore unwinnable under TSR strict.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
