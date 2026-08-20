#!/usr/bin/env python3
"""Why the q35a `hypothesis` arm scores below `default` -- every number in one place.

Evidence behind experiments/ANALYSIS_hypothesis_vs_default.md. Four runs are in scope, and
the fourth is the point: the hypothesis agent ran the 4-hop set twice in campaign q35a, once
per prompt layout, so its own run-to-run spread can be measured against the gap it is being
asked to explain.

  prolong    legacy       154 cells   codex channel
  default    append-only   33 cells   vLLM direct
  hypothesis append-only   20 cells   vLLM direct   <- the arm in question
  hypothesis legacy        28 cells   vLLM direct   <- the same agent, earlier layout

Everything cross-arm is computed on the 20 scenes all four cover. Sections:

  1 scores     -- paired per-scene milestone counts, sign test, on 80 and on the 49 reachable
  2 geometry   -- every position milestone split into never_near / near_never_faced / earned
  3 behaviour  -- action mix, ESC, reply size, from the runner logs (one row per step)
  4 discipline -- the hypothesis agent's own counters: reverted goal confirmations, ESC locks

Usage: python scripts/hyp_vs_default.py [OUT]     # default experiments/stats_hyp_vs_default
"""
from __future__ import annotations

import ast
import csv
import glob
import json
import math
import re
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "experiments" / "stats_hyp_vs_default")

# (label, cell-directory glob, runner-log glob) -- the log name drops the layout suffix for
# the hypothesis arm's legacy run, which is why the two are matched by pattern not by rule.
RUNS = {
    "prolong(legacy)": ("q35a-prolong-codex-%s", None),
    "default(append)": ("q35a-default-vllm-append-only-%s", "log-q35a-default-vllm-append-only-%s.txt"),
    "hypothesis(append)": ("q35a-hypothesis-vllm-append-only-%s", "log-q35a-hypothesis-vllm-append-only-%s.txt"),
    "hypothesis(legacy)": ("q35a-hypothesis-vllm-%s", "log-q35a-hypothesis-vllm-%s.txt"),
}
DIRECT = ["default(append)", "hypothesis(append)", "hypothesis(legacy)"]
POS_RULE = "position_near_with_facing"
MANIP = {"attack", "use", "inventory", "drop", "pickItem", "swapHands"} | {f"hotbar.{i}" for i in range(1, 10)}
LOCO = {"forward", "back", "left", "right", "jump", "sprint"}

TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+ \|")
RAW_RE = re.compile(r"\[(?:Hypothesis|Default)Agent\] Raw LLM response \(attempt (\d+)\):")
POS_RE = re.compile(r"step=(\d+) player_pos=(\{.*?\}) rules_passed=")
SPAWN_RE = re.compile(r"Reset\. Spawn=(\{.*?\})\s")


def shared_scenes() -> list[str]:
    return [r["scene"] for r in csv.DictReader(
        open(ROOT / "experiments" / "stats_q35a" / "per_scene_shared.csv"))]


def sign_test(wins: int, losses: int) -> float:
    n = wins + losses
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(wins, losses) + 1))
    return min(1.0, 2 * tail / 2 ** n)


