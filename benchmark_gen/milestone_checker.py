from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from loguru import logger

from benchmark_gen.utils import evaluate_milestone_rule, attach_judge_queries_to_action

_EVENT_KEYS = {"craft_item", "mine_block", "use_item", "pickup", "kill_entity"}

def _build_state_for_evaluation(info: dict, baseline: dict) -> dict:
    """
    Return a copy of *info* with event counters adjusted by *baseline* so that
    evaluate_milestone_rule sees deltas-since-reset rather than absolute totals.

    All non-event keys are passed through unchanged.
    """
    state = dict(info)
    for key in _EVENT_KEYS:
        raw = info.get(key, {})
        base = baseline.get(key, {})
        if isinstance(raw, dict):
            state[key] = {
                k: float(v) - float(base.get(k, 0))
                for k, v in raw.items()
            }
        else:
            state[key] = {}
    return state


# ---------------------------------------------------------------------------
# MilestoneChecker
# ---------------------------------------------------------------------------

class MilestoneChecker:
    """Evaluates milestone rules against the info dict returned each step.

    Parameters
    ----------
    milestones : list
        The "milestones" array from milestones.json.
    """

    def __init__(self, milestones: List[dict]):
        self._milestones = milestones
        # Runtime state
        self._baseline: dict = {}
        self._spawn_pos: dict = {"x": 0.0, "y": 0.0, "z": 0.0}
        self._completed: List[bool] = [False] * len(milestones)
        self._step_completed: List[Optional[int]] = [None] * len(milestones)
        self._current_step: int = 0
        # Cache the full milestones spec dict for attach_judge_queries_to_action
        self._milestone_spec: dict = {"milestones": milestones}

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @classmethod
    def from_file(cls, milestones_path: str) -> "MilestoneChecker":
        """Load from a standalone milestones.json file."""
        path = Path(milestones_path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        milestones = data.get("milestones", data) if isinstance(data, dict) else data
        return cls(milestones)

    @classmethod
    def from_metadata(cls, metadata_path: str) -> "MilestoneChecker":
        """Load from the 'milestones' key inside a metadata.json file.

        Also looks for a sibling milestones.json in the same directory.
        """
        meta_path = Path(metadata_path)
        # Try sibling milestones.json first
        sibling = meta_path.parent / "milestones.json"
        if sibling.exists():
            return cls.from_file(str(sibling))

        # Fall back to inline milestones key in metadata
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw = data.get("milestones", {})
        milestones = raw.get("milestones", raw) if isinstance(raw, dict) else raw
        if not milestones:
            raise ValueError(f"No milestones found in {metadata_path} or sibling milestones.json")
        return cls(milestones)

    # ------------------------------------------------------------------
    # Episode lifecycle
    # ------------------------------------------------------------------

    def reset(self, info: dict, spawn_pos: Optional[dict] = None) -> None:
        """Call once after env.reset() (after loading-command noop steps) to
        record baselines and the player's spawn position.

        Parameters
        ----------
        info : dict
            The info dict returned by the last env.step() during the loading
            phase (must include player_pos and event counters).
        spawn_pos : dict, optional
            Explicit spawn position {"x":…, "y":…, "z":…}.
            If None, the current player_pos is used as the spawn point.
        """
        # Capture spawn point
        if spawn_pos is not None:
            self._spawn_pos = {
                "x": float(spawn_pos.get("x", 0)),
                "y": float(spawn_pos.get("y", 0)),
                "z": float(spawn_pos.get("z", 0)),
            }
        else:
            pos = info.get("player_pos", {})
            self._spawn_pos = {
                "x": float(pos.get("x", 0)),
                "y": float(pos.get("y", 0)),
                "z": float(pos.get("z", 0)),
            }

        # Capture baseline event counters
        self._baseline = {}
        for key in _EVENT_KEYS:
            raw = info.get(key, {})
            if isinstance(raw, dict):
                self._baseline[key] = {k: float(v) for k, v in raw.items()}
            else:
                self._baseline[key] = {}

        # Reset completion state
        self._completed = [False] * len(self._milestones)
        self._step_completed = [None] * len(self._milestones)
        self._current_step = 0

        logger.info(
            f"[MilestoneChecker] Reset. Spawn={self._spawn_pos}  "
            f"Milestones={len(self._milestones)}"
        )

    # ------------------------------------------------------------------
    # Per-step evaluation
    # ------------------------------------------------------------------

    def check(self, info: dict) -> List[dict]:
        """Evaluate all milestones against the current info dict.

        Internally builds a baseline-adjusted state and delegates each rule
        to evaluate_milestone_rule() from agents.utils (single source of
        truth for coordinate-frame handling and spatial evaluation).

        Milestones with an empty "rules" list are treated as "no milestone
        available" (no_milestone=True).  They are never marked completed and
        are excluded from the all_done() / num_completed() counts.

        Returns a list of status dicts (one per milestone), e.g.:
        [
          {"milestone_id": "craft_iron_sword", "task": "craft iron sword",
           "no_milestone": False, "completed": True,
           "rules_passed": [True], "step_completed": 12},
          {"milestone_id": "build_nether_portal", "task": "build nether portal",
           "no_milestone": True, "completed": False,
           "rules_passed": [], "step_completed": None},
          ...
        ]
        """
        self._current_step += 1

        # Build a state dict with baseline-adjusted event counters so that
        # evaluate_milestone_rule sees deltas-since-reset.
        state = _build_state_for_evaluation(info, self._baseline)

        results = []
        for i, milestone in enumerate(self._milestones):
            rules = milestone.get("rules", [])
            no_milestone = len(rules) == 0

            if no_milestone:
                # No verifiable rule — skip evaluation, never mark completed.
                results.append({
                    "milestone_id": milestone.get("milestone_id", f"milestone_{i}"),
                    "task": milestone.get("task", ""),
                    "description": milestone.get("description", ""),
                    "no_milestone": True,
                    "completed": False,
                    "rules_passed": [],
                    "step_completed": None,
                })
                continue

            rules_passed = []
            for rule in rules:
                rule_type = rule.get("type", "")
                if not rule_type:
                    rules_passed.append(False)
                    continue
                try:
                    passed = evaluate_milestone_rule(
                        rule=rule,
                        state=state,
                        coordinate_origin=self._spawn_pos,
                    )
                except Exception as e:
                    logger.warning(
                        f"[MilestoneChecker] Error evaluating rule '{rule_type}' "
                        f"in milestone '{milestone.get('milestone_id')}': {e}"
                    )
                    passed = False
                rules_passed.append(passed)

            all_passed = all(rules_passed)

            # Milestone latches once completed (monotonic)
            if all_passed and not self._completed[i]:
                self._completed[i] = True
                self._step_completed[i] = self._current_step
                logger.success(
                    f"[MilestoneChecker] ✅ Milestone '{milestone.get('milestone_id')}' "
                    f"(task='{milestone.get('task')}') completed at step {self._current_step}!"
                )

            results.append({
                "milestone_id": milestone.get("milestone_id", f"milestone_{i}"),
                "task": milestone.get("task", ""),
                "description": milestone.get("description", ""),
                "no_milestone": False,
                "completed": self._completed[i],
                "rules_passed": rules_passed,
                "step_completed": self._step_completed[i],
            })

        return results

    # ------------------------------------------------------------------
    # Convenience queries
    # ------------------------------------------------------------------

    def _trackable_indices(self) -> List[int]:
        """Indices of milestones that have at least one rule (excludes no_milestone tasks)."""
        return [
            i for i, m in enumerate(self._milestones)
            if len(m.get("rules", [])) > 0
        ]

    def all_done(self) -> bool:
        """True when every trackable milestone (rules non-empty) has been completed."""
        indices = self._trackable_indices()
        if not indices:
            return False  # No trackable milestones — never consider "all done"
        return all(self._completed[i] for i in indices)

    def num_completed(self) -> int:
        """Number of trackable milestones completed so far (excludes no_milestone tasks)."""
        return sum(self._completed[i] for i in self._trackable_indices())

    def num_trackable(self) -> int:
        """Total number of milestones that have rules (excludes no_milestone tasks)."""
        return len(self._trackable_indices())

    def summary(self) -> str:
        """One-line human-readable summary."""
        done = self.num_completed()
        total = self.num_trackable()
        no_ms = len(self._milestones) - total
        ids = [
            self._milestones[i].get("milestone_id", f"#{i}")
            for i in self._trackable_indices() if self._completed[i]
        ]
        no_ms_note = f"  (+{no_ms} no-milestone)" if no_ms else ""
        return f"Milestones {done}/{total} done: {ids}{no_ms_note}"

    # ------------------------------------------------------------------
    # Action augmentation for voxel / mob queries
    # ------------------------------------------------------------------

    def augment_action_with_queries(self, action: dict, info: Optional[dict] = None) -> dict:
        """Inject voxel and mob query boxes into the action dict.

        The server only populates info["voxels"] and info["mobs"] when the
        corresponding query box is present in the step action.

        Query boxes are expressed in PLAYER-RELATIVE coordinates (as required
        by the Minecraft simulator), so the current player position from *info*
        is needed for the conversion.  If *info* is None or does not contain
        player_pos, the query boxes will fall back to absolute coordinates
        (which may be incorrect — always pass the latest info).

        Delegates to attach_judge_queries_to_action() from agents.utils, which
        handles all coordinate-frame conversions correctly.

        Milestones that are already completed are excluded from the query boxes
        to avoid unnecessary data transfer.

        Parameters
        ----------
        action : dict
            The agent's action dict (will be shallow-copied, not mutated).
        info : dict, optional
            The latest info dict (needed for player-relative coord conversion).

        Returns
        -------
        dict
            A copy of *action* with voxel/mob query fields injected if needed.
        """
        # Build a reduced milestone spec that only includes non-completed milestones
        pending_milestones = [
            m for i, m in enumerate(self._milestones)
            if not self._completed[i]
        ]
        if not pending_milestones:
            return dict(action)  # nothing to query

        pending_spec = {"milestones": pending_milestones}

        return attach_judge_queries_to_action(
            action=action,
            milestone_spec=pending_spec,
            coordinate_origin=self._spawn_pos,
            state=info or {},
        )
