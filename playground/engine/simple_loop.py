from collections import deque
from loguru import logger
import signal
import time
import uuid
import sys
import gymnasium as gym
from pathlib import Path

from playground import utils
from env.tools.render import RenderWrapper
from playground.agent.default import DefaultAgent

class AgentSimpleLoopEndine:
    def __init__(
        self,
        video_save_dir: Path,
        message_save_dir: Path,
        frame_buffer_size: int = 3,
        max_steps: int = 500
    ) -> None:
        self.video_save_dir = video_save_dir
        self.message_save_dir = message_save_dir
        self.frame_buffer_size = frame_buffer_size
        self.max_steps = max_steps
        
    def fire(
        self,
        run_id: str,
        task_id: str,
        task_desc: str,
        agent: DefaultAgent,
        env: gym.Env,
        loading_command_steps: int = 0,
        save_messages: bool = False
    ):
        try:
            # Init state
            video_save_dir = self.video_save_dir / task_id / run_id
            message_save_path = self.message_save_dir / task_id / f"{run_id}.json"

            frame_buffer = deque(maxlen=self.frame_buffer_size)
            thought_history, action_history, message_history = [], [], []  # Keep all history (thought & action & message)
            long_term_memory: str = ""  # agent self-maintained long-term memory
            run_start_time = time.strftime("%YYYY%mm%dd-%HH%MM%SS")

            # Handle signal
            def _handle_singal(sig, frame):
                logger.warning(f"【{run_id}】\nCtrl+C detected! Saving messages before exit...")
                if save_messages and message_history:
                    utils.file.save_messages(
                        message_history, task_id, run_start_time, message_save_path,
                        is_error=True, error_message="Interrupted by user (Ctrl+C)"
                    )
                    logger.success(f"【{run_id}】Saved {len(message_history)} interactions before exit")
                    sys.exit(0)
                else:
                    sys.exit(1)

            signal.signal(signal.SIGINT, _handle_singal)

            env_wrapper = RenderWrapper(env, save_messages, video_save_dir)
            # Main agent loop
            has_loading_command_steps = loading_command_steps > 0
            obs, info = env_wrapper.reset(save_frame=not has_loading_command_steps)
            frame_buffer.append(obs["pov"])
            
            # Wait has_loading_command_steps for command initial
            for step in range(loading_command_steps):
                logger.info(f"【{run_id}】--- Loading Command Step {step + 1}/{loading_command_steps} ---")
                _, action = agent.get_default_action(is_call_failed=False)
                obs, reward, terminated, truncated, info = env_wrapper.step(action, save_frame=(step + 1 == loading_command_steps))
            logger.info(f"【{run_id}】MineCraft Command Loaded.")
            
            agent.load_system_prompt(task_desc)

            episode_num = 1
            for step in range(self.max_steps):
                logger.info(f"【{run_id}】--- Step {step + 1}/{self.max_steps} ---")

                if save_messages:
                    thought, action, memory_update, messages, response = agent.get_action(
                        list(frame_buffer), list(thought_history), list(action_history), 
                        current_step=step + 1, return_messages=True, return_messages_with_pic=True,
                        long_term_memory=long_term_memory
                    )
                    # Save the interaction
                    message_history.append({
                        "step": step + 1,
                        "episode": episode_num,
                        "timestamp": time.strftime("%YYYY%mm%dd-%HH%MM%SS"),
                        "thought": thought,
                        "action": action,
                        "memory_update": memory_update,
                        "messages": messages,
                        "response": response,
                    })
                else:
                    thought, action, memory_update = agent.get_action(
                        list(frame_buffer), list(thought_history), list(action_history), step + 1,
                        long_term_memory=long_term_memory
                    )
                
                if action is None:
                    logger.error(f"【{run_id}】Agent failed to provide an action. Ending episode.")
                    break

                # Update long-term memory with agent's self-reported memory_update
                if memory_update and memory_update.strip():
                    long_term_memory = memory_update.strip()

                thought_history.append(thought)
                action_history.append(action)
                obs, reward, terminated, truncated, info = env_wrapper.step(action)
                done = terminated or truncated
                frame_buffer.append(obs['pov'])
                logger.info(f"【{run_id}】Thought: '{thought}' -> Action: {action}, Reward: {reward}, Done: {done}")

                if save_messages and message_history:
                    message_history[-1]["reward"] = reward
                    message_history[-1]["done"] = done
                    utils.file.save_messages(message_history, task_id, run_start_time, message_save_path)
                    
                    # Log progress every 10 steps
                    if (step + 1) % 10 == 0:
                        logger.info(f"【{run_id}】Auto-saved {len(message_history)} interactions to {message_save_path}")

                # Save video checkpoint every 10 steps so you can preview current progress
                if (step + 1) % 10 == 0:
                    env_wrapper.save_video_checkpoint()
                
                if done:
                    logger.success(f"【{run_id}】Episode {episode_num} finished!")
                    logger.info("【{run_id}】Ending run after episode completion.")
                    break  # Exit the loop instead of resetting for a new episode
            
            env_wrapper.close()

            # Final save (already saved in real-time, but save once more for completeness)
            if save_messages and message_history and message_save_path:
                utils.file.save_messages(message_history, task_id, run_start_time, message_save_path)
                logger.success(f"【{run_id}】✅ Final save: {len(message_history)} total interactions saved to {message_save_path}")
        
        except Exception as e:
            logger.exception("【{run_id}】An error occurred during the agent run:")
            
            # Try to save messages even if there was an error (add ERROR suffix to filename)
            if save_messages and 'message_history' in locals() and message_history and 'messages_file' in locals():
                try:
                    error_message_save_path = message_save_path.replace('.json', '_ERROR.json')
                    utils.file.save_messages(
                        message_history, task_id, run_start_time, error_message_save_path,
                        is_error=True, error_msg="Interrupted by user (Ctrl+C)"
                    )
                    logger.warning(f"【{run_id}】⚠️ Saved {len(message_history)} interactions (with error) to {error_message_save_path}")
                except Exception as save_error:
                    logger.error(f"【{run_id}】Failed to save message history after error: {save_error}")
        finally:
            logger.success("【{run_id}】Agent run finished.")
        