from __future__ import annotations
import copy
from typing import Any
from loguru import logger
from PIL import Image
import base64
import io
import os, sys
import json
import numpy as np
from openai import OpenAI

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
logger.info(f"System path added: {os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))}")

import utils
from components.action_space.default import ActionState, BaseActionSpace
from components.provider.base import BaseLLMProvider
from components.context.default import DefaultContextBuilder
class DefaultAgent:
    def __init__(
        self, 
        action_space: BaseActionSpace,
        provider: BaseLLMProvider,
        context_builder_class: type[DefaultContextBuilder] = DefaultContextBuilder,
        model: str = None,
    ) -> None:
        """
        An agent that uses a multimodal LLM to play Minecraft.
        """
        self.action_space = action_space
        self.provider = provider
        self.context_builder_class = context_builder_class
        self.model = model

        logger.info(
            f"Default Agent use: action_space: {self.action_space.__class__.__name__} "
            f"provider: {self.provider.__class__.__name__} model: {self.model}"
        )
    
    def load_system_prompt(
        self,
        task_desc: str
    ) -> None:
        self.task_desc = task_desc

    def get_action(
        self, 
        frame_buffer: list[np.ndarray], 
        thought_history: dict, 
        action_history: dict, 
        current_step: int | None = None, 
        return_messages: bool = False,
        return_messages_with_pic: bool = False,
        long_term_memory: str = ""
    ) -> tuple[Any, ...]:
        """
        Get the next action from the LLM based on a history of frames and thoughts.
        
        Args:
            frame_buffer: List of recent observation frames
            thought_history: List of recent thoughts
            action_history: List of recent actions (length = frame_buffer - 1)
            current_step: Current step number (optional, for display purposes)
            return_messages: If True, also return the messages sent to LLM
            long_term_memory: Current long-term memory string to inject into the prompt
        Returns:
            If return_messages=False: (thought, action, memory_update)
            If return_messages=True: (thought, action, memory_update, messages, response_content)
        """
        logger.info("Processing observation history...")
        
        # Image processing for all frames in the buffer
        base64_images = utils.convert.convert_buffer_to_base64_images(frame_buffer)
        if not base64_images:
            logger.error("No valid frames could be processed.")
            thought, action = self.get_default_action()
            return thought, action, long_term_memory

        content = [{"type": "text", "text": self.context_builder_class.system_prompt(self.task_desc, long_term_memory=long_term_memory).build()}]
        save_content = copy.deepcopy(content)
        for i, base64_img in enumerate(base64_images):
            # Calculate which step this frame corresponds to
            # If current_step is 8 and we have 3 frames:
            # frame[0] = step 6, frame[1] = step 7, frame[2] = step 8
            frame_step = current_step - (len(base64_images) - 1 - i) if current_step is not None else None
            
            hist_index = frame_step - 2  # Convert to 0-indexed (step 2 → index 0)
            if frame_step > 1 and hist_index < len(action_history) and hist_index < len(thought_history):
                hist_thought = thought_history[hist_index]
                hist_action = action_history[hist_index]
                frame_text = self.context_builder_class.next_step(
                    images_idx=i,
                    total_images_length=len(base64_images),
                    frame_step=frame_step,
                    hist_action=hist_action,
                    hist_thought=hist_thought
                ).build()
            else:
                frame_text = self.context_builder_class.next_step(
                    images_idx=i,
                    total_images_length=len(base64_images),
                    frame_step=frame_step
                ).build()
                    
            content.append({"type": "text", "text": frame_text})
            save_content.append({"type": "text", "text": frame_text})
            content.append({
                "type": "image_url", 
                "image_url": {"url": f"data:image/png;base64,{base64_img}"}
            })
            save_content.append({
                "type": "image_url", 
                "image_url": {"url": f"data:image/png;base64,..."}
            })
        messages = [{"role": "user", "content": content}]
        save_messages = [{"role": "user", "content": save_content}]

        for attempt in range(max_json_retries := 3):
            try:
                response_content = self.provider.chat(messages)
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

                if attempt < max_json_retries - 1:
                    logger.info("Retrying due to error...")
                    continue
                else:
                    logger.error("All retries exhausted. Using default action.")
                    thought, action = self.get_default_action()
                    memory_update = long_term_memory  # keep existing memory on failure
                    response_content = "{}"
        
        if return_messages:
            msg_to_return = messages if return_messages_with_pic else save_messages
            return thought, action, memory_update, msg_to_return, response_content
        return thought, action, memory_update
        
    def get_default_action(
        self, 
        is_call_failed: bool = True
    ) -> tuple[str, dict]:
        """
        A default thought and action to take when the LLM fails.
        Returns:
            Default response: (thought, action)
        """
        if is_call_failed:
            logger.warning("LLM call failed or returned invalid data. Returning a default 'do nothing' action.")
        default_text = "I am experiencing technical difficulties and will stay still."
        default_action_dict = self.action_space.dump_action_to_dict(self.action_space.load_default_action())
        return default_text, default_action_dict