def fisher(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact on [[a,b],[c,d]]."""
    n = a + b + c + d

    def p(a_, b_, c_, d_):
        return math.comb(a_ + b_, a_) * math.comb(c_ + d_, c_) / math.comb(n, a_ + c_)

    p0 = p(a, b, c, d)
    total = 0.0
    for i in range(min(a + b, a + c) + 1):
        j, k = a + b - i, a + c - i
        l = c + d - k
        if j < 0 or k < 0 or l < 0:
            continue
        pi = p(i, j, k, l)
        if pi <= p0 + 1e-12:
            total += pi
    return total


# -- inputs ------------------------------------------------------------------

def milestone_spec(scene: str) -> dict:
    m = json.load(open(ROOT / f"bench_4hop154/_split/{scene}/{scene}/multi-agent/metadata.json"))["milestones"]
    ms = m["milestones"] if isinstance(m, dict) else m
    return {x["milestone_id"]: x for x in ms}


def results(run: str, scenes: list[str]) -> dict:
    out = {}
    for s in scenes:
        f = glob.glob(str(ROOT / "outputs" / (RUNS[run][0] % s) / "*" / "*" / "*" / "result.json"))
        if f:
            out[s] = {m["milestone_id"]: m for m in json.load(open(f[0]))["milestone_status"]}
    return out


def steps(run: str, scene: str) -> tuple[dict | None, list]:
    """(spawn, [(step, pos, action, reply_chars, parsed)]) from the runner log."""
    pat = RUNS[run][1]
    if pat is None:
        return None, []
    log = ROOT / "outputs" / (pat % scene)
    if not log.exists() or log.stat().st_size < 20000:
        return None, []
    spawn, poses, replies = None, {}, {}
    pending = None
    step = 0
    for ln in log.read_text(errors="replace").splitlines():
        if spawn is None:
            m = SPAWN_RE.search(ln)
            if m:
                spawn = ast.literal_eval(m.group(1))
        m = POS_RE.search(ln)
        if m:
            step = int(m.group(1))
            poses[step] = ast.literal_eval(m.group(2))
        m = RAW_RE.search(ln)
        if m:
            if pending:
                _flush(pending, replies)
            pending = (step + 1, [])       # the reply precedes the step= line it produces
            continue
        if pending is not None:
            if TS_RE.match(ln):
                _flush(pending, replies)
                pending = None
            else:
                pending[1].append(ln)
    if pending:
        _flush(pending, replies)
    # A handful of steps write a reply but no `player_pos` line (the episode ends between the
    # two). Keep them, carrying the last known pose, so an action census is not silently short.
    rows = []
    last = None
    for s in sorted(set(poses) | set(replies)):
        last = poses.get(s, last)
        if last is None:
            continue
        act, chars, parsed = replies.get(s, (None, 0, False))
        rows.append((s, last, act, chars, parsed))
    return spawn, rows


def _flush(pending, replies):
    step, body = pending
    text = "\n".join(body).strip()
    if step in replies and replies[step][2]:
        return                             # already have the attempt that parsed; retries follow it
    t = re.sub(r"^```(?:json)?\s*", "", text)
    if t.endswith("```"):
        t = t[:-3]
    obj = None
    try:
        obj = json.loads(t.strip())
    except Exception:
        start = t.find("{")
        depth = 0
        for i, ch in enumerate(t[start:], start) if start >= 0 else []:
            depth += (ch == "{") - (ch == "}")
            if depth == 0:
                try:
                    obj = json.loads(t[start:i + 1])
                except Exception:
                    obj = None
                break
    act = obj.get("action") if isinstance(obj, dict) else None
    replies[step] = (act if isinstance(act, dict) else None, len(text), obj is not None)


def active(action: dict | None) -> set:
    if not isinstance(action, dict):
        return set()
    return {k for k, v in action.items() if v not in (0, None, [0, 0])}


# -- 1. scores ---------------------------------------------------------------

def scores(scenes, res, spec, w):
    npos = sum(1 for s in scenes for m in spec[s] if spec[s][m]["rules"][0]["type"] == POS_RULE)
    w(f"20 shared scenes: 80 milestones, {npos} of them `{POS_RULE}`, "
      f"{80 - npos} of other rule types (never earned by any arm).\n")
    w("| arm | milestones / 80 | / 49 reachable |")
    w("|---|---|---|")
    per = {}
    for run in RUNS:
        got = {s: sum(1 for m in res[run].get(s, {}) if res[run][s][m]["completed"]) for s in scenes}
        per[run] = got
        tot = sum(got.values())
        pos = sum(1 for s in scenes for m in res[run].get(s, {})
                  if res[run][s][m]["completed"] and spec[s][m]["rules"][0]["type"] == POS_RULE)
        w(f"| {run} | {tot}/80 = {100*tot/80:.1f}% | {pos}/{npos} = {100*pos/npos:.1f}% |")
    w("")
    w("| pair | sum | mean diff/scene ± se | W-L-T | sign test |")
    w("|---|---|---|---|---|")
    pairs = [("default(append)", "hypothesis(append)"), ("hypothesis(legacy)", "hypothesis(append)"),
             ("default(append)", "hypothesis(legacy)"), ("prolong(legacy)", "hypothesis(append)"),
             ("prolong(legacy)", "default(append)"), ("prolong(legacy)", "hypothesis(legacy)")]
    rows = []
    for a, b in pairs:
        d = [per[a][s] - per[b][s] for s in scenes]
        win = sum(1 for x in d if x > 0)
        loss = sum(1 for x in d if x < 0)
        se = st.pstdev(d) / math.sqrt(len(d))
        p = sign_test(win, loss)
        note = "  **same agent**" if a.split("(")[0] == b.split("(")[0] else ""
        w(f"| {a} − {b}{note} | {sum(per[a][s] for s in scenes)} vs {sum(per[b][s] for s in scenes)} "
          f"| {st.mean(d):+.2f} ± {se:.2f} | {win}-{loss}-{len(d)-win-loss} | p = {p:.3f} |")
        rows.append(dict(a=a, b=b, sum_a=sum(per[a][s] for s in scenes), sum_b=sum(per[b][s] for s in scenes),
                         mean_diff=round(st.mean(d), 3), se=round(se, 3), w=win, l=loss,
                         t=len(d) - win - loss, p=round(p, 4)))
    w("")
    with open(OUT / "paired_scores.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    return per


# -- 2. geometry -------------------------------------------------------------

def facing_err(pos, target):
    dx, dz = target[0] - pos["x"], target[2] - pos["z"]
    if abs(dx) < 1e-6 and abs(dz) < 1e-6:
        return 0.0
    expected = math.degrees(math.atan2(-dx, dz))
    return abs((float(pos.get("yaw", 0.0)) - expected + 180.0) % 360.0 - 180.0)


def geometry(scenes, res, spec, w):
    rows = []
    for run in DIRECT:
        for scene in scenes:
            spawn, S = steps(run, scene)
            if not S or spawn is None:
                continue
            for mid, ms in spec[scene].items():
                rule = ms["rules"][0]
                if rule["type"] != POS_RULE:
                    continue
                p = rule["params"]
                origin = [spawn["x"], spawn["y"], spawn["z"]]
                tgt = [p["target"][i] + (origin[i] if p.get("coordinate_frame") == "spawn_relative" else 0)
                       for i in range(3)]
                md = float(p.get("max_distance", 5.0))
                tol = float(p.get("facing_tolerance", 360.0))
                dists = [math.dist((q["x"], q["y"], q["z"]), tgt) for _, q, *_ in S]
                near = [q for (_, q, *_), d in zip(S, dists) if d <= md]
                earned = res[run][scene][mid]["completed"]
                fe = min((facing_err(q, tgt) for q in near), default=None)
                rows.append(dict(
                    run=run, scene=scene, milestone=mid, max_distance=md, facing_tol=tol,
                    d_spawn=round(dists[0], 2), d_min=round(min(dists), 2), steps_near=len(near),
                    facing_min_when_near=None if fe is None else round(fe, 1), earned=earned,
                    why=("earned" if earned else "never_near" if fe is None
                         else "near_never_faced" if fe > tol / 2 else "near_faced_unscored")))
    with open(OUT / "geometry.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)

    ref = [r for r in rows if r["run"] == "default(append)"]
    gap = [r["d_spawn"] - r["max_distance"] for r in ref]
    w(f"The 49 position milestones sit a median **{st.median([r['d_spawn'] for r in ref]):.1f} blocks** "
      f"from spawn behind a median **{st.median([r['max_distance'] for r in ref]):.0f}-block** radius, so the "
      f"median milestone asks the agent to close **{st.median(gap):.1f} blocks** and point the camera within "
      f"half of a {st.median([r['facing_tol'] for r in ref]):.0f}° tolerance.\n")
    w("| arm | ever inside the radius | of those, earned | never near | near, never faced | median closest approach − radius |")
    w("|---|---|---|---|---|---|")
    for run in DIRECT:
        R = [r for r in rows if r["run"] == run]
        near = [r for r in R if r["steps_near"] > 0]
        c = Counter(r["why"] for r in R)
        excess = st.median([r["d_min"] - r["max_distance"] for r in R])
        w(f"| {run} | {len(near)}/{len(R)} | {c['earned']}/{len(near)} | {c['never_near']} | "
          f"{c['near_never_faced']} | {excess:+.2f} blocks |")
    w("")
    return rows


# -- 3. behaviour ------------------------------------------------------------

def behaviour(scenes, w):
    per = defaultdict(dict)
    for run in DIRECT:
        for scene in scenes:
            _, S = steps(run, scene)
            if len(S) < 20:
                continue
            n = len(S)
            keys = [active(a) for _, _, a, _, _ in S]
            yaws = [q.get("yaw", 0.0) for _, q, *_ in S]
            per[run][scene] = dict(
                n=n,
                manip=sum(1 for k in keys if k & MANIP) / n,
                loco=sum(1 for k in keys if k & LOCO) / n,
                camera=sum(1 for k in keys if "camera" in k) / n,
                esc=sum(1 for k in keys if "ESC" in k),
                chars=st.median([c for *_, c, _ in S]),
                yaw_swept=sum(abs((yaws[i] - yaws[i - 1] + 180) % 360 - 180) for i in range(1, n)),
                path=sum(math.dist((S[i][1]["x"], S[i][1]["z"]), (S[i - 1][1]["x"], S[i - 1][1]["z"]))
                         for i in range(1, n)),
            )
    w("Medians over the 20 shared scenes; the sign test is paired per scene against `default`.\n")
    w("| metric | default(append) | hypothesis(append) | hypothesis(legacy) |")
    w("|---|---|---|---|")
    for key, label, pct in [("manip", "steps issuing a manipulation action", True),
                            ("camera", "steps issuing a camera move", True),
                            ("loco", "steps issuing a locomotion key", True),
                            ("yaw_swept", "yaw swept over the episode (°)", False),
                            ("path", "blocks walked", False),
                            ("chars", "reply size (chars)", False)]:
        cells = []
        for run in DIRECT:
            v = st.median([per[run][s][key] for s in per[run]])
            cell = f"{100*v:.1f}%" if pct else f"{v:.0f}"
            if run != "default(append)":
                d = [per[run][s][key] - per["default(append)"][s][key] for s in per[run]
                     if s in per["default(append)"]]
                win = sum(1 for x in d if x > 0)
                loss = sum(1 for x in d if x < 0)
                cell += f" (W-L {win}-{loss}, p = {sign_test(win, loss):.3f})"
            cells.append(cell)
        w(f"| {label} | " + " | ".join(cells) + " |")
    w("")
    w("| arm | ESC actions, 20 scenes | cells with any ESC | cells with ≥20 |")
    w("|---|---|---|---|")
    for run in DIRECT:
        e = [per[run][s]["esc"] for s in per[run]]
        w(f"| {run} | {sum(e)} | {sum(1 for x in e if x)}/{len(e)} | {sum(1 for x in e if x >= 20)} |")
    w("")
    with open(OUT / "behaviour.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["run", "scene", "steps", "manip_share", "loco_share", "camera_share",
                     "esc_actions", "reply_chars_median", "yaw_swept_deg", "path_blocks"])
        for run in DIRECT:
            for s, v in sorted(per[run].items()):
                wr.writerow([run, s, v["n"], round(v["manip"], 4), round(v["loco"], 4),
                             round(v["camera"], 4), v["esc"], v["chars"], round(v["yaw_swept"]),
                             round(v["path"], 1)])
    return per


# -- 4. the hypothesis agent's own counters ----------------------------------

def discipline(w):
    rows = []
    for pat, layout in (("q35a-hypothesis-vllm-append-only-*", "append-only"),
                        ("q35a-hypothesis-vllm-[0-9][0-9][0-9][0-9]", "legacy")):
        for f in glob.glob(str(ROOT / "outputs" / pat / "*" / "*" / "*" / "hypothesis_discipline.json")):
            j = json.load(open(f))
            g = json.load(open(Path(f).parent / "hypothesis_graph.json"))
            nodes = g.get("nodes", g)
            nodes = list(nodes.values()) if isinstance(nodes, dict) else nodes
            rows.append(dict(layout=layout, scene=Path(f).parent.name,
                             esc_dropped=j["esc_dropped"], goal_confirm_reverted=j["goal_confirm_reverted"],
                             locked_raise_capped=j["locked_raise_capped"], stale_by_budget=j["stale_by_budget"],
                             nodes=len(nodes),
                             kinds=json.dumps(dict(Counter(n.get("kind") for n in nodes))),
                             status=json.dumps(dict(Counter(n.get("status") for n in nodes)))))
    with open(OUT / "discipline.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    n = len(rows)
    rev = sum(r["goal_confirm_reverted"] for r in rows)
    w(f"Across all **{n} hypothesis cell-runs** (both layouts, {sum(r['nodes'] for r in rows)} graph nodes):\n")
    w(f"- **{rev} reverted goal confirmations** ({rev/n:.1f} per cell; "
      f"{sum(1 for r in rows if r['goal_confirm_reverted'])} of {n} cells have at least one). Each one is the "
      f"model marking a task goal `confirmed` while the environment says NOT verified.")
    w(f"- **{sum(r['esc_dropped'] for r in rows)} dropped ESC presses**, in "
      f"{sum(1 for r in rows if r['esc_dropped'])} of {n} cells "
      f"({sum(1 for r in rows if r['esc_dropped'] >= 20)} of them ≥ 20).")
    kinds = Counter()
    status = Counter()
    for r in rows:
        kinds.update(json.loads(r["kinds"]))
        status.update(json.loads(r["status"]))
    tot = sum(kinds.values())
    w(f"- Node kinds: " + ", ".join(f"**{k} {100*v/tot:.0f}%**" for k, v in kinds.most_common()) + ".")
    w(f"- Node status at the end: " + ", ".join(f"{k} {100*v/tot:.0f}%" for k, v in status.most_common()) + ".")
    w("")
    per_cell = [r for r in csv.DictReader(open(ROOT / "experiments" / "stats_q35a" / "per_cell.csv"))
                if r["arm"] == "default"]
    hyp_esc = sum(1 for r in rows if r["esc_dropped"])
    def_esc = sum(1 for r in per_cell if int(r["esc_presses"]))
    p = fisher(hyp_esc, n - hyp_esc, def_esc, len(per_cell) - def_esc)
    w(f"Cells that try to end the episode early, over every cell each arm has: "
      f"**hypothesis {hyp_esc}/{n} ({100*hyp_esc/n:.0f}%) against default {def_esc}/{len(per_cell)} "
      f"({100*def_esc/len(per_cell):.0f}%)** — Fisher exact **p = {p:.3f}**.\n")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    scenes = shared_scenes()
    spec = {s: milestone_spec(s) for s in scenes}
    res = {run: results(run, scenes) for run in RUNS}
    lines: list[str] = []

    def w(s=""):
        lines.append(s)
        print(s)

    w("## 1. Scores")
    w()
    scores(scenes, res, spec, w)
    w("## 2. Geometry: what the milestones actually ask for")
    w()
    geometry(scenes, res, spec, w)
    w("## 3. Behaviour")
    w()
    behaviour(scenes, w)
    w("## 4. The hypothesis agent's own counters")
    w()
    discipline(w)
    (OUT / "report.md").write_text("\n".join(lines) + "\n")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
