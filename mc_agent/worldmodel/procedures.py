"""Procedures: named action macros the model calls instead of steering blind.

Ported from MCU-AgentBeats' `mcu_worldmodel/procedures.py`, minus the GUI/cursor layer.
That layer existed because MCU's tasks were crafting pipelines and MinecraftSim exposes
no craft action; this repo's scenes (bench_4hop*) are scored on navigation, collection
and placement rules, so what transfers is the movement/mining library and the closed-loop
marker idiom: a macro that depends on run-time state compiles to ONE queue entry (a
marker dict) that the agent resolves tick by tick against ground truth, instead of a
blind pre-computed burst.

Every action a procedure emits is an ordinary env action through the same env.step; the
milestones still only fire when the scene checker verifies them. It is a skill library,
and the `procedures/` box in the memory layout: induction can add to it, and a procedure
that stops working is a belief to be revised like any other.

Markers and their resolvers (mc_agent/worldmodel/agent.py):
    _goto     go_to        walk to (x, z), heading re-derived from [STATE] every tick
    _lookabs  look_abs     steer to an absolute (pitch, yaw)
    _facept   face_point   steer the crosshair onto a world coordinate
    _chop     chop_tree    hold attack, stop the moment wood actually lands
    _dig      dig_down     hold attack, stop at a target depth
    _seq      mine seqs    play a fixed step list (kept a marker so a sentinel can
                           interrupt it; MCU's ore-watcher hung off exactly this hook)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable

from mc_agent.worldmodel import camera as _camera

#: Every key of this repo's env action space (env/minerl_sandbox.py). `ESC` is real here
#: -- the documented "I am finished" signal -- and deliberately absent from `noop`'s
#: zeroed keys would be wrong: the harness reads action.get("ESC") every step.
ENV_KEYS = (
    "ESC", "attack", "back", "drop", "forward", "jump", "left", "pickItem", "right",
    "sneak", "sprint", "swapHands", "use", "inventory",
    *(f"hotbar.{i}" for i in range(1, 10)),
)


def noop() -> dict[str, Any]:
    """One env action with nothing pressed. Built fresh each call because these go into
    a queue the runner mutates."""
    a: dict[str, Any] = {k: 0 for k in ENV_KEYS}
    a["camera"] = [0.0, 0.0]
    return a


def act(**kw) -> dict[str, Any]:
    a = noop()
    for k, v in kw.items():
        key = k.replace("hotbar_", "hotbar.")
        if key == "camera":
            a["camera"] = [float(v[0]), float(v[1])]
        else:
            a[key] = int(v)
    return a


def repeat(action: dict[str, Any], n: int) -> list[dict[str, Any]]:
    return [dict(action) for _ in range(max(1, n))]


@dataclass
class Procedure:
    """A named macro. `build` returns the env actions; `preconditions` is prose the
    prompt shows so the agent knows when calling it is pointless."""
    name: str
    doc: str
    build: Callable[..., Any]
    preconditions: str = ""
    params: dict[str, str] = field(default_factory=dict)
    #: True when `build` takes the live `info` first and returns (actions, note).
    needs_info: bool = False


# -- movement and looking -------------------------------------------------

def look(pitch: float = 0.0, yaw: float = 0.0) -> list[dict[str, Any]]:
    """Turn BY a relative amount. Turning and moving are never combined here: a yaw
    change and `forward` in the same tick curve the path into an arc, which is the single
    most common reason a long traverse ends up back where it started."""
    return [act(camera=[p, y]) for p, y in _camera.plan(pitch, yaw)] or [noop()]


def look_abs(pitch: float | None = None, yaw: float | None = None,
             ticks: int = 20) -> list[dict[str, Any]]:
    """Steer to an ABSOLUTE orientation, closed-loop against [STATE] every tick.

    `look` turns BY an amount and is only right when the starting pose is known at plan
    time. This marker reads the measured pitch/yaw as it runs, so "face yaw 90" means
    the same thing from any starting pose. `None` leaves that axis alone."""
    la: dict[str, Any] = {"remaining": max(1, int(ticks))}
    la["pitch"] = None if pitch is None else max(-90.0, min(90.0, float(pitch)))
    la["yaw"] = None if yaw is None else float(yaw)
    return [{"_lookabs": la, "_cost": max(1, int(ticks))}]


def face_point(x: float = 0.0, y: float = 0.0, z: float = 0.0,
               ticks: int = 20) -> list[dict[str, Any]]:
    """Steer the crosshair onto a world coordinate, re-derived from [STATE] every tick.

    The closed-loop form of MCU's plan-time `look_at`: aiming at a KNOWN place is
    trigonometry against ground truth, and doing it at run time means "face the chest at
    (10, 71, -3)" is correct no matter where the preceding entries left the player --
    which is exactly the shape of this benchmark's `position_near_with_facing` rules.
    Aims from the eye (feet + 1.62); a block's centre is its corner + 0.5 on each axis."""
    fp = {"x": float(x), "y": float(y), "z": float(z), "remaining": max(1, int(ticks))}
    return [{"_facept": fp, "_cost": max(1, int(ticks))}]


