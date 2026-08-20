"""Three-arm 4-hop table on the scene set the arms actually share.

`summarize_4hop.py` totals each arm over whatever cells that arm has, which is the wrong
comparison the moment one arm is further along than another. This restricts every arm to the
intersection of their scenes and reports the three defensible score conventions side by side:

  strict     completed / trackable          -- the repo's own field; `trackable` keeps
                                              spawn-satisfied milestones in the denominator
                                              even though they can never be scored
  ceiling    completed / (total - presat)   -- of the milestones an agent could earn
  msr        (completed + presat) / total   -- counts a spawn-satisfied milestone as met

Presatisfaction is a property of the scene, not the arm, so on a matched set all three rank
the arms identically; they differ only in the absolute number. The script checks that
invariant rather than assuming it.

    python scripts/matched_table.py --prefix q35a --model Qwen3.5-27B [--md]
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


def load(prefix: str, model: str) -> dict[str, dict[str, dict]]:
    cells: dict[str, dict[str, dict]] = defaultdict(dict)
    for res in ROOT.glob(f"outputs/{prefix}-*/*/4-hop/*/result.json"):
        j = json.loads(res.read_text())
        if model and j.get("model") != model:
            continue
        st = j["milestone_status"]
        cells[arm_label(j)][j["scene_id"]] = dict(
            comp=j["milestones_completed"], track=j["milestones_trackable"],
            total=j["milestones_total"], presat=j["milestones_presatisfied"],
            steps=j["total_steps"], end=j["termination_reason"],
            allmine=j["all_milestones_done"],
            got={m["milestone_id"] for m in st if m["completed"]},
        )
    return cells


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="q35a")
    ap.add_argument("--model", default="Qwen3.5-27B")
    ap.add_argument("--md", action="store_true")
    ap.add_argument("--arms", default="", help="comma-separated arm labels to keep. Without it every arm "
                    "found is intersected, which silently shrinks the matched set to whatever the smallest "
                    "side sample has -- the 28 legacy hypothesis cells would cap a 154-scene table at 28.")
    args = ap.parse_args()

    cells = load(args.prefix, args.model)
    if not cells:
        print("no cells"); return 1
    if args.arms:
        want = [a.strip() for a in args.arms.split(",")]
        missing = [a for a in want if a not in cells]
        if missing:
            print("no such arm(s):", missing, "\navailable:", sorted(cells)); return 1
        cells = {a: cells[a] for a in want}
    arms = sorted(cells, key=lambda a: -len(cells[a]))
    common = set.intersection(*(set(cells[a]) for a in arms))
    print(f"# {args.model}, prefix {args.prefix}")
    print(f"per-arm cells: " + ", ".join(f"{a} {len(cells[a])}" for a in arms))
    print(f"matched set: {len(common)} scenes\n")
    if not common:
        return 0

    # Presatisfaction is scene-level; if two arms disagree on a scene, the set-up is not
    # deterministic and every ceiling-corrected number below is suspect. Say so loudly.
    for s in sorted(common):
        p = {cells[a][s]["presat"] for a in arms}
        if len(p) > 1:
            print(f"!! scene {s}: arms disagree on presatisfied count {p} -- ceiling numbers are unsafe")

    cols = ["arm", "scenes", "strict", "ceiling", "msr", "all-done", "esc", "mean steps"]
    rows = []
    for a in arms:
        sub = [cells[a][s] for s in common]
        comp = sum(c["comp"] for c in sub)
        track = sum(c["track"] for c in sub)
        total = sum(c["total"] for c in sub)
        presat = sum(c["presat"] for c in sub)
        rows.append([
            a, str(len(sub)),
            f"{comp}/{track} = {100*comp/track:.1f}%",
            f"{comp}/{total-presat} = {100*comp/(total-presat):.1f}%",
            f"{comp+presat}/{total} = {100*(comp+presat)/total:.1f}%",
            str(sum(1 for c in sub if c["allmine"])),
            str(sum(1 for c in sub if c["end"] == "agent_esc")),
            f"{sum(c['steps'] for c in sub)/len(sub):.0f}",
        ])
    if args.md:
        print("| " + " | ".join(cols) + " |"); print("|" + "---|" * len(cols))
        for r in rows:
            print("| " + " | ".join(r) + " |")
    else:
        w = [max(len(c), *(len(r[i]) for r in rows)) for i, c in enumerate(cols)]
        print("  ".join(c.ljust(w[i]) for i, c in enumerate(cols)))
        for r in rows:
            print("  ".join(r[i].ljust(w[i]) for i in range(len(cols))))

    # Paired per-scene comparison: the same scene, so a win is a win on identical ground.
    # Ties carry no information about direction, so the sign test conditions on the
    # discordant pairs only -- which is also why a small matched set can still separate two
    # arms, and why it cannot separate two that mostly tie.
    from math import comb
    print("\npaired, per scene (milestones earned):")
    for i, a in enumerate(arms):
        for b in arms[i + 1:]:
            win = sum(1 for s in common if cells[a][s]["comp"] > cells[b][s]["comp"])
            loss = sum(1 for s in common if cells[a][s]["comp"] < cells[b][s]["comp"])
            tie = len(common) - win - loss
            n, k = win + loss, max(win, loss)
            p = min(1.0, 2 * sum(comb(n, j) for j in range(k, n + 1)) / 2 ** n) if n else 1.0
            mark = "significant" if p < 0.05 else "not significant"
            print(f"  {a} vs {b}: {win} win / {loss} loss / {tie} tie"
                  f"  -- sign test on the {n} discordant pairs, p = {p:.3f} ({mark})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
