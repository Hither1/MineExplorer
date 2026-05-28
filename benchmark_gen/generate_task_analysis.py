"""
benchmark_gen/generate_task_analysis.py

Batch-analyse atomic Minecraft tasks via a 3-round LLM conversation and
produce a structured task_analysis.json used by the benchmark generator.

Each task entry records:
  {
    "requires_domain_knowledge": "Yes" | "No",
    "domain_knowledge_description": "<text>" | null,
    "capabilities": {
      "perception": [...],
      "reasoning": [...],
      "action": [...]
    }
  }

The three rounds:
  Round 1  – Yes/No: does the task require Minecraft-specific domain knowledge?
  Round 2  – If Yes, describe the domain knowledge. Otherwise output "None".
  Round 3  – Determine the minimal capability set (JSON).
              Retried up to --max-retry-rounds times on parse failure.

Usage (from the minecraft/ directory):
  python benchmark_gen/generate_task_analysis.py \\
      --model openai/Doubao-Seed-2.0-pro \\
      --batch-size 8 \\
      --resume

  The --model flag is required (no default).
  API credentials are read from environment variables:
    AGENT_API_KEY   – API key (required)
    AGENT_API_BASE  – base URL (optional, has built-in fallback)
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import random
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from tqdm import tqdm

# ---------------------------------------------------------------------------
# Path bootstrap – allow running as script or as a package member
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent   # benchmark_gen/
_MINECRAFT_DIR = _SCRIPT_DIR.parent             # minecraft/

if str(_MINECRAFT_DIR) not in sys.path:
    sys.path.insert(0, str(_MINECRAFT_DIR))

# ---------------------------------------------------------------------------
# Default paths / settings
# ---------------------------------------------------------------------------
DEFAULT_API_KEY  = os.getenv("AGENT_API_KEY", "")
DEFAULT_API_BASE = os.getenv("AGENT_API_BASE", "https://aigc.sankuai.com/v1/openai/native")

PROMPTS_DIR      = _SCRIPT_DIR / "prompts"
TASK_LIST_PATH   = _SCRIPT_DIR / "atomic_task_list.txt"
DEFAULT_OUTPUT   = _SCRIPT_DIR / "task_analysis.json"
DEFAULT_FALLBACK = _SCRIPT_DIR / "fallback"

VALID_PERCEPTION = {
    "spatial_perception", "temporal_perception", "entity_perception",
    "state_perception", "inventory_perception",
}
VALID_REASONING = {"common_sense_reasoning", "causal_reasoning", "relational_reasoning"}
VALID_ACTION    = {"move", "jump", "collect", "place", "craft", "attack"}


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _load_file(path: Path | str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _load_tasks(path: Path | str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def _load_prompts(prompts_dir: Path | str) -> Dict[str, str]:
    names = [
        "system",
        "round1_domain_knowledge",
        "round2_domain_description",
        "round3_capabilities",
        "round3_retry",
    ]
    return {name: _load_file(Path(prompts_dir) / f"{name}.txt") for name in names}


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _strip_thinking(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _extract_json(text: str) -> Optional[dict]:
    text = _strip_thinking(text)
    match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    raw = match.group(1) if match else text
    raw = raw.strip()
    if not raw.startswith("{"):
        start = raw.find("{")
        if start == -1:
            return None
        raw = raw[start:]
    end = raw.rfind("}")
    if end == -1:
        return None
    raw = raw[: end + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _parse_yes_no(text: str) -> str:
    text = _strip_thinking(text).strip().lower()
    if "yes" in text:
        return "Yes"
    return "No"


def _validate_capabilities(data: dict) -> Optional[Dict[str, List[str]]]:
    if not isinstance(data, dict):
        return None
    return {
        "perception": [v for v in data.get("perception", []) if v in VALID_PERCEPTION],
        "reasoning":  [v for v in data.get("reasoning",  []) if v in VALID_REASONING],
        "action":     [v for v in data.get("action",     []) if v in VALID_ACTION],
    }


# ---------------------------------------------------------------------------
# Fallback helpers
# ---------------------------------------------------------------------------

def _clear_fallback_dir(fallback_dir: Path) -> None:
    if not fallback_dir.is_dir():
        return
    removed = 0
    for p in fallback_dir.glob("*.json"):
        p.unlink()
        removed += 1
    if removed:
        print(f"Cleared {removed} .json files from {fallback_dir}")


def _task_to_filename(task: str) -> str:
    name = re.sub(r"[^a-z0-9]+", "_", task.strip().lower()).strip("_")
    return name + ".json"


def _save_fallback(fallback_dir: Path, task: str, round_label: str, outputs: List[str]) -> None:
    fallback_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "task": task,
        "failed_at": round_label,
        "attempts": outputs,
    }
    out_path = fallback_dir / _task_to_filename(task)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Core generation loop
# ---------------------------------------------------------------------------

def generate_analyses(
    model: Any,
    tasks: List[str],
    prompts: Dict[str, str],
    output_path: Path,
    fallback_dir: Path,
    temperature: float = 0.3,
    max_new_tokens: int = 1024,
    batch_size: int = 16,
    max_retry_rounds: int = 2,
    existing_results: Optional[Dict[str, Any]] = None,
    capabilities_only: bool = False,
) -> Dict[str, Any]:
    all_results: Dict[str, Any] = dict(existing_results) if existing_results else {}
    fallback_count = 0
    total = len(tasks)

    for start in tqdm(range(0, total, batch_size), desc="Generating task analyses"):
        batch_tasks = tasks[start : start + batch_size]

        if capabilities_only:
            # ── capabilities-only mode: skip Round 1 & 2, reuse existing fields ──
            r1_results = {task: all_results.get(task, {}).get("requires_domain_knowledge", "No") for task in batch_tasks}
            r2_results = {task: all_results.get(task, {}).get("domain_knowledge_description", None) for task in batch_tasks}
        else:
            # ── Round 1: Yes / No ─────────────────────────────────────────────
            convs_r1 = [
                [
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user",   "content": prompts["round1_domain_knowledge"].replace("{task}", task)},
                ]
                for task in batch_tasks
            ]
            responses_r1 = model.chat(convs_r1, temperature=temperature, max_new_tokens=max_new_tokens)

            r1_results: Dict[str, str] = {}
            r1_convs:   Dict[str, List[Dict]] = {}
            for task, conv, resp in zip(batch_tasks, convs_r1, responses_r1):
                yn = _parse_yes_no(resp)
                r1_results[task] = yn
                r1_convs[task] = list(conv) + [{"role": "assistant", "content": resp}]

            # ── Round 2: domain knowledge description ─────────────────────────
            convs_r2 = [
                list(r1_convs[task]) + [{"role": "user", "content": prompts["round2_domain_description"]}]
                for task in batch_tasks
            ]
            responses_r2 = model.chat(convs_r2, temperature=temperature, max_new_tokens=max_new_tokens)

            r2_results: Dict[str, Optional[str]] = {}
            r2_convs:   Dict[str, List[Dict]] = {}
            for task, conv, resp in zip(batch_tasks, convs_r2, responses_r2):
                cleaned = _strip_thinking(resp).strip()
                if r1_results[task] == "No" or cleaned.lower() == "none":
                    r2_results[task] = None
                else:
                    r2_results[task] = cleaned
                r2_convs[task] = list(conv) + [{"role": "assistant", "content": resp}]

        # ── Round 3: capabilities JSON (with retry) ────────────────────────
        # Round 3 starts a fresh conversation – it does NOT see Round 1/2 context
        # (no domain-knowledge signal), so it infers capabilities independently.
        convs_r3 = [
            [
                {"role": "system", "content": prompts["system"]},
                {"role": "user",   "content": f"Task: {task}\n\n{prompts['round3_capabilities']}"},
            ]
            for task in batch_tasks
        ]
        responses_r3 = model.chat(convs_r3, temperature=temperature, max_new_tokens=max_new_tokens)

        pending_tasks:   List[str]        = []
        pending_convs:   List[List[Dict]] = []
        pending_outputs: Dict[str, List[str]] = {}

        for task, conv, resp in zip(batch_tasks, convs_r3, responses_r3):
            parsed = _extract_json(resp)
            caps   = _validate_capabilities(parsed) if parsed else None
            if caps is not None:
                all_results[task] = {
                    "requires_domain_knowledge":    r1_results[task],
                    "domain_knowledge_description": r2_results[task],
                    "capabilities":                 caps,
                }
            else:
                retry_conv = list(conv) + [
                    {"role": "assistant", "content": resp},
                    {"role": "user",      "content": prompts["round3_retry"]},
                ]
                pending_tasks.append(task)
                pending_convs.append(retry_conv)
                pending_outputs[task] = [resp]

        for _ in range(max_retry_rounds):
            if not pending_tasks:
                break
            retry_responses = model.chat(pending_convs, temperature=temperature, max_new_tokens=max_new_tokens)
            next_tasks:  List[str]        = []
            next_convs:  List[List[Dict]] = []
            for task, conv, resp in zip(pending_tasks, pending_convs, retry_responses):
                parsed = _extract_json(resp)
                caps   = _validate_capabilities(parsed) if parsed else None
                if caps is not None:
                    all_results[task] = {
                        "requires_domain_knowledge":    r1_results[task],
                        "domain_knowledge_description": r2_results[task],
                        "capabilities":                 caps,
                    }
                else:
                    next_convs.append(
                        list(conv) + [
                            {"role": "assistant", "content": resp},
                            {"role": "user",      "content": prompts["round3_retry"]},
                        ]
                    )
                    next_tasks.append(task)
                    pending_outputs.setdefault(task, []).append(resp)
            pending_tasks = next_tasks
            pending_convs = next_convs

        for task in pending_tasks:
            fallback_count += 1
            _save_fallback(fallback_dir, task, "Round 3 (capabilities JSON)", pending_outputs.get(task, []))

        # Save after every batch
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        tqdm.write(
            f"  Batch {min(start + len(batch_tasks), total)}/{total}: "
            f"{len(all_results)} succeeded, {fallback_count} failed"
        )

    if fallback_count:
        print(f"\n{fallback_count} tasks failed (Round 3) → saved to {fallback_dir}")

    return all_results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python benchmark_gen/generate_task_analysis.py",
        description="Generate task_analysis.json via 3-round LLM conversation.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="LLM model name, e.g. openai/Doubao-Seed-2.0-pro (required, no default).",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=DEFAULT_API_KEY,
        help="API key (falls back to AGENT_API_KEY env var).",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=DEFAULT_API_BASE,
        help="API base URL (falls back to AGENT_API_BASE env var).",
    )
    parser.add_argument(
        "--task-list",
        type=str,
        default=str(TASK_LIST_PATH),
        help="Path to atomic_task_list.txt.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_OUTPUT),
        help="Output JSON path.",
    )
    parser.add_argument(
        "--fallback-dir",
        type=str,
        default=str(DEFAULT_FALLBACK),
        help="Directory to store failed-task fallback JSON files.",
    )
    parser.add_argument(
        "--prompts-dir",
        type=str,
        default=str(PROMPTS_DIR),
        help="Directory containing prompt .txt files.",
    )
    parser.add_argument("--temperature",      type=float, default=0.3)
    parser.add_argument("--max-new-tokens",   type=int,   default=1024)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1,
        help="Number of tasks processed in parallel per batch.",
    )
    parser.add_argument(
        "--max-retry-rounds",
        type=int,
        default=2,
        help="Max Round-3 retry attempts before writing to fallback.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Per-request timeout in seconds.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="Max HTTP retries per LLM request.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=False,
        help="Resume from existing output: skip already-completed tasks.",
    )
    parser.add_argument(
        "--capabilities-only",
        action="store_true",
        default=False,
        help=(
            "Only regenerate the 'capabilities' field (Round 3). "
            "Rounds 1 & 2 are skipped and the existing "
            "'requires_domain_knowledge' / 'domain_knowledge_description' "
            "values are preserved from the current output file."
        ),
    )
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Validate API key
    # ------------------------------------------------------------------
    api_key = args.api_key or os.getenv("AGENT_API_KEY", "")
    if not api_key:
        print("[ERROR] API key not set. Use --api-key or set AGENT_API_KEY env var.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Load tasks
    # ------------------------------------------------------------------
    tasks = _load_tasks(args.task_list)
    random.shuffle(tasks)
    print(f"Loaded {len(tasks)} tasks from {args.task_list} (shuffled)")

    prompts = _load_prompts(args.prompts_dir)
    print(f"Loaded {len(prompts)} prompt files from {args.prompts_dir}")

    output_path  = Path(args.output)
    fallback_dir = Path(args.fallback_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Resume or fresh start
    # ------------------------------------------------------------------
    existing_results: Dict[str, Any] = {}
    if args.capabilities_only:
        if not output_path.is_file():
            print(f"[ERROR] --capabilities-only requires an existing output file: {output_path}")
            sys.exit(1)
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing_results = json.load(f)
            print(
                f"[capabilities-only] Loaded {len(existing_results)} existing results from {output_path}\n"
                f"[capabilities-only] Will regenerate 'capabilities' for all tasks; "
                "'requires_domain_knowledge' and 'domain_knowledge_description' are kept as-is."
            )
        except (json.JSONDecodeError, OSError) as e:
            print(f"[ERROR] Could not load existing output ({e}).")
            sys.exit(1)
        # Do NOT skip tasks – regenerate capabilities for every task in the list.
    elif args.resume and output_path.is_file():
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing_results = json.load(f)
            print(f"[resume] Loaded {len(existing_results)} existing results from {output_path}")
        except (json.JSONDecodeError, OSError) as e:
            print(f"[resume] Warning: could not load existing output ({e}), starting fresh")
            existing_results = {}
        tasks = [t for t in tasks if t not in existing_results]
        print(f"[resume] {len(tasks)} tasks remaining (skipping {len(existing_results)} already done)")
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2, ensure_ascii=False)
        print(f"Cleared output file: {output_path}")
        _clear_fallback_dir(fallback_dir)

    fallback_dir.mkdir(parents=True, exist_ok=True)
    print(f"Fallback directory: {fallback_dir}")

    if not tasks:
        print("No tasks to process. All tasks are already completed.")
        return

    # ------------------------------------------------------------------
    # Build LLM client (same as generate.py / multi_agent.py)
    # ------------------------------------------------------------------
    from benchmark_gen.llm_client import LLMClient

    model = LLMClient(
        api_key=api_key,
        base_url=args.base_url,
        model=args.model,
        batch_size=args.batch_size,
        timeout=args.timeout,
        max_retries=args.max_retries,
    )
    print(
        f"Using LLMClient: model={args.model}  base_url={args.base_url}  "
        f"batch_size={args.batch_size}"
    )

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------
    results = generate_analyses(
        model=model,
        tasks=tasks,
        prompts=prompts,
        output_path=output_path,
        fallback_dir=fallback_dir,
        temperature=args.temperature,
        max_new_tokens=args.max_new_tokens,
        batch_size=args.batch_size,
        max_retry_rounds=args.max_retry_rounds,
        existing_results=existing_results,
        capabilities_only=args.capabilities_only,
    )

    print(f"\nDone. {len(results)} tasks succeeded.")
    print(f"Results saved to {output_path}")


if __name__ == "__main__":
    main()
