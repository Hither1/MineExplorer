from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_BENCHMARK_GEN = _SCRIPT_DIR / "benchmark_gen"

if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

DEFAULT_API_KEY = os.getenv("AGENT_API_KEY", "")
DEFAULT_API_BASE = os.getenv("AGENT_API_BASE", "https://aigc.sankuai.com/v1/openai/native")

TASK_ANALYSIS_PATH = _BENCHMARK_GEN / "task_analysis.json"
BENCHMARK_DIR = _SCRIPT_DIR / "benchmark"


def _next_start_idx(benchmark_dir: str) -> int:
    """Return the next available folder index in benchmark_dir.

    Scans for directories whose names are zero-padded 4-digit numbers
    (e.g. 0000, 0001, ...) and returns max_existing + 1, or 0 if none found.
    """
    p = Path(benchmark_dir)
    if not p.exists():
        return 0
    existing = [
        int(d.name)
        for d in p.iterdir()
        if d.is_dir() and d.name.isdigit() and len(d.name) == 4
    ]
    return max(existing) + 1 if existing else 0


def _worker_single(worker_args: dict) -> str | None:
    """Picklable worker for parallel single-agent generation.

    Generates exactly ONE sample at the given index and returns the output
    directory path, or None if generation failed.  Each worker runs in its
    own subprocess so there is no shared state between workers.
    """
    import sys
    from pathlib import Path as _Path

    _SCRIPT_DIR = _Path(__file__).resolve().parent
    if str(_SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPT_DIR))

    from benchmark_gen.llm_client import LLMClient
    from benchmark_gen import single_agent

    llm = LLMClient(
        api_key=worker_args["api_key"],
        base_url=worker_args["api_base"],
        model=worker_args["model"],
        batch_size=1,
    )

    # generate() with num_samples=1 returns a list of at most 1 path
    results = single_agent.generate(
        llm=llm,
        task_analysis_path=worker_args["task_analysis_path"],
        benchmark_dir=worker_args["benchmark_dir"],
        num_samples=1,
        candidate_num=worker_args["candidate_num"],
        k_min=worker_args["k_min"],
        k_max=worker_args["k_max"],
        temperature=worker_args["temperature"],
        max_new_tokens=worker_args["max_new_tokens"],
        max_retries=worker_args["max_retries"],
        seed=worker_args["seed"],
        render_preview=worker_args["render_preview"],
        candidate_tasks=worker_args["candidate_tasks"],
        start_idx=worker_args["sample_idx"],
    )
    return results[0] if results else None


