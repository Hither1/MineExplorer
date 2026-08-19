from __future__ import annotations
import copy
import json
import subprocess
from typing import Any

import numpy as np
from loguru import logger

from mc_agent.action_space import ActionState, BaseActionSpace
from mc_agent.context import DefaultContextBuilder, PROMPT_LAYOUTS, RESPONSE_STYLES
from mc_agent.llm_provider import BaseLLMProvider
from mc_agent.utils import convert_buffer_to_base64_images


class DefaultAgent:
    def __init__(
        self,
        action_space: BaseActionSpace,
        provider: BaseLLMProvider,
        context_builder_class: type[DefaultContextBuilder] = DefaultContextBuilder,
        model: str = None,
        prompt_layout: str = "legacy",
        response_style: str = "full",
    ) -> None:
        """An agent that uses a multimodal LLM to play Minecraft.

        prompt_layout: how the request is laid out for the server's prefix cache; see
        PROMPT_LAYOUTS in mc_agent/context.py. "legacy" is today's prompt byte for byte.
        response_style: what the model is asked to write back; see RESPONSE_STYLES there.
        "full" is today's protocol; "compact" sends memory only when it changes, in one line.
        """
        self.action_space = action_space
        self.provider = provider
        self.context_builder_class = context_builder_class
        self.model = model
        if prompt_layout not in PROMPT_LAYOUTS:
            raise ValueError(f"prompt_layout must be one of {PROMPT_LAYOUTS}, got {prompt_layout!r}")
        self.prompt_layout = prompt_layout
        if response_style not in RESPONSE_STYLES:
            raise ValueError(f"response_style must be one of {RESPONSE_STYLES}, got {response_style!r}")
        self.response_style = response_style
        # For the compact style's memory line: the step whose reply last changed the memory.
        # The runner owns the memory and hands it back each step; the agent only watches it.
        self._memory_seen: str | None = None
        self._memory_step: int | None = None

        logger.info(
            f"DefaultAgent  action_space={self.action_space.__class__.__name__}  "
            f"provider={self.provider.__class__.__name__}  model={self.model}  "
            f"prompt_layout={self.prompt_layout}  response_style={self.response_style}"
        )

    def load_system_prompt(self, task_desc: str) -> None:
        self.task_desc = task_desc

    def _note_memory(self, long_term_memory: str, current_step: int | None) -> None:
        """Record at which step the memory last changed (a memory handed in at step k that
        differs from the one handed in at k-1 was written by the reply at k-1)."""
        mem = (long_term_memory or "").strip()
        if mem != self._memory_seen:
            self._memory_seen = mem
            self._memory_step = (current_step - 1) if current_step else None

    def get_action(
        self,
        frame_buffer: list[np.ndarray],
        thought_history: dict,
        action_history: dict,
        current_step: int | None = None,
        return_messages: bool = False,
        return_messages_with_pic: bool = False,
        long_term_memory: str = "",
        milestone_hint: str = "",
        camera_hint: str = "",
        movement_hint: str = ""
    ) -> tuple[Any, ...]:
        """Get the next action from the LLM based on a history of frames and thoughts.

        Args:
            frame_buffer:            Recent observation frames.
            thought_history:         Past thoughts (list of strings).
            action_history:          Past actions  (list of dicts; length = len(frame_buffer) - 1).
            current_step:            Current step number (optional, for display).
            return_messages:         If True, also return messages sent to LLM.
            return_messages_with_pic: If True, include images in returned messages.
            long_term_memory:        Current long-term memory string.
            milestone_hint:          Ground-truth completion status from the environment.
            camera_hint:             Current camera pitch reported by the environment.
            movement_hint:           Ground-truth position deltas reported by the environment.

        Returns:
            (thought, action, memory_update)
            or (thought, action, memory_update, messages, response_content) if return_messages=True.
        """
        logger.info("Processing observation history...")

        base64_images = convert_buffer_to_base64_images(frame_buffer)
        if not base64_images:
            logger.error("No valid frames could be processed.")
            thought, action = self.get_default_action()
            return thought, action, long_term_memory

        layout = self.prompt_layout
        self._note_memory(long_term_memory, current_step)
        content = [{"type": "text", "text": self.context_builder_class.system_prompt(
            self.task_desc, long_term_memory=long_term_memory, milestone_hint=milestone_hint,
            camera_hint=camera_hint, movement_hint=movement_hint, layout=layout,
            style=self.response_style, memory_step=self._memory_step,
            current_step=current_step).build()}]
        save_content = copy.deepcopy(content)

        for i, base64_img in enumerate(base64_images):
            # Calculate which step this frame corresponds to.
            # If current_step is 8 and we have 3 frames:
            #   frame[0] = step 6, frame[1] = step 7, frame[2] = step 8
            frame_step = current_step - (len(base64_images) - 1 - i) if current_step is not None else None

            hist_index = frame_step - 2  # 0-indexed: step 2 → index 0
            if frame_step > 1 and hist_index < len(action_history) and hist_index < len(thought_history):
                hist_thought = thought_history[hist_index]
                hist_action = action_history[hist_index]
                frame_text = self.context_builder_class.next_step(
                    images_idx=i,
                    total_images_length=len(base64_images),
                    frame_step=frame_step,
                    hist_action=hist_action,
                    hist_thought=hist_thought,
                    layout=layout,
                ).build()
            else:
                frame_text = self.context_builder_class.next_step(
                    images_idx=i,
                    total_images_length=len(base64_images),
                    frame_step=frame_step,
                    layout=layout,
                ).build()

            content.append({"type": "text", "text": frame_text})
            save_content.append({"type": "text", "text": frame_text})
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_img}"}
            })
            save_content.append({
                "type": "image_url",
                "image_url": {"url": "data:image/png;base64,..."}  # placeholder; no raw bytes in saved log
            })

        if layout != "legacy":
            # The per-step state comes last, after the frames, so that everything before it is
            # the same request prefix as the previous step (see PROMPT_LAYOUTS).
            state_text = self.context_builder_class.state_block(
                long_term_memory=long_term_memory, milestone_hint=milestone_hint,
                camera_hint=camera_hint, movement_hint=movement_hint,
                style=self.response_style, memory_step=self._memory_step,
                current_step=current_step)
            if state_text:
                content.append({"type": "text", "text": state_text})
                save_content.append({"type": "text", "text": state_text})

        messages = [{"role": "user", "content": content}]
        save_messages = [{"role": "user", "content": save_content}]

        for attempt in range(max_json_retries := 3):
            try:
                response_content = self.provider.chat(messages)
                logger.info(f"[DefaultAgent] Raw LLM response (attempt {attempt + 1}):\n{response_content}")
                action_state = self.action_space.load_action(response_content)
                thought = action_state.think
                memory_update = action_state.memory_update
                action = self.action_space.dump_action_to_dict(action_state)
                break

            except Exception as e:
                if isinstance(e, json.JSONDecodeError):
                    logger.error(f"JSON parsing failed on attempt {attempt + 1}/{max_json_retries}: {e}")
                else:
                    logger.exception(f"Error during LLM call or JSON parsing (attempt {attempt + 1}/{max_json_retries}):")
                logger.error(
                    f"[DefaultAgent] Response content that failed to parse:\n"
                    f"{response_content if 'response_content' in locals() else '<no response received>'}"
                )

                # A call that ran to the provider's ceiling is a stall, not a transient
                # error, and the retries here are priced for transient errors (a parse
                # failure, a dropped connection). Only CodexProvider raises this: with
                # thinking off the model loops `view_image` on the attached frames until
                # the ceiling (measured 2026-08-18), and a retry loops again -- three
                # ceilings per step is 45 min at the 900 s default. One ceiling, then the
                # no-op the ceiling was priced for.
                if isinstance(e, subprocess.TimeoutExpired):
                    logger.error("Provider call hit its ceiling; not retrying. Using default action.")
                    thought, action = self.get_default_action()
                    memory_update = long_term_memory
                    response_content = "{}"
                    break

                if attempt < max_json_retries - 1:
                    logger.info("Retrying due to error...")
                    continue
                else:
                    logger.error("All retries exhausted. Using default action.")
                    thought, action = self.get_default_action()
                    memory_update = long_term_memory
                    response_content = "{}"

        if return_messages:
            msg_to_return = messages if return_messages_with_pic else save_messages
            return thought, action, memory_update, msg_to_return, response_content
        return thought, action, memory_update

    def get_default_action(self, is_call_failed: bool = True) -> tuple[str, dict]:
        """Return a safe do-nothing action when the LLM fails."""
        if is_call_failed:
            logger.warning("LLM call failed or returned invalid data. Returning a default 'do nothing' action.")
        default_text = "I am experiencing technical difficulties and will stay still."
        default_action_dict = self.action_space.dump_action_to_dict(self.action_space.load_default_action())
        return default_text, default_action_dict
