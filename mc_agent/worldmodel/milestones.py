"""Ground truth: what the environment says has actually happened.

Ported from MCU-AgentBeats' `mcu_worldmodel/milestones.py` with the verification source
swapped for this repo's. MCU's ledger recomputed milestones from MineRL stat deltas with
the host's published bits as the preferred source; here the scenes are scored by
`benchmark_gen.milestone_checker.MilestoneChecker` -- rule types like
`position_near_with_facing` that need the spawn origin the harness holds -- so the
published bits are the ONLY source: eval_benchmark runs the checker every step and the
agent adapter hands its verdicts in as `info["milestones"] = {milestone_id: 0|1}`.
Recomputing them here from raw info would create a second scorer that can disagree with
the one that writes result.json, which is the exact failure the MCU ledger's source
priority existed to avoid.

Three consumers, unchanged from MCU:

    the prompt        "2/4 verified; next: ..." -- so the model plans against real
                      progress rather than its own narrative of it
    events.jsonl      the append-only ground-truth channel in the memory filesystem
    discipline        the arbiter for goal hypotheses and completion claims

Nothing here ever reads a model output. A claim and its check must not share a source.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from loguru import logger


def _num(v: Any) -> float:
    return float(v.item()) if isinstance(v, np.ndarray) else float(v)


class MilestoneLedger:
    """Tracks the scene's milestones and reports them as ground truth.

    `spec` is the scene metadata's milestone list: dicts with `milestone_id`, `task` and
    `rules`. Identity is `milestone_id`; `task` is the text the prompt renders.
    """

    def __init__(self, spec: list[dict[str, Any]], task_name: str = "") -> None:
        self.cfg = list(spec or [])
        self.task_name = task_name
        self.order = [str(c.get("milestone_id", i)) for i, c in enumerate(self.cfg)]
        self._task = {ident: str(c.get("task", "")) for ident, c in zip(self.order, self.cfg)}
        # A milestone with no rules is one the checker can never verify; it excludes
        # them from its own all_done()/num_completed(), and this ledger must agree or
        # the ESC gate would hold an episode open the harness would happily end.
        self.trackable = {ident: bool(c.get("rules"))
                          for ident, c in zip(self.order, self.cfg)}
        self.achieved: dict[str, int] = {}       # identity -> step first achieved
        self._prev_stats: dict[tuple[str, str], float] = {}
        self._warned_unpublished = False

    def reset(self, info: dict) -> None:
        self.achieved = {}
        self._prev_stats = {}
        # Take the stat baseline so the first stat_events() call reports deltas from the
        # episode start, not absolutes accumulated during scene loading.
        self.stat_events(info)

    def update(self, info: dict, step: int) -> list[dict[str, Any]]:
        """Advance the ledger one env step. Returns the milestones newly achieved."""
        published = info.get("milestones")
        if not isinstance(published, dict):
            if self.cfg and not self._warned_unpublished:
                logger.warning("[ledger] no info['milestones'] bits from the harness; "
                               "milestones cannot verify this episode")
                self._warned_unpublished = True
            return []
        fired = []
        for ident in self.order:
            if ident in self.achieved or ident not in published:
                continue
            try:
                hit = int(published[ident]) == 1
            except (TypeError, ValueError):
                hit = False
            if hit:
                self.achieved[ident] = step
                fired.append({"kind": "milestone", "identity": ident,
                              "task": self._task.get(ident, "")})
                logger.success(f"[milestone] {ident} at step {step} "
                               f"({len(self.achieved)}/{len(self.cfg)}) [checker-verified]")
        return fired

    #: Statistic buckets worth a ground-truth line each time they move. The same MineRL
    #: buckets the scene checker's event rules read. `use_item` is in: placing a block is
    #: a `use_item` on it, which is how the agent learns its block actually went down.
    STAT_EVENTS = ("mine_block", "craft_item", "pickup", "break_item", "use_item",
                   "kill_entity")

    def stat_events(self, info: dict) -> list[dict[str, Any]]:
        """Every statistic that moved this step, as ground-truth event lines.

        MCU's lesson verbatim: a ledger that logs only milestone lines leaves the agent's
        declared authoritative channel silent for ordinary progress (a chop that landed, a
        block placed), which reads as failure. Deltas on the raw buckets close that gap.
        """
        fired: list[dict[str, Any]] = []
        for event in self.STAT_EVENTS:
            bucket = info.get(event)
            if not isinstance(bucket, dict):
                continue
            for item, val in bucket.items():
                try:
                    cur = _num(val)
                except (TypeError, ValueError):
                    continue
                if cur <= 0:
                    continue
                prev = self._prev_stats.get((event, item), 0.0)
                if cur > prev:
                    fired.append({"kind": "stat", "event": event, "item": str(item),
                                  "delta": round(cur - prev, 2)})
                self._prev_stats[(event, item)] = cur
        return fired

    # -- views ------------------------------------------------------------

    def is_verified(self, identity: str) -> bool:
        return identity in self.achieved

    def num_trackable(self) -> int:
        return sum(1 for v in self.trackable.values() if v)

    def all_done(self) -> bool:
        """All *trackable* milestones verified -- the checker's own definition."""
        n = self.num_trackable()
        return n > 0 and len(self.achieved) == n

    def next_target(self) -> dict[str, Any] | None:
        """The first unachieved trackable milestone in list order -- the hops are a
        dependency chain in these scenes, so the first gap is the working target."""
        for ident in self.order:
            if self.trackable.get(ident) and ident not in self.achieved:
                return {"identity": ident, "task": self._task.get(ident, "")}
        return None

    def progress_line(self) -> str:
        """One line of scored truth. The score is the COUNT of verified milestones."""
        nxt = self.next_target()
        head = (f"Environment-verified progress: {len(self.achieved)}/"
                f"{self.num_trackable()} milestones. Score = COUNT verified; only the "
                f"environment verifies one.")
        if nxt is None:
            return head + " ALL MILESTONES VERIFIED."
        return head + f" First unmet: `{nxt['identity']}` ({nxt['task'][:90]})."

    def progress_block(self) -> str:
        """The full ordered checklist for the prompt. Showing the unmet ones is what
        stops the agent re-deriving the task from scratch every turn."""
        lines = []
        for ident in self.order:
            task = self._task.get(ident, "")
            if not self.trackable.get(ident):
                lines.append(f"  [?] {ident} (not machine-verifiable; do it, but it "
                             f"cannot be checked) {task}")
            elif ident in self.achieved:
                lines.append(f"  [x] {ident} (step {self.achieved[ident]}) {task}")
            else:
                lines.append(f"  [ ] {ident} <- {task}")
        return "\n".join(lines)

    def summary(self) -> dict[str, Any]:
        return {
            "task": self.task_name,
            "milestones_achieved": len(self.achieved),
            "total_milestones": len(self.cfg),
            "completion_rate": (len(self.achieved) / len(self.cfg)) if self.cfg else 0.0,
            "achieved": dict(self.achieved),
            "order": self.order,
        }


