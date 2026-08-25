"""The multimodal filesystem that is the agent's memory.

Layout (the boxes in the figure, one directory each):

    logs.txt            append-only trace: every action, the state that followed it, and
                        the agent's own prior analyses. Grepped, never read whole.
    episodes/           per-episode raw material. frames/step_NNNN.png are written here
                        and referenced from logs.txt by path -- the agent opens the ones
                        it wants rather than being handed all of them.
    events/events.jsonl one line per discrete world event the harness detected (an item
                        mined, crafted, picked up, an entity killed, damage taken). This
                        is the append-only ground-truth channel: the agent may write
                        beliefs anywhere, but it cannot write here.
    entities/           <name>.md, one per kind of thing observed
    locations/          <slug>.md, one per named place
    maps/               visited.csv (harness-written position trace), waypoints.csv
    procedures/         <name>.md, one per action recipe found to work
    hypotheses/         graph.json -- the belief DAG, mirrored to disk every step
    world_model/        the five structured documents induction rewrites

Who writes what matters, and is the reason this is a module rather than a mkdir. The
harness owns logs.txt, events/, maps/visited.csv and episodes/frames/; the agent owns
entities/, locations/, procedures/, world_model/ and maps/waypoints.csv. A belief the
agent holds and a fact the environment reported must not end up in the same file, or the
discipline layer has nothing to check a claim against -- which is precisely the failure
mode ("the model confirmed its own goal") the upstream agent's ESC-gating existed to
catch.
"""
from __future__ import annotations

import csv
import json
import math
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Iterable

from loguru import logger

SEPARATOR = "=" * 80

# Directories the agent may write. Anything else under the root is the harness's, and
# `assert_harness_files_intact` treats a change to one as a bug worth failing loudly on
# rather than a stylistic preference -- an agent that can rewrite events.jsonl can make
# any goal true by editing a file.
AGENT_OWNED = ("entities", "locations", "procedures", "world_model", "notes")
HARNESS_OWNED_FILES = ("logs.txt", "AGENTS.md", "events/events.jsonl", "maps/visited.csv")

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slug(text: str) -> str:
    """A filename for an arbitrary phrase the model produced. Bounded, because these
    become paths and a model asked for a location name will occasionally return a
    paragraph."""
    s = _SLUG_RE.sub("_", (text or "").strip().lower()).strip("_")
    return (s or "unnamed")[:60]


def _xz(pos: dict[str, Any] | None) -> tuple[float, float] | None:
    if not isinstance(pos, dict):
        return None
    x, z = pos.get("x"), pos.get("z")
    return (float(x), float(z)) if x is not None and z is not None else None


def state_line(pos: dict[str, Any] | None, prev: dict[str, Any] | None) -> str:
    """`[STATE] pos=(x, y, z) pitch=P yaw=Y moved=D`.

    Kept byte-compatible with MineExplorer's prolong_mc/log.py: the prompt teaches the
    agent to trust this line over its own read of a frame, and both repos' analysis
    scripts split on it.
    """
    if not isinstance(pos, dict) or pos.get("x") is None:
        return "[STATE] unavailable"
    here, before = _xz(pos), _xz(prev)
    moved = math.dist(here, before) if here and before else 0.0
    return (
        f"[STATE] pos=({pos['x']:.2f}, {pos.get('y', 0.0):.2f}, {pos['z']:.2f}) "
        f"pitch={pos.get('pitch', 0.0):.0f} yaw={pos.get('yaw', 0.0):.0f} "
        f"moved={moved:.2f}"
    )