def cmd_single(args: argparse.Namespace) -> None:
    from benchmark_gen.llm_client import LLMClient
    from benchmark_gen import single_agent

    api_key = DEFAULT_API_KEY
    api_base = DEFAULT_API_BASE
    if not api_key:
        print("[ERROR] AGENT_API_KEY not set.")
        sys.exit(1)

    task_analysis_path = args.task_analysis or str(TASK_ANALYSIS_PATH)
    benchmark_dir = args.output or str(BENCHMARK_DIR)
    candidate_tasks = list(args.candidate_tasks) if args.candidate_tasks else None
    num_workers = getattr(args, "num_workers", 1)

    start_idx = _next_start_idx(benchmark_dir) if getattr(args, "resume", False) else 0
    if args.resume:
        print(f"[single] --resume: continuing from index {start_idx:04d}")

    print(f"[single] model={args.model}  samples={args.num_samples}  "
          f"output={benchmark_dir}  num_workers={num_workers}")
    if candidate_tasks:
        print(f"[single] fixed candidate tasks: {candidate_tasks}")

    if num_workers <= 1:

        llm = LLMClient(api_key=api_key, base_url=api_base, model=args.model, batch_size=1)
        generated = single_agent.generate(
            llm=llm,
            task_analysis_path=task_analysis_path,
            benchmark_dir=benchmark_dir,
            num_samples=args.num_samples,
            candidate_num=args.candidate_num,
            k_min=args.k_min,
            k_max=args.k_max,
            temperature=args.temperature,
            max_new_tokens=args.max_new_tokens,
            max_retries=args.max_retries,
            seed=args.seed,
            render_preview=args.render_preview,
            candidate_tasks=candidate_tasks,
            start_idx=start_idx,
        )
    else:

        # each worker generates exactly 1 sample at a pre-assigned index.
        # The main process waits for the whole batch to finish before starting
        # the next batch, so index assignment is always conflict-free.
        effective_workers = min(num_workers, args.num_samples)
        mp_ctx = __import__("multiprocessing").get_context("spawn")

        generated: list = []
        next_idx = start_idx
        remaining = args.num_samples
        batch_num = 0

        base_job = {
            "api_key": api_key,
            "api_base": api_base,
            "model": args.model,
            "task_analysis_path": task_analysis_path,
            "benchmark_dir": benchmark_dir,
            "candidate_num": args.candidate_num,
            "k_min": args.k_min,
            "k_max": args.k_max,
            "temperature": args.temperature,
            "max_new_tokens": args.max_new_tokens,
            "max_retries": args.max_retries,
            "render_preview": args.render_preview,
            "candidate_tasks": candidate_tasks,
        }

        while remaining > 0:
            batch_size = min(effective_workers, remaining)
            batch_num += 1
            print(f"\n[single] Batch {batch_num}: launching {batch_size} worker(s) "
                  f"for indices {next_idx:04d}~{next_idx + batch_size - 1:04d} ...")

            batch_jobs = []
            for i in range(batch_size):
                job = dict(base_job)
                job["sample_idx"] = next_idx + i
                job["seed"] = (args.seed + next_idx + i) if args.seed is not None else None
                batch_jobs.append(job)

            with ProcessPoolExecutor(max_workers=batch_size, mp_context=mp_ctx) as pool:
                futures = {pool.submit(_worker_single, job): job["sample_idx"]
                           for job in batch_jobs}
                for future in as_completed(futures):
                    idx = futures[future]
                    try:
                        result = future.result()
                        if result is not None:
                            generated.append(result)
                            print(f"  [OK] index={idx:04d}  →  {result}")
                        else:
                            print(f"  [FAIL] index={idx:04d}  generation returned None")
                    except Exception as exc:
                        print(f"  [ERROR] index={idx:04d}  {exc}")

            # Advance past ALL reserved slots (successful or not) so the next
            # batch always uses fresh indices that don't overlap with this batch.
            next_idx += batch_size
            remaining -= batch_size

    print(f"\nGenerated {len(generated)} sample(s).")


def _worker_multi(worker_args: dict) -> str | None:
    """Picklable worker for parallel multi-agent generation.

    Generates exactly ONE sample at the given index.
    Returns the output directory path, or None on failure.
    """
    import sys
    from pathlib import Path as _Path

    _SCRIPT_DIR = _Path(__file__).resolve().parent
    if str(_SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPT_DIR))

    from benchmark_gen import multi_agent

    results = multi_agent.generate(
        api_model=worker_args["api_model"],
        api_key=worker_args["api_key"],
        api_base_url=worker_args["api_base_url"],
        task_analysis_path=worker_args["task_analysis_path"],
        benchmark_dir=worker_args["benchmark_dir"],
        num_samples=1,
        candidate_num=worker_args["candidate_num"],
        k_min=worker_args["k_min"],
        k_max=worker_args["k_max"],
        max_debate_rounds=worker_args["max_debate_rounds"],
        max_retries=worker_args["max_retries"],
        seed=worker_args["seed"],
        candidate_tasks=worker_args["candidate_tasks"],
        render_preview=worker_args["render_preview"],
        sandbox_tmp_dir=worker_args["sandbox_tmp_dir"],
        start_idx=worker_args["sample_idx"],
    )
    return results[0] if results else None


