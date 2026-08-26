"""MineStudio FastAPI sandbox service.

Recovered verbatim from davidzhth/mineexplorer:0.0.1
(/home/sandbox/mc/lumine-client/minestudio/mc_server.py) so the native ARM64 route does
not depend on pulling an image that has no ARM64 manifest. The HTTP contract is identical
to the one `env/minerl_sandbox.py` and `benchmark_gen/sandbox_client.py` speak.
"""
import base64
import io
import os
import signal
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

import gym
import numpy as np
from loguru import logger
from PIL import Image

from fastapi import FastAPI
from pydantic import BaseModel

from minestudio.simulator import MinecraftSim
from minestudio.simulator.callbacks import (
    CommandsCallback, TaskCallback, RecordCallback
)
import yaml


app = FastAPI(title="MineStudio FastAPI Server")

# =========================
# 多实例会话管理
# =========================

@dataclass
class EnvSession:
    env: Any
    env_type: str  # "minestudio" or "gym"
    created_at: float = field(default_factory=time.time)

_sessions: Dict[str, EnvSession] = {}

DEFAULT_SESSION_ID = "default"

#: Reap sessions older than this many seconds. A legitimate episode is
#: create + reset + 300 steps + close, ~75 min at the worst measured load; a
#: session past two hours is debris (an errored cell that never closed, or a
#: close that failed), and its sim object + JVM are what wears this server out.
SESSION_TTL_S = int(os.getenv("MC_SESSION_TTL", "7200"))


def _force_kill_instances(session_id: str, env) -> None:
    """Best-effort SIGKILL of a session's Minecraft JVM process groups.

    MinecraftInstance._destruct asks the mod to quit over the wire
    (`_kill_minecraft_via_malmoenv`); a busy JVM ignores it and keeps burning
    ~2 cores on the server tick loop -- 40 of those wedged this server twice on
    2026-08-26 (leak measured client-side: 53 javas for 14 live cells). The
    Popen handle on each instance is authoritative, so kill by pid, process
    group first (the xvfb-run wrapper tree shares it)."""
    inner = getattr(env, "env", None)
    instances = list(getattr(inner, "instances", None) or [])
    for inst in instances:
        pid = getattr(getattr(inst, "minecraft_process", None), "pid", None)
        if not pid:
            continue
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
            logger.info(f"[{session_id}] force-killed instance pgid of pid={pid}")
        except (ProcessLookupError, PermissionError, OSError):
            try:
                os.kill(pid, signal.SIGKILL)
                logger.info(f"[{session_id}] force-killed instance pid={pid}")
            except (ProcessLookupError, PermissionError, OSError):
                pass


def _close_and_reap(session_id: str, session: "EnvSession") -> None:
    """Graceful close, then make sure the JVMs are actually gone."""
    try:
        session.env.close()
    except Exception as e:
        logger.warning(f"[{session_id}] env.close() raised ({e}); force-killing")
    _force_kill_instances(session_id, session.env)


def _janitor_loop() -> None:
    """Reap sessions past SESSION_TTL_S. Leaked sessions -- errored cells that
    never called close, or closes that failed -- accumulate sim objects, stuck
    handler threads and JVMs until the server wedges (three times on
    2026-08-26: fresh at 17:40, alive-endpoint starving by 20:55)."""
    while True:
        time.sleep(300)
        now = time.time()
        for sid in list(_sessions.keys()):
            s = _sessions.get(sid)
            if s is None or now - s.created_at <= SESSION_TTL_S:
                continue
            _sessions.pop(sid, None)
            age_min = int((now - s.created_at) / 60)
            logger.warning(f"[janitor] session {sid} is {age_min} min old "
                           f"(TTL {SESSION_TTL_S // 60} min); reaping")
            _close_and_reap(sid, s)


threading.Thread(target=_janitor_loop, daemon=True, name="session-janitor").start()


# =========================
# 请求 / 响应模型
# =========================

