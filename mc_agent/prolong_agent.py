"""PRO-LONG's programmatic memory, as a MineExplorer agent mode.

The point of this file is what it does *not* do. It is a drop-in for `DefaultAgent`,
so the episode loop, the loading steps, the frame buffer, `MilestoneChecker.check`,
`RenderWrapper`'s episode.mp4 and result.json all stay exactly as the baseline runs
them. The only difference between the two arms is where the agent's memory lives:

    DefaultAgent   20-frame deque re-sent every step + a `memory_update` string
    ProlongAgent   one append-only logs.txt the agent greps, plus a persistent
                   workspace, plus a plan queue so one analysis covers many steps

A plan-based harness fits the per-step interface through the queue: `get_action`
returns the next queued action and only fires a Codex turn when the queue runs dry,
which is how PRO-LONG's own ActionQueue behaves.
"""
from __future__ import annotations

import io
import json
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger
from PIL import Image

from mc_agent.action_space import BaseActionSpace
from mc_agent.llm_provider import BaseLLMProvider
from prolong_mc import prompts
from prolong_mc.actions import describe_entry, parse_actions
from prolong_mc.codex_backend import CodexTurn
from prolong_mc.log import EpisodeLog

RETRY_NUDGE = (
    "Your previous response did not produce a valid ./actions.json. Write one with "
    'the shape {"actions": [{"action": {...}, "repeat": N}]}.'
)


