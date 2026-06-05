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

BENCHMARK_GEN_DIR = Path(__file__).resolve().parent
LUMINE_CLIENT_DIR = BENCHMARK_GEN_DIR.parent

if str(LUMINE_CLIENT_DIR) not in sys.path:
    sys.path.insert(0, str(LUMINE_CLIENT_DIR))


SandboxHandle = Dict[str, Any]
"""Keys: env, default_action, last_pov, tmp_dir, spawn_pos, _lazy"""


class LazyMCBenchSandboxEnv:
    """HTTP sandbox proxy that mirrors the MineRLSandboxEnv interface.
    Server address is read from MC_SANDBOX_URL; no request is sent until initialize() is called.
    """

    def __init__(
        self,
        sandbox_config: Optional[Dict[str, Any]] = None,
        env_id: str = "MinecraftSim",
        use_friday: bool = False,
    ) -> None:
        self.env_id = env_id
        self._ready = False
        self.task: str = ""

        from benchmark_gen.sandbox_client import SandboxClusterTool as _SCT

        cfg = sandbox_config or {}
        endpoint = cfg.get("endpoint") or None
        self.sandbox_tool = _SCT(endpoint=endpoint, use_friday=use_friday)
        self.server_address: Optional[str] = getattr(self.sandbox_tool, "server_address", None)
        mode = "Friday" if use_friday else "Docker"
        print(f"  [LazySandbox] HTTP sandbox client created – mode: {mode}, server: {self.server_address}")

    def initialize(
        self,
        commands: Optional[List[str]] = None,
        task_text: Optional[str] = None,
    ) -> None:
        """Call create_env to initialize (or rebuild) the scene."""
        is_rebuild = self._ready
        self._create_env(commands=commands, task_text=task_text, is_rebuild=is_rebuild)
        self._ready = True

    def _create_env(
        self,
        commands: Optional[List[str]] = None,
        task_text: Optional[str] = None,
        is_rebuild: bool = False,
    ) -> None:
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
        time.sleep(2 if is_rebuild else 10)

    def reset(self, seed=None, options=None):
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
        import numpy as _np
        import base64 as _b64
        import io as _io
        from PIL import Image as _Img

        serializable_action: Dict[str, Any] = {}
        for k, v in action.items():
            if k == "camera":
                serializable_action[k] = [float(x) for x in v]
            elif k == "chat" or isinstance(v, str):
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
        if not self._ready:
            return
        try:
            self.sandbox_tool.close_env()
            print("  [LazySandbox] close_env OK.")
        except Exception as _e:
            print(f"  [LazySandbox] close_env error: {_e}")
        finally:
            self._ready = False


def lazy_setup_sandbox(
    tmp_dir: str = "/tmp/mcbench_sandbox",
    sandbox_config: Optional[Dict[str, Any]] = None,
    use_friday: bool = False,
) -> SandboxHandle:
    """Create a SandboxHandle with lazy initialization (create_env on first use)."""
    os.makedirs(tmp_dir, exist_ok=True)
    lazy_env = LazyMCBenchSandboxEnv(sandbox_config=sandbox_config, use_friday=use_friday)
    handle: SandboxHandle = {
        "env": lazy_env,
        "default_action": dict(_NOOP_ACTION),
        "last_pov": None,
        "tmp_dir": tmp_dir,
        "spawn_pos": {"x": 0.0, "y": 64.0, "z": 0.0},
        "_lazy": True,
    }
    print("  [LazySandbox] SandboxHandle created – will call create_env on first tool use.")
    return handle


_NOOP_ACTION: Dict[str, Any] = {
    "ESC": 0, "attack": 0, "back": 0, "camera": [0, 0],
    "drop": 0, "forward": 0, "hotbar.1": 0, "hotbar.2": 0,
    "hotbar.3": 0, "hotbar.4": 0, "hotbar.5": 0, "hotbar.6": 0,
    "hotbar.7": 0, "hotbar.8": 0, "hotbar.9": 0,
    "inventory": 0, "jump": 0, "left": 0, "pickItem": 0,
    "right": 0, "sneak": 0, "sprint": 0, "swapHands": 0, "use": 0,
}


