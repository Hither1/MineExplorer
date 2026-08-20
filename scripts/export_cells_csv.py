"""Append a campaign's cells to experiments/4hop_cells.csv, the tracked per-cell record.

`outputs/` is gitignored -- it is ~29 GB of episode video, frames and codex rollouts -- so the
row-per-cell CSV is how a campaign's result survives outside the storage volume. This writes
the same 28 columns the file already uses, plus `prompt_layout` and `response_style`, which it
did not have: by this repo's rule anything but legacy/full is a DIFFERENT ARM, and a q35a row
without those two would read as a legacy run. Existing rows are backfilled with `legacy,full`,
which is what they were -- they predate the knobs and `run_cell.sh` defaults to exactly that.

Cells whose result.json carries an `error` instead of `total_steps` (the a230 outage wrote 11
of them) are skipped and counted, not silently dropped.

    python scripts/export_cells_csv.py --prefix q35a --campaign q35a [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from summarize_4hop import wall_and_server  # noqa: E402  (same repo, same layout assumptions)

CSV = ROOT / "experiments" / "4hop_cells.csv"
NEW_COLS = ["prompt_layout", "response_style"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="q35a")
    ap.add_argument("--campaign", default="")
    ap.add_argument("--model", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    campaign = args.campaign or args.prefix

    rows = list(csv.DictReader(CSV.open()))
    header = list(rows[0].keys()) if rows else []
    for c in NEW_COLS:
        if c not in header:
            header.append(c)
            for r in rows:
                r.setdefault(c, "")
    # Backfill: every pre-existing row is a legacy/full run by construction.
    for r in rows:
        r["prompt_layout"] = r.get("prompt_layout") or "legacy"
        r["response_style"] = r.get("response_style") or "full"

    have = {(r["campaign"], r["agent_mode"], r["channel"], r["scene"],
             r["prompt_layout"], r["response_style"]) for r in rows}
    added = skipped = damaged = 0
    for res in sorted(ROOT.glob(f"outputs/{args.prefix}-*/*/4-hop/*/result.json")):
        j = json.loads(res.read_text())
        if "total_steps" not in j:
            damaged += 1
            continue
        if args.model and j.get("model") != args.model:
            continue
        tag = res.parts[-5]
        key = (campaign, j["agent_mode"], j["provider"], j["scene_id"],
               j.get("prompt_layout", "legacy"), j.get("response_style", "full"))
        if key in have:
            skipped += 1
            continue
        wall, server, calls, ceil = wall_and_server(ROOT / "outputs" / f"log-{tag}.txt")
        rows.append({
            "campaign": campaign, "model": j["model"], "agent_mode": j["agent_mode"],
            "channel": j["provider"], "scene": j["scene_id"], "hops": 4,
            "milestones_done": j["milestones_completed"],
            "milestones_trackable": j["milestones_trackable"],
            "milestones_presatisfied": j["milestones_presatisfied"],
            "steps_used": j["total_steps"], "termination": j["termination_reason"],
            "frames_completed": "|".join(str(m["frame_completed"]) for m in j["milestone_status"]),
            "max_steps": j["max_steps"], "temperature": 0.7, "output_cap": 1024,
            "thinking": "off", "milestone_hint": "on" if j.get("milestone_hint") else "off",
            "seed_count": 1,
            "codex_sandboxed": j.get("codex_sandboxed", ""),
            "codex_timeout_s": 900 if j["provider"] == "codex" else "",
            "server_port": server, "wall_min": re.sub(r"m$", "", wall or ""),
            "model_calls": calls, "ceiling_hits": ceil,
            "wire_requests": "", "input_tokens": "", "output_tokens": "",
            "trajectory": "",
            "prompt_layout": j.get("prompt_layout", "legacy"),
            "response_style": j.get("response_style", "full"),
        })
        have.add(key)
        added += 1

    print(f"added {added}, already present {skipped}, damaged/skipped {damaged}; "
          f"file will hold {len(rows)} rows")
    if args.dry_run:
        return 0
    with CSV.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
