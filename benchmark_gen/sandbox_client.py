"""
benchmark_gen/sandbox_client.py

Canonical SandboxClusterTool for lumine-client/minecraft.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from pssdk import BaseSandboxClusterTool, with_retry
except ImportError as _e:
    raise ImportError(
        "pssdk is required. Install it with: pip install mt-paas-sandbox-python-sdk==1.1.0"
    ) from _e


@with_retry(max_attempts=3, retry_interval=10, infinite_retry_on_resource_limit=True, exclude_methods=[])
class SandboxClusterTool(BaseSandboxClusterTool):
    """
    lumine-server 工具的封装类。
    每个会话应该创建一个新的实例。跨会话复用实例可能导致未预期的后果。
    """

    def create_env(self, env: str = 'MinecraftSim', obs_size: List[int] = [128, 128], render_size: List[int] = [640, 360], seed: int = 0, record: bool = False, record_path: str = './output/', yaml_config: str = None, commands: List[str] = None, task_text: str = None, call_timeout: int = 0):
        """创建并初始化 MineStudio/Minecraft 游戏环境，支持 YAML 配置、commands 列表或 gym.make"""
        request_body = {"obs_size": obs_size, "yaml_config": yaml_config, "seed": seed, "render_size": render_size, "record": record, "record_path": record_path, "env": env, "commands": commands, "task_text": task_text}
        request_header = {}
        request_query = {}
        return self._gateway_post(uri="/create_env", request_body=request_body, call_timeout=call_timeout, params=request_query, headers=request_header)

    def reset_env(self, call_timeout: int = 0):
        """重置游戏环境，返回初始截图（base64 JPEG）"""
        request_body = {}
        request_header = {}
        request_query = {}
        return self._gateway_post(uri="/reset_env", request_body=request_body, call_timeout=call_timeout, params=request_query, headers=request_header)

    def step(self, action: Dict[str, Any], call_timeout: int = 0):
        """执行一步游戏动作，返回截图、奖励和是否结束"""
        request_body = {"action": action}
        request_header = {}
        request_query = {}
        return self._gateway_post(uri="/step", request_body=request_body, call_timeout=call_timeout, params=request_query, headers=request_header)

    def close_env(self, call_timeout: int = 0):
        """关闭游戏环境，释放资源"""
        request_body = {}
        request_header = {}
        request_query = {}
        return self._gateway_post(uri="/close_env", request_body=request_body, call_timeout=call_timeout, params=request_query, headers=request_header)
