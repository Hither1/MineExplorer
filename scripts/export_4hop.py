"""Freeze the strict 4-hop campaigns into the repository: one row per cell, one trace per
episode, small enough to read on a laptop and to keep in git.

The cells themselves are 23 GB of `outputs/` (episode videos, every frame PRO-LONG
attached, every codex rollout) and live only on this filesystem. What a reader actually
needs to re-derive the tables is much smaller: the settings each cell ran under, its
outcome, and what the agent did step by step. That is what this writes.

    python scripts/export_4hop.py            # both campaigns
    python scripts/export_4hop.py --campaign q35:Qwen3.5-27B

Outputs (all under experiments/):

  4hop_cells.csv                       one row per cell: settings, outcome, cost
  trajectories/<model>/<arm>-<scene>.jsonl
      line 1 is a `meta` record; the rest are one `step` record each --
      position, which milestone rules passed, which milestones completed on that
      step, and (for the arms that call the model once per step) the thought,
      action and memory the model produced for it.
  trajectories/<model>/<arm>-<scene>.prolong_log.txt
      PRO-LONG only: the agent's own append-only episode log, which is both its
      memory and the closest thing that arm has to a per-step narration.
  trajectories/<model>/<arm>-<scene>.hypothesis.json
      hypothesis agent only: the final DAG and plan.

Everything here is derived. Re-run it after a campaign; do not hand-edit.
"""
from __future__ import annotations

import argparse
import ast
import csv
import datetime as dt
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "experiments"
TS = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+) \| ")
STEP = re.compile(r"step=(\d+) player_pos=(\{.*?\}) rules_passed=(\[.*\])$")
DONE = re.compile(r"Milestone '([^']+)' completed at step (\d+) \(frame (-?\d+)\)")
RESP = re.compile(r"\[(DefaultAgent|HypothesisAgent)\] Raw LLM response \(attempt (\d+)\):")
QUEUED = re.compile(r"\[prolong\] step (\d+): queued (\d+) entries = (\d+) steps \(turn (\d+)\)")
TURN = re.compile(r"\[codex\] turn (\d+) model=(\S+) resume=(\S+) images=(\d+)")
CEIL = re.compile(r"\[CodexProvider\] call (\d+) .*timed out after")
RAW_KEEP = 500          # a degenerate reply can be 1024 tokens of "!"


def parse_json_block(text: str) -> tuple[dict | None, str]:
    """The agents log a ```json fenced block. Return (parsed, raw-if-unparsed)."""
    body = text.strip()
    if body.startswith("```"):
        body = re.sub(r"^```[a-zA-Z]*\n", "", body)
        body = re.sub(r"\n?```\s*$", "", body)
    try:
        obj = json.loads(body)
        return (obj, "") if isinstance(obj, dict) else (None, body[:RAW_KEEP])
    except json.JSONDecodeError:
        return None, body[:RAW_KEEP]


