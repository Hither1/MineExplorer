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
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger
from PIL import Image

from mc_agent.action_space import ActionState, BaseActionSpace
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

        self.workspace = Path(workspace)
        self.log = EpisodeLog(self.workspace, stateless=stateless)
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
            )
        )

    def get_default_action(self, is_call_failed: bool = True):
        if is_call_failed:
            logger.warning("[prolong] falling back to a no-op action")
        return "", self.action_space.load_default_action()

    def on_esc_rejected(self, step: int) -> None:
        self.log.set_plan(
            f"[note] ESC at step {step} was rejected: the environment says the task "
            f"is not verified complete. Keep working."
        )

    def save_state(self, output_dir) -> None:
        """The workspace *is* the state; record what the agent built in it."""
        kept = sorted(p.name for p in self.workspace.glob("*") if p.is_file())
        (Path(output_dir) / "prolong_workspace_files.txt").write_text(
            "\n".join(kept), encoding="utf-8"
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
            self.log.write_action(
                action_num=self._action_num,
                step=step,
                entry_desc=describe_entry(self._last_entry),
                pos=pos,
                prev_pos=self._prev_pos,
                frame_name=frame_name,
                milestone_note=f"[MILESTONE] {milestone_hint}" if milestone_hint.strip() else "",
            )
            self._prev_pos = pos

        if not self.queue and not self._refill(step):
            # Three values, not two: eval_benchmark unpacks a triple, and returning a
            # pair here turns a recoverable analyzer failure into a ValueError that
            # kills the episode instead of hitting its retry path.
            return "", None, ""

        item = self.queue.popleft()
        self._last_entry = item["entry"]
        self._action_num += 1
        state = _state_from_wire(self.action_space, item["wire"])
        state.think = item["think"]
        return state.think, state, ""

    # -- the mechanism ---------------------------------------------------

    _last_entry: dict | None = None

    def _refill(self, step: int) -> bool:
        log_name = "logs.txt"
        if self.log_window is not None:
            self.log.windowed_copy(self.workspace / "logs_window.txt", self.log_window)
            log_name = "logs_window.txt"

        base = prompts.build_turn_prompt(log_name, self._action_num == 0, self.log_window)
        for attempt in range(self.analyzer_retries):
            prompt = base if attempt == 0 else f"{base}\n\n{RETRY_NUDGE}"
            result = self.codex.run(prompt)
            if not result["ok"]:
                logger.warning(
                    f"[prolong] analyzer attempt {attempt + 1}/{self.analyzer_retries} "
                    f"produced no actions.json ({result['error']})"
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
                for _ in range(entry["repeat"]):
                    self.queue.append(
                        {"entry": entry, "wire": plan.steps[offset], "think": think}
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


def _state_from_wire(space: BaseActionSpace, wire: dict[str, Any]) -> ActionState:
    """The queue holds wire dicts; the eval loop wants an ActionState back."""
    state = ActionState()
    for key, value in wire.items():
        if key == "camera":
            state.camera = list(value)
        elif key.startswith("hotbar."):
            idx = int(key.split(".", 1)[1])
            hotbars = list(state.hotbars)
            hotbars[idx - 1] = int(value)
            state.hotbars = hotbars
        elif key == "pickItem":
            state.pick_item = int(value)
        elif key == "swapHands":
            state.swap_hands = int(value)
        else:
            setattr(state, key, int(value))
    return state