def cmd_multi(args: argparse.Namespace) -> None:
    from benchmark_gen import multi_agent

    api_key = DEFAULT_API_KEY
    api_base = DEFAULT_API_BASE
    if not api_key:
        print("[ERROR] AGENT_API_KEY not set.")
        sys.exit(1)

    # Strip provider prefixes (openai/, litellm/, azure/) — orchestrator expects bare name
    model = args.model
    for prefix in ("openai/", "litellm/", "azure/"):
        if model.startswith(prefix):
            model = model[len(prefix):]
            break

    task_analysis_path = args.task_analysis or str(TASK_ANALYSIS_PATH)
    benchmark_dir = args.output or str(BENCHMARK_DIR)
    candidate_tasks = list(args.candidate_tasks) if args.candidate_tasks else None
    num_workers = getattr(args, "num_workers", 1)

    start_idx = _next_start_idx(benchmark_dir) if getattr(args, "resume", False) else 0
    if args.resume:
        print(f"[multi] --resume: continuing from index {start_idx:04d}")

    print(f"[multi] model={model}  samples={args.num_samples}  "
          f"output={benchmark_dir}  num_workers={num_workers}")

    if num_workers <= 1:

        generated = multi_agent.generate(
            api_model=model,
            api_key=api_key,
            api_base_url=api_base,
            task_analysis_path=task_analysis_path,
            benchmark_dir=benchmark_dir,
            num_samples=args.num_samples,
            candidate_num=args.candidate_num,
            k_min=args.k_min,
            k_max=args.k_max,
            max_debate_rounds=args.max_debate_rounds,
            max_retries=args.max_retries,
            seed=args.seed,
            candidate_tasks=candidate_tasks,
            render_preview=args.render_preview,
            sandbox_tmp_dir=args.sandbox_tmp_dir,
            start_idx=start_idx,
        )
    else:

        effective_workers = min(num_workers, args.num_samples)
        mp_ctx = __import__("multiprocessing").get_context("spawn")

        generated: list = []
        next_idx = start_idx
        remaining = args.num_samples
        batch_num = 0

        base_job = {
            "api_model": model,
            "api_key": api_key,
            "api_base_url": api_base,
            "task_analysis_path": task_analysis_path,
            "benchmark_dir": benchmark_dir,
            "candidate_num": args.candidate_num,
            "k_min": args.k_min,
            "k_max": args.k_max,
            "max_debate_rounds": args.max_debate_rounds,
            "max_retries": args.max_retries,
            "candidate_tasks": candidate_tasks,
            "render_preview": args.render_preview,
        }

        while remaining > 0:
            batch_size = min(effective_workers, remaining)
            batch_num += 1
            print(f"\n[multi] Batch {batch_num}: launching {batch_size} worker(s) "
                  f"for indices {next_idx:04d}~{next_idx + batch_size - 1:04d} ...")

            batch_jobs = []
            for i in range(batch_size):
                job = dict(base_job)
                job["sample_idx"] = next_idx + i
                job["seed"] = (args.seed + next_idx + i) if args.seed is not None else None
                # Each worker gets its own sandbox_tmp_dir to avoid screenshot collisions.
                job["sandbox_tmp_dir"] = f"{args.sandbox_tmp_dir}_b{batch_num}_w{i}"
                batch_jobs.append(job)

            with ProcessPoolExecutor(max_workers=batch_size, mp_context=mp_ctx) as pool:
                futures = {pool.submit(_worker_multi, job): job["sample_idx"]
                           for job in batch_jobs}
                for future in as_completed(futures):
                    idx = futures[future]
                    try:
                        result = future.result()
                        if result is not None:
                            generated.append(result)
                            print(f"  [OK] index={idx:04d}  →  {result}")
                        else:
                            print(f"  [FAIL] index={idx:04d}  generation returned None")
                    except Exception as exc:
                        print(f"  [ERROR] index={idx:04d}  {exc}")

            next_idx += batch_size
            remaining -= batch_size

    print(f"\nGenerated {len(generated)} sample(s).")