class MultimodalMemory:
    """Owns the directory tree, and the harness's half of what is written into it."""

    def __init__(self, root: str | Path, episode: int = 0) -> None:
        # Absolute, always. The Codex backend runs with cwd == this root and resolves
        # image paths against it, so a relative root silently points nowhere -- the same
        # bug that cost MineExplorer a 300-step run (see prolong_agent.py's note).
        self.root = Path(root).resolve()
        self.episode = episode
        self.episode_dir = self.root / "episodes" / f"ep_{episode:04d}"
        self.frames_dir = self.episode_dir / "frames"
        self.logs_path = self.root / "logs.txt"
        self.events_path = self.root / "events" / "events.jsonl"
        self.visited_path = self.root / "maps" / "visited.csv"
        self.graph_path = self.root / "hypotheses" / "graph.json"
        self.world_model_dir = self.root / "world_model"

        for d in ("entities", "locations", "maps", "events", "procedures",
                  "hypotheses", "world_model", "notes", "tools"):
            (self.root / d).mkdir(parents=True, exist_ok=True)
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self._write_tools()
        self.logs_path.touch()
        self.events_path.touch()
        if not self.visited_path.exists():
            with self.visited_path.open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(["step", "x", "y", "z", "pitch", "yaw", "biome"])

        self._plan: str | None = None
        self._pending_briefing: str | None = None
        self._pending_notes: list[str] = []

    def _write_tools(self) -> None:
        """Executable helpers the agent can run against its own visual memory.

        The frames are addressable (every log section carries its [FRAME] path) but not
        *inspectable*: a 640x360 PNG viewed whole is where dm4_wmv3 spent its last 1,700
        steps strip-mining past walls it could not read -- iron ore at that resolution is
        a handful of beige pixels. `zoom.py` dereferences a frame pointer at pixel level:
        crop a region, magnify it, and hand the result to view_image. The shebang pins
        this venv's interpreter so the script works from the agent's bare shell.
        """
        zoom = self.root / "tools" / "zoom.py"
        if zoom.exists():
            return
        zoom.write_text(f'''#!{sys.executable}
"""Crop a frame region and magnify it, for reading detail a full frame hides.

    ./tools/zoom.py <frame.png> <x> <y> <w> <h> [out.png]

x,y = top-left of the region in the frame's own pixels (640x360); the crop is scaled
4x nearest-neighbour (pixel-accurate, no smoothing) into out.png (default ./zoom.png).
Then open the result with view_image. Compare two frames by zooming the same region in
both and viewing them in sequence.
"""
import sys
from PIL import Image

frame, x, y, w, h = sys.argv[1], *map(int, sys.argv[2:6])
out = sys.argv[6] if len(sys.argv) > 6 else "zoom.png"
img = Image.open(frame).convert("RGB")
x = max(0, min(img.width - 1, x)); y = max(0, min(img.height - 1, y))
w = max(1, min(img.width - x, w)); h = max(1, min(img.height - y, h))
img.crop((x, y, x + w, y + h)).resize((w * 4, h * 4), Image.NEAREST).save(out)
print(f"wrote {{out}}: {{w}}x{{h}} region at ({{x}},{{y}}), 4x")
''', encoding="utf-8")
        zoom.chmod(0o755)

    # -- the append-only trace -------------------------------------------

    def set_plan(self, plan: str, briefing: str | None = None) -> None:
        """One analysis from the agent: the briefing is written once into the next
        section, the plan into every section it governs.

        Both, not just the plan. MineExplorer's first port wrote the plan and dropped the
        briefing, so the reasoning behind a stretch of actions survived only inside the
        resumed model conversation -- invisible to `grep`, and gone entirely on a context
        overflow. The log is supposed to be the memory of record; that means it holds the
        thinking too.
        """
        self._plan = (plan or "").strip() or None
        self._pending_briefing = (briefing or "").strip() or None

    def add_note(self, note: str) -> None:
        """Hold a harness-side note (a rejected claim, a dropped action) for the next
        section. Kept separate from set_plan so a note arriving on the same step as a
        fresh plan does not overwrite it."""
        note = (note or "").strip()
        if note:
            self._pending_notes.append(note)

    def save_frame(self, step: int, png_bytes: bytes) -> str:
        rel = f"episodes/ep_{self.episode:04d}/frames/step_{step:04d}.png"
        (self.root / rel).write_bytes(png_bytes)
        return rel

    def write_initial(self, task_text: str, pos: dict | None, frame: str | None) -> None:
        with self.logs_path.open("a", encoding="utf-8") as f:
            f.write(f"{SEPARATOR}\nAction 0 | Step 0 | INITIAL STATE\n\n")
            f.write(f"Task: {task_text}\n{state_line(pos, None)}\n")
            if frame:
                f.write(f"[FRAME] {frame}\n")

    def write_action(
        self, *, action_num: int, step: int, entry_desc: str, pos: dict | None,
        prev_pos: dict | None, frame: str | None, plan_step: str = "",
        verified: str = "", events: Iterable[str] = (),
        inventory_delta: str = "", gui_open: bool | None = None,
        cursor_line: str = "",
    ) -> None:
        with self.logs_path.open("a", encoding="utf-8") as f:
            head = f"{SEPARATOR}\nAction {action_num} | Step {step}"
            if plan_step:
                head += f" | Plan Step {plan_step}"
            if verified:
                head += f" | {verified}"
            f.write(head + "\n\n")
            if self._pending_briefing:
                f.write(f"[PLAN] {self._pending_briefing}\n")
                self._pending_briefing = None
            if self._plan:
                f.write(f"[PLAN] {self._plan}\n")
            f.write(f"{entry_desc}\n{state_line(pos, prev_pos)}\n")
            # What the entry actually changed in the inventory, and whether a GUI is up.
            # This is the feedback channel for GUI work: the frame shows where the cursor
            # is, and this line says whether the last click moved anything. Without it a
            # `grep` over the log cannot tell a click that landed from one that did not.
            if gui_open is not None:
                f.write(f"[GUI] open={gui_open}\n")
            if cursor_line:
                f.write(f"{cursor_line}\n")
            if inventory_delta:
                f.write(f"[INV] {inventory_delta}\n")
            for e in events:
                f.write(f"[EVENT] {e}\n")
            for n in self._pending_notes:
                f.write(f"[NOTE] {n}\n")
            self._pending_notes.clear()
            if frame:
                f.write(f"[FRAME] {frame}\n")

    # -- the ground-truth event channel ----------------------------------

    def append_events(self, step: int, events: list[dict[str, Any]]) -> None:
        """Ground truth only. Everything here came from MineRL's own statistics, never
        from the model, which is what lets `discipline` use it as the arbiter."""
        if not events:
            return
        with self.events_path.open("a", encoding="utf-8") as f:
            for e in events:
                f.write(json.dumps({"step": step, **e}, separators=(",", ":")) + "\n")

    def append_visited(self, step: int, pos: dict | None, biome: str = "") -> None:
        if not isinstance(pos, dict) or pos.get("x") is None:
            return
        with self.visited_path.open("a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                step, f"{pos.get('x', 0):.2f}", f"{pos.get('y', 0):.2f}",
                f"{pos.get('z', 0):.2f}", f"{pos.get('pitch', 0):.1f}",
                f"{pos.get('yaw', 0):.1f}", biome,
            ])

    def read_events(self, limit: int | None = None) -> list[dict[str, Any]]:
        if not self.events_path.exists():
            return []
        lines = self.events_path.read_text(encoding="utf-8").splitlines()
        if limit is not None:
            lines = lines[-limit:]
        out = []
        for ln in lines:
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
        return out

    # -- the structured world model --------------------------------------

    #: The five documents in the figure's "Structured World Model" box. Seeded so the
    #: agent's first act turn reads a real file rather than discovering an empty
    #: directory and inventing its own layout -- across episodes those ad-hoc layouts
    #: diverge, and induction then cannot merge two episodes' knowledge.
    WORLD_MODEL_DOCS = {
        "spatial": "Where things are: coordinates, topology, routes, what is near what.",
        "semantic": "What things are: entities, their attributes, and their affordances.",
        "dynamics": "How the world responds: action -> consequence, timings, costs.",
        "procedural": "Recipes that worked: ordered action sequences, with preconditions.",
        "causal": "Why things happen: dependencies, and what must be true before what.",
    }

    def seed_world_model(self, task_text: str) -> None:
        for name, blurb in self.WORLD_MODEL_DOCS.items():
            p = self.world_model_dir / f"{name}.md"
            if p.exists():
                continue
            p.write_text(
                f"# {name.capitalize()} model\n\n_{blurb}_\n\n"
                f"Task: {task_text}\n\n"
                "> Nothing induced yet. This file is rewritten by the induction pass "
                "from `logs.txt`, `events/events.jsonl`, `maps/visited.csv` and the "
                "hypothesis graph.\n",
                encoding="utf-8",
            )

    def world_model_summary(self, per_doc_chars: int = 1200) -> str:
        """The world model as it goes into an act turn's prompt.

        Truncated per document rather than in total: a `causal.md` that induction has
        grown large must not be able to push `spatial.md` out of the prompt entirely,
        because the act turn needs all five to plan. Induction is told the budget, so
        growth past it is a signal the document needs compacting, not a silent loss.
        """
        parts = []
        for name in self.WORLD_MODEL_DOCS:
            p = self.world_model_dir / f"{name}.md"
            if not p.exists():
                continue
            text = p.read_text(encoding="utf-8").strip()
            if len(text) > per_doc_chars:
                text = text[:per_doc_chars] + f"\n... [truncated; read {p.name} in full]"
            parts.append(text)
        return "\n\n".join(parts)

    # -- integrity --------------------------------------------------------

    def snapshot_harness_files(self) -> dict[str, int]:
        return {
            rel: (self.root / rel).stat().st_size
            for rel in HARNESS_OWNED_FILES if (self.root / rel).exists()
        }

    def assert_harness_files_intact(self, before: dict[str, int]) -> list[str]:
        """Harness files only ever grow. A shrink means the agent rewrote the record it
        is supposed to be reasoning from, which invalidates every claim checked against
        it -- so this is reported, not silently repaired."""
        bad = []
        for rel, size in before.items():
            now = (self.root / rel).stat().st_size if (self.root / rel).exists() else 0
            if now < size:
                bad.append(f"{rel}: {size} -> {now} bytes")
        if bad:
            logger.error(f"[memory] agent modified harness-owned files: {bad}")
        return bad

    def archive_crashed(self) -> None:
        """Move a leftover workspace aside instead of appending a second episode to the
        same logs.txt. The debris of a crashed attempt is evidence, so it is renamed
        rather than deleted."""
        if not self.logs_path.exists() or self.logs_path.stat().st_size == 0:
            return
        n, suffix = 1, ".crashed"
        while self.root.with_name(self.root.name + suffix).exists():
            n += 1
            suffix = f".crashed{n}"
        dest = self.root.with_name(self.root.name + suffix)
        shutil.move(str(self.root), str(dest))
        logger.warning(f"[memory] stale workspace moved to {dest}")
