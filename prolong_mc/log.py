"""The append-only episode log that is PRO-LONG's entire memory mechanism.

Replaces `game_state.render_board` plus the log writing scattered through
`environment/runner.py`. The markers are the ones `prompts.py` declares, and the
section separator is the same 80-`=` rule PRO-LONG uses, because the log-window
ablation splits on it.

Frames are written as files rather than embedded: the agent decides which to look at
with the image viewer. That is the point of the architecture -- grep the numeric
trace, pull pixels only where they matter -- and it is also the only way a 300-step
episode's frames fit anywhere near a context window.
"""
from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

SEPARATOR = "=" * 80


def _xz(pos: dict[str, Any] | None) -> tuple[float, float] | None:
    if not isinstance(pos, dict):
        return None
    x, z = pos.get("x"), pos.get("z")
    return (float(x), float(z)) if x is not None and z is not None else None


def state_line(pos: dict[str, Any] | None, prev: dict[str, Any] | None) -> str:
    """`[STATE] pos=(x, y, z) pitch=P yaw=Y moved=D` — the log's load-bearing line."""
    if not isinstance(pos, dict) or pos.get("x") is None:
        return "[STATE] unavailable"
    here, before = _xz(pos), _xz(prev)
    moved = math.dist(here, before) if here and before else 0.0
    return (
        f"[STATE] pos=({pos['x']:.2f}, {pos.get('y', 0.0):.2f}, {pos['z']:.2f}) "
        f"pitch={pos.get('pitch', 0.0):.0f} yaw={pos.get('yaw', 0.0):.0f} "
        f"moved={moved:.2f}"
    )


class EpisodeLog:
    """Writes `logs.txt` and `frames/`, and produces the windowed copies the
    ablation arms read."""

    def __init__(self, workspace: Path, stateless: bool = False):
        self.workspace = Path(workspace)
        self.frames_dir = self.workspace / "frames"
        self.path = self.workspace / "logs.txt"
        self.plans_path = self.workspace / "plans.txt"
        self.stateless = stateless
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self.path.touch()
        self._pending_plan: str | None = None
        self._pending_notes: list[str] = []

    def set_plan(self, plan: str) -> None:
        """Hold the agent's plan until the next action section is written."""
        self._pending_plan = (plan or "").strip() or None

    def add_note(self, note: str) -> None:
        """Hold a runner-side note (an ESC refusal, say) until the next section.

        Separate from `set_plan` deliberately: a note arriving in the same step as a
        fresh plan used to overwrite it, so the analyzer's own reasoning vanished from
        the log at exactly the steps where it was being overruled.
        """
        note = (note or "").strip()
        if note:
            self._pending_notes.append(note)

    def save_frame(self, step: int, png_bytes: bytes) -> str:
        name = f"frames/step_{step:04d}.png"
        (self.workspace / name).write_bytes(png_bytes)
        return name

    def write_initial(self, task_text: str, pos: dict | None, frame_name: str | None) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(f"{SEPARATOR}\n")
            f.write(f"Action 0 | Step 0 | INITIAL STATE\n\n")
            f.write(f"Task: {task_text}\n")
            f.write(f"{state_line(pos, None)}\n")
            if frame_name:
                f.write(f"[FRAME] {frame_name}\n")

    def write_action(
        self,
        *,
        action_num: int,
        step: int,
        entry_desc: str,
        pos: dict | None,
        prev_pos: dict | None,
        frame_name: str | None,
        milestone_note: str = "",
    ) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(f"\n{SEPARATOR}\n")
            f.write(f"Action {action_num} | Step {step}\n\n")
            if self._pending_plan:
                block = f"[PLAN]\n{self._pending_plan}\n"
                if self.stateless:
                    # The stateless ablation keeps the plan for our records but does
                    # not carry it forward: next turn sees only the objective trace.
                    with self.plans_path.open("a", encoding="utf-8") as pf:
                        pf.write(f"\n{SEPARATOR}\nAction {action_num}\n{block}")
                else:
                    f.write(f"{block}\n")
                self._pending_plan = None
            for note in self._pending_notes:
                f.write(f"[NOTE] {note}\n")
            self._pending_notes.clear()
            f.write(f"Tool Call: {entry_desc}\n")
            f.write(f"{state_line(pos, prev_pos)}\n")
            if frame_name:
                f.write(f"[FRAME] {frame_name}\n")
            if milestone_note:
                f.write(f"{milestone_note}\n")

    def windowed_copy(self, dest: Path, window: int | None) -> Path:
        """Write the copy the agent actually reads.

        `window` follows PRO-LONG: None keeps everything, 0 keeps the header plus the
        latest section, N keeps the header plus the last N sections.
        """
        text = self.path.read_text(encoding="utf-8")
        if window is None:
            dest.write_text(text, encoding="utf-8")
            return dest
        parts = re.split(rf"(?={re.escape(SEPARATOR)}\n)", text)
        head = parts[0] if parts and not parts[0].startswith(SEPARATOR) else ""
        sections = [p for p in parts if p.startswith(SEPARATOR)]
        if window == 0:
            kept = sections[:1] + (sections[-1:] if len(sections) > 1 else [])
        else:
            kept = sections[:1] + sections[-window:] if len(sections) > window else sections
        dest.write_text(head + "".join(kept), encoding="utf-8")
        return dest
