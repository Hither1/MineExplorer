"""Camera-delta planning: split a large turn into per-tick deltas.

The MCU original composes every turn from the 11 mu-law-quantised values MinecraftSim's
`action_type="agent"` encoder can deliver. This repo's env is the HTTP sandbox
(env/minerl_sandbox.py), whose action space takes raw float degrees in [-180, 180] and
whose server steps the sim with them directly -- the arms that run today (default /
hypothesis / prolong) all emit plain float deltas and turn by the amounts they ask for.
So `plan` here only chunks, it does not quantise.

The seam is kept module-shaped on purpose: if a smoke run ever measures the server
rounding deltas (the MCU failure was 4.32 requested -> 3.215 delivered), the composition
logic belongs here, behind the same `plan()` signature, and nothing else changes.
"""
from __future__ import annotations

# Per-tick ceiling. The env accepts up to 180, but a 30-degree tick is what the repo's
# other agents use for a deliberate turn, and holding to it keeps every intermediate
# frame recognisable -- a 170-degree snap leaves the log with two unrelated views and
# nothing between them.
MAX_STEP_DEG = 30.0


def plan(pitch: float, yaw: float) -> list[tuple[float, float]]:
    """Split (pitch, yaw) into per-tick (pitch, yaw) deltas, largest axis first.

    Yaw is normalised into [-180, 180) so "turn 270" means the 90-degree turn the other
    way, matching actions._clean_action. Pitch is clamped conservatively to [-180, 180]
    here; the in-game absolute clamp at +/-90 is the env's own behaviour.
    """
    yaw = ((float(yaw) + 180.0) % 360.0) - 180.0
    pitch = max(-180.0, min(180.0, float(pitch)))
    steps: list[tuple[float, float]] = []
    p, y = pitch, yaw
    while abs(p) > 1e-6 or abs(y) > 1e-6:
        dp = max(-MAX_STEP_DEG, min(MAX_STEP_DEG, p))
        dy = max(-MAX_STEP_DEG, min(MAX_STEP_DEG, y))
        steps.append((dp, dy))
        p -= dp
        y -= dy
        if len(steps) > 24:      # 24 * 30 covers any legal turn; guard against NaN loops
            break
    return steps
