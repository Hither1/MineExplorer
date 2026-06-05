from __future__ import annotations

import os
import uuid
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
    """HTTP client for the Minecraft sandbox server.

    If both FRIDAY_SANDBOX_TOKEN and FRIDAY_SANDBOX_ENDPOINT are set, the
    Friday platform SDK (pssdk / mt-paas-sandbox-python-sdk) is used.
    Otherwise, the original direct-HTTP mode (MC_SANDBOX_URL) is used.
    """

    def __init__(self, endpoint: Optional[str] = None, token: Optional[str] = None,
                 session_id: Optional[str] = None):
        friday_token = token or os.getenv("FRIDAY_SANDBOX_TOKEN", "")
        friday_endpoint = endpoint or os.getenv("FRIDAY_SANDBOX_ENDPOINT", "")

        self.use_friday_platform = bool(friday_token and friday_endpoint)

        if self.use_friday_platform:
            # pip install mt-paas-sandbox-python-sdk==1.1.0
            from pssdk import BaseSandboxClusterTool, with_retry
            from pssdk import errors as pssdk_errors

            @with_retry(max_attempts=3, retry_interval=10,
                        infinite_retry_on_resource_limit=True, exclude_methods=[])
            class _FridayTool(BaseSandboxClusterTool):
                pass

            self._friday_tool = _FridayTool(friday_endpoint, friday_token)
            # 复用 Friday SDK 自动生成的 session_id（除非调用方显式传入）
            if session_id:
                self._friday_tool.session_id = session_id
            self.session_id: str = self._friday_tool.session_id
            self._friday_tool.sandbox_start()
        else:
            self.server_address = (
                (endpoint or _get_server_address()) if not friday_endpoint
                else friday_endpoint
            ).rstrip("/")
            # 每个实例拥有独立的 session_id，确保并发时服务端可路由到正确实例
            self.session_id: str = session_id or str(uuid.uuid4())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _post(self, uri: str, request_body: dict = None, call_timeout: int = 0) -> dict:
        if self.use_friday_platform:
            # Friday SDK 通过 _gateway_post 发送请求，session_id 由 SDK 自动注入
            return self._friday_tool._gateway_post(
                uri=uri,
                request_body=dict(request_body or {}),
                call_timeout=call_timeout,
                params={},
                headers={},
            )
        else:
            timeout = call_timeout if call_timeout > 0 else 180
            url = f"{self.server_address}/{uri.lstrip('/')}"
            body = dict(request_body or {})
            body["session_id"] = self.session_id
            r = requests.post(url, json=body, timeout=timeout)
            r.raise_for_status()
            return r.json()

    def close(self) -> None:
        """Release platform-side resources (only needed for Friday platform mode)."""
        if self.use_friday_platform:
            self._friday_tool.sandbox_stop()

    # ------------------------------------------------------------------
    # Public API  (identical signatures to the original class)
    # ------------------------------------------------------------------

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
        # session_id 由 self._post 统一注入
        return self._post("/reset_env", {}, call_timeout)

    def step(self, action: Dict[str, Any], call_timeout: int = 0) -> dict:
        # session_id 由 self._post 统一注入
        return self._post("/step", {"action": action}, call_timeout)

    def close_env(self, call_timeout: int = 0) -> dict:
        # session_id 由 self._post 统一注入
        return self._post("/close_env", {}, call_timeout)