def _worker_both(worker_args: dict) -> tuple | None:
    """Picklable worker for parallel both-mode generation.

    Generates exactly ONE (single, multi) pair at the given index.
    Returns (single_dir, multi_dir) on success, or None on failure.
    """
    import random
    import shutil
    import sys
    from pathlib import Path as _Path

    _SCRIPT_DIR = _Path(__file__).resolve().parent
    if str(_SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPT_DIR))

    from benchmark_gen.llm_client import LLMClient
    from benchmark_gen import single_agent
    from benchmark_gen.utils import save_benchmark_sample
    from benchmark_gen.orchestrator import BenchmarkOrchestrator

    api_key = worker_args["api_key"]
    api_base = worker_args["api_base"]
    multi_model = worker_args["multi_model"]
    single_model = worker_args["single_model"]
    task_analysis_path = worker_args["task_analysis_path"]
    benchmark_dir = worker_args["benchmark_dir"]
    sample_idx = worker_args["sample_idx"]
    candidate_num = worker_args["candidate_num"]
    k_min = worker_args["k_min"]
    k_max = worker_args["k_max"]
    temperature = worker_args["temperature"]
    max_new_tokens = worker_args["max_new_tokens"]
    max_debate_rounds = worker_args["max_debate_rounds"]
    max_retries = worker_args["max_retries"]
    seed = worker_args["seed"]
    fixed_candidates = worker_args["candidate_tasks"]
    render_preview = worker_args["render_preview"]
    sandbox_tmp_dir = worker_args["sandbox_tmp_dir"]

    if seed is not None:
        random.seed(seed)

    if fixed_candidates:
        easy_tasks = fixed_candidates
    else:
        easy_tasks = single_agent.load_easy_tasks(task_analysis_path)

    system_prompt = single_agent.load_prompt("bench_system")
    single_round_prompt = single_agent.load_prompt("bench_single_round")

    llm = LLMClient(api_key=api_key, base_url=api_base, model=single_model, batch_size=1)
    orchestrator = BenchmarkOrchestrator(
        api_model=multi_model,
        api_key=api_key,
        api_base_url=api_base,
        max_debate_rounds=max_debate_rounds,
        max_retries=max_retries,
        sandbox_tmp_dir=sandbox_tmp_dir,
        verbose=True,
    )

    benchmark_path = _Path(benchmark_dir)
    benchmark_path.mkdir(parents=True, exist_ok=True)
    fallback_dir = str(benchmark_path / "_fallback")

    # Retry loop: try up to max_retries*10 times to get one successful pair.
    max_attempts = max_retries * 10
    for attempt in range(1, max_attempts + 1):
        if fixed_candidates:
            _candidates = fixed_candidates
            k = len(fixed_candidates)
        else:
            _candidates = random.sample(easy_tasks, min(candidate_num, len(easy_tasks)))
            k = random.randint(k_min, k_max)

        single_result = single_agent.run_single_turn(
            llm=llm,
            candidate_tasks=_candidates,
            k=k,
            system_prompt=system_prompt,
            single_round_prompt=single_round_prompt,
            sample_idx=attempt - 1,
            fallback_dir=fallback_dir,
            temperature=temperature,
            max_new_tokens=max_new_tokens,
            max_retries=max_retries,
        )
        if single_result is None or single_result.get("scene_design") is None \
                or single_result.get("milestones") is None:
            continue

        single_dir = save_benchmark_sample(
            single_result,
            sample_idx=sample_idx,
            benchmark_dir=benchmark_dir,
            mode="single",
            render_preview=render_preview,
        )
        if single_dir is None:
            continue

        attempt_log_dir = benchmark_path / f"_tmp_attempt_{attempt:04d}_idx{sample_idx}"
        attempt_log_dir.mkdir(parents=True, exist_ok=True)

        multi_result = orchestrator.generate_sample(
            candidate_tasks=_candidates,
            k=k,
            sample_idx=attempt - 1,
            log_dir=str(attempt_log_dir),
        )
        if multi_result is None:
            shutil.rmtree(str(attempt_log_dir), ignore_errors=True)
            continue

        is_partial = multi_result.get("partial", False)
        multi_dir = save_benchmark_sample(
            multi_result,
            sample_idx=sample_idx,
            benchmark_dir=benchmark_dir,
            mode="multi",
            tool_log_staging_dir=str(attempt_log_dir),
            render_preview=render_preview if not is_partial else False,
        )
        if multi_dir is None or is_partial:
            shutil.rmtree(str(attempt_log_dir), ignore_errors=True)
            continue

        return (single_dir, multi_dir)

    return None


