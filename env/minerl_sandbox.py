import base64
import io
import os
import time
import uuid
from typing import Any, Dict, List, Optional

import gymnasium as gym
import numpy as np
import requests
from PIL import Image
from gymnasium import spaces
from loguru import logger


def _get_server_address() -> str:
    addr = os.getenv("MC_SANDBOX_URL", "").rstrip("/")
    if not addr:
        raise ValueError(
            "MC_SANDBOX_URL environment variable is not set. "
            "Please add 'export MC_SANDBOX_URL=http://<host>:<port>' to ~/.zshrc "
            "and restart your shell (or run: source ~/.zshrc)."
        )
    return addr


def _post(server_address: str, endpoint: str, json_data: dict = None, timeout: int = 180,
          session_id: Optional[str] = None) -> dict:
    url = f"{server_address}/{endpoint.lstrip('/')}"
    body = dict(json_data or {})
    if session_id is not None:
        body["session_id"] = session_id
    r = requests.post(url, json=body, timeout=timeout)
    r.raise_for_status()
    return r.json()


class MineRLSandboxEnv(gym.Env):
    """Gym environment backed by a remote Minecraft HTTP server.

    If both FRIDAY_SANDBOX_TOKEN and FRIDAY_SANDBOX_ENDPOINT are set, the
    Friday platform SDK (pssdk / mt-paas-sandbox-python-sdk) is used.
    Otherwise, the original direct-HTTP mode (MC_SANDBOX_URL) is used.
    """

    metadata = {'render_modes': ['human']}

    def __init__(self, server_address: Optional[str] = None, env_id: str = "MineRLBasaltFindCave-v0",
                 sandbox_config: Optional[dict] = None, session_id: Optional[str] = None):
        super(MineRLSandboxEnv, self).__init__()
        self.env_id = env_id
        self.sandbox_tool = None

        friday_token = os.getenv("FRIDAY_SANDBOX_TOKEN", "")
        friday_endpoint = server_address or os.getenv("FRIDAY_SANDBOX_ENDPOINT", "")
        self.use_friday_platform = bool(friday_token and friday_endpoint)

        if self.use_friday_platform:
            # pip install mt-paas-sandbox-python-sdk==1.1.0
            from pssdk import BaseSandboxClusterTool, with_retry

            @with_retry(max_attempts=3, retry_interval=10,
                        infinite_retry_on_resource_limit=True, exclude_methods=[])
            class _FridayTool(BaseSandboxClusterTool):
                pass

            self._friday_tool = _FridayTool(friday_endpoint, friday_token)
            if session_id:
                self._friday_tool.session_id = session_id
            self.session_id: str = self._friday_tool.session_id
            self.server_address = friday_endpoint.rstrip("/")
            self._friday_tool.sandbox_start()
            logger.info(f"Using Friday platform sandbox: {self.server_address}")
        else:
            self.server_address = (server_address or _get_server_address()).rstrip("/")
            # 每个实例拥有独立的 session_id，确保并发时服务端可路由到正确实例
            self.session_id: str = session_id or str(uuid.uuid4())
            logger.info(f"Using HTTP sandbox server: {self.server_address}")

        logger.info(f"Session ID: {self.session_id}")
        self._init_remote_env()

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

    def _post(self, endpoint: str, json_data: dict = None, timeout: int = 180) -> dict:
        if self.use_friday_platform:
            return self._friday_tool._gateway_post(
                uri=f"/{endpoint.lstrip('/')}",
                request_body=dict(json_data or {}),
                call_timeout=timeout,
                params={},
                headers={},
            )
        return _post(self.server_address, endpoint, json_data, timeout, self.session_id)

    def _init_remote_env(self):
        try:
            logger.info(f"Creating environment '{self.env_id}' on server {self.server_address} ...")
            response = self._post("create_env", {"env": self.env_id}, timeout=6000)
            self.task = response.get("task_text", "")
            if response.get("status") != 0:
                raise RuntimeError(response.get("msg", "create_env failed"))
            logger.success(f"Remote environment '{self.env_id}' created successfully. session_id={self.session_id}")
            time.sleep(10)
        except Exception as e:
            raise ConnectionError(f"Failed to create env on server: {e}") from e

    def create_env(
        self,
        env: str = "MinecraftSim",
        obs_size: Optional[List[int]] = None,
        render_size: Optional[List[int]] = None,
        seed: int = 0,
        record: bool = False,
        record_path: str = "./output/",
        yaml_config: Optional[str] = None,
        commands: Optional[List[str]] = None,
        task_text: Optional[str] = None,
        call_timeout: int = 0,
    ) -> dict:
        """Send create_env to the server (used to rebuild the scene with new commands)."""
        timeout = call_timeout if call_timeout > 0 else 180
        body = {
            "env": env,
            "obs_size": obs_size if obs_size is not None else [128, 128],
            "render_size": render_size if render_size is not None else [640, 360],
            "seed": seed,
            "record": record,
            "record_path": record_path,
            "yaml_config": yaml_config,
            "commands": commands,
            "task_text": task_text,
        }
        # session_id 由 self._post 统一注入
        return self._post("create_env", body, timeout=timeout)

    def _get_obs_from_response(self, response_data: dict) -> dict:
        try:
            screenshot_b64 = response_data.get("screenshot")
            if not screenshot_b64:
                if response_data.get("status") != 0:
                    logger.error(f"Server returned error: {response_data.get('msg')}")
                raise ValueError("Response does not contain 'screenshot'")
            img_bytes = base64.b64decode(screenshot_b64)
            img = Image.open(io.BytesIO(img_bytes))
            pov = np.array(img, dtype=np.uint8)
            if pov.ndim == 3 and pov.shape[2] == 4:
                pov = pov[:, :, :3]
            self.last_pov_shape = pov.shape
        except Exception as e:
            logger.error(f"Error processing screenshot: {e}")
            pov = np.zeros(self.last_pov_shape, dtype=np.uint8)
        return {"pov": pov}

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Resetting environment (attempt {attempt + 1}/{max_retries}) session_id={self.session_id}...")
                response = self._post("reset_env", timeout=180)
                if response.get("status") != 0:
                    raise RuntimeError(f"Server error during reset: {response.get('msg')}")
                return self._get_obs_from_response(response), {}
            except Exception as e:
                logger.warning(f"Error during reset (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                logger.error("Reset failed after all retries.")
                if os.getenv("MINE_RL_DEBUG_BREAKPOINT") == "1":
                    import pdb; pdb.set_trace()
                raise RuntimeError(f"Failed to reset environment after {max_retries} attempts: {e}")

    def step(self, action):
        serializable_action: Dict[str, Any] = {}
        for key, value in action.items():
            if key == 'camera':
                serializable_action[key] = [float(v) for v in value]
            elif isinstance(value, str):
                serializable_action[key] = value
            elif isinstance(value, dict):
                # Pass through dict values as-is (e.g. voxel_query, mob_query injected by MilestoneChecker)
                serializable_action[key] = value
            elif isinstance(value, (list, tuple)):
                serializable_action[key] = [int(v) for v in value]
            else:
                serializable_action[key] = int(value)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # session_id 由 self._post 统一注入到 body
                response = self._post("step", {"action": serializable_action}, timeout=120)
                if response.get("status") != 0:
                    raise RuntimeError(f"Server error during step: {response.get('msg')}")
                observation = self._get_obs_from_response(response)
                reward = float(response.get("reward", 0.0))
                terminated = bool(response.get("done", False))
                raw_info = response.get("info")
                if isinstance(raw_info, dict):
                    info = raw_info
                else:
                    _proto_keys = {"status", "msg", "screenshot", "reward", "done"}
                    info = {k: v for k, v in response.items() if k not in _proto_keys}
                return observation, reward, terminated, False, info
            except Exception as e:
                logger.warning(f"Error during step (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                logger.error("Step failed after all retries.")
                if os.getenv("MINE_RL_DEBUG_BREAKPOINT") == "1":
                    import pdb; pdb.set_trace()
                raise RuntimeError(
                    f"Connection to MineRL server lost during step after {max_retries} attempts: {e}"
                )

    def close(self):
        logger.info(f"Environment is closing. session_id={self.session_id}")
        try:
            resp = self._post("close_env", timeout=30)
            if resp.get("status") == 0:
                logger.success(f"close_env: server-side resources released. session_id={self.session_id}")
            else:
                logger.warning(f"close_env returned non-zero status: {resp.get('msg')}")
        except Exception as e:
            logger.warning(f"close_env request failed (ignored): {e}")
        if self.use_friday_platform:
            try:
                self._friday_tool.sandbox_stop()
                logger.info(f"Friday platform sandbox stopped. session_id={self.session_id}")
            except Exception as e:
                logger.warning(f"Friday sandbox_stop failed (ignored): {e}")

    def render(self, mode='human'):
        if mode != 'human':
            super().render(mode=mode)
