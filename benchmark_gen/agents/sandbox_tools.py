"""
agents/sandbox_tools.py

Minecraft Sandbox Tool Library
================================
Provides callable tools that AutoGen agents can invoke to interact with the
Minecraft sandbox environment (via MineRLSandboxEnv / pssdk gateway).

Key capabilities exposed as plain Python functions (AutoGen tool-use compatible):
  - setup_sandbox()          : start & connect to a sandbox, return handle
  - execute_commands()       : send /commands, return screenshot(s) as base64
  - execute_agent_action()   : control an AI agent for N steps, return screenshots
  - take_screenshot()        : grab current frame
  - close_sandbox()          : release the sandbox

All functions accept a SandboxHandle (opaque dict) so that multiple agents can
share / pass around the same live environment.
"""

from __future__ import annotations

import base64
import io
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Resolve lumine-client/minecraft path
# This file lives at: lumine-client/minecraft/benchmark_gen/agents/sandbox_tools.py
# ---------------------------------------------------------------------------
AGENTS_DIR = Path(__file__).resolve().parent           # benchmark_gen/agents/
BENCHMARK_GEN_DIR = AGENTS_DIR.parent                  # benchmark_gen/
LUMINE_CLIENT_DIR = BENCHMARK_GEN_DIR.parent           # lumine-client/minecraft/

if str(LUMINE_CLIENT_DIR) not in sys.path:
    sys.path.insert(0, str(LUMINE_CLIENT_DIR))


# ---------------------------------------------------------------------------
# SandboxHandle – opaque dict with live env + metadata
# ---------------------------------------------------------------------------

SandboxHandle = Dict[str, Any]
"""
Keys:
  env           : MineRLSandboxEnv instance (or LazyMCBenchSandboxEnv for lazy handles)
  default_action: dict  – zero noop action
  last_pov      : np.ndarray | None  – most-recent RGB frame
  tmp_dir       : str  – scratch directory for saving images
  _lazy         : bool – True when using lazy-init semantics (env not yet started)
"""


# ---------------------------------------------------------------------------
# LazyMCBenchSandboxEnv – deferred sandbox startup
# ---------------------------------------------------------------------------

class LazyMCBenchSandboxEnv:
    """
    A thin proxy that mirrors the MineRLSandboxEnv interface but defers
    the actual sandbox_start + create_env call until the first time
    commands are provided.

    Lifecycle
    ---------
    1. Construction (``__init__``):
       - Creates the ``SandboxClusterTool`` (only reads credentials from env).
       - Does NOT call ``sandbox_start`` or ``create_env``.
       - The sandbox resource is therefore not allocated yet.

    2. First real use (``initialize(commands, task_text)``):
       - Calls ``sandbox_tool.sandbox_start()`` to acquire a pod.
       - Calls ``sandbox_tool.create_env(env='MinecraftSim', commands=commands, …)``
         with the commands the agent has designed — exactly as
         ``eval_benchmark.py``'s ``MineRLBenchmarkEnv._init_remote_env()`` does.
       - Sets ``self._ready = True``.

    3. Subsequent calls:
       - ``create_env(commands, task_text)`` just re-sends the scene commands to
         rebuild the scene (no re-``sandbox_start``).
       - ``reset_env``, ``step``, ``close_env`` delegate to ``sandbox_tool``.
    """

    def __init__(
        self,
        sandbox_config: Optional[Dict[str, Any]] = None,
        env_id: str = "MinecraftSim",
    ) -> None:
        self.env_id = env_id
        self._ready = False
        self.server_address: Optional[str] = None
        self.task: str = ""

        # Build the SandboxClusterTool (credentials only, no network call yet)
        from benchmark_gen.sandbox_client import SandboxClusterTool as _SCT

        cfg = sandbox_config or {}
        endpoint = (
            cfg.get("endpoint")
            or os.getenv(
                "FRIDAY_SANDBOX_ENDPOINT",
                "https://model.sankuai.com/sandboxGateway/system/347",
            )
        )
        token = cfg.get("token") or os.getenv("FRIDAY_SANDBOX_TOKEN")
        if not token:
            raise ValueError(
                "Sandbox token must be provided in sandbox_config or "
                "FRIDAY_SANDBOX_TOKEN environment variable."
            )
        self.sandbox_tool = _SCT(endpoint, token)
        self._sandbox_config = cfg
        print("  [LazySandbox] SandboxClusterTool created – sandbox NOT yet started.")

    # ------------------------------------------------------------------
    # Lazy initialisation – called on first real tool invocation
    # ------------------------------------------------------------------

    def initialize(
        self,
        commands: Optional[List[str]] = None,
        task_text: Optional[str] = None,
    ) -> None:
        """
        Start the sandbox and run create_env with the agent's commands.

        This mirrors ``eval_benchmark.py``'s ``MineRLBenchmarkEnv._init_remote_env``
        exactly: sandbox_start first, then create_env with the full parameter set.
        """
        if self._ready:
            # Already started – just rebuild the scene with new commands
            # (no sandbox_start needed; skip the long init sleep in _create_env)
            self._create_env(commands=commands, task_text=task_text, is_rebuild=True)
            return

        # ── Step 1: sandbox_start ──────────────────────────────────────
        cfg = self._sandbox_config
        body = cfg.get("body")
        if body is None:
            body_str = os.getenv("FRIDAY_SANDBOX_BODY")
            if body_str:
                try:
                    body = json.loads(body_str)
                except json.JSONDecodeError:
                    body = {}
            else:
                body = {}

        print("  [LazySandbox] Calling sandbox_start()…")
        start_params = self.sandbox_tool.sandbox_start(body)
        if not start_params or not start_params.get("success"):
            raise RuntimeError(f"sandbox_start failed: {start_params}")

        data = start_params.get("data", {})
        host_ip = data.get("host_ip")
        port_mapping = data.get("port_mapping")
        if not host_ip or not port_mapping:
            raise RuntimeError(
                f"Sandbox started but missing host_ip or port_mapping: {data}"
            )
        port = port_mapping.split(":")[0]
        self.server_address = f"http://{host_ip}:{port}"
        print(f"  [LazySandbox] Sandbox started at {self.server_address}")

        # ── Step 2: create_env (scene build) ─────────────────────────
        self._create_env(commands=commands, task_text=task_text, is_rebuild=False)
        self._ready = True

    def _create_env(
        self,
        commands: Optional[List[str]] = None,
        task_text: Optional[str] = None,
        is_rebuild: bool = False,
    ) -> None:
        """
        Send create_env to the server with the full parameter set used by
        eval_benchmark.py's MineRLBenchmarkEnv._init_remote_env().

        Args:
            is_rebuild: True when the sandbox is already running and we are only
                        rebuilding the scene (subsequent calls).  In this case
                        a shorter settle sleep (2 s) is used instead of 10 s.
        """
        print(
            f"  [LazySandbox] create_env: {len(commands or [])} commands, "
            f"task='{(task_text or '')[:60]}'"
        )
        response = self.sandbox_tool.create_env(
            env="MinecraftSim",
            obs_size=[128, 128],
            render_size=[640, 360],
            seed=0,
            record=False,
            record_path="./output/",
            yaml_config=None,
            commands=commands if commands else None,
            task_text=task_text or None,
            call_timeout=120,
        )
        if response.get("status") != 0:
            raise RuntimeError(f"create_env failed: {response.get('msg')}")
        self.task = response.get("task_text", "") or (task_text or "")
        print(f"  [LazySandbox] create_env OK – task='{self.task[:60]}'")
        # First init needs a longer wait for the server to fully boot the world.
        # Scene rebuilds (is_rebuild=True) only need a short settle.
        settle = 2 if is_rebuild else 10
        time.sleep(settle)

    # ------------------------------------------------------------------
    # Env interface (delegated to sandbox_tool after init)
    # ------------------------------------------------------------------

    def reset(self, seed=None, options=None):
        """Reset the remote environment; returns (obs, info)."""
        import numpy as _np
        import base64 as _b64
        import io as _io
        from PIL import Image as _Img

        response = self.sandbox_tool.reset_env()
        if response.get("status") != 0:
            raise RuntimeError(f"reset_env failed: {response.get('msg')}")
        screenshot_b64 = response.get("screenshot", "")
        if screenshot_b64:
            img_bytes = _b64.b64decode(screenshot_b64)
            img = _Img.open(_io.BytesIO(img_bytes))
            pov = _np.array(img, dtype=_np.uint8)
            if pov.ndim == 3 and pov.shape[2] == 4:
                pov = pov[:, :, :3]
        else:
            pov = _np.zeros((128, 128, 3), dtype=_np.uint8)
        return {"pov": pov}, {}

    def step(self, action: Dict[str, Any]):
        """Execute one action; returns (obs, reward, terminated, truncated, info)."""
        import numpy as _np
        import base64 as _b64
        import io as _io
        from PIL import Image as _Img

        serializable_action: Dict[str, Any] = {}
        for k, v in action.items():
            if k == "camera":
                serializable_action[k] = [float(x) for x in v]
            elif k == "chat" or isinstance(v, str):
                # Preserve string commands like "/gamemode spectator @s"
                serializable_action[k] = v
            elif isinstance(v, (list, tuple)):
                serializable_action[k] = [int(x) for x in v]
            else:
                serializable_action[k] = int(v)

        response = self.sandbox_tool.step(serializable_action)
        if response.get("status") != 0:
            raise RuntimeError(f"step failed: {response.get('msg')}")

        screenshot_b64 = response.get("screenshot", "")
        if screenshot_b64:
            img_bytes = _b64.b64decode(screenshot_b64)
            img = _Img.open(_io.BytesIO(img_bytes))
            pov = _np.array(img, dtype=_np.uint8)
            if pov.ndim == 3 and pov.shape[2] == 4:
                pov = pov[:, :, :3]
        else:
            pov = _np.zeros((128, 128, 3), dtype=_np.uint8)

        reward = float(response.get("reward", 0.0))
        terminated = bool(response.get("done", False))
        raw_info = response.get("info")
        if isinstance(raw_info, dict):
            info = raw_info
        else:
            _proto = {"status", "msg", "screenshot", "reward", "done"}
            info = {k: v for k, v in response.items() if k not in _proto}
        return {"pov": pov}, reward, terminated, False, info

    def close(self) -> None:
        """Stop the sandbox and release resources."""
        if not self._ready:
            return
        try:
            self.sandbox_tool.sandbox_stop()
            print("  [LazySandbox] Sandbox stopped.")
        except Exception as _e:
            print(f"  [LazySandbox] sandbox_stop error: {_e}")
        finally:
            self._ready = False
            self.server_address = None