def read_cell_log(path: Path) -> dict:
    """Every fact the log carries, keyed by step. One pass, no line kept twice."""
    steps: dict[int, dict] = {}
    completed: dict[int, list] = {}
    turns: list[dict] = []
    step_turn: dict[int, int] = {}
    pending: str | None = None          # the reply that will drive the next step
    pending_attempt = 0
    pending_ceiling = False             # this step's call ran to the provider ceiling
    buf: list[str] | None = None
    first = last = None
    ceilings = 0
    calls = 0
    server = ""

    for line in path.read_text(errors="replace").splitlines():
        m = TS.match(line)
        if m:
            t = dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S.%f")
            first = first or t
            last = t
            if buf is not None:                      # a fenced block ended here
                pending = "\n".join(buf)
                buf = None
        elif buf is not None:
            buf.append(line)
            continue

        # One per request the agent made, retries included -- so calls >= steps.
        if ("Querying vLLM" in line
                or ("[codex] turn" in line and "model=" in line)
                or ("[CodexProvider] call " in line and "model=" in line)):
            calls += 1

        if r := RESP.search(line):
            buf, pending_attempt = [], int(r.group(2))
            continue
        if s := STEP.search(line):
            n = int(s.group(1))
            rec = {"pos": ast.literal_eval(s.group(2)),
                   "rules": {k: v for k, v in ast.literal_eval(s.group(3))}}
            if pending is not None:
                obj, raw = parse_json_block(pending)
                if obj is not None:
                    rec["thought"] = obj.get("thought")
                    rec["action"] = obj.get("action")
                    rec["memory"] = obj.get("memory_update")
                    for extra in ("hypotheses", "plan", "hypothesis_updates", "plan_update"):
                        if extra in obj:
                            rec[extra] = obj[extra]
                else:
                    rec["unparsed"] = raw
                rec["attempt"] = pending_attempt
                pending = None
            if pending_ceiling:
                # No reply was logged for this step because the call never returned; the
                # agent stepped the no-op the ceiling was priced for. Say so, rather than
                # leaving a reader to infer it from a missing field.
                rec["ceiling"] = True
                pending_ceiling = False
            steps[n] = rec
            continue
        if d := DONE.search(line):
            completed.setdefault(int(d.group(2)), []).append(
                {"milestone": d.group(1), "frame": int(d.group(3))})
            continue
        if q := QUEUED.search(line):
            start, n_steps, turn = int(q.group(1)), int(q.group(3)), int(q.group(4))
            for k in range(start, start + n_steps):
                step_turn[k] = turn
            continue
        if t_ := TURN.search(line):
            turns.append({"turn": int(t_.group(1)), "resume": t_.group(3) == "yes",
                          "images": int(t_.group(4))})
            continue
        if CEIL.search(line):
            ceilings += 1
            pending_ceiling = True
            continue
        if not server and ("Connected to vLLM server at" in line or "endpoint=" in line):
            if mm := re.search(r"http://[\d.]+:(\d+)", line):
                server = mm.group(1)

    return {"steps": steps, "completed": completed, "turns": turns, "step_turn": step_turn,
            "ceilings": ceilings, "calls": calls, "server": server,
            "wall_s": (last - first).total_seconds() if first and last else 0}


def rollout_cost(result: Path, tag: str) -> tuple[int, int, int]:
    """(requests, input tokens, output tokens) from codex's own token_count events."""
    srcs: list[Path] = []
    audit = result.parent / "prolong_vision_audit.json"
    if audit.exists():
        src = json.loads(audit.read_text()).get("vision_audit_source")
        if src and Path(src).exists():
            srcs = [Path(src)]
    else:
        srcs = sorted((ROOT / "outputs" / tag / "codex_home" / "sessions").rglob("rollout-*.jsonl"))
    reqs = tin = tout = 0
    for src in srcs:
        for line in src.read_text(errors="replace").splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            pl = e.get("payload") or {}
            if e.get("type") == "event_msg" and pl.get("type") == "token_count":
                lu = (pl.get("info") or {}).get("last_token_usage") or {}
                if lu.get("input_tokens"):
                    reqs += 1
                    tin += lu["input_tokens"]
                    tout += lu.get("output_tokens", 0)
    return reqs, tin, tout


def scene_task(metadata_path: str | None) -> str | None:
    """The task text the agent is given. Only that field: the same file holds the
    milestone coordinates, which nothing outside the scorer may see."""
    if not metadata_path:
        return None
    p = ROOT / metadata_path
    if not p.exists():
        return None
    return json.loads(p.read_text()).get("task_text")


