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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSITION_RULES = {"position_near_with_facing", "position_inside_box"}


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
        rows.append({
            "scene": meta_path.parts[-3], "tier": tier, "depth": depth, "free": free,
            "unscorable": unscorable, "max_dist": max(distances or [0]),
            "task": meta.get("task_text", "")[:64],
        })

    shown = [r for r in rows
             if (args.tier is None or r["tier"] == args.tier)
             and (args.max_free is None or r["free"] <= args.max_free)]

    print(f"{len(rows)} scenes with {args.hops} milestones; {len(shown)} pass the filter")
    print(f"  by verification tier: {dict(collections.Counter(r['tier'] for r in rows))}")
    print(f"  by real dependency depth: {dict(sorted(collections.Counter(r['depth'] for r in rows).items()))}")
    print(f"  by milestones free at spawn: {dict(sorted(collections.Counter(r['free'] for r in rows).items()))}")
    print()
    print(f"{'scene':6s} {'tier':13s} {'depth':>5s} {'free':>4s} {'dead':>4s} {'max_d':>6s}  task")
    for r in sorted(shown, key=lambda r: (r["free"], -r["depth"], -r["max_dist"])):
        print(f"{r['scene']:6s} {r['tier']:13s} {r['depth']:5d} {r['free']:4d} "
              f"{r['unscorable']:4d} {r['max_dist']:6.1f}  {r['task']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
