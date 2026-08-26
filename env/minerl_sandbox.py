import base64
import io
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import gymnasium as gym
import numpy as np
import requests
from PIL import Image
from gymnasium import spaces
from loguru import logger


DOCKER_SANDBOX_DEFAULT_URL = "http://localhost:8000"

# `reset_env` starts a Minecraft JVM and generates the scene's world, and 180s is
# not enough for that on a cold container -- measured at 63s once warm and over
# 180s cold on scene 0694. Every retry starts *another* JVM and leaks the one that
# timed out, so a too-short ceiling degrades the sandbox instead of recovering it.
MC_RESET_TIMEOUT = int(os.getenv("MC_RESET_TIMEOUT", 600))
MC_STEP_TIMEOUT = int(os.getenv("MC_STEP_TIMEOUT", 120))

# Cluster-wide cap on concurrent resets. A reset is the server's expensive operation
# (JVM boot + world gen + first-obs encode, all GIL-contended with every session's
# steps); the 154-scene campaign's short episodes made resets cluster until none
# finished inside 600s x 3 -- 7 episodes died that way in the first 40 minutes of the
# g56l154 rerun while /monitor/alive answered in 0.0s. Slots serialise the expensive
# op and leave stepping alone. mkdir is the atomic primitive (works on the shared
# pool); a crashed holder's slot is stolen after the TTL; the holder refreshes its
# timestamp before each attempt so a legitimate 600s attempt is never stolen.
# 0 slots = off, byte-identical behaviour.
MC_RESET_SLOTS = int(os.getenv("MC_RESET_SLOTS", "0"))
MC_RESET_SLOT_DIR = os.getenv("MC_RESET_SLOT_DIR", "")
_RESET_SLOT_TTL = 900


def _acquire_reset_slot(session_id: str):
    """Take one of the MC_RESET_SLOTS mkdir-slots, or None when disabled/timed out.
    Waiting longer than the episode can afford is worse than contending: after 15
    minutes the reset proceeds slotless rather than deadlocking the cell."""
    if not MC_RESET_SLOTS or not MC_RESET_SLOT_DIR:
        return None
    import random, shutil as _sh
    base = Path(MC_RESET_SLOT_DIR)
    base.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + 900
    while time.time() < deadline:
        for i in range(MC_RESET_SLOTS):
            d = base / f"slot{i}.d"
            try:
                d.mkdir()
                (d / "owner").write_text(f"{os.getpid()} {session_id} {time.time()}")
                return d
            except FileExistsError:
                try:
                    ts = float((d / "owner").read_text().split()[-1])
                    if time.time() - ts > _RESET_SLOT_TTL:
                        _sh.rmtree(d, ignore_errors=True)
                except Exception:
                    pass
        time.sleep(3 + random.random() * 3)
    logger.warning(f"[reset-slot] none free after 15 min; resetting without one "
                   f"session_id={session_id}")
    return None


def _refresh_reset_slot(slot, session_id: str) -> None:
    if slot is not None:
        try:
            (slot / "owner").write_text(f"{os.getpid()} {session_id} {time.time()}")
        except OSError:
            pass


def _release_reset_slot(slot) -> None:
    if slot is not None:
        import shutil as _sh
        _sh.rmtree(slot, ignore_errors=True)


def _get_server_address() -> str:
    addr = os.getenv("MC_SANDBOX_URL", "").rstrip("/")
    if not addr:
        logger.info(
            f"MC_SANDBOX_URL not set, falling back to Docker default: {DOCKER_SANDBOX_DEFAULT_URL}"
        )
        return DOCKER_SANDBOX_DEFAULT_URL
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
                 sandbox_config: Optional[dict] = None, session_id: Optional[str] = None,
                 use_friday: bool = False):
        super(MineRLSandboxEnv, self).__init__()
        self.env_id = env_id
        self.sandbox_tool = None

        friday_token = os.getenv("FRIDAY_SANDBOX_TOKEN", "")
        friday_endpoint = server_address or os.getenv("FRIDAY_SANDBOX_ENDPOINT", "")
        # 默认走 Docker；仅当显式传入 use_friday=True 时才走 Friday 平台
        self.use_friday_platform = use_friday and bool(friday_token and friday_endpoint)

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
        slot = _acquire_reset_slot(self.session_id)
        try:
            for attempt in range(max_retries):
                try:
                    _refresh_reset_slot(slot, self.session_id)
                    logger.info(f"Resetting environment (attempt {attempt + 1}/{max_retries}) session_id={self.session_id}...")
                    response = self._post("reset_env", timeout=MC_RESET_TIMEOUT)
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
        finally:
            _release_reset_slot(slot)

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
                response = self._post("step", {"action": serializable_action}, timeout=MC_STEP_TIMEOUT)
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
