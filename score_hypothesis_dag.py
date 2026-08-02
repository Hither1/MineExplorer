"""Score how well a HypothesisAgent episode's hypothesis DAG recovers the
hidden ground-truth dependency DAG of a multi-hop benchmark scene.

Each multi-hop scene's `metadata.json` carries a `reasoning_graph`: the
atomic (single-hop) tasks that were composed to build the scene, plus edges
saying which atomic task depends on / enables which other one (see
benchmark_gen's TaskSelectorAgent). This is the "hidden DAG" the agent never
sees directly - it only sees the composite task_text. A HypothesisAgent
episode instead saves its own self-authored `hypothesis_graph.json`
(mc_agent/hypothesis.py) built purely from what it observed in-episode.

This script asks an LLM judge to align the agent's hypothesis nodes to the
scene's ground-truth atomic tasks, then reports:
  - node_recall:  fraction of ground-truth atomic tasks the agent formed
                  *any* hypothesis about
  - edge_recall:  fraction of ground-truth dependency edges the agent's
                  own depends_on edges also captured (only counted when
                  both endpoints were matched)
  - confirmed_recall: same as node_recall but restricted to hypotheses the
                  agent itself marked "confirmed" (i.e. it believed it had
                  verified them, not just guessed)

Usage:
    python score_hypothesis_dag.py \\
        --results-dir results_hypothesis_multihop/Qwen3-VL-32B-Instruct \\
        --benchmark-dir benchmark_multihop_sample \\
        --model Qwen3-VL-32B-Instruct --use-vllm --vllm-url http://localhost:8001/v1

    # or against a hosted OpenAI-compatible judge (reads AGENT_API_KEY/AGENT_API_BASE):
    python score_hypothesis_dag.py \\
        --results-dir results_hypothesis_multihop/Qwen3-VL-32B-Instruct \\
        --benchmark-dir benchmark_multihop_sample \\
        --model gpt-5.2-chat
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

import typer
from loguru import logger

_ROOT_DIR = Path(__file__).resolve().parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.append(str(_ROOT_DIR))

from mc_agent import HypothesisGraph, OpenAIProvider, VLLMProvider, extract_json_from_response

app = typer.Typer(help="Score HypothesisAgent DAG recovery against ground-truth reasoning graphs")

JUDGE_PROMPT_TEMPLATE = """You are grading a Minecraft agent's self-authored belief graph against a
list of ground-truth subtasks it was never shown directly.

**Ground-truth atomic tasks** (numbered, this is what the composite task was actually built from):
{gt_list}

**Agent's hypotheses** (id, status, confidence, statement - authored turn-by-turn during the episode):
{hyp_list}