CSV_COLUMNS = [
    "campaign", "model", "agent_mode", "channel", "scene", "hops",
    "milestones_done", "milestones_trackable", "milestones_presatisfied",
    "steps_used", "termination", "frames_completed",
    "max_steps", "temperature", "output_cap", "thinking", "milestone_hint", "seed_count",
    "codex_sandboxed", "codex_timeout_s", "server_port",
    "wall_min", "model_calls", "ceiling_hits", "wire_requests", "input_tokens", "output_tokens",
    "trajectory",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign", action="append", default=None,
                    help="prefix:model, repeatable (default: c4h:Qwen3.8-27B and q35:Qwen3.5-27B)")
    args = ap.parse_args()
    campaigns = [c.split(":", 1) for c in (args.campaign or ["c4h:Qwen3.8-27B", "q35:Qwen3.5-27B"])]

    rows = []
    for prefix, model in campaigns:
        traj_dir = OUT / "trajectories" / model
        traj_dir.mkdir(parents=True, exist_ok=True)
        for result in sorted(ROOT.glob(f"outputs/{prefix}-*/{model}/4-hop/*/result.json")):
            j = json.loads(result.read_text())
            tag = result.parts[-5]
            agent, channel, scene = j["agent_mode"], j["provider"], j["scene_id"]
            arm = f"{agent}-{channel}"
            log = read_cell_log(ROOT / "outputs" / f"log-{tag}.txt")
            reqs = tin = tout = 0
            if channel == "codex":
                reqs, tin, tout = rollout_cost(result, tag)

            name = f"{arm}-{scene}"
            traj = traj_dir / f"{name}.jsonl"
            meta = {
                "record": "meta", "campaign": prefix, "model": model, "agent_mode": agent,
                "channel": channel, "scene": scene, "hops": len(j["milestone_status"]),
                "task": scene_task(j.get("metadata_path")),
                "result": {"milestones_done": j["milestones_completed"],
                           "milestones_trackable": j["milestones_trackable"],
                           "termination": j["termination_reason"],
                           "steps": j["total_steps"],
                           "milestones": j["milestone_status"]},
                "settings": {"max_steps": 300, "temperature": 0.7, "top_p": 0.8, "top_k": 20,
                             "output_cap_tokens": 1024, "thinking": False,
                             "milestone_hint": True, "seeds": 1,
                             "codex_sandboxed": j.get("codex_sandboxed"),
                             "server_port": log["server"]},
                "cost": {"wall_s": round(log["wall_s"]), "model_calls": log["calls"],
                         "ceiling_hits": log["ceilings"],
                         "analyzer_turns": len(log["turns"]) or None,
                         "wire_requests": reqs or None,
                         "input_tokens": tin or None, "output_tokens": tout or None},
            }
            with traj.open("w", encoding="utf-8") as f:
                f.write(json.dumps(meta, ensure_ascii=False) + "\n")
                for n in sorted(log["steps"]):
                    rec = {"record": "step", "step": n, **log["steps"][n]}
                    if n in log["completed"]:
                        rec["completed"] = log["completed"][n]
                    if n in log["step_turn"]:
                        rec["analyzer_turn"] = log["step_turn"][n]
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")

            if agent == "prolong":
                src = result.parent / "prolong_workspace" / "logs.txt"
                if src.exists():
                    shutil.copyfile(src, traj_dir / f"{name}.prolong_log.txt")
            if agent == "hypothesis":
                g, p = result.parent / "hypothesis_graph.json", result.parent / "hypothesis_plan.json"
                if g.exists():
                    payload = {"graph": json.loads(g.read_text()),
                               "plan": json.loads(p.read_text()).get("plan") if p.exists() and p.stat().st_size else None}
                    (traj_dir / f"{name}.hypothesis.json").write_text(
                        json.dumps(payload, ensure_ascii=False, indent=1))

            rows.append({
                "campaign": prefix, "model": model, "agent_mode": agent, "channel": channel,
                "scene": scene, "hops": len(j["milestone_status"]),
                "milestones_done": j["milestones_completed"],
                "milestones_trackable": j["milestones_trackable"],
                "milestones_presatisfied": len(j["milestone_status"]) - j["milestones_trackable"],
                "steps_used": j["total_steps"], "termination": j["termination_reason"],
                "frames_completed": "|".join(str(m["frame_completed"]) for m in j["milestone_status"]),
                "max_steps": 300, "temperature": 0.7, "output_cap": 1024, "thinking": "off",
                "milestone_hint": "on", "seed_count": 1,
                "codex_sandboxed": j.get("codex_sandboxed", ""),
                "codex_timeout_s": (900 if agent == "prolong" else 120) if channel == "codex" else "",
                "server_port": log["server"], "wall_min": round(log["wall_s"] / 60),
                "model_calls": log["calls"],
                "ceiling_hits": log["ceilings"], "wire_requests": reqs,
                "input_tokens": tin, "output_tokens": tout,
                "trajectory": str(traj.relative_to(OUT)),
            })

    rows.sort(key=lambda r: (r["model"], r["agent_mode"], r["channel"], r["scene"]))
    csv_path = OUT / "4hop_cells.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} cells -> {csv_path.relative_to(ROOT)}")
    for (model, agent, channel), group in _by_arm(rows):
        done = sum(r["milestones_done"] for r in group)
        total = sum(r["milestones_trackable"] for r in group)
        print(f"  {model} {agent}x{channel}: {done}/{total} over {len(group)} scenes")
    return 0


def _by_arm(rows):
    keys = sorted({(r["model"], r["agent_mode"], r["channel"]) for r in rows})
    for k in keys:
        yield k, [r for r in rows if (r["model"], r["agent_mode"], r["channel"]) == k]


if __name__ == "__main__":
    raise SystemExit(main())
