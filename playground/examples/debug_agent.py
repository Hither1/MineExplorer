from loguru import logger
import typer
import sys
import os
from pathlib import Path

sys.path.append(Path(__file__).resolve().parent.parent.parent.as_posix())
from playground.engine.simple_loop import AgentSimpleLoopEndine
from env.minerl_local import MineRLLocalEnv
from env.minerl_sandbox import MineRLSandboxEnv
from playground.agent.default import DefaultAgent
from playground.components.action_space.minerl import MinerRLActionSpace
from playground.components.action_space.cua import CUAActionSpace
from playground.components.provider.openai_provider import OpenAIProvider
from playground.components.context.default import DefaultContextBuilder
from playground.components.context.cua import CUAContextBuilder
from playground.components.context.default import DefaultContextBuilder, MINERL_TASK_MAP, MINERL_DEFAULT_TASK_EXAMPLE


FRAME_BUFFER_SIZE = 5
THOUGHT_HISTORY_SIZE = 5
MAX_STEPS = 500

BASE_VIDEO_SAVE_DIR = Path("./debug_output/playground/video")
BASE_MESSAGE_SAVE_DIR = Path("./debug_output/playground/messages")

AGENT_API_KEY = os.getenv("AGENT_API_KEY", "")
AGENT_API_BASE = os.getenv("AGENT_API_BASE", "")
if not AGENT_API_KEY:
    raise ValueError("AGENT_API_KEY not found. Please set it in your shell: export AGENT_API_KEY=<your_key>")
if not AGENT_API_BASE:
    raise ValueError("AGENT_API_BASE not found. Please set it in your shell: export AGENT_API_BASE=<your_base_url>")


app = typer.Typer(
    name="debug_agent",
    help="debug_agent - Run agent in local server.",
    no_args_is_help=True,
)

@app.command()
def invoke_typer_command() -> None:
    raise NotImplementedError("invoke_typer_command() just a hook to activate commands of typer.")


@app.command()
def run_minerl(
    env_id: str = typer.Option("MineRLBasaltFindCave-v0", "--env", "-e", help="The Minecraft environment ID to run."),
    model: str = typer.Option(None, "--model", "-m", help="LLM model name, e.g. aws.claude-opus-4.6. Overrides AGENT_MODEL env var."),
    action_space_type: str = typer.Option("minerl", "--action-space-type", "-a", help="ActionSpace type for agent to handle MineCraft. e.g. CUA."),
    use_local_server: bool = typer.Option(True, "--use-local-server/--no-use-local-server", help="Use the local server for running MineCraft simulator."),
    save_messages: bool = typer.Option(True, "--save-messages/--no-save-messages", help="Eable saving LLM messages (messages are saved by default).")
) -> None:

    agent_model = model or os.getenv("AGENT_MODEL") or "aws.claude-opus-4.6"
    logger.info(f"--- Initializing MineCraft Gym environment and Agent (model={agent_model}) ---")
        
    if env_id not in MINERL_TASK_MAP:
        logger.warning(f"Environment {env_id} was not in MINERL_TASK_MAP, use default environment: MineRLBasaltFindCave-v0")
        env_id = MINERL_DEFAULT_TASK_EXAMPLE
    task_desc = MINERL_TASK_MAP[env_id]

    # Env & Agent init.
    if use_local_server:
        env = MineRLLocalEnv(server_address="http://localhost:8000", env_id=env_id)
    else:
        env = MineRLSandboxEnv(env_id=env_id)

    llm_provider = OpenAIProvider(AGENT_API_KEY, AGENT_API_BASE, agent_model)

    if action_space_type == "minerrl":
        action_space = MinerRLActionSpace()
        context_builder_class = DefaultContextBuilder
    elif action_space_type == "cua":
        action_space = CUAActionSpace()
        context_builder_class = CUAContextBuilder
    else:
        action_space = MinerRLActionSpace()
        context_builder_class = DefaultContextBuilder
        logger.warning(f"ActionSpace type {action_space_type} was not existed, use default actionspace: MinerRLActionSpace")

    agent = DefaultAgent(
        action_space=action_space, 
        provider=llm_provider, 
        context_builder_class=context_builder_class,
        model=agent_model
    )

    # Sanitize run_id: replace '/' in model name (e.g. "openai/model") to avoid nested dirs
    safe_run_id = f"{agent_model}_{env_id}_debug".replace("/", "_")
    AgentSimpleLoopEndine(
        video_save_dir=BASE_VIDEO_SAVE_DIR,
        message_save_dir=BASE_MESSAGE_SAVE_DIR,
        frame_buffer_size=FRAME_BUFFER_SIZE,
        max_steps=MAX_STEPS
    ).fire(
        run_id=safe_run_id,
        task_id=env_id, 
        task_desc=task_desc, 
        agent=agent, 
        env=env, 
        save_messages=save_messages
    )


