"""Parse and validate the `actions.json` one turn produces.

Ported from MCU-AgentBeats' `mcu_worldmodel/actions.py`. Two entry shapes, because the
agent works at two levels:

    {"action": {"forward": 1}, "repeat": 20}          a raw action, held N ticks
    {"procedure": "go_to", "args": {"x": 10, "z": -3}} a named macro from procedures.py

The raw form is prolong_mc/actions.py's contract unchanged. The procedure form is what
lets one turn cover a stretch of the episode instead of a step of it.

Validation is deliberately lenient about *entries* and strict about *keys*: an
unrecognised key is dropped with a warning and the rest of the entry still runs, because
a whole plan discarded over one typo costs the episode a turn and teaches the model
nothing about which key was wrong. What is never lenient is the step cap -- a turn cannot
run more environment steps than it was budgeted, or the plan queue stops being a bound on
how long the agent goes without looking.

The caps are scaled to this repo's 300-step episodes (MCU ran 40/200/400 against 6,000+
step budgets): 20 entries, repeat <= 50, <= 80 ticks a plan, so a plan can cover one
whole leg of a hop while the agent still looks at the world several times per episode.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from loguru import logger

from mc_agent.worldmodel import procedures as P

ENTRY_CAP = 20
REPEAT_CAP = 50
STEP_CAP = 80

#: Keys of the real env action space (env/minerl_sandbox.py). `ESC` is among them: it is
#: the documented end-of-episode signal, and it is gated by the AGENT (a premature press
#: is a false completion claim -- see agent._gate_esc), not silently stripped here.
VALID_KEYS = {
    "ESC", "attack", "back", "forward", "jump", "left", "right", "sneak", "sprint",
    "use", "inventory", "drop", "pickItem", "swapHands",
    *(f"hotbar.{i}" for i in range(1, 10)),
}

#: In the action dict on the wire but not the agent's to set: `mobs`/`voxels` are the
#: milestone checker's observation-region queries, injected by the runner.
FORBIDDEN_KEYS = {"chat", "mobs", "voxels", "mob_query", "voxel_query"}

#: Verbs models reliably hallucinate from other Minecraft APIs. Naming them beats a
#: generic unknown-key note: the agent is told the verb does not exist here at all.
UNSUPPORTED_KEYS = {"craft", "nearbyCraft", "nearbySmelt", "smelt", "place", "equip"}


class ActionPlan:
    def __init__(self, entries: list[dict[str, Any]], steps: list[dict[str, Any]],
                 notes: list[str] | None = None) -> None:
        self.entries = entries
        self.steps = steps
        self.notes = notes or []

    def __len__(self) -> int:
        return len(self.steps)

    def __bool__(self) -> bool:
        return bool(self.steps)


def _clean_action(raw: dict[str, Any], notes: list[str]) -> dict[str, Any]:
    a = P.noop()
    for key, value in raw.items():
        if key == "camera":
            try:
                pitch, yaw = float(value[0]), float(value[1])
            except (TypeError, ValueError, IndexError):
                notes.append(f"bad camera value {value!r}, ignored")
                continue
            # Pitch is an absolute clamp in-game; yaw wraps. Normalising here rather than
            # rejecting keeps a 270-degree turn meaning what the model meant by it.
            pitch = max(-90.0, min(90.0, pitch))
            yaw = ((yaw + 180.0) % 360.0) - 180.0
            a["camera"] = [pitch, yaw]
        elif key in VALID_KEYS:
            try:
                a[key] = 1 if int(value) else 0
            except (TypeError, ValueError):
                notes.append(f"non-numeric value for {key!r}, ignored")
        elif key in FORBIDDEN_KEYS:
            notes.append(f"`{key}` is not available to you; dropped")
        elif key in UNSUPPORTED_KEYS:
            notes.append(f"`{key}` does not exist in this action space; dropped. "
                         f"There is no direct craft/place verb -- act through the "
                         f"primitive keys and procedures")
        else:
            notes.append(f"unknown action key {key!r}; dropped")
    # Mutually exclusive pairs, resolved rather than rejected: pressing both is a no-op
    # in-game, so silently keeping them would spend ticks doing nothing.
    for x, y in (("forward", "back"), ("left", "right")):
        if a[x] and a[y]:
            a[x] = a[y] = 0
            notes.append(f"`{x}`+`{y}` cancel out; both cleared")
    hot = [k for k in a if k.startswith("hotbar.") and a[k]]
    if len(hot) > 1:
        for k in hot[1:]:
            a[k] = 0
        notes.append(f"multiple hotbar slots set; kept {hot[0]}")
    return a


def _expand_custom(name: str, custom_dir: Path | None,
                   repeat_cap: int) -> tuple[list[dict[str, Any]], str]:
    """A procedure the model wrote itself: `<custom_dir>/<name>.json`, a list of raw
    `{"action": {...}, "repeat": N}` entries under key "entries". Built-in names win
    (this is only consulted when the registry misses); nesting is rejected so a skill
    cannot recurse. The cap arithmetic downstream is unchanged -- a custom skill pays
    for its ticks like any hand-written plan, it just does not cost a turn to restate."""
    if custom_dir is None or not re.fullmatch(r"[A-Za-z0-9_\-]{1,48}", name or ""):
        return [], ""
    path = custom_dir / f"{name}.json"
    if not path.is_file():
        return [], ""
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [], f"custom procedure {name!r} unreadable: {e}"
    entries = obj.get("entries") if isinstance(obj, dict) else obj
    if not isinstance(entries, list) or not entries:
        return [], f"custom procedure {name!r}: expected a non-empty list under 'entries'"
    out: list[dict[str, Any]] = []
    for e in entries[:12]:
        if not isinstance(e, dict) or not isinstance(e.get("action"), dict):
            return [], (f"custom procedure {name!r}: every entry must be a raw "
                        f"{{'action': ..., 'repeat': N}} object (no nested procedures)")
        try:
            rep = max(1, min(repeat_cap, int(e.get("repeat", 1))))
        except (TypeError, ValueError):
            rep = 1
        notes: list[str] = []
        cleaned = _clean_action(e["action"], notes)
        for _ in range(rep):
            out.append(dict(cleaned))
    if len(entries) > 12:
        return out, f"custom procedure {name!r} truncated to its first 12 entries"
    return out, ""


def parse_actions(raw_text: str, *, entry_cap: int = ENTRY_CAP,
                  repeat_cap: int = REPEAT_CAP, step_cap: int = STEP_CAP,
                  info: dict[str, Any] | None = None,
                  custom_dir: Path | None = None) -> ActionPlan:
    """Return the validated plan. An empty plan means the turn produced nothing usable.

    The budget is charged in *ticks*, not list entries: a closed-loop marker (`_goto`,
    `_chop`) is one queue entry that the runner resolves over up to `_cost` ticks, so it
    is charged its worst case here. Charging it as 1 would let a plan of markers run
    several times the step cap before the agent looks again.
    """
    notes: list[str] = []
    try:
        obj = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.warning(f"[actions] actions.json malformed: {exc}")
        return ActionPlan([], [], [f"actions.json did not parse: {exc}"])

    entries = obj.get("actions") if isinstance(obj, dict) else obj
    if not isinstance(entries, list):
        return ActionPlan([], [], ["expected a list under key 'actions'"])

    kept: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    used = 0
    for entry in entries[:entry_cap]:
        if not isinstance(entry, dict):
            notes.append(f"skipped non-object entry: {entry!r}")
            continue
        room = step_cap - used
        if room <= 0:
            notes.append(f"step cap {step_cap} reached; remaining entries dropped")
            break

        if "procedure" in entry:
            name = str(entry["procedure"])
            args = entry.get("args") or {}
            if not isinstance(args, dict):
                notes.append(f"`args` for {name!r} must be an object; ignored")
                args = {}
            expanded, note = P.expand(name, info=info, **args)
            if not expanded and note.startswith("unknown procedure"):
                custom, cnote = _expand_custom(name, custom_dir, repeat_cap)
                if custom or cnote:
                    expanded, note = custom, cnote
            if note:
                # A procedure's own note is the most useful thing the turn produces
                # when it produces nothing else, so it reaches the log either way.
                notes.append(note)
            if not expanded:
                continue
            cut: list[dict[str, Any]] = []
            cost = 0
            for s in expanded:
                c = max(0, int(s.get("_cost", 1)))
                if cost + c > room:
                    notes.append(f"procedure {name!r} truncated by the step cap")
                    break
                cut.append(s)
                cost += c
            if not cut:
                continue
            # `steps` is the tick budget (what describe_entry reports); `items` is how
            # many queue entries were actually appended -- a closed-loop marker is one
            # item worth many ticks, and the runner's (action, entry) pairing walks items.
            kept.append({"procedure": name, "args": args, "steps": cost,
                         "items": len(cut)})
            steps.extend(cut)
            used += cost
            continue

        if not isinstance(entry.get("action"), dict):
            notes.append(f"entry has neither `procedure` nor `action`: {entry!r}")
            continue
        try:
            rep = max(1, min(repeat_cap, int(entry.get("repeat", 1))))
        except (TypeError, ValueError):
            notes.append(f"non-numeric repeat in {entry!r}; using 1")
            rep = 1
        action = _clean_action(entry["action"], notes)
        if rep > room:
            notes.append(f"repeat {rep} truncated to {room} by the step cap")
            rep = room
        kept.append({"action": dict(entry["action"]), "repeat": rep})
        steps.extend(dict(action) for _ in range(rep))
        used += rep

    if len(entries) > entry_cap:
        notes.append(f"{len(entries)} entries submitted; only the first {entry_cap} ran")
    for n in notes:
        logger.warning(f"[actions] {n}")
    return ActionPlan(kept, steps, notes)


def describe_entry(entry: dict[str, Any]) -> str:
    """Compact rendering for the log -- only what the agent actually set."""
    if "procedure" in entry:
        args = ",".join(f"{k}={v}" for k, v in (entry.get("args") or {}).items())
        return f"[ACTION] {entry['procedure']}({args}) -> {entry['steps']} ticks"
    act = {k: v for k, v in entry["action"].items()
           if v not in (0, [0, 0], [0.0, 0.0])}
    return f"[ACTION] {json.dumps(act, separators=(',', ':'))} x{entry['repeat']}"