def bearing(pos: dict[str, float], x: float, z: float) -> float:
    """The yaw that faces (x, z) from `pos`. Minecraft convention: yaw 0 = +z (south),
    positive turns right; hence atan2(-dx, dz). Shared by the _goto and _facept
    resolvers so the two cannot disagree about what a heading means."""
    return math.degrees(math.atan2(-(x - pos["x"]), z - pos["z"]))


def travel(n: int = 40, sprint: bool = True) -> list[dict[str, Any]]:
    """Straight-line travel in the direction currently faced. Jump is held with forward
    so a one-block rise does not silently stop the traverse -- `moved=0.00` for 40 ticks
    is the signature of walking into a wall."""
    return repeat(act(forward=1, sprint=1 if sprint else 0, jump=1), n)


def go_to(x: float = 0.0, z: float = 0.0, within: float = 1.5, n: int = 120
          ) -> list[dict[str, Any]]:
    """Walk to a world coordinate, correcting the heading against [STATE] each tick.

    `travel` walks the direction you happened to be facing; terrain deflects it and the
    error is only visible a model turn later. This closes the loop: the position is
    ground truth, so the heading to a *known place* is arithmetic, re-done every tick.
    Stops within `within` blocks (horizontal), or after `n` ticks with a [NOTE] saying
    where it actually got to -- repeated no-progress ticks mean a wall or a drop, and
    the runner says so rather than walking into it for the rest of the budget."""
    return [{"_goto": {"x": float(x), "z": float(z), "within": max(0.5, float(within)),
                       "remaining": max(1, int(n)), "stuck": 0, "last": None},
             "_cost": max(1, int(n))}]


# -- mining and interaction -----------------------------------------------

def _mine_seq(steps: list[dict[str, Any]], watch: bool = False) -> list[dict[str, Any]]:
    """Wrap a mining sequence in a marker so the runner resolves it tick by tick.

    Kept a marker rather than inlined raw steps for two reasons that both bit MCU: raw
    pure-attack holds are cut by the break-refund rule (these sequences re-aim and must
    not be), and a marker is the hook a sentinel interrupts -- MCU's ore-watcher lived
    here, and any future frame-watcher for this benchmark goes in the same place."""
    return [{"_seq": {"steps": steps, "i": 0, "watch": bool(watch)},
             "_cost": len(steps)}]


def mine_forward(n: int = 60) -> list[dict[str, Any]]:
    """Hold attack on whatever the crosshair is on, as a sequence (not a raw hold, so it
    runs its aim through multiple blocks instead of being cut at the first break)."""
    return _mine_seq(repeat(act(attack=1), n))


def dig_down(n: int = 40, until_y: float | None = None) -> list[dict[str, Any]]:
    """Straight down. `until_y` makes the depth the target instead of the tick count:
    the runner stops the moment [STATE] y reaches it, so "dig to y=20" is one entry
    rather than a guessed number of fixed slices."""
    dig = [{"_dig": {"remaining": max(1, int(n)),
                     "until_y": None if until_y is None else float(until_y)},
            "_cost": max(1, int(n))}]
    return look(pitch=60) + dig


def stair_down(depth: int = 10) -> list[dict[str, Any]]:
    """Descend on a walkable staircase: two blocks out, one step down, repeat.

    The safe descent -- a staircase cannot be fallen down and can be walked back up
    unaided. The opening aim is ABSOLUTE (pitch 38): entered at pitch 25 a relative turn
    dug MCU's staircase at 63, and entered at pitch 90 it clamped into digging straight
    down, the exact shaft this macro exists to avoid."""
    out: list[dict[str, Any]] = []
    for _ in range(max(1, int(depth))):
        out += repeat(act(attack=1), 18)        # the step's two blocks, head then foot
        out += repeat(act(forward=1), 6)        # walk onto the new step
        out += [noop(), noop()]
    return look_abs(pitch=38.0, ticks=20) + _mine_seq(out)


def chop_tree(n: int = 80, until_logs: int = 1) -> list[dict[str, Any]]:
    """Hold attack on a trunk, stopping the moment wood actually breaks.

    Keyed on the `mine_block` statistic: the block breaking is the instant the aim is
    proven. A chop aimed at leaves or sky is ended early too -- two non-wood breaks, or
    75 ticks with nothing breaking, answer in ticks what a blind hold only reveals at the
    [INV] line 180 ticks later. `until_logs=0` restores fixed duration."""
    return [{"_chop": {"remaining": max(1, int(n)), "until": max(0, int(until_logs))},
             "_cost": max(1, int(n))}]