For each ground-truth atomic task, decide whether ANY agent hypothesis is clearly about that same
real-world object/action (e.g. ground-truth "find wheat" matches a hypothesis stating "there is a
wheat field to the southwest" or "I found the wheat crops"). A match requires the hypothesis to be
about the same concrete target, not just a vague thematic overlap. If several hypotheses could match,
pick the single best one (highest confidence / most specific). If none match, use null.

Respond with ONLY a JSON object, no other text:
{{
  "matches": [
    {{"atomic_task": "<exact ground-truth task string>", "hypothesis_id": "<id or null>", "reason": "<one short sentence>"}}
  ]
}}
"""


def _format_gt_list(nodes: list[str]) -> str:
    return "\n".join(f"{i + 1}. {n}" for i, n in enumerate(nodes))


def _format_hyp_list(graph: HypothesisGraph) -> str:
    if not graph.nodes:
        return "(agent proposed no hypotheses at all)"
    lines = []
    for n in graph.nodes.values():
        lines.append(f"- [{n.id}] (status={n.status}, confidence={n.confidence:.2f}) {n.statement}")
    return "\n".join(lines)


def judge_matches(
    provider, model: str, gt_nodes: list[str], graph: HypothesisGraph
) -> dict[str, Optional[str]]:
    """Returns {ground_truth_task_string: hypothesis_id or None}."""
    if not gt_nodes:
        return {}
    if not graph.nodes:
        return {n: None for n in gt_nodes}

    prompt = JUDGE_PROMPT_TEMPLATE.format(
        gt_list=_format_gt_list(gt_nodes),
        hyp_list=_format_hyp_list(graph),
    )
    messages = [{"role": "user", "content": prompt}]

    raw = provider.chat(messages, model=model, temperature=0.0)
    try:
        parsed = extract_json_from_response(raw)
    except Exception:
        # extract_json_from_response expects "action"/"thought" keys for one
        # of its fast paths; fall back to a bare ```json``` / brace scan.
        m = re.search(r"```json\s*(.*?)```", raw, re.DOTALL) or re.search(r"(\{.*\})", raw, re.DOTALL)
        if not m:
            logger.warning(f"[judge] could not parse judge response, treating all as unmatched:\n{raw}")
            return {n: None for n in gt_nodes}
        parsed = json.loads(m.group(1))

    valid_ids = set(graph.nodes.keys())
    result: dict[str, Optional[str]] = {n: None for n in gt_nodes}
    for m in parsed.get("matches", []) or []:
        task = m.get("atomic_task")
        hid = m.get("hypothesis_id")
        if task in result and hid in valid_ids:
            result[task] = hid
    return result


def score_scene(
    gt: dict[str, Any], graph: HypothesisGraph, matches: dict[str, Optional[str]]
) -> dict[str, Any]:
    gt_nodes: list[str] = gt.get("nodes", []) or []
    gt_edges: list[dict] = gt.get("edges", []) or []

    matched_count = sum(1 for v in matches.values() if v)
    node_recall = matched_count / len(gt_nodes) if gt_nodes else None

    confirmed_ids = {n.id for n in graph.nodes.values() if n.status == "confirmed"}
    confirmed_count = sum(1 for v in matches.values() if v and v in confirmed_ids)
    confirmed_recall = confirmed_count / len(gt_nodes) if gt_nodes else None

    scoreable_edges = 0
    recovered_edges = 0
    edge_details = []
    for e in gt_edges:
        parent_task, child_task = e.get("from"), e.get("to")
        parent_hid, child_hid = matches.get(parent_task), matches.get(child_task)
        if not parent_hid or not child_hid:
            edge_details.append({
                "from": parent_task, "to": child_task, "scoreable": False, "recovered": False,
            })
            continue
        scoreable_edges += 1
        child_node = graph.nodes.get(child_hid)
        recovered = bool(child_node and parent_hid in child_node.depends_on)
        recovered_edges += int(recovered)
        edge_details.append({
            "from": parent_task, "to": child_task, "scoreable": True, "recovered": recovered,
            "matched_from_id": parent_hid, "matched_to_id": child_hid,
        })

    edge_recall = recovered_edges / scoreable_edges if scoreable_edges else None

    return {
        "n_gt_nodes": len(gt_nodes),
        "n_gt_edges": len(gt_edges),
        "n_hypotheses": len(graph.nodes),
        "matched_nodes": matched_count,
        "node_recall": node_recall,
        "confirmed_recall": confirmed_recall,
        "scoreable_edges": scoreable_edges,
        "recovered_edges": recovered_edges,
        "edge_recall": edge_recall,
        "matches": matches,
        "edge_details": edge_details,
    }


@app.command()
def run(
    results_dir: str = typer.Option(..., "--results-dir", "-r",
                                    help="Root of one model's eval_benchmark.py output "
                                         "(contains <N>-hop/<scene_id>/hypothesis_graph.json)"),
    benchmark_dir: str = typer.Option(..., "--benchmark-dir", "-b",
                                      help="Benchmark dir whose scene metadata.json files hold "
                                           "the ground-truth reasoning_graph"),
    model: str = typer.Option(..., "--model", "-m", help="Judge LLM model name"),
    use_vllm: bool = typer.Option(False, "--use-vllm", help="Use a local vLLM server as judge"),
    vllm_url: str = typer.Option("http://localhost:8000/v1", "--vllm-url"),
    output: str = typer.Option(None, "--output", "-o",
                               help="Where to write the aggregate report JSON "
                                    "(default: <results-dir>/dag_recovery_report.json)"),
):
    """Score every scene under results_dir that has a hypothesis_graph.json."""
    import os

    if use_vllm:
        provider = VLLMProvider(model_name=model, base_url=vllm_url, temperature=0.0)
    else:
        api_key = os.getenv("AGENT_API_KEY", "")
        api_base = os.getenv("AGENT_API_BASE", "")
        if not api_key or not api_base:
            raise ValueError("AGENT_API_KEY / AGENT_API_BASE must be set (or pass --use-vllm)")
        provider = OpenAIProvider(api_key, api_base, model, temperature=0.0)

    results_path = Path(results_dir)
    bench_path = Path(benchmark_dir)

    hyp_paths = sorted(results_path.glob("*-hop/*/hypothesis_graph.json"))
    if not hyp_paths:
        logger.warning(f"No hypothesis_graph.json found under {results_path}")
        return

    per_scene = []
    for hyp_path in hyp_paths:
        scene_id = hyp_path.parent.name
        hop_folder = hyp_path.parent.parent.name
        meta_path = bench_path / scene_id / "multi-agent" / "metadata.json"
        if not meta_path.exists():
            logger.warning(f"[{scene_id}] no metadata.json under {bench_path}, skipping")
            continue

        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        gt = metadata.get("reasoning_graph", {}) or {}
        graph = HypothesisGraph.load(hyp_path)

        logger.info(f"[{scene_id}] judging {len(graph.nodes)} hypotheses against "
                    f"{len(gt.get('nodes', []))} ground-truth atomic tasks...")
        matches = judge_matches(provider, model, gt.get("nodes", []) or [], graph)
        scored = score_scene(gt, graph, matches)
        scored["scene_id"] = scene_id
        scored["hop_folder"] = hop_folder
        scored["task_text"] = metadata.get("task_text", "")
        per_scene.append(scored)

        logger.success(
            f"[{scene_id}] node_recall={scored['node_recall']} "
            f"edge_recall={scored['edge_recall']} "
            f"confirmed_recall={scored['confirmed_recall']}"
        )

    def _avg(key: str) -> Optional[float]:
        vals = [s[key] for s in per_scene if s.get(key) is not None]
        return sum(vals) / len(vals) if vals else None

    summary = {
        "results_dir": str(results_path),
        "benchmark_dir": str(bench_path),
        "judge_model": model,
        "n_scenes": len(per_scene),
        "avg_node_recall": _avg("node_recall"),
        "avg_edge_recall": _avg("edge_recall"),
        "avg_confirmed_recall": _avg("confirmed_recall"),
        "scenes": per_scene,
    }

    out_path = Path(output) if output else results_path / "dag_recovery_report.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.success(
        f"Aggregate: node_recall={summary['avg_node_recall']} "
        f"edge_recall={summary['avg_edge_recall']} "
        f"confirmed_recall={summary['avg_confirmed_recall']} "
        f"over {summary['n_scenes']} scene(s) -> {out_path}"
    )


if __name__ == "__main__":
    app()