# ---------------------------------------------------------------------------
# lazy_setup_sandbox – create a SandboxHandle without starting the sandbox
# ---------------------------------------------------------------------------

def lazy_setup_sandbox(
    tmp_dir: str = "/tmp/mcbench_sandbox",
    sandbox_config: Optional[Dict[str, Any]] = None,
) -> SandboxHandle:
    """
    Create a SandboxHandle whose underlying env is a ``LazyMCBenchSandboxEnv``.

    The sandbox is **not** started at this point — only the credentials are
    validated and the ``SandboxClusterTool`` is instantiated.

    The first call to ``execute_commands`` or ``preview_scene_in_sandbox``
    (which both supply ``commands``) will trigger the actual
    ``sandbox_start + create_env`` sequence.

    Args:
        tmp_dir:        Directory for screenshot files.
        sandbox_config: Optional override for sandbox connection credentials.

    Returns:
        SandboxHandle with ``_lazy=True``.
    """
    os.makedirs(tmp_dir, exist_ok=True)
    lazy_env = LazyMCBenchSandboxEnv(sandbox_config=sandbox_config)
    handle: SandboxHandle = {
        "env": lazy_env,
        "default_action": dict(_NOOP_ACTION),
        "last_pov": None,
        "tmp_dir": tmp_dir,
        "spawn_pos": {"x": 0.0, "y": 64.0, "z": 0.0},
        "_lazy": True,
    }
    print("  [LazySandbox] Lazy SandboxHandle created – waiting for first tool call.")
    return handle


