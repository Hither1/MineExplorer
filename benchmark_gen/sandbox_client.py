from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests


def _get_server_address() -> str:
    addr = os.getenv("MC_SANDBOX_URL", "").rstrip("/")
    if not addr:
        raise ValueError(
            "MC_SANDBOX_URL environment variable is not set. "
            "Please add 'export MC_SANDBOX_URL=http://<host>:<port>' to ~/.zshrc "
            "and restart your shell (or run: source ~/.zshrc)."
        )
    return addr


class SandboxClusterTool:
    """HTTP client for the Minecraft sandbox server (MC_SANDBOX_URL)."""

    def __init__(self, endpoint: Optional[str] = None, token: Optional[str] = None):
        self.server_address = (endpoint or _get_server_address()).rstrip("/")

    def _post(self, uri: str, request_body: dict = None, call_timeout: int = 0) -> dict:
        timeout = call_timeout if call_timeout > 0 else 180
        url = f"{self.server_address}/{uri.lstrip('/')}"
        r = requests.post(url, json=request_body or {}, timeout=timeout)
        r.raise_for_status()
        return r.json()

    def create_env(
        self,
        env: str = "MinecraftSim",
        obs_size: List[int] = None,
        render_size: List[int] = None,
        seed: int = 0,
        record: bool = False,
        record_path: str = "./output/",
        yaml_config: Optional[str] = None,
        commands: Optional[List[str]] = None,
        task_text: Optional[str] = None,
        call_timeout: int = 0,
    ) -> dict:
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
        return self._post("/create_env", body, call_timeout)

    def reset_env(self, call_timeout: int = 0) -> dict:
        return self._post("/reset_env", {}, call_timeout)

    def step(self, action: Dict[str, Any], call_timeout: int = 0) -> dict:
        return self._post("/step", {"action": action}, call_timeout)

    def close_env(self, call_timeout: int = 0) -> dict:
        return self._post("/close_env", {}, call_timeout)