class ProlongAgent:
    """Same constructor shape as DefaultAgent so eval_benchmark can swap it in."""

    def __init__(
        self,
        action_space: BaseActionSpace,
        provider: BaseLLMProvider,
        context_builder_class: type | None = None,
        model: str | None = None,
        *,
        workspace: str | Path,
        transcript_dir: str | Path | None = None,
        reasoning_effort: str = "low",
        base_url: str | None = None,
        codex_home: str | Path | None = None,
        action_cap: int = 15,
        repeat_cap: int = 20,
        step_cap: int = 40,
        log_window: int | None = None,
        stateless: bool = False,
        analyzer_retries: int = 3,
        milestone_hint: bool = False,
    ) -> None:
        self.action_space = action_space
        self.provider = provider          # unused: Codex is the model channel here
        self.model = model
        self.task_desc = ""
        self.action_cap = action_cap
        self.repeat_cap = repeat_cap
        self.step_cap = step_cap
        self.log_window = log_window
        self.stateless = stateless
        self.analyzer_retries = analyzer_retries
        self.milestone_hint = milestone_hint
        self._esc_rejected_at: list[int] = []

        # Absolute, always -- the same rule CodexTurn applies to the workspace it is
        # handed. Codex runs with cwd == the workspace and resolves `-i` against that,
        # so a frame path built from a relative workspace points nowhere and
        # CodexTurn's guard rejects every call. Nothing catches this earlier: the
        # guard is asserted by selftest against paths it constructs itself, and the
        # DeltaAI runners happened to pass an absolute --output-dir, so the runner
        # path was never exercised with a relative one until it failed 300 steps of
        # 20260818 s0694-prolong-codex in a row.
        self.workspace = Path(workspace).resolve()
        # Under an ablation the canonical record moves out of the directory Codex is
        # given: a truncated log next to the full one, or a "workspace does not persist"
        # instruction next to the notes it wrote last turn, is a request, not a
        # constraint. `EpisodeLog.publish` then decides each turn how much of the record
        # crosses back in. Upstream draws the same line by handing Codex a sandbox
        # *underneath* its run directory (`codex_agent.py:274`).
        #
        # The unablated arm keeps writing straight into the visible workspace, the exact
        # layout its finished runs were produced under.
        self.record_dir = self.workspace
        if log_window is not None or stateless:
            self.record_dir = self.workspace.with_name(f"{self.workspace.name}_record")
        # Reaching this constructor means the scene has no result.json (`--resume`
        # skips the ones that do), so any workspace still sitting here is the debris
        # of a crashed attempt. Left in place it would append a second episode to the
        # same append-only logs.txt -- two INITIAL STATEs, one file -- and AGENTS.md's
        # write-once guard would keep the old system prompt. Move it aside instead of
        # deleting it: the crashed attempt is still evidence.
        if (self.record_dir / "logs.txt").exists():
            n, suffix = 1, ".crashed"
            while any((d.with_name(d.name + suffix)).exists()
                      for d in {self.workspace, self.record_dir}):
                n += 1
                suffix = f".crashed{n}"
            for d in {self.workspace, self.record_dir}:
                if d.exists():
                    d.rename(d.with_name(d.name + suffix))
                    logger.warning(f"[prolong] found a stale workspace; moved it to {d}{suffix}")
        self.log = EpisodeLog(self.record_dir, stateless=stateless)
        # EpisodeLog creates the record directory; the visible one is Codex's cwd and
        # holds AGENTS.md, which is written before the first turn publishes anything.
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.codex = CodexTurn(
            self.workspace,
            model=model or "gpt-5.6-sol",
            reasoning_effort=reasoning_effort,
            base_url=base_url,
            codex_home=Path(codex_home) if codex_home else None,
            transcript_dir=Path(transcript_dir) if transcript_dir else None,
        )
        self.queue: deque[dict[str, Any]] = deque()
        self._action_num = 0
        self._prev_pos: dict | None = None
        self._initial_written = False
        logger.info(
            f"ProlongAgent  workspace={self.workspace}  model={model}  "
            f"log_window={log_window}  stateless={stateless}"
        )

    # -- DefaultAgent-compatible surface ---------------------------------

    def load_system_prompt(self, task_desc: str) -> None:
        self.task_desc = task_desc
        self.codex.write_system_prompt(
            prompts.build_system_prompt(
                task_text=task_desc,
                action_cap=self.action_cap,
                step_cap=self.step_cap,
                repeat_cap=self.repeat_cap,
                log_window=self.log_window,
                stateless=self.stateless,
                milestone_hint=self.milestone_hint,
            )
        )

    def get_default_action(self, is_call_failed: bool = True) -> tuple[str, dict]:
        # A wire dict, not an ActionState: the caller feeds this straight to
        # env.step() and to checker.augment_action_with_queries().
        if is_call_failed:
            logger.warning("[prolong] falling back to a no-op action")
        return "", self.action_space.dump_action_to_dict(
            self.action_space.load_default_action()
        )

    def _milestone_note(self, hint: str) -> str:
        hint = (hint or "").strip()
        if not hint or hint == self._last_milestone_hint:
            return ""
        self._last_milestone_hint = hint
        return f"[MILESTONE] {hint}"

    def on_esc_rejected(self, step: int) -> None:
        # Collected, not written here: under the hint protocol a model that believes
        # it is finished presses ESC on every remaining step, and one log line per
        # rejection would bury the trace it is supposed to annotate. One line per
        # action section, carrying the count, says the same thing.
        self._esc_rejected_at.append(step)
        self._esc_rejections += 1

    def save_state(self, output_dir) -> None:
        """The workspace *is* the state; record what the agent built in it."""
        kept = sorted(p.name for p in self.workspace.glob("*") if p.is_file())
        out = Path(output_dir)
        (out / "prolong_workspace_files.txt").write_text(
            "\n".join(kept), encoding="utf-8"
        )
        # How much vision this episode actually got, next to its score. Without it a
        # comparison cannot tell a memory effect from a "one arm was blind" effect.
        (out / "prolong_vision_audit.json").write_text(
            json.dumps(
                {
                    "analyzer_turns": self.codex.calls,
                    # From the rollout, not the event stream: codex 0.147 hides the
                    # model's nested tool calls from `--json`, so the old counters said
                    # "N frames attached, 0 looked at" whether or not a single frame ever
                    # reached the model. `image_attach_failures` must be 0.
                    **self.codex.vision_audit(),
                    "overflow_resets": self.codex.overflow_resets,
                    # Expected 0. Nonzero means codex compacted the conversation, which
                    # is a different memory architecture than the one being measured.
                    "compactions": self.codex.compactions,
                    "actions_logged": self._action_num,
                    "esc_rejections": self._esc_rejections,
                    # Which arm this is, and -- for the ablations -- what the last
                    # turn's enforcement actually did. A C-arm score is only readable
                    # next to evidence that its ablation bound; `frames_visible` below
                    # the frame count above is that evidence for the window arm, and a
                    # nonzero `files_removed` is it for stateless.
                    "log_window": self.log_window,
                    "stateless": self.stateless,
                    "ablation_enforced": bool((self._published or {}).get("published")),
                    "frames_visible": (self._published or {}).get("frames_visible"),
                    "files_removed": self._files_removed,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

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
    ) -> tuple[Any, ...]:
        step = current_step or 0
        pos = (info or {}).get("player_pos")

        # The newest frame is the observation this decision is made from.
        frame_name = None
        if frame_buffer:
            frame_name = self.log.save_frame(step, _png(frame_buffer[-1]))

        if not self._initial_written:
            self.log.write_initial(self.task_desc, pos, frame_name)
            self._initial_written = True
            self._prev_pos = pos
        elif self._last_entry is not None:
            if self._esc_rejected_at:
                steps = self._esc_rejected_at
                where = f"step {steps[0]}" if len(steps) == 1 else f"steps {steps[0]}-{steps[-1]}"
                self.log.add_note(
                    f"ESC was rejected at {where} ({len(steps)}x): the environment has "
                    f"not verified the task as complete. Keep working."
                )
                self._esc_rejected_at = []
            self.log.write_action(
                action_num=self._action_num,
                step=self._last_step,
                entry_desc=self._last_desc,
                pos=pos,
                prev_pos=self._prev_pos,
                frame_name=frame_name,
                # Only on change. The baseline re-renders this every step because it
                # rebuilds its context every step; an append-only log would instead
                # accumulate 150 copies of the same sentence, crowding out the trace
                # it annotates and hastening the context overflow. The transition --
                # which is the whole signal -- is still recorded the step it happens.
                milestone_note=self._milestone_note(milestone_hint),
            )
            self._prev_pos = pos
            # Consume it. Without this, a failed refill leaves the entry set and every
            # later call re-appends the same section -- duplicate `Action N` headers
            # with moved=0.00, which reads to the analyzer as a stuck player.
            self._last_entry = None

        self._current_frame = frame_name

        if not self.queue and not self._refill(step):
            # Three values, not two: eval_benchmark unpacks a triple, and returning a
            # pair here turns a recoverable analyzer failure into a ValueError that
            # kills the episode instead of hitting its retry path.
            return "", None, ""

        item = self.queue.popleft()
        self._last_entry = item["entry"]
        # Name the tick within its plan entry. Without this every drained tick logs
        # the whole entry ("... x10"), which reads as if ten times the movement was
        # issued each step -- misleading to the agent that reads this log back.
        self._last_desc = f'{describe_entry(item["entry"])} [tick {item["tick"]}/{item["entry"]["repeat"]}]'
        self._last_step = step
        self._action_num += 1
        # (thought, wire action dict, memory_update) -- the same triple DefaultAgent
        # returns. PRO-LONG has no memory_update: the log is the memory.
        return item["think"], item["wire"], ""

    # -- the mechanism ---------------------------------------------------

    _last_entry: dict | None = None
    _last_desc: str = ""
    _last_step: int = 0
    _current_frame: str | None = None
    _esc_rejections: int = 0
    _last_milestone_hint: str = ""
    _published: dict | None = None
    _files_removed: int = 0

    def _refill(self, step: int) -> bool:
        # What the agent may see this turn. The file is always ./logs.txt, as upstream's
        # sandbox copy is: naming the windowed one differently advertised that a fuller
        # log exists somewhere, and it used to be sitting right beside it.
        published = self.log.publish(self.workspace, self.log_window, self.stateless)
        self._published = published
        self._files_removed += published["removed"]
        log_name = "logs.txt"

        # Unconditional, not on demand. The baseline agent is handed its frames every
        # step; an analyzer that has to decide to look is not information-matched to
        # it, and in prolong-gpt56-v3 it never did (8 turns, 0 view_image calls).
        # The [FRAME] markers still cover history -- this covers *now*.
        frames = [self.workspace / self._current_frame] if self._current_frame else []

        base = prompts.build_turn_prompt(
            log_name, self._action_num == 0, self.log_window, bool(frames)
        )
        for attempt in range(self.analyzer_retries):
            prompt = base if attempt == 0 else f"{base}\n\n{RETRY_NUDGE}"
            result = self.codex.run(prompt, images=frames)
            if not result["ok"]:
                logger.warning(
                    f"[prolong] analyzer attempt {attempt + 1}/{self.analyzer_retries} "
                    f"produced no actions.json "
                    f"({'context overflow; ' if result.get('overflow') else ''}"
                    f"{result['error']})"
                )
                continue
            plan = parse_actions(
                result["actions_json"],
                action_cap=self.action_cap,
                repeat_cap=self.repeat_cap,
                step_cap=self.step_cap,
            )
            if not plan:
                logger.warning(f"[prolong] attempt {attempt + 1}: no usable entries")
                continue
            think = CodexTurn.extract_plan(result["message"])
            self.log.set_plan(think)
            offset = 0
            for entry in plan.entries:
                for tick in range(1, entry["repeat"] + 1):
                    self.queue.append(
                        {"entry": entry, "wire": plan.steps[offset],
                         "think": think, "tick": tick}
                    )
                    offset += 1
            logger.info(
                f"[prolong] step {step}: queued {len(plan.entries)} entries "
                f"= {len(plan.steps)} steps (turn {self.codex.calls})"
            )
            return True
        logger.error(f"[prolong] analyzer produced nothing after {self.analyzer_retries} tries")
        return False


def _png(frame: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(np.asarray(frame).astype(np.uint8), "RGB").save(buf, format="PNG")
    return buf.getvalue()