_NOOP_ACTION: Dict[str, Any] = {
    "ESC": 0, "attack": 0, "back": 0, "camera": [0, 0],
    "drop": 0, "forward": 0, "hotbar.1": 0, "hotbar.2": 0,
    "hotbar.3": 0, "hotbar.4": 0, "hotbar.5": 0, "hotbar.6": 0,
    "hotbar.7": 0, "hotbar.8": 0, "hotbar.9": 0,
    "inventory": 0, "jump": 0, "left": 0, "pickItem": 0,
    "right": 0, "sneak": 0, "sprint": 0, "swapHands": 0, "use": 0,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _rgb_to_b64png(rgb: np.ndarray) -> str:
    """Convert an RGB numpy array to a base64-encoded PNG string."""
    from PIL import Image as _Image
    img = _Image.fromarray(rgb.astype(np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _save_rgb(rgb: np.ndarray, path: str) -> None:
    """Save RGB numpy array to disk as PNG."""
    try:
        import cv2
        import numpy as _np
        cv2.imwrite(path, cv2.cvtColor(rgb.astype(_np.uint8), cv2.COLOR_RGB2BGR))
    except Exception:
        from PIL import Image as _Image
        _Image.fromarray(rgb.astype(np.uint8)).save(path)


def _step_noop(env, n: int = 1) -> np.ndarray:
    """Execute n noop steps; return last POV frame."""
    pov = None
    for _ in range(n):
        obs, _, _, _, _ = env.step(dict(_NOOP_ACTION))
        pov = obs["pov"]
    return pov


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def setup_sandbox(
    tmp_dir: str = "/tmp/mcbench_sandbox",
    sandbox_config: Optional[Dict[str, Any]] = None,
    local_server_address: Optional[str] = None,
) -> SandboxHandle:
    """
    Start a Minecraft sandbox and return a SandboxHandle.

    Initialization flow (mirrors eval_benchmark.py's MineRLBenchmarkEnv exactly):
      1. MineRLSandboxEnv.__init__ calls sandbox_tool.sandbox_start() to acquire
         a remote sandbox instance.
      2. _init_remote_env() is overridden to call create_env(env='MinecraftSim',
         obs_size=[128,128], render_size=[640,360], seed=0, ..., commands=None)
         — the full parameter set identical to eval_benchmark.py — so the server
         initialises correctly without trying to import the 'minerl' Python package.
      3. Scene commands are applied later via execute_commands(), which calls
         sandbox_tool.create_env(env='MinecraftSim', commands=[...]) to build
         the scene.

    Args:
        tmp_dir:              Directory for saving screenshot files.
        sandbox_config:       Override for sandbox connection (endpoint/token/body).
                              If None, reads FRIDAY_SANDBOX_ENDPOINT /
                              FRIDAY_SANDBOX_TOKEN / FRIDAY_SANDBOX_BODY from
                              environment variables.
        local_server_address: If set, connect directly to a local mc_server HTTP
                              API (e.g. "http://localhost:8000") instead of using
                              the remote pssdk-managed sandbox.  The mc_server
                              must already be running.

    Returns:
        SandboxHandle dict, ready to pass to other tool functions.

    Raises:
        RuntimeError: If the sandbox fails to start or connect.
    """
    os.makedirs(tmp_dir, exist_ok=True)

    # ── Local mode: connect to a pre-started mc_server ────────────────────────
    if local_server_address:
        from env.minerl_local import MineRLLocalEnv
        env = MineRLLocalEnv(
            server_address=local_server_address.rstrip("/"),
        )
        obs, _ = env.reset()
        pov = obs["pov"]
    else:
        # ── Remote sandbox mode (pssdk) ───────────────────────────────────────
        # Subclass MineRLSandboxEnv and override _init_remote_env to use the
        # exact same create_env call as eval_benchmark.py's MineRLBenchmarkEnv.
        # Scene commands are supplied later via execute_commands().
        from env.minerl_sandbox import MineRLSandboxEnv

        class _MCBenchSandboxEnv(MineRLSandboxEnv):
            """
            MineRLSandboxEnv subclass for MCBench scene-generation.

            Overrides _init_remote_env to mirror eval_benchmark.py exactly:
            calls create_env with env='MinecraftSim' and the full parameter set
            so the server initialises correctly.  Scene commands are applied
            later via execute_commands() → create_env(commands=[...]).
            """

            def _init_remote_env(self) -> None:  # type: ignore[override]
                if not self.sandbox_tool:
                    raise RuntimeError("sandbox_tool not initialised.")
                import time as _time
                print("  [SandboxSetup] Sending create_env to server...")
                response = self.sandbox_tool.create_env(
                    env='MinecraftSim',
                    obs_size=[128, 128],
                    render_size=[640, 360],
                    seed=0,
                    record=False,
                    record_path='./output/',
                    yaml_config=None,
                    commands=None,
                    task_text=None,
                    call_timeout=120,
                )
                if response.get("status") != 0:
                    raise RuntimeError(
                        f"create_env failed: {response.get('msg')}"
                    )
                self.task = response.get("task_text", "")
                print("  [SandboxSetup] create_env OK — server ready.")
                _time.sleep(10)  # let the server finish initializing (same as eval_benchmark.py)

        if sandbox_config is not None:
            env = _MCBenchSandboxEnv(
                env_id="MinecraftSim",
                sandbox_config=sandbox_config,
            )
        else:
            # Credentials come from env vars:
            # FRIDAY_SANDBOX_ENDPOINT, FRIDAY_SANDBOX_TOKEN, FRIDAY_SANDBOX_BODY
            env = _MCBenchSandboxEnv(env_id="MinecraftSim")
        obs, _ = env.reset()
        pov = obs["pov"]

    # Run a few noop steps so the world has loaded, then record spawn position.
    spawn_pos = {"x": 0.0, "y": 64.0, "z": 0.0}
    try:
        for _ in range(5):
            obs, _, _, _, _ = env.step(dict(_NOOP_ACTION))
        pov = obs["pov"]
        # MineRL obs may contain location_stats or gps info
        if "location_stats" in obs:
            ls = obs["location_stats"]
            spawn_pos = {
                "x": float(ls.get("xpos", 0.0)),
                "y": float(ls.get("ypos", 64.0)),
                "z": float(ls.get("zpos", 0.0)),
            }
        elif "gps" in obs:
            gps = obs["gps"]
            spawn_pos = {"x": float(gps[0]), "y": float(gps[1]), "z": float(gps[2])}
    except Exception:
        pass

    handle: SandboxHandle = {
        "env": env,
        "default_action": dict(_NOOP_ACTION),
        "last_pov": pov,
        "tmp_dir": tmp_dir,
        "spawn_pos": spawn_pos,  # absolute spawn coordinates for /tp
    }
    return handle


def _parse_body_env() -> Dict[str, Any]:
    body_str = os.getenv("FRIDAY_SANDBOX_BODY", "{}")
    try:
        return json.loads(body_str)
    except Exception:
        return {}


def close_sandbox(handle: SandboxHandle) -> None:
    """Release the sandbox and all resources."""
    try:
        handle["env"].close()
    except Exception:
        pass


def take_screenshot(handle: SandboxHandle, save_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Capture the current first-person view.

    Args:
        handle:    SandboxHandle.
        save_path: Optional file path to save the PNG. If None, uses tmp_dir.

    Returns:
        Dict with:
          "first_person": base64-encoded PNG string of the current frame.
          "saved_paths":  {"first_person": "<path>"}  — where the file was saved.
    """
    # Guard: lazy sandbox must be initialised before taking a screenshot.
    env = handle.get("env")
    if isinstance(env, LazyMCBenchSandboxEnv) and not env._ready:
        return {
            "error": (
                "Sandbox not yet initialised. Call preview_scene_in_sandbox or "
                "execute_minecraft_commands with scene commands first."
            ),
            "first_person": "",
            "saved_paths": {},
        }

    pov = handle.get("last_pov")
    if pov is None:
        # try a noop step to get a fresh frame
        pov = _step_noop(handle["env"], 1)
        handle["last_pov"] = pov

    if save_path is None:
        save_path = os.path.join(handle["tmp_dir"], f"screenshot_{int(time.time()*1000)}.png")

    _save_rgb(pov, save_path)
    b64 = _rgb_to_b64png(pov)
    return {
        "first_person": b64,
        "saved_paths": {"first_person": save_path},
    }


# Mapping: perspective name → (yaw_degrees, description)
# Yaw: 0=south, 90=west, 180=north, 270=east (Minecraft convention)
_PERSPECTIVE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "first_person":  {"type": "first_person",  "description": "Player spawn eye-level"},
    "overhead":      {"type": "overhead",       "description": "Bird's-eye view from above"},
    "inventory":     {"type": "inventory",      "description": "Player inventory view"},
"north":         {"type": "cardinal",       "yaw": 180,  "pitch": 10,  "description": "Agent looks north (eye-level)"},
"south":         {"type": "cardinal",       "yaw": 0,    "pitch": 10,  "description": "Agent looks south (eye-level)"},
"east":          {"type": "cardinal",       "yaw": 270,  "pitch": 10,  "description": "Agent looks east (eye-level)"},
"west":          {"type": "cardinal",       "yaw": 90,   "pitch": 10,  "description": "Agent looks west (eye-level)"},
}


def execute_commands(
    handle: SandboxHandle,
    commands: List[str],
    wait_steps_per_cmd: int = 5,
    settle_steps: int = 3,
    perspectives: Optional[List[str]] = None,
    save_dir: Optional[str] = None,
    task_text: str = "",
) -> Dict[str, Any]:
    """
    Execute a list of Minecraft /commands (e.g. /fill, /setblock, /summon) and
    return screenshots from multiple perspectives.

    Calls create_env(commands=[...]) to rebuild the scene on the server, then
    resets and captures screenshots.  No env_id is forwarded — the server
    renders entirely from the commands list.

    Args:
        handle:              SandboxHandle.
        commands:            List of Minecraft command strings (e.g. "/fill ~0 ~0 ~0 ~5 ~0 ~5 stone").
        wait_steps_per_cmd:  (unused, kept for API compatibility)
        settle_steps:        Noop steps after reset to let the world settle.
        perspectives:        List of perspectives to capture.
                             Supported: "first_person", "overhead", "inventory",
                             "north", "south", "east", "west".
                             Defaults to ["first_person"].
        save_dir:            Optional directory to save PNG files.
        task_text:           Optional task description string forwarded to create_env.

    Returns:
        Dict with keys matching requested perspectives, each containing a
        base64 PNG string. Also includes "saved_paths" mapping perspective→path.
    """
    if perspectives is None:
        perspectives = ["first_person"]

    env = handle["env"]
    save_dir = save_dir or handle["tmp_dir"]
    os.makedirs(save_dir, exist_ok=True)

    # --- Rebuild the scene via create_env(commands=[...]) ---
    # Two cases:
    #  1. Lazy handle (LazyMCBenchSandboxEnv): call initialize() which performs
    #     sandbox_start (first time) + create_env in one step, mirroring
    #     eval_benchmark.py's MineRLBenchmarkEnv._init_remote_env().
    #  2. Pre-started handle (MineRLSandboxEnv): call sandbox_tool.create_env()
    #     directly to rebuild the scene (existing behaviour).
    #
    # IMPORTANT: commands must be a non-empty list.
    # The server interprets commands=None as "use env_id for gym.make()" which
    # requires the 'minerl' package on the server — and our sandbox server does NOT
    # have minerl installed.  Never send an empty/None commands list to the server.
    if not commands:
        raise ValueError(
            "execute_minecraft_commands requires a non-empty 'commands' list. "
            "Provide at least one Minecraft /command (e.g. '/fill ~-5 ~0 ~-5 ~5 ~5 ~5 minecraft:stone'). "
            "Sending commands=None or commands=[] would cause the server to call gym.make() "
            "which fails with 'No module named minerl'."
        )

    print(f"  [SandboxTool] create_env with {len(commands)} commands...")
    try:
        if isinstance(env, LazyMCBenchSandboxEnv):
            # Lazy path: sandbox_start (first call only) + create_env in one step
            env.initialize(commands=commands, task_text=task_text or None)
        else:
            # Pre-started path: mirror eval_benchmark.py's MineRLBenchmarkEnv._init_remote_env exactly
            response = env.sandbox_tool.create_env(
                env='MinecraftSim',
                obs_size=[128, 128],
                render_size=[640, 360],
                seed=0,
                record=False,
                record_path='./output/',
                yaml_config=None,
                commands=commands,
                task_text=task_text or None,
                call_timeout=120,
            )
            if response.get("status") != 0:
                print(f"  [SandboxTool] create_env returned error: {response.get('msg')}")
            else:
                print(f"  [SandboxTool] create_env OK — task={str(response.get('task_text',''))[:60]}")
    except Exception as e:
        print(f"  [SandboxTool] create_env / initialize failed: {e}")
        raise

    # reset_env to get the initial observation (scene is now built)
    try:
        obs, _ = env.reset()
        handle["last_pov"] = obs["pov"]
        print(f"  [SandboxTool] reset_env OK")
    except Exception as e:
        print(f"  [SandboxTool] reset_env failed: {e}")
        raise

    # Let the world settle (noop steps)
    if settle_steps > 0:
        pov = _step_noop(env, settle_steps)
        handle["last_pov"] = pov

    results: Dict[str, Any] = {}
    saved_paths: Dict[str, str] = {}
    ts = int(time.time() * 1000)

    # --- Capture requested perspectives ---
    for persp in perspectives:
        cfg = _PERSPECTIVE_CONFIGS.get(persp)
        if cfg is None:
            print(f"  [SandboxTool] Unknown perspective: {persp}, skipping.")
            continue

        if cfg["type"] == "first_person":
            path = os.path.join(save_dir, f"fp_{ts}.png")
            b64 = _capture_first_person(handle, path)
            results["first_person"] = b64
            saved_paths["first_person"] = path

        elif cfg["type"] == "overhead":
            path = os.path.join(save_dir, f"overhead_{ts}.png")
            b64 = _capture_overhead(handle, path, commands)
            if b64:
                results["overhead"] = b64
                saved_paths["overhead"] = path

        elif cfg["type"] == "inventory":
            path = os.path.join(save_dir, f"inventory_{ts}.png")
            b64 = _capture_inventory(handle, path)
            results["inventory"] = b64
            saved_paths["inventory"] = path

        elif cfg["type"] == "cardinal":
            path = os.path.join(save_dir, f"{persp}_{ts}.png")
            b64 = _capture_cardinal(handle, path, cfg["yaw"], cfg.get("pitch", 10), commands)
            if b64:
                results[persp] = b64
                saved_paths[persp] = path

    results["saved_paths"] = saved_paths
    results["perspectives_requested"] = perspectives
    results["commands_executed"] = len(commands)
    return results


def _look_straight(env, target_pitch: float = 0.0, target_yaw_delta: float = 0.0,
                    steps: int = 20) -> np.ndarray:
    """
    Use camera actions to move the view toward (target_pitch, +target_yaw_delta).
    First resets pitch to 0 by looking up maximally, then adjusts.

    MineRL camera action: [pitch_delta, yaw_delta] in degrees per step.
    Positive pitch_delta = look more down. Positive yaw_delta = turn right.
    Pitch is clamped to [-90, 90].

    Strategy:
      1. Send one large camera=[-180, 0] step to slam pitch to -90 (straight up)
      2. Send one large camera=[90 + target_pitch, target_yaw_delta] to reach target
      3. One settle noop
    Total: 3 HTTP requests regardless of target_pitch.
    """
    obs = None
    # Step 1: slam pitch all the way up with a single large delta (-180 clamps to -90)
    a = dict(_NOOP_ACTION)
    a["camera"] = [-180.0, 0.0]
    obs, _, _, _, _ = env.step(a)
    # Step 2: one large step to reach target pitch from -90
    remaining_pitch = 90.0 + target_pitch   # delta to reach target from -90
    a = dict(_NOOP_ACTION)
    a["camera"] = [remaining_pitch, target_yaw_delta]
    obs, _, _, _, _ = env.step(a)
    # Step 3: one settle noop
    obs, _, _, _, _ = env.step(dict(_NOOP_ACTION))
    return obs["pov"]


def _capture_first_person(handle: SandboxHandle, save_path: str) -> str:
    """Capture first-person view after straightening the camera to pitch=0."""
    env = handle["env"]
    # Straighten camera: look ahead horizontally (pitch 0)
    pov = _look_straight(env, target_pitch=0.0, target_yaw_delta=0.0)
    handle["last_pov"] = pov
    _save_rgb(pov, save_path)
    return _rgb_to_b64png(pov)


def _capture_inventory(handle: SandboxHandle, save_path: str) -> str:
    """Open inventory, capture, close."""
    env = handle["env"]
    # Open inventory
    action = dict(_NOOP_ACTION)
    action["inventory"] = 1
    obs, _, _, _, _ = env.step(action)
    pov = obs["pov"]
    # Close inventory
    _step_noop(env, 2)
    _save_rgb(pov, save_path)
    handle["last_pov"] = pov
    return _rgb_to_b64png(pov)


def _capture_overhead(
    handle: SandboxHandle,
    save_path: str,
    commands: Optional[List[str]] = None,
) -> Optional[str]:
    """Teleport to spectator overhead view, capture, return to survival."""
    env = handle["env"]
    spawn = handle.get("spawn_pos", {"x": 0.0, "y": 64.0, "z": 0.0})

    # Estimate scene bbox from commands for positioning
    cam_y = spawn["y"] + 40
    cam_x = spawn["x"]
    cam_z = spawn["z"]

    if commands:
        try:
            from .utils import _estimate_scene_bbox
            min_x, max_x, min_y, max_y, min_z, max_z = _estimate_scene_bbox(commands)
            # scene commands use relative coords (~), add spawn offset
            cx = spawn["x"] + (min_x + max_x) / 2.0
            cz = spawn["z"] + (min_z + max_z) / 2.0
            span = max(max_x - min_x, max_z - min_z)
            cam_y = spawn["y"] + max_y + max(15.0, min(60.0, span * 0.8))
            cam_x = cx
            cam_z = cz
        except Exception:
            pass

    try:
        # Switch to spectator
        sp_action = dict(_NOOP_ACTION)
        sp_action["chat"] = "/gamemode spectator @s"
        env.step(sp_action)
        _step_noop(env, 1)

        # Teleport to overhead position using absolute coords + pitch 90 (straight down)
        tp_action = dict(_NOOP_ACTION)
        tp_action["chat"] = f"/tp @s {cam_x:.1f} {cam_y:.1f} {cam_z:.1f} 0 90"
        env.step(tp_action)
        _step_noop(env, 1)

        # Force camera to look straight down using camera actions
        # (in case /tp yaw/pitch args were ignored by the server)
        pov = _look_straight(env, target_pitch=90.0, target_yaw_delta=0.0)
        handle["last_pov"] = pov
        _save_rgb(pov, save_path)
        b64 = _rgb_to_b64png(pov)

        # Return to survival
        surv_action = dict(_NOOP_ACTION)
        surv_action["chat"] = "/gamemode survival @s"
        env.step(surv_action)
        _step_noop(env, 1)
        return b64

    except Exception as e:
        print(f"  [SandboxTool] overhead capture failed: {e}")
        return None


def _capture_cardinal(
    handle: SandboxHandle,
    save_path: str,
    yaw: float,
    pitch: float = 10.0,
    commands: Optional[List[str]] = None,
) -> Optional[str]:
    """
    Capture the scene from the agent's current spawn position looking in the
    given cardinal direction (yaw).  No teleport away, no spectator mode —
    the agent stays in place and just turns to face the requested direction.

    Args:
        handle:    SandboxHandle.
        save_path: Where to save the PNG.
        yaw:       Target camera yaw in degrees (Minecraft: 0=south, 90=west,
                   180=north, 270=east). This is the FACING direction.
        pitch:     Camera pitch in degrees (positive = looking slightly down,
                   0 = horizontal). Default 10° gives a natural eye-level look.
        commands:  Unused (kept for API compatibility).

    Returns:
        Base64 PNG string, or None on failure.
    """
    env = handle["env"]
    try:
        # Rotate in-place: keep current XYZ with ~ ~ ~, only set yaw+pitch.
        tp_action = dict(_NOOP_ACTION)
        tp_action["chat"] = f"/tp @s ~ ~ ~ {yaw:.1f} {pitch:.1f}"
        env.step(tp_action)
        _step_noop(env, 1)

        # Force exact camera orientation via camera actions (reliable even if
        # /tp yaw/pitch args are ignored by the server build).
        pov = _look_straight(env, target_pitch=pitch, target_yaw_delta=0.0)
        handle["last_pov"] = pov
        _save_rgb(pov, save_path)
        return _rgb_to_b64png(pov)

    except Exception as e:
        print(f"  [SandboxTool] cardinal ({yaw}°) capture failed: {e}")
        return None


def execute_agent_action(
    handle: SandboxHandle,
    action: Dict[str, Any],
    repeat: int = 1,
    save_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute one agent action (MinerRL action dict) for `repeat` steps.

    This allows agents like SceneDesigner or Validator to directly control
    the Minecraft player and observe results (e.g. navigate to inspect a spot).

    Args:
        handle:   SandboxHandle.
        action:   MinerRL action dict (keys: forward, attack, camera, chat, …).
        repeat:   Number of simulation steps to repeat the action.
        save_dir: Directory to save per-step screenshots. None = tmp_dir.

    Returns:
        Dict with:
          "frames_b64": list of base64 PNG per step,
          "saved_paths": list of file paths,
          "last_frame_b64": final frame as base64 PNG.
    """
    env = handle["env"]
    save_dir = save_dir or handle["tmp_dir"]
    os.makedirs(save_dir, exist_ok=True)

    frames_b64: List[str] = []
    saved_paths: List[str] = []
    ts = int(time.time() * 1000)

    for i in range(max(1, repeat)):
        try:
            obs, _, _, _, _ = env.step(action)
            pov = obs["pov"]
            handle["last_pov"] = pov
            path = os.path.join(save_dir, f"action_{ts}_{i:03d}.png")
            _save_rgb(pov, path)
            frames_b64.append(_rgb_to_b64png(pov))
            saved_paths.append(path)
        except Exception as e:
            print(f"  [SandboxTool] action step {i} failed: {e}")
            break

    last_b64 = frames_b64[-1] if frames_b64 else ""
    return {
        "frames_b64": frames_b64,
        "saved_paths": saved_paths,
        "last_frame_b64": last_b64,
    }


def run_agent_episode(
    handle: SandboxHandle,
    task_text: str,
    provider_config: Dict[str, Any],
    max_steps: int = 10,
    save_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run a DefaultAgent (lumine-client) for up to max_steps steps in the sandbox.

    Allows Validator / MilestoneAgent to verify that a task is actually achievable
    by observing an AI agent attempting it.

    Args:
        handle:          SandboxHandle.
        task_text:       Task description for the agent.
        provider_config: Dict with keys: base_url, api_key, model.
        max_steps:       Max agent decision steps.
        save_dir:        Directory to save frames.

    Returns:
        Dict with:
          "steps": list of {thought, action_text, frame_b64, step_idx},
          "final_frame_b64": last frame,
          "total_steps": int.
    """
    from playground.components.action_space.minerl import MinerRLActionSpace
    from playground.components.context.default import DefaultContextBuilder
    from playground.components.provider.openai_provider import OpenAIProvider
    from playground.agent.default import DefaultAgent

    save_dir = save_dir or handle["tmp_dir"]
    os.makedirs(save_dir, exist_ok=True)

    model = provider_config.get("model") or os.getenv("AGENT_MODEL")
    if not model:
        raise ValueError("[run_agent_episode] Model name is required. Pass it via provider_config['model'] or set AGENT_MODEL env var.")
    # Strip provider prefix (openai/, litellm/, azure/) — OpenAI client doesn't need it
    for _pfx in ("openai/", "litellm/", "azure/"):
        if model.startswith(_pfx):
            model = model[len(_pfx):]
            break
    provider = OpenAIProvider(
        api_key=provider_config.get("api_key", os.getenv("AGENT_API_KEY", "")),
        api_base=provider_config.get("base_url", os.getenv("AGENT_API_BASE", "")),
        default_model=model,
    )

    action_space = MinerRLActionSpace()
    agent = DefaultAgent(
        action_space=action_space,
        provider=provider,
        context_builder_class=DefaultContextBuilder,
        model=model,
    )
    agent.load_system_prompt(task_text)

    env = handle["env"]
    thought_history: List[str] = []
    action_history: List[Dict[str, Any]] = []
    steps_log: List[Dict[str, Any]] = []

    pov = handle.get("last_pov")
    if pov is None:
        pov = _step_noop(env, 1)
        handle["last_pov"] = pov

    from collections import deque
    frame_buffer: deque = deque(maxlen=3)
    frame_buffer.append(pov)

    ts = int(time.time() * 1000)

    for step_idx in range(max_steps):
        frames = list(frame_buffer)
        while len(frames) < 3:
            frames.insert(0, np.array(frames[0], copy=True))

        thought, action = agent.get_action(
            frame_buffer=frames,
            thought_history=thought_history,
            action_history=action_history,
            current_step=step_idx + 1,
            return_messages=False,
        )
        if action is None:
            break

        action_text = json.dumps(
            {k: v for k, v in action.items() if v != 0 and k != "camera"} |
            ({"camera": action["camera"]} if action.get("camera", [0, 0]) != [0, 0] else {}),
            ensure_ascii=False,
        )

        obs, _, term, trunc, _ = env.step(action)
        pov = obs["pov"]
        handle["last_pov"] = pov
        frame_buffer.append(pov)

        path = os.path.join(save_dir, f"agent_{ts}_step{step_idx:03d}.png")
        _save_rgb(pov, path)
        b64 = _rgb_to_b64png(pov)

        steps_log.append({
            "step_idx": step_idx,
            "thought": thought,
            "action_text": action_text,
            "frame_b64": b64,
            "saved_path": path,
        })

        thought_history.append(thought)
        action_history.append(action)

        if term or trunc:
            break

    final_b64 = steps_log[-1]["frame_b64"] if steps_log else ""
    return {
        "steps": steps_log,
        "final_frame_b64": final_b64,
        "total_steps": len(steps_log),
    }


# ---------------------------------------------------------------------------
# Convenience: build autogen-compatible tool function signatures
# ---------------------------------------------------------------------------

def make_execute_commands_tool(handle: SandboxHandle, default_log_dir: Optional[str] = None):
    """
    Return a closure that AutoGen can call as a tool.

    Args:
        handle:          SandboxHandle.
        default_log_dir: If set, screenshots are saved to
                         ``<default_log_dir>/logs/execute_commands_<ts>/``
                         when the caller does not supply a save_dir.

    Usage (in agent tool_calls):
        result = execute_commands_tool(
            commands=["/fill ~-5 ~0 ~-5 ~5 ~5 ~5 minecraft:oak_log"],
            perspectives=["first_person", "overhead"],
        )
    """
    def execute_commands_tool(
        commands: List[str],
        perspectives: List[str] = None,
        wait_steps_per_cmd: int = 5,
        settle_steps: int = 3,
        save_dir: str = None,
    ) -> Dict[str, Any]:
        """Execute Minecraft commands and capture screenshots."""
        resolved_save_dir = save_dir
        if resolved_save_dir is None and default_log_dir:
            resolved_save_dir = os.path.join(
                default_log_dir,
                f"execute_commands_{int(time.time()*1000)}"
            )
            os.makedirs(resolved_save_dir, exist_ok=True)
        return execute_commands(
            handle=handle,
            commands=commands,
            wait_steps_per_cmd=wait_steps_per_cmd,
            settle_steps=settle_steps,
            perspectives=perspectives or ["first_person"],
            save_dir=resolved_save_dir,
        )
    return execute_commands_tool


def make_agent_action_tool(handle: SandboxHandle, default_log_dir: Optional[str] = None):
    """
    Return a closure for single-action execution.

    Args:
        handle:          SandboxHandle.
        default_log_dir: If set, per-step screenshots are saved to
                         ``<default_log_dir>/logs/agent_action_<ts>/``
                         when the caller does not supply a save_dir.
    """
    def agent_action_tool(
        action: Dict[str, Any],
        repeat: int = 1,
        save_dir: str = None,
    ) -> Dict[str, Any]:
        """Execute a MinerRL agent action and return screenshots."""
        resolved_save_dir = save_dir
        if resolved_save_dir is None and default_log_dir:
            resolved_save_dir = os.path.join(
                default_log_dir,
                f"agent_action_{int(time.time()*1000)}"
            )
            os.makedirs(resolved_save_dir, exist_ok=True)
        return execute_agent_action(handle, action, repeat=repeat, save_dir=resolved_save_dir)
    return agent_action_tool


def make_screenshot_tool(handle: SandboxHandle, default_log_dir: Optional[str] = None):
    """
    Return a closure for taking screenshots.

    Args:
        handle:          SandboxHandle.
        default_log_dir: If set, screenshots are saved to
                         ``<default_log_dir>/logs/`` when save_path is not supplied.
    """
    def screenshot_tool(save_path: str = None) -> Dict[str, Any]:
        """
        Take a screenshot of the current Minecraft view.

        Returns:
            Dict with:
              "first_person": base64 PNG string of the current view.
              "saved_paths":  {"first_person": "<path>"}
        """
        resolved_save_path = save_path
        if resolved_save_path is None and default_log_dir:
            os.makedirs(default_log_dir, exist_ok=True)
            resolved_save_path = os.path.join(
                default_log_dir, f"screenshot_{int(time.time()*1000)}.png"
            )
        return take_screenshot(handle, save_path=resolved_save_path)
    return screenshot_tool


def make_run_agent_tool(
    handle: SandboxHandle,
    default_log_dir: Optional[str] = None,
    agent_model: Optional[str] = None,
):
    """
    Return a closure for running an AI agent episode.

    Args:
        handle:          SandboxHandle.
        default_log_dir: If set, per-step agent frames are saved to
                         ``<default_log_dir>/logs/run_agent_<ts>/``
                         when the caller does not supply a save_dir.
agent_model:     Default LLM model name (provider prefix will be stripped
before passing to the OpenAI client).  Falls back to
AGENT_MODEL env var (required — no built-in default).
    """
    def run_agent_tool(
        task_text: str,
        max_steps: int = 10,
        model: str = None,
        save_dir: str = None,
    ) -> Dict[str, Any]:
        """Run an AI agent for max_steps, observe its behaviour and return frames."""
        resolved_save_dir = save_dir
        if resolved_save_dir is None and default_log_dir:
            resolved_save_dir = os.path.join(
                default_log_dir,
                f"run_agent_{int(time.time()*1000)}"
            )
            os.makedirs(resolved_save_dir, exist_ok=True)
        _raw_model = model or agent_model or os.getenv("AGENT_MODEL")
        if not _raw_model:
            raise ValueError("[run_agent_tool] Model name is required. Pass it via the 'model' arg, agent_model factory param, or set AGENT_MODEL env var.")
        # Strip provider prefix (openai/, litellm/, azure/) — OpenAI client doesn't need it
        for _pfx in ("openai/", "litellm/", "azure/"):
            if _raw_model.startswith(_pfx):
                _raw_model = _raw_model[len(_pfx):]
                break
        cfg = {
            "api_key": os.getenv("AGENT_API_KEY", ""),
            "base_url": os.getenv("AGENT_API_BASE", ""),
            "model": _raw_model,
        }
        return run_agent_episode(handle, task_text, cfg, max_steps=max_steps, save_dir=resolved_save_dir)
    return run_agent_tool


# ---------------------------------------------------------------------------
# Preview Scene in Sandbox
# ---------------------------------------------------------------------------

_PREVIEW_MAX_STEPS = 20  # hard cap for scene-designer free-roam exploration


def preview_scene_in_sandbox(
    handle: SandboxHandle,
    commands: List[str],
    explore_prompt: Optional[str] = None,
    max_walk_steps: int = _PREVIEW_MAX_STEPS,
    loading_steps: int = 20,
    save_dir: Optional[str] = None,
    agent_model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a Minecraft scene and explore it with an AI agent — identical logic to
    eval_benchmark.py's ``_run_benchmark``.

    Execution flow (mirrors eval_benchmark.py exactly):
      1. **Build**: call create_env(commands=[...]) to rebuild the scene on the server.
      2. **Reset**: env.reset() → get the first observation frame.
      3. **Settle**: run ``loading_steps`` noop steps (same as eval_benchmark.py's
         ``loading_command_steps``) to let init commands fully apply.
         The final noop frame is saved as the **initial screenshot**.
      4. **Explore**: run the DefaultAgent for up to ``max_walk_steps`` steps.
         Each step: agent.get_action(frame_buffer, thought_history, action_history,
         current_step) → env.step(action) → append frame.
         This is identical to eval_benchmark.py's main agent loop.

    No extra spectator-camera screenshots, no teleports, no overhead views.
    The agent sees only what a real player would see, and autonomously decides
    where to walk and look.

    Args:
        handle:         SandboxHandle (lazy or pre-started).
        commands:       Minecraft /commands to build the scene (/fill, /setblock, etc.).
        explore_prompt: Task description for the exploration agent.
                        Defaults to a generic scene-observation prompt.
        max_walk_steps: Hard cap on total agent exploration steps (default 20).
        loading_steps:  Noop steps after reset to let commands settle (default 20,
                        same as eval_benchmark.py's --loading-command-steps).
save_dir:       Directory to save all PNG frames.
agent_model:    LLM model name (e.g. "openai/gpt-5.1"). Falls back to
AGENT_MODEL env var (required — no built-in default).

    Returns:
        Dict with:
          "initial_frame":    {"b64": str, "path": str} — frame after settle
          "explore_frames":   list of {"step": int, "b64": str, "path": str,
                                        "thought": str, "action_text": str}
          "all_frames":       unified list of {"phase": "initial"|"explore",
                                               "label": str, "b64": str, "path": str}
          "total_steps":      int — actual number of exploration steps executed
          "saved_dir":        str
          "commands_executed": int
    """
    from collections import deque

    save_dir = save_dir or handle["tmp_dir"]
    ts = int(time.time() * 1000)
    preview_dir = os.path.join(save_dir, f"preview_{ts}")
    os.makedirs(preview_dir, exist_ok=True)

    env = handle["env"]

    # ── Step 1: Build scene via create_env ───────────────────────────────────
    print(f"  [Preview] Building scene: {len(commands)} commands...")
    try:
        if isinstance(env, LazyMCBenchSandboxEnv):
            env.initialize(commands=commands if commands else None, task_text=None)
        else:
            response = env.sandbox_tool.create_env(
                env='MinecraftSim',
                obs_size=[128, 128],
                render_size=[640, 360],
                seed=0,
                record=False,
                record_path='./output/',
                yaml_config=None,
                commands=commands if commands else None,
                task_text=None,
                call_timeout=120,
            )
            if response.get("status") != 0:
                print(f"  [Preview] create_env error: {response.get('msg')}")
            else:
                print(f"  [Preview] create_env OK")
    except Exception as e:
        print(f"  [Preview] create_env failed: {e}")

    # ── Step 2: Reset env ────────────────────────────────────────────────────
    try:
        obs, _ = env.reset()
        pov = obs["pov"]
        handle["last_pov"] = pov
        print(f"  [Preview] reset OK")
    except Exception as e:
        print(f"  [Preview] reset failed: {e}")
        pov = handle.get("last_pov")

    # ── Step 3: Settle (loading_steps noops, same as eval_benchmark.py) ──────
    # eval_benchmark.py uses agent.get_default_action(is_call_failed=False) which returns
    # a plain NOOP action — identical to _NOOP_ACTION defined at the top of this file.
    print(f"  [Preview] Settling: {loading_steps} noop steps...")
    for _s in range(loading_steps):
        try:
            obs, _, _, _, _ = env.step(dict(_NOOP_ACTION))
            pov = obs["pov"]
            handle["last_pov"] = pov
        except Exception:
            break
    print(f"  [Preview] Settle done. Saving initial frame...")

    # Save the post-settle frame as the initial screenshot
    initial_path = os.path.join(preview_dir, "initial.png")
    _save_rgb(pov, initial_path)
    initial_b64 = _rgb_to_b64png(pov)
    initial_frame = {"b64": initial_b64, "path": initial_path}

    all_frames: List[Dict[str, Any]] = [{
        "phase": "initial",
        "label": "initial",
        "b64": initial_b64,
        "path": initial_path,
    }]

    # ── Step 4: AI agent exploration (same loop as eval_benchmark.py) ────────
    explore_frames: List[Dict[str, Any]] = []
    total_steps = 0

    _observe_prompt = explore_prompt or (
        "You are an AI agent exploring a freshly-built Minecraft scene. "
        "Your goal is OBSERVATION, not task completion. "
        "Walk around, look at different areas, and take note of the spatial layout, "
        "block placement, structures, and any issues with the scene design."
    )

    print(f"  [Preview] Starting agent exploration "
          f"(max {max_walk_steps} steps)...")

    try:
        # ── Fix module conflicts before importing DefaultAgent ──────────────
        _stale_keys = [k for k in sys.modules if k == "utils" or k.startswith("utils.")]
        for _k in _stale_keys:
            _mod = sys.modules.get(_k)
            if _mod is not None and not hasattr(_mod, "convert"):
                del sys.modules[_k]
        _playground_keys = [
            k for k in sys.modules
            if k == "playground.agent.default"
            or k.startswith("playground.agent.")
            or k.startswith("components.")
        ]
        for _k in _playground_keys:
            if _k in sys.modules:
                del sys.modules[_k]

        _playground_dir = str(LUMINE_CLIENT_DIR / "playground")
        if _playground_dir not in sys.path:
            sys.path.insert(0, _playground_dir)

        from playground.agent.default import DefaultAgent
        from playground.components.action_space.minerl import MinerRLActionSpace
        from playground.components.context.default import DefaultContextBuilder
        from playground.components.provider.openai_provider import OpenAIProvider

        _api_key  = os.getenv("AGENT_API_KEY", "")
        _api_base = os.getenv("AGENT_API_BASE", "")
        _model = agent_model or os.getenv("AGENT_MODEL")
        if not _model:
            raise ValueError("[preview_scene_in_sandbox] Model name is required. Pass agent_model or set AGENT_MODEL env var.")
        # Strip provider prefix (openai/, litellm/, azure/) — OpenAI client doesn't need it
        for _pfx in ("openai/", "litellm/", "azure/"):
            if _model.startswith(_pfx):
                _model = _model[len(_pfx):]
                break

        provider = OpenAIProvider(_api_key, _api_base, _model)
        agent = DefaultAgent(
            action_space=MinerRLActionSpace(),
            provider=provider,
            context_builder_class=DefaultContextBuilder,
            model=_model,
        )
        agent.load_system_prompt(_observe_prompt)

        # Frame buffer (maxlen=3, same as eval_benchmark.py FRAME_BUFFER_SIZE=3)
        frame_buffer: deque = deque(maxlen=3)
        frame_buffer.append(pov)
        thought_history: List[str] = []
        action_history:  List[Dict[str, Any]] = []

        # ── Main agent loop — identical to eval_benchmark.py _run_benchmark ──
        for step_idx in range(max_walk_steps):
            print(f"  [Preview] --- Step {step_idx + 1}/{max_walk_steps} ---")

            frames = list(frame_buffer)
            # Pad to 3 frames if buffer not yet full (same as eval_benchmark.py)
            while len(frames) < 3:
                frames.insert(0, np.array(frames[0], copy=True))

            try:
                thought, action = agent.get_action(
                    frame_buffer=frames,
                    thought_history=thought_history,
                    action_history=action_history,
                    current_step=step_idx + 1,
                    return_messages=False,
                )
            except Exception as agent_err:
                print(f"  [Preview] get_action failed at step {step_idx + 1}: {agent_err}")
                break

            if action is None:
                print(f"  [Preview] Agent returned None at step {step_idx + 1}, stopping.")
                break

            action_text = json.dumps(
                {k: v for k, v in action.items() if v != 0 and k != "camera"}
                | ({"camera": action["camera"]} if action.get("camera", [0, 0]) != [0, 0] else {}),
                ensure_ascii=False,
            )
            print(f"  [Preview] Step {step_idx + 1}  thought='{(thought or '')[:60]}'  action={action_text}")

            try:
                obs, _, term, trunc, _ = env.step(action)
                pov = obs["pov"]
                handle["last_pov"] = pov
                frame_buffer.append(pov)
            except Exception as step_err:
                print(f"  [Preview] env.step failed at step {step_idx + 1}: {step_err}")
                break

            frame_path = os.path.join(preview_dir, f"step_{total_steps:03d}.png")
            _save_rgb(pov, frame_path)
            b64 = _rgb_to_b64png(pov)

            frame_entry = {
                "step": total_steps,
                "b64": b64,
                "path": frame_path,
                "thought": thought or "",
                "action_text": action_text,
            }
            explore_frames.append(frame_entry)
            all_frames.append({
                "phase": "explore",
                "label": f"step_{total_steps:03d}",
                "b64": b64,
                "path": frame_path,
            })
            total_steps += 1

            thought_history.append(thought)
            action_history.append(action)

            if term or trunc:
                print(f"  [Preview] Episode ended at step {total_steps}.")
                break

    except ImportError as ie:
        print(f"  [Preview] Cannot import DefaultAgent: {ie}. Skipping exploration.")
    except Exception as e:
        print(f"  [Preview] Agent exploration failed: {e}")

    print(f"  [Preview] Done: {total_steps} exploration steps, "
          f"{len(all_frames)} total frames saved.")

    return {
        "initial_frame":     initial_frame,
        "explore_frames":    explore_frames,
        "all_frames":        all_frames,
        "total_steps":       total_steps,
        "saved_dir":         preview_dir,
        "commands_executed": len(commands),
    }


def make_preview_scene_tool(
    handle: SandboxHandle,
    default_log_dir: Optional[str] = None,
    agent_model: Optional[str] = None,
):
    """
    Return an AutoGen-compatible closure for ``preview_scene_in_sandbox``.

    Mirrors eval_benchmark.py exactly:
      1. Build scene via create_env(commands=[...]).
      2. reset() → loading_steps noops → save one initial frame.
      3. DefaultAgent explores for up to max_walk_steps steps autonomously.

    Args:
        handle:          SandboxHandle.
default_log_dir: Base directory for saving preview files.
agent_model:     LLM model name (e.g. "openai/gpt-5.1"). Falls back to
AGENT_MODEL env var (required — no built-in default).

    Returns:
        A callable that AutoGen can register as a tool function.
    """
    def preview_scene_tool(
        commands: List[str],
        explore_prompt: str = None,
        max_walk_steps: int = _PREVIEW_MAX_STEPS,
        loading_steps: int = 20,
        save_dir: str = None,
    ) -> Dict[str, Any]:
        """
        Build the Minecraft scene and explore it with an AI agent.

        Identical to eval_benchmark.py's _run_benchmark loop:
          - create_env(commands) → reset() → loading_steps noops → save initial frame
          - Agent loop: get_action(frame_buffer, thoughts, actions) → env.step → save frame

        Args:
            commands:       List of Minecraft /commands to build the scene.
            explore_prompt: Task description for the exploration agent.
                            Defaults to a generic scene-observation prompt.
            max_walk_steps: Hard cap on total agent steps (default 20).
            loading_steps:  Noop steps after reset to let commands settle (default 20).
            save_dir:       Optional override for save directory.

        Returns:
            Dict with initial_frame, explore_frames, all_frames,
            total_steps, saved_dir, commands_executed.
        """
        resolved_save_dir = save_dir
        if resolved_save_dir is None and default_log_dir:
            resolved_save_dir = os.path.join(
                default_log_dir,
                f"preview_scene_{int(time.time()*1000)}"
            )
            os.makedirs(resolved_save_dir, exist_ok=True)
        elif resolved_save_dir is None:
            resolved_save_dir = handle["tmp_dir"]

        return preview_scene_in_sandbox(
            handle=handle,
            commands=commands,
            explore_prompt=explore_prompt,
            max_walk_steps=min(max_walk_steps, _PREVIEW_MAX_STEPS),
            loading_steps=loading_steps,
            save_dir=resolved_save_dir,
            agent_model=agent_model,
        )

    return preview_scene_tool