@app.command()
def run_minestudio(
    env_id: str = typer.Option("MineRLBasaltFindCave-v0", "--env", "-e", help="MineRL env ID for system/347 sandbox, e.g. MineRLBasaltFindCave-v0."),
    model: str = typer.Option(None, "--model", "-m", help="LLM model name, e.g. aws.claude-opus-4.6. Overrides AGENT_MODEL env var."),
    task_desc: str = typer.Option(None, "--task-desc", "-t", help="Task description for the agent. If not set, falls back to MINERL_TASK_MAP or env.task."),
    action_space_type: str = typer.Option("minerl", "--action-space-type", "-a", help="ActionSpace type for agent to handle MineCraft. e.g. CUA."),
    loading_command_steps: int = typer.Option(20, "--loading-command-steps", help="Loading command steps for MineStudio"),
    use_local_server: bool = typer.Option(False, "--use-local-server/--no-use-local-server", help="Use the local server for running MineCraft simulator."),
    save_messages: bool = typer.Option(True, "--save-messages/--no-save-messages", help="Eable saving LLM messages (messages are saved by default).")
) -> None:

    agent_model = model or os.getenv("AGENT_MODEL") or "aws.claude-opus-4.6"
    logger.info(f"--- Initializing MineCraft Gym environment and Agent (model={agent_model}) ---")

    # Env & Agent init.
    if use_local_server:
        env = MineRLLocalEnv(server_address="http://localhost:8000", env_id=env_id)
    else:
        env = MineRLSandboxEnv(env_id=env_id)

    # Resolve task description: --task-desc arg > env.task (MineStudio) > MINERL_TASK_MAP fallback
    if task_desc:
        resolved_task_desc = task_desc
    elif hasattr(env, "task") and env.task:
        resolved_task_desc = env.task
    else:
        resolved_task_desc = MINERL_TASK_MAP.get(env_id, f"Complete the task in Minecraft for environment {env_id}.")
    logger.info(f"Task description: {resolved_task_desc}")

    llm_provider = OpenAIProvider(AGENT_API_KEY, AGENT_API_BASE, agent_model)

    if action_space_type == "minerrl":
        action_space = MinerRLActionSpace()
        context_builder_class = DefaultContextBuilder
    elif action_space_type == "cua":
        action_space = CUAActionSpace()
        context_builder_class = CUAContextBuilder
    else:
        action_space = MinerRLActionSpace()
        context_builder_class = DefaultContextBuilder
        logger.warning(f"ActionSpace type {action_space_type} was not existed, use default actionspace: MinerRLActionSpace")

    agent = DefaultAgent(
        action_space=action_space, 
        provider=llm_provider, 
        context_builder_class=context_builder_class,
        model=agent_model
    )

    # Sanitize run_id: replace '/' in model name (e.g. "openai/model") to avoid nested dirs
    safe_run_id = f"{agent_model}_{env_id}_debug".replace("/", "_")
    AgentSimpleLoopEndine(
        video_save_dir=BASE_VIDEO_SAVE_DIR,
        message_save_dir=BASE_MESSAGE_SAVE_DIR,
        frame_buffer_size=FRAME_BUFFER_SIZE,
        max_steps=MAX_STEPS
    ).fire(
        run_id=safe_run_id,
        task_id=env_id, 
        task_desc=resolved_task_desc, 
        agent=agent, 
        env=env, 
        loading_command_steps=loading_command_steps,
        save_messages=save_messages
    )


if __name__ == "__main__":
    print(__file__)
    app()
