from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

from .llm_client import LLMClient
from .utils import (
    extract_json_object,
    validate_scene_design,
    validate_reasoning_graph,
    validate_milestones,
    save_fallback_response,
    save_benchmark_sample,
)

BENCHMARK_GEN_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = BENCHMARK_GEN_DIR / "prompts"


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.txt"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_easy_tasks(task_analysis_path: str) -> List[str]:
    """Return all atomic task names where requires_domain_knowledge == 'No'."""
    with open(task_analysis_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [
        task for task, info in data.items()
        if info.get("requires_domain_knowledge") == "No"
    ]


def _validate_full_response(data: Optional[Dict[str, Any]], expected_k: int) -> bool:
    """Return True if the single-turn response contains all required fields."""
    if not isinstance(data, dict):
        return False
    selected = data.get("selected_tasks")
    if not isinstance(selected, list) or len(selected) != expected_k:
        return False
    if not validate_scene_design({
        "scene_name": data.get("scene_name"),
        "scene_description": data.get("scene_description"),
        "task_text": data.get("task_text"),
        "atomic_tasks_ordered": data.get("atomic_tasks_ordered"),
        "commands": data.get("commands"),
        "design_notes": data.get("design_notes"),
    }):
        return False
    if not validate_reasoning_graph(data.get("reasoning_graph")):
        return False
    ordered = data.get("atomic_tasks_ordered", selected)
    if not validate_milestones({"milestones": data.get("milestones")}, ordered):
        return False
    return True


def run_single_turn(
    llm: LLMClient,
    candidate_tasks: List[str],
    k: int,
    system_prompt: str,
    single_round_prompt: str,
    sample_idx: int = 0,
    fallback_dir: Optional[str] = None,
    temperature: float = 0.7,
    max_new_tokens: int = 8192,
    max_retries: int = 2,
) -> Optional[Dict[str, Any]]:
    """Send one LLM turn and parse full benchmark JSON. Returns result dict or None."""
    candidate_list_str = "\n".join(
        f"  {i + 1}. {t}" for i, t in enumerate(candidate_tasks)
    )
    user_content = (
        single_round_prompt
        .replace("{candidate_num}", str(len(candidate_tasks)))
        .replace("{k}", str(k))
        .replace("{candidate_list}", candidate_list_str)
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    resp = llm.chat([messages], temperature=temperature, max_new_tokens=max_new_tokens)[0]
    data = extract_json_object(resp)

    retry_messages = list(messages) + [{"role": "assistant", "content": resp}]
    for attempt in range(max_retries):
        if _validate_full_response(data, k):
            break
        print(f"  [Single-turn] JSON validation failed (attempt {attempt + 1}/{max_retries})")
        if fallback_dir:
            save_fallback_response(
                fallback_dir, sample_idx, "single_round",
                resp, attempt + 1, "validate_full_response failed",
            )
        retry_prompt = (
            "Your previous response could not be fully validated. "
            "Output ONLY a single raw JSON object — first character { last character }. "
            "No markdown, no code fences. "
            f"The JSON must have exactly these top-level keys: "
            "selected_tasks (list of exactly {k} task strings), "
            "selection_reasoning, scene_name, scene_description, task_text, "
            "atomic_tasks_ordered (list of exactly {k} strings), commands, design_notes, "
            "reasoning_graph (with nodes and edges), "
            "milestones (list of exactly {k} milestone objects each with task, milestone_id, description, rules)."
        ).replace("{k}", str(k))
        retry_messages.append({"role": "user", "content": retry_prompt})
        resp = llm.chat([retry_messages], temperature=0.3, max_new_tokens=max_new_tokens)[0]
        data = extract_json_object(resp)
        retry_messages.append({"role": "assistant", "content": resp})

    if not _validate_full_response(data, k):
        print("  [Single-turn] FAILED — could not parse full response JSON after retries.")
        if fallback_dir:
            save_fallback_response(
                fallback_dir, sample_idx, "single_round",
                resp, max_retries + 1, "validate_full_response failed after all retries",
            )
        return None

    ordered_tasks = data.get("atomic_tasks_ordered", data["selected_tasks"])

    scene_design = {
        "scene_name":           data.get("scene_name"),
        "scene_description":    data.get("scene_description"),
        "task_text":            data.get("task_text"),
        "atomic_tasks_ordered": ordered_tasks,
        "commands":             data.get("commands"),
        "design_notes":         data.get("design_notes"),
    }
    reasoning_graph = data.get("reasoning_graph")
    milestones = {"milestones": data.get("milestones")}

    print(
        f"  [Single-turn] Scene: {scene_design.get('scene_name', '?')} "
        f"— {len(scene_design.get('commands', []))} commands, "
        f"{len(milestones.get('milestones', []))} milestones"
    )

    return {
        "selected_tasks":      data["selected_tasks"],
        "selection_reasoning": data.get("selection_reasoning", ""),
        "scene_design":        scene_design,
        "reasoning_graph":     reasoning_graph,
        "milestones":          milestones,
    }


def generate(
    llm: LLMClient,
    task_analysis_path: str,
    benchmark_dir: str,
    num_samples: int = 5,
    candidate_num: int = 8,
    k_min: int = 2,
    k_max: int = 4,
    temperature: float = 0.8,
    max_new_tokens: int = 8192,
    max_retries: int = 2,
    seed: Optional[int] = None,
    candidate_tasks: Optional[List[str]] = None,
    start_idx: int = 0,
) -> List[str]:
    """Generate num_samples samples in single-agent (single-turn) mode.
    Returns a list of output directory paths.
    """
    if seed is not None:
        random.seed(seed)

    system_prompt = load_prompt("bench_system")
    single_round_prompt = load_prompt("bench_single_round")

    fixed_candidates: Optional[List[str]] = list(candidate_tasks) if candidate_tasks else None
    if fixed_candidates:
        easy_tasks = fixed_candidates
        print(f"Using manually specified candidate tasks ({len(fixed_candidates)}): {fixed_candidates}")
    else:
        easy_tasks = load_easy_tasks(task_analysis_path)
        print(f"Loaded {len(easy_tasks)} easy tasks from {task_analysis_path}")

    fallback_dir = str(Path(benchmark_dir) / "_fallback")

    generated_dirs: List[str] = []
    attempted = 0
    max_attempts = num_samples * 5

    while len(generated_dirs) < num_samples and attempted < max_attempts:
        attempted += 1
        if fixed_candidates:
            _candidates = fixed_candidates
            k = len(fixed_candidates)
        else:
            _candidates = random.sample(easy_tasks, min(candidate_num, len(easy_tasks)))
            k = random.randint(k_min, k_max)
        print(f"\n{'='*60}")
        print(f"[Attempt {attempted}] candidates={len(_candidates)}, k={k}")

        result = run_single_turn(
            llm=llm,
            candidate_tasks=_candidates,
            k=k,
            system_prompt=system_prompt,
            single_round_prompt=single_round_prompt,
            sample_idx=attempted - 1,
            fallback_dir=fallback_dir,
            temperature=temperature,
            max_new_tokens=max_new_tokens,
            max_retries=max_retries,
        )

        if result is None:
            print("  [SKIP] Single-turn generation returned None.")
            continue
        if result.get("scene_design") is None:
            print("  [SKIP] No valid scene design produced.")
            continue
        if result.get("milestones") is None:
            print("  [SKIP] No valid milestones produced.")
            continue

        out_dir = save_benchmark_sample(
            result,
            sample_idx=start_idx + len(generated_dirs),
            benchmark_dir=benchmark_dir,
            mode="single",
        )
        if out_dir is None:
            continue

        generated_dirs.append(out_dir)
        print(f"  [OK] Generated {len(generated_dirs)}/{num_samples}")

    print(f"\nDone. Generated {len(generated_dirs)}/{num_samples} samples "
          f"({attempted} attempts).")
    return generated_dirs
