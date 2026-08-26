"""The world-model agent, as a MineExplorer agent mode.

Same drop-in contract as ProlongAgent: the episode loop, the loading steps, the frame
buffer, MilestoneChecker.check, RenderWrapper's episode.mp4 and result.json all stay
exactly as the baseline runs them. What differs is the memory architecture -- the
dual-turn act/induction loop over a multimodal filesystem, ported from MCU-AgentBeats'
`mcu_worldmodel` (see mc_agent/worldmodel/agent.py for the loop itself).

Codex is the model channel (like prolong): the loop's mechanism *is* a workspace the
model greps and writes, which a stateless chat provider cannot express. The harness
passes two extras for this mode: `info` (the raw observation the [STATE] lines are
derived from) and `milestones` (MilestoneChecker.check's status list, which is the
ledger's only verification source -- this agent never re-scores the scene itself).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from mc_agent.action_space import BaseActionSpace
from mc_agent.llm_provider import BaseLLMProvider
from mc_agent.worldmodel.agent import WorldModelCore
from mc_agent.worldmodel.milestones import MilestoneLedger
from prolong_mc.codex_backend import CodexTurn


_BRAIN_DOCS = ("dynamics.md", "semantic.md", "procedural.md")


def _brain_copy(src_root: Path, dst_root: Path) -> int:
    """Carry environment-level knowledge between a workspace and a cross-episode brain
    directory: the three environment-level world_model docs plus every executable skill
    in procedures/*.json. spatial/causal (scene-bound) and hypotheses never travel.
    Writes are tmp+replace so a reader never sees a torn file; the brain is still meant
    for SERIAL campaigns -- concurrent episodes would race last-writer-wins."""
    copied = 0

    def _put(src: Path, dst: Path) -> None:
        nonlocal copied
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_name(dst.name + ".tmp")
        tmp.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        tmp.replace(dst)
        copied += 1

    for name in _BRAIN_DOCS:
        s = src_root / "world_model" / name
        # An untouched seed template must not overwrite induced knowledge: a
        # zero-induction episode exporting its templates would wipe the brain.
        if s.is_file() and "Nothing induced yet" not in s.read_text(encoding="utf-8"):
            _put(s, dst_root / "world_model" / name)
    sdir = src_root / "procedures"
    if sdir.is_dir():
        for f in sorted(sdir.glob("*.json")):
            _put(f, dst_root / "procedures" / f.name)
    return copied


def _published_bits(milestones: list[dict] | None) -> dict[str, int] | None:
    """MilestoneChecker.check's status list as the {milestone_id: 0|1} dict the ledger
    consumes. None (not {}) when the harness sent nothing, so the ledger can tell "no
    signal yet" from "signal: nothing verified"."""
    if not isinstance(milestones, list):
        return None
    out: dict[str, int] = {}
    for ms in milestones:
        if isinstance(ms, dict) and "milestone_id" in ms:
            out[str(ms["milestone_id"])] = 1 if ms.get("completed") else 0
    return out or None


class WorldModelAgent:
    """Same constructor shape as ProlongAgent so eval_benchmark can swap it in."""

    def __init__(
        self,
        action_space: BaseActionSpace,
        provider: BaseLLMProvider,
        context_builder_class: type | None = None,
        model: str | None = None,
        *,
        workspace: str | Path,
        milestones_spec: list[dict[str, Any]] | None = None,
        transcript_dir: str | Path | None = None,
        reasoning_effort: str = "low",
        base_url: str | None = None,
        codex_home: str | Path | None = None,
        entry_cap: int = 20,
        repeat_cap: int = 50,
        step_cap: int = 80,
        induction_every: int = 60,
        per_doc_chars: int = 1200,
        analyzer_retries: int = 3,
        max_steps: int = 300,
        brain_dir: str | Path | None = None,
    ) -> None:
        self.action_space = action_space
        self.provider = provider          # unused: Codex is the model channel here
        self.model = model
        self.task_desc = ""
        # Absolute, always -- Codex runs with cwd == the workspace and resolves `-i`
        # frame paths against it; a relative workspace points nowhere (the bug that cost
        # a 300-step prolong run before the same rule landed there).
        self.workspace = Path(workspace).resolve()
        # Reaching this constructor means the scene has no result.json, so a workspace
        # already here is the debris of a crashed attempt. Left in place it would append
        # a second episode to the same append-only logs.txt; moved aside it stays
        # evidence.
        if (self.workspace / "logs.txt").exists() and \
                (self.workspace / "logs.txt").stat().st_size > 0:
            n, suffix = 1, ".crashed"
            while self.workspace.with_name(self.workspace.name + suffix).exists():
                n += 1
                suffix = f".crashed{n}"
            dest = self.workspace.with_name(self.workspace.name + suffix)
            self.workspace.rename(dest)
            logger.warning(f"[wm] found a stale workspace; moved it to {dest}")
        self.workspace.mkdir(parents=True, exist_ok=True)

        # Cross-episode brain: seed the workspace from it BEFORE the core exists, so
        # the core's seed_world_model only fills the docs the brain did not provide.
        self.brain_dir = Path(brain_dir).resolve() if brain_dir else None
        if self.brain_dir:
            try:
                n = _brain_copy(self.brain_dir, self.workspace)
                logger.info(f"[wm] brain seeded from {self.brain_dir}: {n} files")
            except Exception as e:
                logger.warning(f"[wm] brain seeding failed (fresh start): {e}")

        self.codex = CodexTurn(
            self.workspace,
            model=model or "gpt-5.6-sol",
            reasoning_effort=reasoning_effort,
            base_url=base_url,
            codex_home=Path(codex_home) if codex_home else None,
            transcript_dir=Path(transcript_dir) if transcript_dir else None,
        )
        self.ledger = MilestoneLedger(milestones_spec or [])
        self._core_kwargs = dict(
            entry_cap=entry_cap, repeat_cap=repeat_cap, step_cap=step_cap,
            induction_every=induction_every, per_doc_chars=per_doc_chars,
            analyzer_retries=analyzer_retries, max_steps=max_steps,
        )
        self.core: WorldModelCore | None = None
        logger.info(f"WorldModelAgent  workspace={self.workspace}  model={model}  "
                    f"milestones={len(self.ledger.cfg)}  "
                    f"induction_every={induction_every}")

    # -- DefaultAgent-compatible surface ----------------------------------

    def load_system_prompt(self, task_desc: str) -> None:
        # Stored, not written: AGENTS.md needs the milestone checklist rendered, and the
        # ledger baseline needs the first real observation -- both exist at the first
        # get_action, where core.start writes the prompt exactly once.
        self.task_desc = task_desc

    def get_default_action(self, is_call_failed: bool = True) -> tuple[str, dict]:
        if is_call_failed:
            logger.warning("[wm] falling back to a no-op action")
        return "", self.action_space.dump_action_to_dict(
            self.action_space.load_default_action()
        )

    def on_esc_rejected(self, step: int) -> None:
        """The harness refused an ESC this agent let through -- its ledger and the
        checker disagreed (a race on the same step, or a trackability edge). Costed the
        same way the agent's own gate costs it."""
        if self.core is None:
            return
        self.core.stats["esc_blocked"] += 1
        unverified = [i for i in self.core.ledger.order
                      if not self.core.ledger.is_verified(i)]
        note = self.core.discipline.check_claim({"completed": unverified}, step)
        self.core.memory.add_note(
            "the runner refused your ESC: the environment's checker does not agree the "
            "task is done." + (f" {note}" if note else ""))

    def save_state(self, output_dir) -> None:
        """The workspace *is* the state; record what the agent built in it."""
        if self.core is None:
            return
        # Environment-level knowledge survives the episode whatever its outcome -- a
        # failed episode's induced dynamics are still true tomorrow. Template docs are
        # filtered inside _brain_copy, so an episode that never ran induction exports
        # nothing and cannot regress the brain.
        if self.brain_dir:
            try:
                n = _brain_copy(self.workspace, self.brain_dir)
                logger.info(f"[wm] brain export to {self.brain_dir}: {n} files")
            except Exception as e:
                logger.warning(f"[wm] brain export failed: {e}")
        out = Path(output_dir)
        report = self.core.report()
        # The report must land even when the audit cannot: this runs at episode end,
        # after the score, and losing it to a rollout-parsing error would discard the
        # episode's only mechanism-level record.
        try:
            report["vision_audit"] = self.codex.vision_audit()
        except Exception as e:
            report["vision_audit"] = {"error": str(e)}
        report["analyzer_turns"] = self.codex.calls
        for k in ("overflow_resets", "timeout_resets", "empty_resets", "age_resets",
                  "compactions", "session_max_turns"):
            report[k] = getattr(self.codex, k, None)
        (out / "worldmodel_report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8")

    # -- the per-step interface -------------------------------------------

    def get_action(
        self,
        frame_buffer: list[np.ndarray],
        thought_history: list,
        action_history: list,
        current_step: int | None = None,
        return_messages: bool = False,
        return_messages_with_pic: bool = False,
        long_term_memory: str = "",
        milestone_hint: str = "",
        camera_hint: str = "",
        movement_hint: str = "",
        info: dict | None = None,
        milestones: list[dict] | None = None,
        presatisfied: set | None = None,
    ) -> tuple[Any, ...]:
        step = current_step or 0
        info = dict(info or {})
        if presatisfied:
            # Constant for the episode; applied before observe so this step's bits
            # cannot bank a milestone the harness has blocklisted.
            self.ledger.set_presatisfied(presatisfied)
        bits = _published_bits(milestones)
        if bits is not None:
            # The checker's verdicts, in the shape the ledger consumes. Injected into
            # info so the core's observe path matches MCU's "host-published milestones"
            # source exactly.
            info["milestones"] = bits

        frame = np.asarray(frame_buffer[-1]) if frame_buffer else None
        core = self.core
        if core is None:
            core = self.core = WorldModelCore(
                workspace=self.workspace,
                task_text=self.task_desc,
                ledger=self.ledger,
                codex_turn=self.codex,
                **self._core_kwargs,
            )
            core.start(info, frame)

        try:
            core.observe(info, step, frame)
            action = core.next_action(info)
        except Exception as e:
            logger.error(f"[wm] step {step} failed: {e}")
            thought, action = self.get_default_action()
            return thought, action, ""

        thought = "; ".join(core.plan) or "(no plan)"
        return thought, action, ""
