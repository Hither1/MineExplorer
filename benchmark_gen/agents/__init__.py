"""
benchmark_gen/agents — Multi-Agent Framework (AutoGen-based)
=============================================================

Five specialized agents collaborate via AutoGen GroupChat to generate
high-quality Minecraft benchmark scenarios.
"""

from .orchestrator import BenchmarkOrchestrator
from .sandbox_tools import (
    SandboxHandle,
    setup_sandbox,
    lazy_setup_sandbox,
    LazyMCBenchSandboxEnv,
    close_sandbox,
    execute_commands,
    take_screenshot,
    execute_agent_action,
    run_agent_episode,
    preview_scene_in_sandbox,
    make_preview_scene_tool,
)

__all__ = [
    "BenchmarkOrchestrator",
    "SandboxHandle",
    "setup_sandbox",
    "lazy_setup_sandbox",
    "LazyMCBenchSandboxEnv",
    "close_sandbox",
    "execute_commands",
    "take_screenshot",
    "execute_agent_action",
    "run_agent_episode",
    "preview_scene_in_sandbox",
    "make_preview_scene_tool",
]