def cmd_both(args: argparse.Namespace) -> None:
    """Run single then multi **on the same candidate list** for each sample.

    For each index we:
      1. Draw one candidate task list (and k value) at random.
      2. Run the single-agent dialogue on that candidate list.
      3. Run the multi-agent debate on the *same* candidate list.
    Both results are saved under the same index directory:
      benchmark/0000/single-agent/
      benchmark/0000/multi-agent/
    This ensures a fair, controlled comparison between the two modes.
    """
    import random
    import shutil
    from pathlib import Path as _Path

    from benchmark_gen.llm_client import LLMClient
    from benchmark_gen import single_agent, multi_agent
    from benchmark_gen.utils import save_benchmark_sample

    api_key = DEFAULT_API_KEY
    api_base = DEFAULT_API_BASE
    if not api_key:
        print("[ERROR] AGENT_API_KEY not set.")
        sys.exit(1)

    # Strip provider prefixes for multi-agent orchestrator
    multi_model = args.model
    for prefix in ("openai/", "litellm/", "azure/"):
        if multi_model.startswith(prefix):
            multi_model = multi_model[len(prefix):]
            break

    task_analysis_path = args.task_analysis or str(TASK_ANALYSIS_PATH)
    benchmark_dir = args.output or str(BENCHMARK_DIR)
    fixed_candidates = list(args.candidate_tasks) if args.candidate_tasks else None
    num_workers = getattr(args, "num_workers", 1)

    start_idx = _next_start_idx(benchmark_dir) if getattr(args, "resume", False) else 0
    if args.resume:
        print(f"[both] --resume: continuing from index {start_idx:04d}")

    print(f"[both] model={args.model}  samples={args.num_samples}  "
          f"output={benchmark_dir}  num_workers={num_workers}")

    if num_workers <= 1:

        llm = LLMClient(api_key=api_key, base_url=api_base, model=args.model, batch_size=1)

        if args.seed is not None:
            random.seed(args.seed)

        if fixed_candidates:
            easy_tasks = fixed_candidates
            print(f"[both] fixed candidate tasks ({len(fixed_candidates)}): {fixed_candidates}")
        else:
            easy_tasks = single_agent.load_easy_tasks(task_analysis_path)
            print(f"[both] loaded {len(easy_tasks)} easy tasks from {task_analysis_path}")

        system_prompt = single_agent.load_prompt("bench_system")
        single_round_prompt = single_agent.load_prompt("bench_single_round")

        from benchmark_gen.orchestrator import BenchmarkOrchestrator
        orchestrator = BenchmarkOrchestrator(
            api_model=multi_model,
            api_key=api_key,
            api_base_url=api_base,
            max_debate_rounds=args.max_debate_rounds,
            max_retries=args.max_retries,
            sandbox_tmp_dir=args.sandbox_tmp_dir,
            verbose=True,
        )

        benchmark_path = _Path(benchmark_dir)
        benchmark_path.mkdir(parents=True, exist_ok=True)
        fallback_dir = str(benchmark_path / "_fallback")

        generated: list = []
        attempted = 0
        next_idx = start_idx
        max_attempts = args.num_samples * 10

        while len(generated) < args.num_samples and attempted < max_attempts:
            attempted += 1
            global_idx = next_idx

            if fixed_candidates:
                _candidates = fixed_candidates
                k = len(fixed_candidates)
            else:
                _candidates = random.sample(easy_tasks, min(args.candidate_num, len(easy_tasks)))
                k = random.randint(args.k_min, args.k_max)

            print(f"\n{'='*60}")
            print(f"[both][Attempt {attempted}] index={global_idx:04d}  "
                  f"candidates={len(_candidates)}, k={k}")
            print(f"  Candidates: {_candidates}")

            print(f"\n  --- single-agent ---")
            single_result = single_agent.run_single_turn(
                llm=llm,
                candidate_tasks=_candidates,
                k=k,
                system_prompt=system_prompt,
                single_round_prompt=single_round_prompt,
                sample_idx=attempted - 1,
                fallback_dir=fallback_dir,
                temperature=args.temperature,
                max_new_tokens=args.max_new_tokens,
                max_retries=args.max_retries,
            )
            if single_result is None or single_result.get("scene_design") is None \
                    or single_result.get("milestones") is None:
                print("  [SKIP] Single-agent failed, skipping this attempt entirely.")
                continue

            single_dir = save_benchmark_sample(
                single_result,
                sample_idx=global_idx,
                benchmark_dir=benchmark_dir,
                mode="single",
                render_preview=args.render_preview,
            )
            if single_dir is None:
                print("  [SKIP] Saving single-agent result failed, skipping this attempt.")
                continue

            next_idx += 1
            print(f"  [OK] single-agent saved: {single_dir}")

            print(f"\n  --- multi-agent ---")
            attempt_log_dir = benchmark_path / f"_tmp_attempt_{attempted:04d}"
            attempt_log_dir.mkdir(parents=True, exist_ok=True)

            multi_result = orchestrator.generate_sample(
                candidate_tasks=_candidates,
                k=k,
                sample_idx=attempted - 1,
                log_dir=str(attempt_log_dir),
            )
            if multi_result is None:
                print(f"  [WARN] Multi-agent returned None; single-agent result already saved at {single_dir}.")
                shutil.rmtree(str(attempt_log_dir), ignore_errors=True)
                continue

            is_partial = multi_result.get("partial", False)
            if is_partial:
                missing = []
                if multi_result.get("scene_design") is None:
                    missing.append("scene_design")
                if multi_result.get("milestones") is None:
                    missing.append("milestones")
                print(
                    f"  [WARN] Multi-agent partial result (missing: {', '.join(missing)}); "
                    f"saving conversation log to multi-agent folder."
                )

            multi_dir = save_benchmark_sample(
                multi_result,
                sample_idx=global_idx,
                benchmark_dir=benchmark_dir,
                mode="multi",
                tool_log_staging_dir=str(attempt_log_dir),
                render_preview=args.render_preview if not is_partial else False,
            )
            if multi_dir is None:
                print(f"  [WARN] Saving multi-agent result failed; single already saved at {single_dir}.")
                shutil.rmtree(str(attempt_log_dir), ignore_errors=True)
                continue

            if is_partial:
                print(f"  [WARN] Multi-agent partial result saved at {multi_dir} (single: {single_dir}).")
                continue

            generated.append((single_dir, multi_dir))
            print(f"\n  [OK] {len(generated)}/{args.num_samples} pairs generated.")

    else:

        effective_workers = min(num_workers, args.num_samples)
        mp_ctx = __import__("multiprocessing").get_context("spawn")

        generated: list = []
        next_idx = start_idx
        remaining = args.num_samples
        batch_num = 0

        base_job = {
            "api_key": api_key,
            "api_base": api_base,
            "multi_model": multi_model,
            "single_model": args.model,
            "task_analysis_path": task_analysis_path,
            "benchmark_dir": benchmark_dir,
            "candidate_num": args.candidate_num,
            "k_min": args.k_min,
            "k_max": args.k_max,
            "temperature": args.temperature,
            "max_new_tokens": args.max_new_tokens,
            "max_debate_rounds": args.max_debate_rounds,
            "max_retries": args.max_retries,
            "candidate_tasks": fixed_candidates,
            "render_preview": args.render_preview,
        }

        while remaining > 0:
            batch_size = min(effective_workers, remaining)
            batch_num += 1
            print(f"\n[both] Batch {batch_num}: launching {batch_size} worker(s) "
                  f"for indices {next_idx:04d}~{next_idx + batch_size - 1:04d} ...")

            batch_jobs = []
            for i in range(batch_size):
                job = dict(base_job)
                job["sample_idx"] = next_idx + i
                job["seed"] = (args.seed + next_idx + i) if args.seed is not None else None
                job["sandbox_tmp_dir"] = f"{args.sandbox_tmp_dir}_b{batch_num}_w{i}"
                batch_jobs.append(job)

            with ProcessPoolExecutor(max_workers=batch_size, mp_context=mp_ctx) as pool:
                futures = {pool.submit(_worker_both, job): job["sample_idx"]
                           for job in batch_jobs}
                for future in as_completed(futures):
                    idx = futures[future]
                    try:
                        result = future.result()
                        if result is not None:
                            generated.append(result)
                            print(f"  [OK] index={idx:04d}  single={result[0]}  multi={result[1]}")
                        else:
                            print(f"  [FAIL] index={idx:04d}  generation returned None")
                    except Exception as exc:
                        print(f"  [ERROR] index={idx:04d}  {exc}")

            next_idx += batch_size
            remaining -= batch_size

    print(f"\nDone. Generated {len(generated)}/{args.num_samples} pairs.")
    for i, pair in enumerate(generated):
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            s, m = pair
            print(f"  [{i:04d}] single: {s}")
            print(f"  [{i:04d}]  multi: {m}")


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", required=True,
                        help="LLM model name (required, e.g. aws.claude-opus-4.6).")
    parser.add_argument("--num-samples", type=int, default=5,
                        help="Number of benchmark samples to generate.")
    parser.add_argument("--candidate-num", type=int, default=8,
                        help="Candidate tasks to draw per sample.")
    parser.add_argument("--k-min", type=int, default=2,
                        help="Min atomic tasks per sample.")
    parser.add_argument("--k-max", type=int, default=4,
                        help="Max atomic tasks per sample.")
    parser.add_argument("--max-retries", type=int, default=2,
                        help="Max JSON parse retries.")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed.")
    parser.add_argument("--task-analysis", default=None,
                        help=f"Path to task_analysis.json (default: {TASK_ANALYSIS_PATH}).")
    parser.add_argument("--output", default=None,
                        help=f"Output directory (default: {BENCHMARK_DIR}).")
    parser.add_argument("--render-preview", action="store_true", default=False,
                        help="Capture a scene_preview.png from the sandbox after generation.")
    parser.add_argument("--resume", action="store_true", default=False,
                        help=(
                            "Resume generation: scan the output directory for existing "
                            "zero-padded folders (0000, 0001, …) and start numbering "
                            "from max+1.  E.g. if 0000 and 0001 already exist, the next "
                            "sample will be saved as 0002."
                        ))
    parser.add_argument("--num-workers", type=int, default=1,
                        help=(
                            "Number of parallel worker processes for generation.  "
                            "Each worker runs independently so there are no conflicts "
                            "between instances.  Default 1 = sequential."
                        ))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python generate_benchmark.py",
        description="Generate Minecraft multi-hop benchmark scenarios.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    # single
    p_single = subparsers.add_parser("single", help="Single-agent dialogue (fast).",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    _add_common_args(p_single)
    p_single.add_argument("--temperature", type=float, default=0.8)
    p_single.add_argument("--max-new-tokens", type=int, default=4096)
    p_single.add_argument("--candidate-tasks", nargs="+", default=None,
                          help="Manually specify candidate task names (skips random sampling).")

    # multi
    p_multi = subparsers.add_parser("multi", help="Multi-agent AutoGen debate (higher quality).",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    _add_common_args(p_multi)
    p_multi.add_argument("--max-debate-rounds", type=int, default=2,
                         help="Debate rounds after initial generation.")
    p_multi.add_argument("--candidate-tasks", nargs="+", default=None,
                         help="Manually specify candidate task names.")
    p_multi.add_argument("--sandbox-tmp-dir", default="/tmp/benchmark_gen_sandbox",
                         help="Temp directory for sandbox screenshots.")

    # both
    p_both = subparsers.add_parser("both", help="Run single then multi on the same candidates.",
                                   formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    _add_common_args(p_both)
    p_both.add_argument("--temperature", type=float, default=0.8)
    p_both.add_argument("--max-new-tokens", type=int, default=4096)
    p_both.add_argument("--max-debate-rounds", type=int, default=2,
                        help="Debate rounds after initial generation.")
    p_both.add_argument("--candidate-tasks", nargs="+", default=None,
                        help="Manually specify candidate task names.")
    p_both.add_argument("--sandbox-tmp-dir", default="/tmp/benchmark_gen_sandbox",
                        help="Temp directory for sandbox screenshots.")

    args = parser.parse_args()
    if args.mode == "single":
        cmd_single(args)
    elif args.mode == "multi":
        cmd_multi(args)
    elif args.mode == "both":
        cmd_both(args)


if __name__ == "__main__":
    main()