class CreateEnvRequest(BaseModel):
    session_id: Optional[str] = None
    env: str = "MinecraftSim"
    yaml_config: Optional[str] = None       # YAML 文本内容
    commands: Optional[List[str]] = None    # 直接传初始化命令列表
    task_text: Optional[str] = None         # 任务描述
    obs_size: Tuple[int, int] = (128, 128)
    render_size: Tuple[int, int] = (640, 360)
    seed: int = 0
    record: bool = False
    record_path: str = "./output/"


class SessionRequest(BaseModel):
    session_id: Optional[str] = None


class StepRequest(BaseModel):
    session_id: Optional[str] = None
    action: Dict[str, Any]


def ok(data: dict = None):
    resp = {"status": 0, "msg": "success"}
    if data:
        resp.update(data)
    return resp


def err(msg: str):
    return {"status": 1, "msg": msg}


# =========================
# 工具函数
# =========================

def frame_to_base64(frame: np.ndarray, fmt: str = "JPEG", quality: int = 80) -> str:
    img = Image.fromarray(frame)
    buf = io.BytesIO()
    if fmt == "JPEG":
        img.save(buf, format="JPEG", quality=quality)
    else:
        img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def convert_numpy_types(obj):
    if obj is None:
        return None
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {str(k): convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(item) for item in obj]
    return obj


# Frame-sized arrays are already delivered as `screenshot`; everything else in info is
# small enough to serialise per step.
_INFO_EXCLUDE = {"pov", "image"}


def build_info(obs: dict, info: dict) -> dict:
    """Expose the observation fields the benchmark client scores against.

    MinecraftSim's `_wrap_obs_info` already merges the observation into `info`, so
    `player_pos`, `voxels` and `mobs` are present here. The published server never sent
    them, which left `position_near_with_facing` milestones permanently unscorable
    (`eval_benchmark.py` logs `player_pos=None` and defaults spawn to the origin).
    """
    merged: Dict[str, Any] = {}
    for source in (info or {}), (obs or {}):
        if not isinstance(source, dict):
            continue
        for key, value in source.items():
            if key in _INFO_EXCLUDE:
                continue
            if isinstance(value, np.ndarray) and value.ndim >= 2:
                continue
            merged[key] = value
    return convert_numpy_types(merged)


def get_frame(obs: dict, info: dict = None) -> np.ndarray:
    # 优先用 info 中的原始高清帧 (render_size)
    if info and "pov" in info:
        return info["pov"]
    # MineStudio obs["image"] 是缩小后的 (obs_size)
    if "image" in obs:
        return obs["image"]
    # MineRL obs["pov"]
    if "pov" in obs:
        return obs["pov"]
    raise RuntimeError("obs/info contains neither 'image' nor 'pov'")


# =========================
# API 实现
# =========================

@app.get("/monitor/alive")
def monitor_alive():
    active_sessions = len(_sessions)
    return ok({
        "timestamp": time.time(),
        "status": "alive",
        "service": "minestudio-server",
        "active_sessions": active_sessions,
    })


@app.get("/list_sessions")
def list_sessions():
    sessions_info = [
        {
            "session_id": sid,
            "env_type": s.env_type,
            "created_at": s.created_at,
        }
        for sid, s in _sessions.items()
    ]
    return ok({"sessions": sessions_info})


