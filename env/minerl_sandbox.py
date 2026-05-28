import base64
import io
import os
import json
import time
from typing import Any, Dict, List, Optional

import gymnasium as gym
import numpy as np
import requests
from PIL import Image
from gymnasium import spaces
from loguru import logger

try:
    # Re-export the canonical SandboxClusterTool from benchmark_gen so every
    # part of the codebase uses the same implementation.
    import sys
    from pathlib import Path
    _MINECRAFT_DIR = Path(__file__).resolve().parent.parent
    if str(_MINECRAFT_DIR) not in sys.path:
        sys.path.insert(0, str(_MINECRAFT_DIR))
    from benchmark_gen.sandbox_client import SandboxClusterTool
except ImportError:
    # Fallback: minimal inline definition (pssdk must still be installed)
    try:
        from pssdk import BaseSandboxClusterTool
    except ImportError:
        logger.warning("pssdk not found. Sandbox management will not be available.")
        BaseSandboxClusterTool = object

    class SandboxClusterTool(BaseSandboxClusterTool):  # type: ignore[no-redef]
        """Fallback SandboxClusterTool — prefer benchmark_gen.sandbox_client."""

        def create_env(self, env: str = 'MinecraftSim', obs_size: List[int] = [128, 128], render_size: List[int] = [640, 360], seed: int = 0, record: bool = False, record_path: str = './output/', yaml_config: str = None, commands: List[str] = None, task_text: str = None, call_timeout: int = 0):
            request_body = {"obs_size": obs_size, "yaml_config": yaml_config, "seed": seed, "render_size": render_size, "record": record, "record_path": record_path, "env": env, "commands": commands, "task_text": task_text}
            return self._gateway_post(uri="/create_env", request_body=request_body, call_timeout=call_timeout)

        def reset_env(self, call_timeout: int = 0):
            return self._gateway_post(uri="/reset_env", request_body={}, call_timeout=call_timeout)

        def step(self, action: Dict[str, Any], call_timeout: int = 0):
            return self._gateway_post(uri="/step", request_body={"action": action}, call_timeout=call_timeout)

        def close_env(self, call_timeout: int = 0):
            return self._gateway_post(uri="/close_env", request_body={}, call_timeout=call_timeout)


