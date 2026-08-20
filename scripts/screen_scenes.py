"""Screen benchmark scenes for the ones that can actually discriminate between agents.

A scene's advertised difficulty is its milestone count, and that number is wrong in
two directions at once.

  * Milestone count is not dependency depth. 154 scenes carry four milestones, but
    the reasoning graph over them is often a shallow tree -- 16 of them have only two
    edges, so four milestones sit at depth two. A "4-hop" scene that is really two
    hops wide does not test the long horizon it is being chosen for.

  * A milestone can be satisfied at spawn. `position_near_with_facing` passes when the
    player is within `max_distance` of the target and looking at it, and in 12 of the
    19 four-milestone navigation scenes at least one target is already inside its own
    radius before the agent moves -- one scene hands over three of four. Those points
    accrue to every arm equally and compress the score range the comparison depends on.

Usage: python scripts/screen_scenes.py [--hops 4] [--max-free 0]
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSITION_RULES = {"position_near_with_facing", "position_inside_box"}

# Tasks the action space cannot express, whatever the model does. ActionState carries an
# `inventory` toggle that opens the GUI but no cursor and no click, so anything requiring
# a slot -- crafting, villager trades, anvils, furnaces, brewing -- cannot be performed.
# 138 of the 299 scenes with three or more milestones contain at least one. Scoring zero
# on those measures the harness, not the agent.
GUI_ONLY_VERBS = ("craft", "trade", "sell", "rename", "enchant", "smelt", "brew")


def dependency_depth(nodes: list, edges: list) -> int:
    """Longest path through the reasoning graph, which is the real hop count."""
    adj = collections.defaultdict(list)
    for e in edges:
        adj[e["from"]].append(e["to"])

    def longest(node, seen):
        if node in seen:
            return 0
        return 1 + max([longest(n, seen | {node}) for n in adj[node]] or [0])

    return max([longest(n, frozenset()) for n in nodes] or [0])


def satisfied_at_spawn(milestone: dict) -> bool:
    """True when the player passes this rule without moving, facing aside."""
    rules = milestone.get("rules") or []
    if not rules:
        return False
    rule = rules[0]
    if rule.get("type") != "position_near_with_facing":
        return False
    params = rule.get("params", {})
    target, max_distance = params.get("target"), params.get("max_distance")
    if target is None or max_distance is None:
        return False
    return math.dist((0, 0, 0), tuple(target)) <= max_distance


def hop_slack(milestone: dict) -> float | None:
    """How far past its own trigger radius a milestone's target sits.

    `position_near_with_facing` fires when the player is within `max_distance`
    of the target, so `|target| - max_distance` is the distance actually
    separating spawn from the trigger -- the honest measure of how hard a hop
    is to reach, where `|target|` alone overstates a generous radius.
    """
    rules = milestone.get("rules") or []
    if not rules or rules[0].get("type") != "position_near_with_facing":
        return None
    params = rules[0].get("params", {})
    target, max_distance = params.get("target"), params.get("max_distance")
    if target is None or max_distance is None:
        return None
    return math.dist((0, 0, 0), tuple(target)) - max_distance


def satisfiable_out_of_order(milestones: list) -> bool:
    """True when a later hop is easier to reach than an earlier one.

    Filtering scenes satisfied *at spawn* is not enough: a scene can also be
    satisfied *backwards*. On 0694 the slacks run 11.2, 9.5, 3.5, 0.1 in task
    order, so the fourth hop's trigger sits a tenth of a block outside its own
    radius and the first sits eleven blocks out. Both a Qwen3.8 run and a
    gpt-5.6 run scored it 3/4 by completing hops 4, 3, 2 in that order with
    hop 1 never completed -- two unrelated models, one signature, so it is the
    scene and not the agent. A scene scored that way measures wandering, and
    reporting it as a depth-4 result would credit multi-hop reasoning that
    never happened.

    Conservative on purpose: scenes whose hops are not all position rules
    cannot be checked this way and are not dropped.
    """
    raw = [hop_slack(m) for m in milestones]
    if len(raw) < 2 or any(s is None for s in raw):
        return False
    slacks = [s for s in raw if s is not None]
    return any(b < a for a, b in zip(slacks, slacks[1:]))


def verification_tier(milestones: list) -> str:
    """What the scene needs the environment to report, which is also its risk order."""
    types = {r["type"] for m in milestones for r in (m.get("rules") or [])}
    if types <= POSITION_RULES:
        return "position"
    if types & {"count_in_box_at_least", "count_in_box_at_most"}:
        return "voxel-counts"
    return "inventory"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hops", type=int, default=4, help="milestone count to screen")
    ap.add_argument("--max-free", type=int, default=None,
                    help="only show scenes with at most this many spawn-satisfied milestones")
    ap.add_argument("--tier", default=None, choices=["position", "inventory", "voxel-counts"])
    ap.add_argument("--reachable", action="store_true",
                    help="drop scenes containing a task the action space cannot perform")
    ap.add_argument("--min-depth", type=int, default=None,
                    help="require this real dependency depth, not just this milestone count")
    ap.add_argument("--no-backwards", action="store_true",
                    help="drop scenes whose later hops are easier to reach than earlier ones "
                         "(satisfiable_out_of_order); only decidable when every hop is a "
                         "position rule, so mixed-tier scenes are kept and shown as '?'")
    ap.add_argument("--split-to", default=None,
                    help="also materialise the scenes that pass as one-scene benchmark dirs "
                         "under DIR/<scene>/<scene>/, which is what launch_4hop.sh feeds a cell. "
                         "Keeps the scene set defined by this filter and nothing else.")
    args = ap.parse_args()

    rows = []
    for meta_path in sorted(ROOT.glob("benchmark/*/multi-agent/metadata.json")):
        meta = json.loads(meta_path.read_text())
        graph = meta.get("reasoning_graph") or {}
        nodes = graph.get("nodes") or []
        if len(nodes) != args.hops:
            continue
        milestones = json.loads((meta_path.parent / "milestones.json").read_text())["milestones"]
        tier = verification_tier(milestones)
        free = sum(1 for m in milestones if satisfied_at_spawn(m))
        depth = dependency_depth(nodes, graph.get("edges") or [])
        unscorable = sum(1 for m in milestones if not (m.get("rules") or []))
        distances = [
            math.dist((0, 0, 0), tuple(r["params"].get("target") or r["params"].get("min") or (0, 0, 0)))
            for m in milestones for r in (m.get("rules") or [])
        ]
        tasks = [t.lower() for t in (meta.get("atomic_tasks_ordered") or [])]
        gui = [t for t in tasks if t.startswith(GUI_ONLY_VERBS)]
        slacks = [hop_slack(m) for m in milestones]
        # None when the check cannot decide (a hop is not a position rule); the filter
        # keeps those, per the docstring, and the table shows them as '?'.
        backwards = satisfiable_out_of_order(milestones) if all(x is not None for x in slacks) else None
        rows.append({
            "scene": meta_path.parts[-3], "tier": tier, "depth": depth, "free": free,
            "unscorable": unscorable, "max_dist": max(distances or [0]), "gui": len(gui),
            "backwards": backwards,
            "task": meta.get("task_text", "")[:64],
        })

    shown = [r for r in rows
             if (args.tier is None or r["tier"] == args.tier)
             and (args.max_free is None or r["free"] <= args.max_free)
             and (not args.reachable or r["gui"] == 0)
             and (args.min_depth is None or r["depth"] >= args.min_depth)
             and (not args.no_backwards or not r["backwards"])]

    print(f"{len(rows)} scenes with {args.hops} milestones; {len(shown)} pass the filter")
    print(f"  by verification tier: {dict(collections.Counter(r['tier'] for r in rows))}")
    print(f"  by real dependency depth: {dict(sorted(collections.Counter(r['depth'] for r in rows).items()))}")
    print(f"  by milestones free at spawn: {dict(sorted(collections.Counter(r['free'] for r in rows).items()))}")
    print(f"  containing a task the action space cannot perform: {sum(1 for r in rows if r['gui'])}")
    print(f"  satisfiable out of order (all-position scenes only): "
          f"{sum(1 for r in rows if r['backwards'])} of "
          f"{sum(1 for r in rows if r['backwards'] is not None)} decidable")
    print()
    print(f"{'scene':6s} {'tier':13s} {'depth':>5s} {'free':>4s} {'dead':>4s} {'gui':>3s} {'bwd':>3s} {'max_d':>6s}  task")
    for r in sorted(shown, key=lambda r: (r["free"], -r["depth"], -r["max_dist"])):
        bwd = "?" if r["backwards"] is None else ("Y" if r["backwards"] else "N")
        print(f"{r['scene']:6s} {r['tier']:13s} {r['depth']:5d} {r['free']:4d} "
              f"{r['unscorable']:4d} {r['gui']:3d} {bwd:>3s} {r['max_dist']:6.1f}  {r['task']}")

    if args.split_to:
        dest = Path(args.split_to)
        for r in shown:
            out = dest / r["scene"] / r["scene"]
            out.mkdir(parents=True, exist_ok=True)
            shutil.copytree(ROOT / "benchmark" / r["scene"] / "multi-agent",
                            out / "multi-agent", dirs_exist_ok=True)
        print(f"\nwrote {len(shown)} one-scene benchmark dirs under {dest}/")
        print("SCENES=\"" + " ".join(r["scene"] for r in shown) + "\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