@app.post("/create_env")
def create_env(req: CreateEnvRequest):
    try:
        session_id = req.session_id or DEFAULT_SESSION_ID

        # 如果 session 已存在，先关闭旧环境
        old_session = _sessions.pop(session_id, None)
        if old_session is not None:
            _close_and_reap(session_id, old_session)
            logger.info(f"[{session_id}] Closed existing env")

        callbacks = []
        task_text_resp = None

        if req.yaml_config:
            data = yaml.safe_load(req.yaml_config)
            commands = data.get("custom_init_commands", [])
            task_name = data.get("name", req.env or "custom")
            task_text = data.get("text", "")
            task_dict = {"name": task_name, "text": task_text}
            callbacks.append(CommandsCallback(commands))
            callbacks.append(TaskCallback([task_dict]))
            task_text_resp = task_text
            logger.info(f"[{session_id}] create_env from yaml: commands={len(commands)}, task={task_name}")

        elif req.commands:
            callbacks.append(CommandsCallback(req.commands))
            task_name = req.env or "custom"
            task_dict = {"name": task_name, "text": req.task_text or ""}
            callbacks.append(TaskCallback([task_dict]))
            task_text_resp = task_dict["text"]
            logger.info(f"[{session_id}] create_env from commands: {len(req.commands)} commands, task_text={req.task_text}")

        if callbacks:
            if req.record:
                callbacks.insert(0, RecordCallback(
                    record_path=req.record_path, fps=30, frame_type="pov"
                ))

            new_env = MinecraftSim(
                action_type="env",
                obs_size=req.obs_size,
                render_size=req.render_size,
                seed=req.seed,
                callbacks=callbacks,
            )
            env_type = "minestudio"
            logger.info(f"[{session_id}] MinecraftSim created: obs_size={req.obs_size}, seed={req.seed}")

        else:
            import minerl
            new_env = gym.make(req.env)
            env_type = "gym"
            logger.info(f"[{session_id}] gym.make({req.env}) created")

        _sessions[session_id] = EnvSession(env=new_env, env_type=env_type)

        resp_data = {"session_id": session_id}
        if task_text_resp:
            resp_data["task_text"] = task_text_resp
        return ok(resp_data)

    except Exception as e:
        logger.exception("error")
        return err(f"{type(e).__name__}: {e}")


@app.post("/reset_env")
def reset_env(req: SessionRequest = SessionRequest()):
    session_id = req.session_id or DEFAULT_SESSION_ID
    session = _sessions.get(session_id)
    if session is None:
        return err(f"session '{session_id}' not found")

    try:
        result = session.env.reset()

        if isinstance(result, tuple):
            obs, info = result
        else:
            obs, info = result, {}

        frame = get_frame(obs, info)
        screenshot = frame_to_base64(frame)

        return ok({"session_id": session_id, "screenshot": screenshot,
                   "info": build_info(obs, info)})
    except Exception as e:
        logger.exception(f"[{session_id}] reset_env error")
        return err(f"{type(e).__name__}: {e}")


@app.post("/step")
def step_env(req: StepRequest):
    session_id = req.session_id or DEFAULT_SESSION_ID
    session = _sessions.get(session_id)
    if session is None:
        return err(f"session '{session_id}' not found")

    try:
        t0 = time.time()

        if session.env_type == "gym" and not hasattr(session.env, "done"):
            session.env.done = False

        action = req.action

        t1 = time.time()
        result = session.env.step(action)
        t2 = time.time()

        if len(result) == 5:
            obs, reward, terminated, truncated, info = result
            done = bool(terminated or truncated)
        else:
            obs, reward, done, info = result
            done = bool(done)

        frame = get_frame(obs, info)
        t3 = time.time()
        screenshot = frame_to_base64(frame)
        t4 = time.time()

        resp = ok({
            "session_id": session_id,
            "screenshot": screenshot,
            "reward": float(reward),
            "done": done,
            "info": build_info(obs, info),
            "timing": {
                "env_step_ms": round((t2 - t1) * 1000, 1),
                "encode_ms": round((t4 - t3) * 1000, 1),
                "total_server_ms": round((t4 - t0) * 1000, 1),
            }
        })
        print(f"[{session_id}][step] env={t2-t1:.3f}s encode={t4-t3:.3f}s total={t4-t0:.3f}s")
        return resp

    except Exception as e:
        logger.exception(f"[{session_id}] step error")
        return err(f"{type(e).__name__}: {e}")


@app.post("/close_env")
def close_env(req: SessionRequest = SessionRequest()):
    session_id = req.session_id or DEFAULT_SESSION_ID
    session = _sessions.pop(session_id, None)
    if session is None:
        return ok({"msg": f"session '{session_id}' not found or already closed"})

    try:
        _close_and_reap(session_id, session)
        logger.info(f"[{session_id}] env closed and reaped")
        return ok({"session_id": session_id})
    except Exception as e:
        logger.exception(f"[{session_id}] close error")
        return err(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("SERVER_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