class MineRLSandboxEnv(gym.Env):
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
        super(MineRLSandboxEnv, self).__init__()
        self.env_id = env_id
        self.sandbox_config = sandbox_config or {}
        self.sandbox_tool = None
        self.server_address = server_address

        # Initialize sandbox tool if configuration or address is available
        endpoint = (
            self.sandbox_config.get("endpoint")
            or os.getenv("FRIDAY_SANDBOX_ENDPOINT", "https://model.sankuai.com/sandboxGateway/system/347")
        )
        token = self.sandbox_config.get("token") or os.getenv("FRIDAY_SANDBOX_TOKEN")
        if endpoint and token:
            self.sandbox_tool = SandboxClusterTool(endpoint, token)

        # Initialize sandbox if no address is provided
        if not self.server_address:
            self._start_sandbox()
        else:
            self._init_remote_env()

        # Define action and observation spaces
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
            "use": spaces.Discrete(2),
        })

        self.observation_space = spaces.Dict({
            "pov": spaces.Box(low=0, high=255, shape=(64, 64, 3), dtype=np.uint8)
        })

        self.last_pov_shape = self.observation_space['pov'].shape

        logger.success(f"Environment '{env_id}' initialized.")

    def _start_sandbox(self):
        """Starts a new sandbox instance and sets the server_address."""
        if not self.sandbox_tool:
            endpoint = (
                self.sandbox_config.get("endpoint")
                or os.getenv("FRIDAY_SANDBOX_ENDPOINT", "https://model.sankuai.com/sandboxGateway/system/347")
            )
            token = self.sandbox_config.get("token") or os.getenv("FRIDAY_SANDBOX_TOKEN")
            if not token:
                raise ValueError(
                    "Sandbox token must be provided in sandbox_config or FRIDAY_SANDBOX_TOKEN environment variable."
                )
            self.sandbox_tool = SandboxClusterTool(endpoint, token)

        body = self.sandbox_config.get("body")
        if body is None:
            body_str = os.getenv("FRIDAY_SANDBOX_BODY")
            if body_str:
                try:
                    body = json.loads(body_str)
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse FRIDAY_SANDBOX_BODY as JSON: {body_str}")
                    body = {}
            else:
                body = {}

        logger.info(f"Starting a new sandbox for environment '{self.env_id}'...")

        try:
            start_params = self.sandbox_tool.sandbox_start(body)
            if not start_params or not start_params.get("success"):
                raise RuntimeError(f"Failed to start sandbox: {start_params}")

            data = start_params.get("data", {})
            host_ip = data.get("host_ip")
            port_mapping = data.get("port_mapping")

            if not host_ip or not port_mapping:
                raise RuntimeError(f"Sandbox started but missing host_ip or port_mapping: {data}")

            port = port_mapping.split(':')[0]
            self.server_address = f"http://{host_ip}:{port}"

            logger.success(
                f"Sandbox started successfully at {self.server_address} "
                f"(Session ID: {self.sandbox_tool.session_id})"
            )

            self._init_remote_env()

        except Exception as e:
            logger.error(f"Error starting sandbox: {e}")
            self._stop_sandbox()
            raise

    def _stop_sandbox(self):
        """Stops the managed sandbox instance."""
        if self.sandbox_tool:
            logger.info(f"Stopping sandbox (Session ID: {self.sandbox_tool.session_id})...")
            try:
                self.sandbox_tool.sandbox_stop()
                logger.success("Sandbox stopped successfully.")
            except Exception as e:
                logger.error(f"Error stopping sandbox: {e}")
            finally:
                self.sandbox_tool = None
                self.server_address = None

    def _init_remote_env(self):
        """Sends the create_env request to the remote server via pssdk gateway."""
        if not self.sandbox_tool:
            raise ValueError("sandbox_tool must be initialized before initializing remote environment.")

        try:
            logger.info(f"Creating remote environment '{self.env_id}' via pssdk gateway...")
            response = self.sandbox_tool.create_env(env=self.env_id)
            self.task = response.get("task_text", "")
            if response.get("status") != 0:
                raise RuntimeError(f"Failed to create remote env: {response.get('msg')}")
            logger.success(f"Remote environment '{self.env_id}' created successfully.")
            time.sleep(10)
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to the MineRL server via gateway. Details: {e}"
            ) from e

    def _get_obs_from_response(self, response_data):
        """
        Extracts and formats observation from the server response dictionary.
        The 'screenshot' value in the dictionary is expected to be a base64 encoded PNG string.
        """
        try:
            screenshot_b64 = response_data.get("screenshot")
            if not screenshot_b64:
                if response_data.get("status") != 0:
                    logger.error(f"Server returned error: {response_data.get('msg')}")
                raise ValueError("Response dictionary does not contain 'screenshot'")

            img_bytes = base64.b64decode(screenshot_b64)
            img = Image.open(io.BytesIO(img_bytes))
            pov = np.array(img, dtype=np.uint8)

            if pov.shape[2] == 4:
                pov = pov[:, :, :3]

            self.last_pov_shape = pov.shape

        except Exception as e:
            logger.error(f"Error processing screenshot from response: {e}")
            pov = np.zeros(self.last_pov_shape, dtype=np.uint8)

        return {"pov": pov}

    def reset(self, seed=None, options=None):
        """Resets the environment to an initial state via pssdk gateway."""
        super().reset(seed=seed)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Resetting environment via gateway (attempt {attempt + 1}/{max_retries})...")
                response = self.sandbox_tool.reset_env()

                if response.get("status") != 0:
                    raise RuntimeError(f"Server error during reset: {response.get('msg')}")

                observation = self._get_obs_from_response(response)
                return observation, {}
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
        """Executes one time step in the environment via pssdk gateway."""
        serializable_action = {}
        for key, value in action.items():
            if key == 'camera':
                serializable_action[key] = [float(v) for v in value]
            elif isinstance(value, (list, tuple)):
                # voxels / mobs query boxes and any other list-valued keys
                serializable_action[key] = [int(v) for v in value]
            else:
                serializable_action[key] = int(value)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.sandbox_tool.step(serializable_action)
                if response.get("status") != 0:
                    raise RuntimeError(f"Server error during step: {response.get('msg')}")

                observation = self._get_obs_from_response(response)
                reward = float(response.get("reward", 0.0))
                terminated = bool(response.get("done", False))
                truncated = False
                # Pass through any extra fields the server returns as info.
                # The server may return a nested "info" dict (MineStudio style)
                # or flat top-level keys (player_pos, inventory, events, etc.).
                raw_info = response.get("info")
                if isinstance(raw_info, dict):
                    info = raw_info
                else:
                    # Collect all non-protocol top-level keys as info.
                    _proto_keys = {"status", "msg", "screenshot", "reward", "done"}
                    info = {k: v for k, v in response.items() if k not in _proto_keys}

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

                raise RuntimeError(
                    f"Connection to MineRL server lost during step after {max_retries} attempts: {e}"
                )

    def close(self):
        """Cleans up the environment."""
        logger.info("Environment is closing.")
        self._stop_sandbox()

    def render(self, mode='human'):
        """Rendering is handled by the Minecraft client, not this environment wrapper."""
        if mode == 'human':
            logger.info("Rendering is handled by the Minecraft client instance.")
        else:
            super().render(mode=mode)
