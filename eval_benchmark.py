from __future__ import annotations

import json
import os
import sys
import time
import signal
from collections import deque
from concurrent.futures import ProcessPoolExecutor, as_completed
from loguru import logger
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer

_ROOT_DIR = Path(__file__).resolve().parent
_PLAYGROUND_DIR = _ROOT_DIR / "playground"
_BENCHMARK_GEN = _ROOT_DIR / "benchmark_gen"

if str(_PLAYGROUND_DIR) not in sys.path:
    sys.path.insert(0, str(_PLAYGROUND_DIR))
if str(_ROOT_DIR) not in sys.path:
    sys.path.append(str(_ROOT_DIR))

from playground.engine.simple_loop import AgentSimpleLoopEndine
from env.minerl_local import MineRLLocalEnv
from env.minerl_sandbox import MineRLSandboxEnv
from env.tools.render import RenderWrapper
from playground.agent.default import DefaultAgent
from playground.components.action_space.minerl import MinerRLActionSpace
from playground.components.provider.openai_provider import OpenAIProvider
from playground.components.provider.vllm_provider import VLLMProvider
from playground.components.context.default import DefaultContextBuilder

FRAME_BUFFER_SIZE = 20
MAX_STEPS = 300
MAX_WORKERS = 8

AGENT_API_KEY = os.getenv("AGENT_API_KEY", "")
AGENT_API_BASE = os.getenv("AGENT_API_BASE", "")
if not AGENT_API_KEY:
    raise ValueError("AGENT_API_KEY not found. Please set it in .env or environment")
if not AGENT_API_BASE:
    raise ValueError("AGENT_API_BASE not found. Please set it in .env or environment")

app = typer.Typer(help="Evaluate benchmark scenarios")


class MineRLBenchmarkEnv(MineRLSandboxEnv):
    """MineRLSandboxEnv that builds the scene from a benchmark metadata.json."""

    def __init__(self, metadata_path: str):
        meta_path = Path(metadata_path)
        if not meta_path.exists():
            raise FileNotFoundError(f"Metadata not found: {meta_path}")
        with open(meta_path, "r", encoding="utf-8") as f:
            self._metadata = json.load(f)
        self._parse_metadata()
        super().__init__(env_id=self._scene_name)

    def _parse_metadata(self) -> None:
        self._commands_list = self._metadata.get("commands", [])
        self._task_text = self._metadata.get("task_text", "")
        self._scene_name = self._metadata.get("scene_name", "benchmark_scene")
        logger.info(f"[BenchmarkEnv] scene={self._scene_name} commands={len(self._commands_list)}")
        logger.info(f"[BenchmarkEnv] task: {self._task_text[:100]}")

    def _init_remote_env(self) -> None:
        if not self.sandbox_tool:
            raise RuntimeError("sandbox_tool not initialised.")
        logger.info(f"Sending /create_env with {len(self._commands_list)} commands...")
        response = self.sandbox_tool.create_env(
            env='MinecraftSim',
            obs_size=[128, 128],
            render_size=[640, 360],
            seed=0,
            record=False,
            record_path='./output/',
            yaml_config=None,
            commands=self._commands_list,
            task_text=self._task_text,
            call_timeout=120,
        )
        if response.get("status") != 0:
            raise RuntimeError(f"create_env failed: {response.get('msg')}")
        self.task = response.get("task_text", "") or self._task_text
        logger.success(f"Benchmark environment created: {self.task[:80]}")
        time.sleep(10)


try:
    if str(_BENCHMARK_GEN) not in sys.path:
        sys.path.append(str(_BENCHMARK_GEN))
    from benchmark_gen.milestone_checker import MilestoneChecker
    _HAS_MILESTONE_CHECKER = True