def _rgb_to_b64png(rgb: np.ndarray) -> str:
    from PIL import Image as _Image
    img = _Image.fromarray(rgb.astype(np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _save_rgb(rgb: np.ndarray, path: str) -> None:
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


def close_sandbox(handle: SandboxHandle) -> None:
    """Release the sandbox and all resources."""
    try:
        handle["env"].close()
    except Exception:
        pass


def take_screenshot(handle: SandboxHandle, save_path: Optional[str] = None) -> Dict[str, Any]:
    """Capture the current first-person view and return base64 PNG."""
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


# Yaw: 0=south, 90=west, 180=north, 270=east (Minecraft convention)
_PERSPECTIVE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "first_person":  {"type": "first_person",  "description": "Player spawn eye-level"},
    "overhead":      {"type": "overhead",       "description": "Bird's-eye view from above"},
    "inventory":     {"type": "inventory",      "description": "Player inventory view"},
    "north":         {"type": "cardinal",       "yaw": 180,  "pitch": 10,  "description": "Agent looks north"},
    "south":         {"type": "cardinal",       "yaw": 0,    "pitch": 10,  "description": "Agent looks south"},
    "east":          {"type": "cardinal",       "yaw": 270,  "pitch": 10,  "description": "Agent looks east"},
    "west":          {"type": "cardinal",       "yaw": 90,   "pitch": 10,  "description": "Agent looks west"},
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
    """Execute Minecraft /commands, rebuild the scene, and return screenshots.

    Args:
        handle:           SandboxHandle.
        commands:         Non-empty list of Minecraft command strings.
        settle_steps:     Noop steps after reset to let the world settle.
        perspectives:     Perspectives to capture (default: ["first_person"]).
        save_dir:         Optional directory to save PNG files.
        task_text:        Task description forwarded to create_env.
    """
    if perspectives is None:
        perspectives = ["first_person"]

    env = handle["env"]
    save_dir = save_dir or handle["tmp_dir"]
    os.makedirs(save_dir, exist_ok=True)

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
            env.initialize(commands=commands, task_text=task_text or None)
        else:
            response = env.create_env(
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

    try:
        obs, _ = env.reset()
        handle["last_pov"] = obs["pov"]
        print(f"  [SandboxTool] reset_env OK")
    except Exception as e:
        print(f"  [SandboxTool] reset_env failed: {e}")
        raise

    if settle_steps > 0:
        pov = _step_noop(env, settle_steps)
        handle["last_pov"] = pov

    results: Dict[str, Any] = {}
    saved_paths: Dict[str, str] = {}
    ts = int(time.time() * 1000)

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
    """Snap camera to (target_pitch, +target_yaw_delta) in 3 HTTP requests."""
    a = dict(_NOOP_ACTION)
    a["camera"] = [-180.0, 0.0]
    env.step(a)
    remaining_pitch = 90.0 + target_pitch
    a = dict(_NOOP_ACTION)
    a["camera"] = [remaining_pitch, target_yaw_delta]
    env.step(a)
    obs, _, _, _, _ = env.step(dict(_NOOP_ACTION))
    return obs["pov"]


def _capture_first_person(handle: SandboxHandle, save_path: str) -> str:
    env = handle["env"]
    pov = _look_straight(env, target_pitch=0.0, target_yaw_delta=0.0)
    handle["last_pov"] = pov
    _save_rgb(pov, save_path)
    return _rgb_to_b64png(pov)


def _capture_inventory(handle: SandboxHandle, save_path: str) -> str:
    """Open inventory, capture, close."""
    env = handle["env"]
    action = dict(_NOOP_ACTION)
    action["inventory"] = 1
    obs, _, _, _, _ = env.step(action)
    pov = obs["pov"]
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

    cam_y = spawn["y"] + 40
    cam_x = spawn["x"]
    cam_z = spawn["z"]

    if commands:
        try:
            from benchmark_gen.utils import _estimate_scene_bbox
            min_x, max_x, min_y, max_y, min_z, max_z = _estimate_scene_bbox(commands)
            cx = spawn["x"] + (min_x + max_x) / 2.0
            cz = spawn["z"] + (min_z + max_z) / 2.0
            span = max(max_x - min_x, max_z - min_z)
            cam_y = spawn["y"] + max_y + max(15.0, min(60.0, span * 0.8))
            cam_x = cx
            cam_z = cz
        except Exception:
            pass

    try:
        sp_action = dict(_NOOP_ACTION)
        sp_action["chat"] = "/gamemode spectator @s"
        env.step(sp_action)
        _step_noop(env, 1)

        tp_action = dict(_NOOP_ACTION)
        tp_action["chat"] = f"/tp @s {cam_x:.1f} {cam_y:.1f} {cam_z:.1f} 0 90"
        env.step(tp_action)
        _step_noop(env, 1)

        pov = _look_straight(env, target_pitch=90.0, target_yaw_delta=0.0)
        handle["last_pov"] = pov
        _save_rgb(pov, save_path)
        b64 = _rgb_to_b64png(pov)

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
    """Rotate in-place to the given yaw/pitch and capture."""
    env = handle["env"]
    try:
        tp_action = dict(_NOOP_ACTION)
        tp_action["chat"] = f"/tp @s ~ ~ ~ {yaw:.1f} {pitch:.1f}"
        env.step(tp_action)
        _step_noop(env, 1)

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
    """Execute one MinerRL action dict for `repeat` steps and return frames."""
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
    """Run a DefaultAgent for up to max_steps steps and return frames + logs."""
    from mc_agent import MinerRLActionSpace, DefaultContextBuilder, OpenAIProvider, DefaultAgent

    save_dir = save_dir or handle["tmp_dir"]
    os.makedirs(save_dir, exist_ok=True)

    model = provider_config.get("model") or os.getenv("AGENT_MODEL")
    if not model:
        raise ValueError("[run_agent_episode] Model name is required. Pass it via provider_config['model'] or set AGENT_MODEL env var.")
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


def make_execute_commands_tool(handle: SandboxHandle, default_log_dir: Optional[str] = None):
    """Return an AutoGen-compatible closure for execute_commands."""
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
    """Return an AutoGen-compatible closure for execute_agent_action."""
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
    """Return an AutoGen-compatible closure for take_screenshot."""
    def screenshot_tool(save_path: str = None) -> Dict[str, Any]:
        """Take a screenshot of the current Minecraft view."""
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
    """Return an AutoGen-compatible closure for run_agent_episode."""
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


_PREVIEW_MAX_STEPS = 20


def preview_scene_in_sandbox(
    handle: SandboxHandle,
    commands: List[str],
    explore_prompt: Optional[str] = None,
    max_walk_steps: int = _PREVIEW_MAX_STEPS,
    loading_steps: int = 20,
    save_dir: Optional[str] = None,
    agent_model: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a scene and explore it with an AI agent (mirrors eval_benchmark.py logic).

    Returns dict with initial_frame, explore_frames, all_frames,
    total_steps, saved_dir, commands_executed.
    """
    from collections import deque

    save_dir = save_dir or handle["tmp_dir"]
    ts = int(time.time() * 1000)
    preview_dir = os.path.join(save_dir, f"preview_{ts}")
    os.makedirs(preview_dir, exist_ok=True)

    env = handle["env"]

    print(f"  [Preview] Building scene: {len(commands)} commands...")
    try:
        if isinstance(env, LazyMCBenchSandboxEnv):
            env.initialize(commands=commands if commands else None, task_text=None)
        else:
            response = env.create_env(
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

    try:
        obs, _ = env.reset()
        pov = obs["pov"]
        handle["last_pov"] = pov
        print(f"  [Preview] reset OK")
    except Exception as e:
        print(f"  [Preview] reset failed: {e}")
        pov = handle.get("last_pov")

    print(f"  [Preview] Settling: {loading_steps} noop steps...")
    for _s in range(loading_steps):
        try:
            obs, _, _, _, _ = env.step(dict(_NOOP_ACTION))
            pov = obs["pov"]
            handle["last_pov"] = pov
        except Exception:
            break
    print(f"  [Preview] Settle done. Saving initial frame...")

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

    explore_frames: List[Dict[str, Any]] = []
    total_steps = 0

    _observe_prompt = explore_prompt or (
        "You are an AI agent exploring a freshly-built Minecraft scene. "
        "Your goal is OBSERVATION, not task completion. "
        "Walk around, look at different areas, and take note of the spatial layout, "
        "block placement, structures, and any issues with the scene design."
    )

    print(f"  [Preview] Starting agent exploration (max {max_walk_steps} steps)...")

    try:
        from mc_agent import DefaultAgent, MinerRLActionSpace, DefaultContextBuilder, OpenAIProvider

        _api_key  = os.getenv("AGENT_API_KEY", "")
        _api_base = os.getenv("AGENT_API_BASE", "")
        _model = agent_model or os.getenv("AGENT_MODEL")
        if not _model:
            raise ValueError("[preview_scene_in_sandbox] Model name is required. Pass agent_model or set AGENT_MODEL env var.")
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

        frame_buffer: deque = deque(maxlen=3)
        frame_buffer.append(pov)
        thought_history: List[str] = []
        action_history:  List[Dict[str, Any]] = []

        for step_idx in range(max_walk_steps):
            print(f"  [Preview] --- Step {step_idx + 1}/{max_walk_steps} ---")

            frames = list(frame_buffer)
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

    print(f"  [Preview] Done: {total_steps} exploration steps, {len(all_frames)} total frames saved.")

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
    """Return an AutoGen-compatible closure for preview_scene_in_sandbox."""
    def preview_scene_tool(
        commands: List[str],
        explore_prompt: str = None,
        max_walk_steps: int = _PREVIEW_MAX_STEPS,
        loading_steps: int = 20,
        save_dir: str = None,
    ) -> Dict[str, Any]:
        """Build the Minecraft scene and explore it with an AI agent."""
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
