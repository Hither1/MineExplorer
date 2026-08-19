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
import os
import re
import shutil
from pathlib import Path
from typing import Any

from loguru import logger

SEPARATOR = "=" * 80

# The log names its own frames, so the log decides which of them the agent may see.
_FRAME_RE = re.compile(r"^\[FRAME\] (\S+)", re.M)

# Written by the harness, not by the agent, and required for the turn to happen at all.
_HARNESS_FILES = {"logs.txt", "AGENTS.md"}


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
    """Writes `logs.txt` and `frames/`, and publishes the view the agent is given.

    `workspace` is where the canonical record lives. In the unablated arm that is also
    the directory Codex works in; under an ablation it is not, and `publish` is what
    decides how much of the record crosses into the directory that is.
    """

    def __init__(self, workspace: Path, stateless: bool = False):
        self.workspace = Path(workspace)
        self.frames_dir = self.workspace / "frames"
        self.path = self.workspace / "logs.txt"
        self.plans_path = self.workspace / "plans.txt"
        self.stateless = stateless
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self.path.touch()
        self._pending_briefing: str | None = None
        self._plan: str | None = None
        self._pending_notes: list[str] = []

    def set_plan(self, plan: str, briefing: str | None = None) -> None:
        """Take one analysis: the briefing is written once, into the next section; the
        plan is written into every section until the next analysis replaces it.

        That is upstream's `set_external_hint` / `set_persistent_hint` pair
        (`game_state.py:26-62`, `runner.py:497-508`): the log's definition includes
        "your own prior analyses", and the section a `tail` lands on always says what
        the agent was doing when it issued that action. The first version of this port
        wrote the plan once and the briefing never, so the analysis survived only in
        the resumed codex conversation -- gone on an overflow reset, and invisible to a
        `grep PLAN`.
        """
        self._plan = (plan or "").strip() or None
        self._pending_briefing = (briefing or "").strip() or None

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
        plan_step: tuple[int, int] | None = None,
        verified: str | None = None,
    ) -> None:
        """One section per environment tick.

        The header carries what upstream's carries (`runner.py:495`): the plan step
        this tick belongs to and, under the hint protocol, the environment's
        verification state -- upstream's `Score:`. That field is the same bit the arm
        already receives on change as a `[MILESTONE]` line, written where every
        `tail` sees it instead of once per transition; under the no-hint protocol
        `verified` is None and the field is absent, as the baseline's status section
        is.
        """
        with self.path.open("a", encoding="utf-8") as f:
            f.write(f"\n{SEPARATOR}\n")
            header = f"Action {action_num} | Step {step}"
            if plan_step:
                header += f" | Plan Step {plan_step[0]}/{plan_step[1]}"
            if verified is not None:
                header += f" | Verified: {verified}"
            f.write(f"{header}\n\n")
            blocks = []
            if self._pending_briefing:
                blocks.append(f"[PLAN]\n{self._pending_briefing}\n")
                self._pending_briefing = None
            if self._plan:
                blocks.append(f"[PLAN]\n{self._plan}\n")
            for block in blocks:
                if self.stateless:
                    # The stateless ablation keeps the plan for our records but does
                    # not carry it forward: next turn sees only the objective trace.
                    with self.plans_path.open("a", encoding="utf-8") as pf:
                        pf.write(f"\n{SEPARATOR}\nAction {action_num}\n{block}")
                else:
                    f.write(f"{block}\n")
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
        latest section, N keeps the header plus the last N sections, -1 writes no log
        at all (the No-Log control).
        """
        text = self.path.read_text(encoding="utf-8")
        if window is None:
            dest.write_text(text, encoding="utf-8")
            return dest
        if window == -1:
            # The No-Log control (upstream `--log-window -1`): there is no log file. The
            # current state travels in the turn prompt instead, and whatever the agent
            # wants to remember it must write itself.
            dest.unlink(missing_ok=True)
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

    def publish(self, visible: Path, window: int | None, stateless: bool,
                current_frame: str | None = None) -> dict:
        """Build the directory the agent is given, and remove what the ablation denies it.

        Upstream keeps the canonical record in the run directory and hands Codex a
        *sandbox* underneath it, so a truncated log is the only log there is
        (`codex_agent.py:274,417-460`). This port wrote both files into one directory,
        which made every ablation a request rather than a constraint: `logs_window.txt`
        sat next to the full `logs.txt`, and stateless only reworded the prompt while the
        agent's own notes survived the turn. An ablation the agent can read around does
        not measure what its name says.

        So, when an ablation is active, `self.workspace` is the record directory and
        *visible* is what Codex gets:

        - `logs.txt` in *visible* is the windowed copy, and the full log is not there;
        - frames are linked in only where the copy still names them, because in this
          port history is pixels as well as text and a window that leaves `frames/`
          whole leaves history readable by another route;
        - under stateless, everything else the agent wrote is deleted, matching
          upstream's `keep = {logs.txt, AGENTS.md}`. The Codex conversation itself stays
          alive -- that is upstream's behaviour too, and is not ours to "fix".

        No-op when *visible* is the record directory itself, which is the unablated arm:
        it must keep writing exactly the layout its finished runs were produced under.
        """
        if visible == self.workspace:
            return {"published": False, "frames_visible": 0, "removed": 0}

        visible.mkdir(parents=True, exist_ok=True)
        view = self.windowed_copy(visible / "logs.txt", window)
        allowed = (set(_FRAME_RE.findall(view.read_text(encoding="utf-8")))
                   if view.exists() else set())
        if window == -1:
            # No history by any route: only the frame the turn attaches.
            allowed = {current_frame} if current_frame else set()

        for name in sorted(allowed):
            src, dst = self.workspace / name, visible / name
            if not src.exists() or dst.exists():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                # A hardlink, so a 300-frame episode is not stored twice. Frames are
                # written once and never rewritten, so the two names cannot diverge.
                os.link(src, dst)
            except OSError:
                shutil.copyfile(src, dst)

        removed = 0
        for path in sorted(visible.rglob("*"), reverse=True):
            if not path.is_file():
                continue
            rel = path.relative_to(visible).as_posix()
            if rel in _HARNESS_FILES or rel in allowed:
                continue
            # Outside stateless the workspace is meant to persist; only the frames the
            # window has dropped are taken back, and they are the harness's files.
            if not stateless and not rel.startswith("frames/"):
                continue
            path.unlink(missing_ok=True)
            removed += 1

        logger.info(
            f"[prolong] ablation view: {len(allowed)} frame(s) visible, "
            f"{removed} file(s) removed (window={window} stateless={stateless})"
        )
        return {"published": True, "frames_visible": len(allowed), "removed": removed}