def inventory_counts(info: dict) -> dict[str, int]:
    """`info['inventory']` aggregated to {item: total count}.

    The wire shape is **slot-keyed** ({"0": {"type": ..., "quantity": ...}, ...} across
    36 slots -- see benchmark_gen/utils.py), so aggregating is required, not cosmetic.
    `air`/`none` are dropped: empty slots are reported as such, and a model shown the raw
    dict reliably concludes it is carrying thirty air.
    """
    inv = info.get("inventory")
    if not isinstance(inv, dict):
        return {}
    out: dict[str, int] = {}
    for slot in inv.values():
        if not isinstance(slot, dict):
            continue
        name = slot.get("type")
        if not name or name in ("air", "none"):
            continue
        try:
            qty = int(_num(slot.get("quantity", 0)))
        except (TypeError, ValueError):
            continue
        if qty > 0:
            out[str(name)] = out.get(str(name), 0) + qty
    return out


def hotbar_line(info: dict) -> str:
    """What is in each hotbar slot. Slots 0-8 are the hotbar and `hotbar.1`..`hotbar.9`
    select them; the agent has no other way to learn which number to press."""
    inv = info.get("inventory")
    if not isinstance(inv, dict):
        return "unknown"
    parts = []
    for slot in range(9):
        entry = inv.get(slot) or inv.get(str(slot))
        if not isinstance(entry, dict):
            continue
        name = entry.get("type")
        if not name or name in ("air", "none"):
            continue
        try:
            qty = int(_num(entry.get("quantity", 0)))
        except (TypeError, ValueError):
            continue
        if qty > 0:
            parts.append(f"hotbar.{slot + 1}={name}x{qty}")
    return ", ".join(parts) or "empty"


def vitals(info: dict) -> str:
    """Health and food, when the server reports them; silent degradation otherwise."""
    bits = []
    for key, label in (("health", "health"), ("food_level", "food"), ("food", "food")):
        v = info.get(key)
        if v is None:
            continue
        try:
            bits.append(f"{label}={_num(v):.0f}/20")
        except (TypeError, ValueError):
            continue
        if label == "food":
            break
    return " ".join(bits) or "unknown"


def location(info: dict) -> dict[str, float] | None:
    """`info['player_pos']` as the {x,y,z,pitch,yaw} shape memory.state_line wants."""
    pos = info.get("player_pos")
    if not isinstance(pos, dict) or pos.get("x") is None:
        return None

    def g(name: str) -> float:
        v = pos.get(name)
        try:
            return _num(v) if v is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    return {"x": g("x"), "y": g("y"), "z": g("z"), "pitch": g("pitch"), "yaw": g("yaw")}
