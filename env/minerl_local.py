import base64
import io
import os
import json
import time
import http.client
from typing import Dict, Any

import gymnasium as gym
import numpy as np
import requests
from PIL import Image
from gymnasium import spaces
from loguru import logger

try:
    from pssdk import BaseSandboxClusterTool
    from pssdk import errors as pssdk_errors
except ImportError:
    logger.warning("pssdk not found. Sandbox management will not be available.")
    BaseSandboxClusterTool = object
    pssdk_errors = None


class MineRLLocalEnv(gym.Env):
    """
    A custom OpenAI Gym environment for MineRL, controlled by a remote HTTP server.

    This environment can optionally manage its own remote sandbox instance.
    The server is expected to have the following endpoints:
    - POST /create_env: Creates the MineRL environment.
    - POST /reset_env: Resets the environment and returns the initial observation.
    - POST /step: Executes an action and returns the next state.
    """
    metadata = {'render_modes': ['human']}

    def __init__(self, server_address=None, env_id="MineRLBasaltFindCave-v0", sandbox_config=None):
        """
        Initializes the environment.

        Args:
            server_address (str, optional): The full URL of the remote MineRL server.
                If None, it will attempt to start a new sandbox using sandbox_config.
            env_id (str): The ID of the MineRL environment to create.
            sandbox_config (dict, optional): Configuration for starting a new sandbox.
                Expected keys: 'endpoint', 'token', 'body'.
        """
        super(MineRLLocalEnv, self).__init__()
        self.env_id = env_id
        self.server_address = server_address
        
        # Initialize sandbox tool if configuration or address is available
        logger.info(f"Using direct server: {self.server_address}")
        self._init_remote_env()

        # Define action and observation spaces
        # Based on the script, the action is a dictionary of controls.
        self.action_space = spaces.Dict({
            "ESC": spaces.Discrete(2),
            "attack": spaces.Discrete(2),
            "back": spaces.Discrete(2),
            "camera": spaces.Box(low=-180.0, high=180.0, shape=(2,), dtype=np.float32),
            "drop": spaces.Discrete(2),
            "forward": spaces.Discrete(2),
            "hotbar.1": spaces.Discrete(2),
            "hotbar.2": spaces.Discrete(2),
            "hotbar.3": spaces.Discrete(2),
            "hotbar.4": spaces.Discrete(2),
            "hotbar.5": spaces.Discrete(2),
            "hotbar.6": spaces.Discrete(2),
            "hotbar.7": spaces.Discrete(2),
            "hotbar.8": spaces.Discrete(2),
            "hotbar.9": spaces.Discrete(2),
            "inventory": spaces.Discrete(2),
            "jump": spaces.Discrete(2),
            "left": spaces.Discrete(2),
            "pickItem": spaces.Discrete(2),
            "right": spaces.Discrete(2),
            "sneak": spaces.Discrete(2),
            "sprint": spaces.Discrete(2),
            "swapHands": spaces.Discrete(2),
            "use": spaces.Discrete(2)
        })

        # MineRL observations are typically a dictionary including a POV image.
        self.observation_space = spaces.Dict({
            "pov": spaces.Box(low=0, high=255, shape=(64, 64, 3), dtype=np.uint8)
        })
        
        # Initialize last_pov_shape with the default from observation space
        self.last_pov_shape = self.observation_space['pov'].shape
        
        logger.success(f"Environment '{env_id}' initialized.")

    def __post_mine_rl_request(
        self,
        endpoint: str,
        json_data: dict = None,
        timeout: int = 180
    ) -> dict:
        base = self.server_address.rstrip("/")
        r = requests.post(f"{base}/{endpoint}", json=json_data, timeout=timeout)
        r.raise_for_status()
        return r.json()

    def _init_remote_env(self):
        """Sends the create_env request to the remote server via pssdk gateway."""
        try:
            logger.info(f"Creating environment '{self.env_id}' on local server...")
            data = self.__post_mine_rl_request("create_env", json_data={"env": self.env_id}, timeout=6000)
            self.task = data.get("task_text", "")
            if data.get("status") != 0:
                raise RuntimeError(data.get("msg", "create_env failed"))
            logger.success(f"Environment '{self.env_id}' created on local server.")
        except Exception as e:
            raise ConnectionError(f"Failed to create env on local server: {e}") from e

    def _get_obs_from_response(self, response_data):
        """
        Extracts and formats observation from the server response dictionary.
        The 'screenshot' value in the dictionary is expected to be a base64 encoded PNG string.
        """
        try:
            screenshot_b64 = response_data.get("screenshot")
            if not screenshot_b64:
                # If it's a reset or step and we have no screenshot, it's an error in the response
                if response_data.get("status") != 0:
                    logger.error(f"Server returned error: {response_data.get('msg')}")
                raise ValueError("Response dictionary does not contain 'screenshot'")

            img_bytes = base64.b64decode(screenshot_b64)
            img = Image.open(io.BytesIO(img_bytes))
            pov = np.array(img, dtype=np.uint8)

            # The server might return images with an alpha channel (RGBA).
            # Our observation space is RGB, so we slice it off if present.
            if pov.shape[2] == 4:
                pov = pov[:, :, :3]
            
            # Update the last known shape on success
            self.last_pov_shape = pov.shape

        except Exception as e:
            logger.error(f"Error processing screenshot from response: {e}")
            # On error, return a zero-array with the last known good shape
            pov = np.zeros(self.last_pov_shape, dtype=np.uint8)

        return {"pov": pov}

    def reset(self, seed=None, options=None):
        """
        Resets the environment to an initial state via pssdk gateway.
        """
        super().reset(seed=seed)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Resetting environment on local server (attempt {attempt + 1}/{max_retries})...")
                response = self.__post_mine_rl_request("reset_env", timeout=180)
                if response.get("status") != 0:
                    raise RuntimeError(f"Server error during reset: {response.get('msg')}")
                
                observation = self._get_obs_from_response(response)
                info = {} # No extra info from reset

                return observation, info
            except Exception as e:
                logger.warning(f"Error during reset (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                
                logger.error("Reset failed after all retries.")
                if os.getenv("MINE_RL_DEBUG_BREAKPOINT") == "1":
                    logger.info("Entering breakpoint due to reset failure...")
                    import pdb; pdb.set_trace()
                
                raise RuntimeError(f"Failed to reset environment after {max_retries} attempts: {e}")

    def step(self, action):
        """
        Executes one time step in the environment via pssdk gateway.
        """
        # The action from action_space.sample() needs to be converted to a JSON-serializable format.
        serializable_action = {}
        for key, value in action.items():
            if key == 'camera':
                serializable_action[key] = [float(v) for v in value]
            else:
                serializable_action[key] = int(value)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.__post_mine_rl_request("step", {"action": serializable_action}, timeout=120)
                if response.get("status") != 0:
                    raise RuntimeError(f"Server error during step: {response.get('msg')}")
                
                # Extract observation, reward, done status from response
                observation = self._get_obs_from_response(response)
                reward = float(response.get("reward", 0.0))
                terminated = bool(response.get("done", False))
                truncated = False 
                info = {}

                return observation, reward, terminated, truncated, info

            except Exception as e:
                logger.warning(f"Error during step (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                
                logger.error("Step failed after all retries.")
                if os.getenv("MINE_RL_DEBUG_BREAKPOINT") == "1":
                    logger.info("Entering breakpoint due to step failure...")
                    import pdb; pdb.set_trace()
                
                raise RuntimeError(f"Connection to MineRL server lost during step after {max_retries} attempts: {e}")

    def close(self):
        """
        Cleans up the environment.
        """
        logger.info("Environment is closing.")
        # If there were a /close_env endpoint, it would be called here.
        # requests.post(f"{self.server_address}/close_env")


    def render(self, mode='human'):
        """
        Rendering is handled by the Minecraft client, not this environment wrapper.
        """
        if mode == 'human':
            logger.info("Rendering is handled by the Minecraft client instance.")
        else:
            super().render(mode=mode)