def click(button: str = "use", hold: int = 2) -> list[dict[str, Any]]:
    key = "use" if button != "attack" else "attack"
    return repeat(act(**{key: 1}), max(1, int(hold))) + [noop()]


def place_block(pitch_down: float = 45.0) -> list[dict[str, Any]]:
    """Look down and place the selected hotbar item on the ground ahead."""
    return look(pitch=pitch_down) + click("use", hold=1)


def equip_hotbar(slot: int = 1) -> list[dict[str, Any]]:
    slot = max(1, min(9, int(slot)))
    return [act(**{f"hotbar_{slot}": 1}), noop()]


def end_episode() -> list[dict[str, Any]]:
    """Declare the task complete: emit ESC=1, the documented end-of-episode signal.

    This is a completion claim, and it is gated like one: while any milestone is
    unverified the runner refuses the press, tells you which milestones are open, and
    locks the goals you believed done (see discipline.check_claim). Press it only when
    the checklist shows ALL verified."""
    return [act(ESC=1)]


# -- the registry ---------------------------------------------------------

REGISTRY: dict[str, Procedure] = {}


def register(p: Procedure) -> None:
    REGISTRY[p.name] = p


for _p in [
    Procedure("go_to", "walk to a world (x, z), re-aiming from [STATE] every tick; "
              "stops within `within` blocks or notes where it got stuck",
              go_to, params={"x": "x", "z": "z", "within": "blocks, default 1.5",
                             "n": "tick budget, default 120"}),
    Procedure("face_point", "steer the crosshair onto a world (x, y, z), closed-loop; "
              "use after go_to for stand-near-AND-face targets",
              face_point, params={"x": "x", "y": "y", "z": "z",
                                  "ticks": "budget, default 20"}),
    Procedure("look", "turn BY a relative (pitch, yaw) in degrees; +pitch looks down, "
              "+yaw turns right", look,
              params={"pitch": "deg", "yaw": "deg"}),
    Procedure("look_abs", "steer to an ABSOLUTE (pitch, yaw) read from [STATE]; None "
              "leaves an axis alone", look_abs,
              params={"pitch": "deg or null", "yaw": "deg or null",
                      "ticks": "budget, default 20"}),
    Procedure("travel", "walk straight ahead n ticks (jump held, sprint optional)",
              travel, params={"n": "ticks, default 40", "sprint": "default true"}),
    Procedure("chop_tree", "hold attack on a trunk; stops the moment wood breaks, or "
              "early with a [NOTE] when the aim is wrong",
              chop_tree, preconditions="crosshair on a trunk face, within ~3 blocks",
              params={"n": "max ticks, default 80", "until_logs": "default 1"}),
    Procedure("mine_forward", "mine whatever the crosshair is on, n ticks",
              mine_forward, params={"n": "ticks, default 60"}),
    Procedure("dig_down", "look down 60 and dig; stops at until_y if given",
              dig_down, params={"n": "max ticks, default 40", "until_y": "target y or null"}),
    Procedure("stair_down", "walkable staircase descent, ~26 ticks per block of depth",
              stair_down, params={"depth": "blocks, default 10"}),
    Procedure("place_block", "look down and place the selected hotbar item",
              place_block, preconditions="a placeable block selected in the hotbar",
              params={"pitch_down": "deg, default 45"}),
    Procedure("equip_hotbar", "select hotbar slot 1-9", equip_hotbar,
              params={"slot": "1-9"}),
    Procedure("end_episode", "declare the task complete (ESC=1); refused and "
              "penalised while any milestone is unverified", end_episode),
]:
    register(_p)


def expand(name: str, info: dict[str, Any] | None = None, **kwargs
           ) -> tuple[list[dict[str, Any]], str]:
    """Turn a procedure call into env actions. Returns (actions, note)."""
    p = REGISTRY.get(str(name))
    if p is None:
        known = ", ".join(REGISTRY)
        return [], f"unknown procedure {name!r}; available: {known}"
    try:
        if p.needs_info:
            out = p.build(info or {}, **kwargs)
        else:
            out = p.build(**kwargs)
    except TypeError as e:
        sig = ", ".join(f"{k}=<{v}>" for k, v in p.params.items())
        return [], f"bad arguments for {name}({sig}): {e}"
    except Exception as e:
        return [], f"procedure {name!r} failed to build: {e}"
    if isinstance(out, tuple):
        return out
    return out, ""


def reference() -> str:
    """The procedure list as the prompt shows it."""
    lines = []
    for p in REGISTRY.values():
        args = ", ".join(f"{k}=<{v}>" for k, v in p.params.items())
        lines.append(f"- `{p.name}({args})` -- {p.doc}"
                     + (f"  [{p.preconditions}]" if p.preconditions else ""))
    return "\n".join(lines)
