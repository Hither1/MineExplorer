from __future__ import annotations

import json
import os
import random
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from .utils import save_benchmark_sample

BENCHMARK_GEN_DIR = Path(__file__).resolve().parent


def load_easy_tasks(task_analysis_path: str) -> List[str]:
    """Return all atomic task names where requires_domain_knowledge == 'No'."""
    with open(task_analysis_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [
        task for task, info in data.items()
        if info.get("requires_domain_knowledge") == "No"
    ]


def generate(
    api_model: str,
    api_key: str,
    api_base_url: str,
    task_analysis_path: str,
    benchmark_dir: str,
    num_samples: int = 5,
    candidate_num: int = 8,
    k_min: int = 2,
    k_max: int = 4,
    max_debate_rounds: int = 2,
    temperature_task_selector: float = 0.7,
    temperature_scene_designer: float = 0.7,
    temperature_milestone: float = 0.2,
    temperature_commonsense: float = 0.3,
    temperature_validator: float = 0.2,
    max_retries: int = 2,
    sandbox_tmp_dir: str = "/tmp/benchmark_gen_sandbox",
    seed: Optional[int] = None,
    candidate_tasks: Optional[List[str]] = None,
    start_idx: int = 0,
    extremely_hard: bool = False,
) -> List[str]:
    """Generate num_samples benchmark samples using AutoGen multi-agent debate.
    Returns a list of output directory paths.
    """
    from .orchestrator import BenchmarkOrchestrator

    if seed is not None:
        random.seed(seed)

    if candidate_tasks:
        easy_tasks = None
        fixed_candidates: Optional[List[str]] = list(candidate_tasks)
        print(f"Using manually specified candidate tasks ({len(fixed_candidates)}): {fixed_candidates}")
    else:
        easy_tasks = load_easy_tasks(task_analysis_path)
        fixed_candidates = None
        print(f"Loaded {len(easy_tasks)} easy tasks from {task_analysis_path}")

    orchestrator = BenchmarkOrchestrator(
        api_model=api_model,
        api_key=api_key,
        api_base_url=api_base_url,
        max_debate_rounds=max_debate_rounds,
        temperature_task_selector=temperature_task_selector,
        temperature_scene_designer=temperature_scene_designer,
        temperature_milestone=temperature_milestone,
        temperature_commonsense=temperature_commonsense,
        temperature_validator=temperature_validator,
        max_retries=max_retries,
        sandbox_tmp_dir=sandbox_tmp_dir,
        extremely_hard=extremely_hard,
        verbose=True,
    )

    benchmark_path = Path(benchmark_dir)
    benchmark_path.mkdir(parents=True, exist_ok=True)

    generated_dirs: List[str] = []
    attempted = 0
    max_attempts = num_samples * 5

    while len(generated_dirs) < num_samples and attempted < max_attempts:
        attempted += 1

        attempt_log_dir = benchmark_path / f"_tmp_attempt_{attempted:04d}"
        attempt_log_dir.mkdir(parents=True, exist_ok=True)

        if fixed_candidates is not None:
            _candidates = fixed_candidates
        else:
            _candidates = random.sample(easy_tasks, min(candidate_num, len(easy_tasks)))

        k = random.randint(k_min, k_max)
        print(f"\n{'='*60}")
        print(f"[Attempt {attempted}] candidates={len(_candidates)}, k={k}")
        print(f"  Candidates: {_candidates[:4]}{'...' if len(_candidates) > 4 else ''}")

        result = orchestrator.generate_sample(
            candidate_tasks=_candidates,
            k=k,
            sample_idx=attempted - 1,
            log_dir=str(attempt_log_dir),
        )

        if result is None:
            print("  [SKIP] Multi-agent workflow returned None.")
            shutil.rmtree(str(attempt_log_dir), ignore_errors=True)
            continue

        is_partial = result.get("partial", False)
        if is_partial:
            missing = []
            if result.get("scene_design") is None:
                missing.append("scene_design")
            if result.get("milestones") is None:
                missing.append("milestones")
            print(
                f"  [WARN] Multi-agent partial result (missing: {', '.join(missing)}); "
                f"saving conversation log to multi-agent folder."
            )

        out_dir = save_benchmark_sample(
            result,
            sample_idx=start_idx + len(generated_dirs),
            benchmark_dir=str(benchmark_path),
            mode="multi",
            tool_log_staging_dir=str(attempt_log_dir),
        )
        if out_dir is None:
            print("  [SKIP] save_benchmark_sample returned None.")
            shutil.rmtree(str(attempt_log_dir), ignore_errors=True)
            continue

        if is_partial:
            print(f"  [WARN] Partial result saved at {out_dir} (conversation log preserved).")
            continue

        generated_dirs.append(out_dir)
        print(f"  [OK] Generated {len(generated_dirs)}/{num_samples}")

    print(f"\nDone. Generated {len(generated_dirs)}/{num_samples} samples "
          f"({attempted} attempts).")
    return generated_dirs