except ImportError:
    _HAS_MILESTONE_CHECKER = False

    class MilestoneChecker:
        """Stub when benchmark_gen is not available."""
        def __init__(self, milestones): self._milestones = milestones
        def reset(self, info): pass
        def check(self, info): return []
        def summary(self): return "no milestone checker"
        def augment_action_with_queries(self, action, info): return action
        def num_completed(self): return 0
        def num_trackable(self): return 0
        def all_done(self): return False

        @classmethod
        def from_metadata(cls, path): return cls([])


# Global flag to track shutdown request
_shutdown_requested = False


def _signal_handler(signum, frame):
    """Handle SIGINT by setting global shutdown flag."""
    global _shutdown_requested
    _shutdown_requested = True
    logger.warning("\n[INTERRUPT] Shutdown requested, finishing current step and closing sandbox...")


def _run_benchmark(
    *,
    metadata_path: str,
    model: str,
    output_dir: Path,
    loading_command_steps: int,
    max_steps: int,
    use_vllm: bool = False,
    vllm_url: str = "http://localhost:8000/v1",
    frame_size: int = FRAME_BUFFER_SIZE,
) -> Dict[str, Any]:
    """Run one benchmark scenario and save results."""
    global _shutdown_requested

    meta_path = Path(metadata_path)
    with open(meta_path, "r", encoding="utf-8") as f:
        metadata_dict = json.load(f)

    scene_id = meta_path.parent.parent.name
    task_desc = metadata_dict.get("task_text", f"Complete the Minecraft task for {scene_id}.")
    safe_model = model.replace("/", "_")

    if _HAS_MILESTONE_CHECKER:
        try:
            checker = MilestoneChecker.from_metadata(metadata_path)
            logger.info(f"Loaded {len(checker._milestones)} milestones")
        except Exception as e:
            logger.warning(f"Could not load milestones: {e}")
            checker = MilestoneChecker([])
    else:
        checker = MilestoneChecker([])

    _base_env = MineRLBenchmarkEnv(metadata_path=metadata_path)
    if use_vllm:
        _provider = VLLMProvider(model_name=model, base_url=vllm_url)
    else:
        _provider = OpenAIProvider(AGENT_API_KEY, AGENT_API_BASE, model)
    agent = DefaultAgent(
        action_space=MinerRLActionSpace(),
        provider=_provider,
        context_builder_class=DefaultContextBuilder,
        model=model,
    )

    run_id = f"{safe_model}_{scene_id}"

    output_dir.mkdir(parents=True, exist_ok=True)
    result_save_path = output_dir / "result.json"

    env = RenderWrapper(_base_env, save_messages=True, save_path=str(output_dir))

    frame_buffer = deque(maxlen=frame_size)
    thought_history: List[str] = []
    action_history: List[Dict] = []
    _frame_completed: Dict[str, Optional[int]] = {}
    _all_done_logged: bool = False
    long_term_memory: str = ""

    # Register signal handler for graceful shutdown
    original_sigint_handler = signal.signal(signal.SIGINT, _signal_handler)

    try:
        # Reset
        has_loading = loading_command_steps > 0
        obs, info = env.reset(save_frame=not has_loading)
        frame_buffer.append(obs["pov"])

        for step in range(loading_command_steps):
            if _shutdown_requested:
                logger.info(f"[{run_id}] Shutdown requested during loading, exiting...")
                break
            logger.info(f"[{run_id}] Loading command step {step + 1}/{loading_command_steps}")
            _, noop_action = agent.get_default_action(is_call_failed=False)
            obs, reward, terminated, truncated, info = env.step(
                noop_action, save_frame=(step + 1 == loading_command_steps)
            )

        logger.info(f"[{run_id}] Minecraft commands loaded.")

        if not info.get("player_pos"):
            _, noop_action = agent.get_default_action(is_call_failed=False)
            obs, reward, terminated, truncated, info = env.step(noop_action, save_frame=True)
            frame_buffer.append(obs["pov"])

        checker.reset(info)
        agent.load_system_prompt(task_desc)

        step_error: Optional[str] = None
        step = -1

        for step in range(max_steps):
            if _shutdown_requested:
                logger.info(f"[{run_id}] Shutdown requested, exiting after step {step}...")
                step_error = "interrupted_by_user"
                break

            logger.info(f"[{run_id}] --- Step {step + 1}/{max_steps} ---")

            # Check for interrupt with shorter timeout
            try:
                thought, action, memory_update = agent.get_action(
                    list(frame_buffer), list(thought_history), list(action_history), step + 1,
                    long_term_memory=long_term_memory
                )
            except Exception as agent_err:
                logger.error(f"[{run_id}] Agent call failed: {agent_err}. Retrying in 10s...")
                time.sleep(10)
                continue

            if action is None:
                logger.warning(f"[{run_id}] Agent failed to provide action. Retrying in 10s...")
                time.sleep(10)
                continue

            if memory_update and memory_update.strip():
                long_term_memory = memory_update.strip()

            thought_history.append(thought)
            action_history.append(action)

            try:
                augmented_action = checker.augment_action_with_queries(action, info)
                obs, reward, terminated, truncated, info = env.step(augmented_action)
            except Exception as env_err:
                logger.error(f"[{run_id}] env.step failed: {env_err}. Retrying in 10s...")
                time.sleep(10)
                continue

            done = terminated or truncated
            frame_buffer.append(obs["pov"])

            milestone_status = checker.check(info)
            for ms in milestone_status:
                mid = ms["milestone_id"]
                if ms.get("completed") and mid not in _frame_completed:
                    _frame_completed[mid] = env.frame_count
                    logger.success(f"[{run_id}] Milestone '{mid}' completed at step {step + 1}")

            if not _all_done_logged and checker.num_completed() > 0 and checker.all_done():
                _all_done_logged = True
                logger.success(f"[{run_id}] All milestones completed at step {step + 1}!")

            if (step + 1) % 10 == 0:
                env.save_video_checkpoint()

            if done:
                logger.success(f"[{run_id}] Episode finished.")
                break

    except KeyboardInterrupt:
        logger.warning(f"[{run_id}] KeyboardInterrupt received, shutting down...")
        step_error = "interrupted_by_user"
    finally:
        # Restore original signal handler
        signal.signal(signal.SIGINT, original_sigint_handler)

        # Always close the environment to release sandbox
        logger.info(f"[{run_id}] Closing sandbox environment...")
        try:
            env.close()
            logger.success(f"[{run_id}] Sandbox closed successfully")
        except Exception as close_err:
            logger.warning(f"[{run_id}] env.close() raised: {close_err}")

    # Build final status even if interrupted
    final_status = []
    for ms in checker._milestones:
        mid = ms.get("milestone_id", "")
        completed_frame = _frame_completed.get(mid)
        final_status.append({
            "milestone_id": mid,
            "task": ms.get("task", ""),
            "completed": completed_frame is not None,
            "frame_completed": completed_frame if completed_frame is not None else -1,
        })

    total_steps = step + 1 if step >= 0 else 0
    summary: Dict[str, Any] = {
        "run_id": run_id,
        "model": model,
        "scene_id": scene_id,
        "mode": "multi-agent",
        "metadata_path": str(meta_path),
        "total_steps": total_steps,
        "milestones_completed": checker.num_completed(),
        "milestones_trackable": checker.num_trackable(),
        "milestones_total": len(checker._milestones),
        "all_milestones_done": checker.all_done(),
        "milestone_status": final_status,
    }
    if step_error:
        summary["error"] = step_error

    with open(result_save_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    logger.success(f"[{run_id}] Result saved -> {result_save_path}")

    return summary


def _worker_eval(worker_args: dict) -> dict:
    """Picklable worker for parallel benchmark evaluation."""
    import signal as _signal
    _signal.signal(_signal.SIGINT, _signal.SIG_IGN)

    _root = Path(__file__).resolve().parent
    sys.path.insert(0, str(_root / "playground"))
    sys.path.append(str(_root))

    return _run_benchmark(
        metadata_path=worker_args["metadata_path"],
        model=worker_args["model"],
        output_dir=Path(worker_args["output_dir"]),
        loading_command_steps=worker_args["loading_command_steps"],
        max_steps=worker_args["max_steps"],
        use_vllm=worker_args.get("use_vllm", False),
        vllm_url=worker_args.get("vllm_url", "http://localhost:8000/v1"),
        frame_size=worker_args.get("frame_size", FRAME_BUFFER_SIZE),
    )


@app.command(name="run")
def eval_benchmark(
    model: str = typer.Option(..., "--model", "-m", help="LLM model name"),
    benchmark_dir: str = typer.Option("benchmark_shuffled", "--benchmark-dir", "-b",
                                      help="Path to benchmark directory"),
    output_dir: str = typer.Option("outputs", "--output-dir", "-o",
                                   help="Output directory"),
    loading_command_steps: int = typer.Option(20, "--loading-command-steps",
                                              help="No-op steps after reset"),
    max_steps: int = typer.Option(MAX_STEPS, "--max-steps",
                                  help="Maximum agent steps per episode"),
    resume: bool = typer.Option(False, "--resume",
                                help="Resume evaluation (skip completed)"),
    use_vllm: bool = typer.Option(False, "--use-vllm",
                                  help="Use local vLLM server"),
    vllm_url: str = typer.Option("http://localhost:8000/v1", "--vllm-url",
                                 help="vLLM server URL"),
    num_workers: int = typer.Option(1, "--num-workers", "-n",
                                    help="Number of parallel workers"),
    limit: Optional[int] = typer.Option(None, "--limit",
                                        help="Limit number of scenarios to evaluate"),
):
    """Evaluate all benchmark scenarios in the specified directory.

    Scans for metadata.json files in <benchmark_dir>/<scene>/multi-agent/ structure.
    """
    logger.info(f"--- Starting evaluation (model={model}) ---")

    bench_path = Path(benchmark_dir)
    out_root = Path(output_dir) / model.replace("/", "_")

    if not bench_path.exists():
        raise FileNotFoundError(f"Benchmark directory not found: {bench_path}")

    # Discover all metadata.json files
    metadata_entries: List[tuple] = []
    for scene_dir in sorted(d for d in bench_path.iterdir() if d.is_dir() and not d.name.startswith("_")):
        meta_path = scene_dir / "multi-agent" / "metadata.json"
        if meta_path.exists():
            metadata_entries.append((scene_dir.name, str(meta_path)))

    if not metadata_entries:
        logger.warning(f"No metadata.json found under {bench_path}")
        return

    # Apply limit if specified
    if limit and limit > 0:
        metadata_entries = metadata_entries[:limit]

    logger.info(f"Found {len(metadata_entries)} scenario(s) to evaluate")

    pending: List[tuple] = []
    all_results: List[Dict[str, Any]] = []

    for scene_num, meta_path in metadata_entries:
        scene_out_dir = out_root / scene_num
        result_path = scene_out_dir / "result.json"

        if resume and result_path.exists():
            logger.info(f"[SKIP] {scene_num} - result.json exists")
            with open(result_path, "r", encoding="utf-8") as f:
                all_results.append(json.load(f))
        else:
            pending.append((scene_num, meta_path))

    logger.info(f"Scenarios to run: {len(pending)} (skipped: {len(metadata_entries) - len(pending)})")

    def _make_error_summary(scene_num, e):
        return {
            "run_id": f"{model}_{scene_num}",
            "model": model,
            "scene_id": scene_num,
            "mode": "multi-agent",
            "error": str(e),
            "milestones_completed": 0,
            "milestones_trackable": 0,
            "all_milestones_done": False,
        }

    if num_workers <= 1:
        for idx, (scene_num, meta_path) in enumerate(pending):
            scene_out_dir = out_root / scene_num
            result_path = scene_out_dir / "result.json"

            logger.info(f"\n{'='*60}")
            logger.info(f"[{idx+1}/{len(pending)}] {scene_num}")

            try:
                summary = _run_benchmark(
                    metadata_path=meta_path,
                    model=model,
                    output_dir=scene_out_dir,
                    loading_command_steps=loading_command_steps,
                    max_steps=max_steps,
                    use_vllm=use_vllm,
                    vllm_url=vllm_url,
                )
            except Exception as e:
                logger.error(f"[ERROR] {scene_num}: {e}")
                summary = _make_error_summary(scene_num, e)
                scene_out_dir.mkdir(parents=True, exist_ok=True)
                with open(result_path, "w", encoding="utf-8") as f:
                    json.dump(summary, f, ensure_ascii=False, indent=2)

            all_results.append(summary)

            task_icon = "✅" if summary.get("all_milestones_done") else "❌"
            logger.info(f"Result: {task_icon} | milestones {summary.get('milestones_completed', 0)}/{summary.get('milestones_trackable', 0)}")

    else:
        import multiprocessing as _mp

        effective_workers = min(num_workers, len(pending))
        mp_ctx = _mp.get_context("spawn")

        remaining = list(pending)
        batch_num = 0

        while remaining:
            batch = remaining[:effective_workers]
            remaining = remaining[effective_workers:]
            batch_num += 1

            logger.info(f"\n[Batch {batch_num}] Launching {len(batch)} worker(s)")

            batch_jobs: List[Dict[str, Any]] = []
            for scene_num, meta_path in batch:
                scene_out_dir = out_root / scene_num
                scene_out_dir.mkdir(parents=True, exist_ok=True)
                batch_jobs.append({
                    "metadata_path": str(meta_path),
                    "model": model,
                    "output_dir": str(scene_out_dir),
                    "loading_command_steps": loading_command_steps,
                    "max_steps": max_steps,
                    "use_vllm": use_vllm,
                    "vllm_url": vllm_url,
                    "_scene_num": scene_num,
                })

            with ProcessPoolExecutor(max_workers=len(batch_jobs), mp_context=mp_ctx) as pool:
                futures = {pool.submit(_worker_eval, job): job for job in batch_jobs}
                for future in as_completed(futures):
                    job = futures[future]
                    scene_num = job["_scene_num"]
                    try:
                        summary = future.result()
                        all_results.append(summary)
                        task_icon = "✅" if summary.get("all_milestones_done") else "❌"
                        logger.info(f"[DONE] {scene_num} {task_icon} | milestones {summary.get('milestones_completed', 0)}/{summary.get('milestones_trackable', 0)}")
                    except Exception as exc:
                        logger.error(f"[ERROR] {scene_num}: {exc}")
                        summary = _make_error_summary(scene_num, exc)
                        all_results.append(summary)

    # Aggregated summary
    total = len(all_results)
    done = sum(1 for r in all_results if r.get("all_milestones_done"))
    ms_done = sum(r.get("milestones_completed", 0) for r in all_results)
    ms_total = sum(r.get("milestones_trackable", 0) for r in all_results)

    logger.info(f"\n{'='*60}")
    logger.info("EVALUATION COMPLETE")
    logger.info("-" * 60)
    task_rate = done / total * 100 if total > 0 else 0.0
    ms_rate = ms_done / ms_total * 100 if ms_total > 0 else 0.0
    logger.info(f"Scenes: {total} | Tasks: {done}/{total} ({task_rate:.1f}%) | Milestones: {ms_done}/{ms_total} ({ms_rate:.1f}%)")
    logger.info(f"{'='*60}")

    agg_path = out_root / "eval_summary.json"
    with open(agg_path, "w", encoding="utf-8") as f:
        json.dump({
            "model": model,
            "benchmark": str(bench_path),
            "total": total,
            "done": done,
            "ms_done": ms_done,
            "ms_total": ms_total,
            "task_success_rate": task_rate,
            "milestone_success_rate": ms_rate,
            "results": all_results,
        }, f, ensure_ascii=False, indent=2)
    logger.success(f"Aggregated summary -> {agg_path}")


if __name__ == "__main__":
    app()
