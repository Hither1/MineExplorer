#!/usr/bin/env python3
"""Replay a MineExplorer cell against a vLLM server, without Minecraft, and time each step.

  .venv/bin/python scripts/bench_agent_latency.py --base-url http://192.168.2.20:8004/v1 \
      --video outputs/c4h-hypothesis-vllm-0182/Qwen3.8-27B/4-hop/0182/episode.mp4 \
      --log outputs/log-c4h-default-vllm-0182.txt \
      --agent default --layout legacy --style full --concurrency 3 --steps 12

Each concurrent "cell" runs the real DefaultAgent/HypothesisAgent + VLLMProvider code path:
frames come from a recorded episode video (sliding or append-only window, per --layout, exactly
as eval_benchmark.py would hand them over), previous thoughts/actions from a recorded log, and
the memory the model wrote at the previous step is fed back, so the request is what a live cell
sends -- 20 images, ~5-8k tokens, a memory that changes every step -- and the reply is a real
200-460-token JSON. What is measured is the wall time of agent.get_action per step (the number
the campaign logs as its step time, minus the ~0.2 s env.step) plus, from the server's own
/metrics counters sampled before and after, prompt/generation tokens per request, TTFT,
prefix-cache hit rate and speculative-decoding acceptance during the run.

Run it against a server nobody else is using, or the numbers include the neighbours.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics as st
import sys
import threading
import time
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("AGENT_API_KEY", "bench")
os.environ.setdefault("AGENT_API_BASE", "bench")

import imageio.v3 as iio  # noqa: E402
import requests  # noqa: E402
from loguru import logger  # noqa: E402

from eval_benchmark import FRAME_BUFFER_SIZE, FRAME_WINDOW_REBASE  # noqa: E402
from mc_agent import DefaultAgent, DefaultContextBuilder, MinerRLActionSpace, VLLMProvider  # noqa: E402
from mc_agent.context import PROMPT_LAYOUTS, RESPONSE_STYLES  # noqa: E402
from mc_agent.hypothesis_agent import HypothesisAgent, HypothesisContextBuilder  # noqa: E402

TASK = ("Find the green banner landmark, then locate and find the dark oak button on the stone "
        "wall. Pass through the wall, mine the magma block, and bridge the lava gap.")


def _history_from_log(path: str, n: int) -> tuple[list[str], list[dict]]:
    """Previous thoughts/actions as a live cell would carry them, taken from a recorded cell's log."""
    txt = open(path, errors="replace").read()
    thoughts, actions = [], []
    for block in re.findall(r"Raw LLM response \(attempt \d\):\n(.*?)\n\d{4}-\d\d-\d\d", txt, re.S):
        m = re.search(r"\{.*\}", block, re.S)
        if not m:
            continue
        try:
            d = json.loads(m.group(0))
        except Exception:
            continue
        a = dict(d.get("action", {}))
        a.setdefault("camera", [0, 0])
        thoughts.append(str(d.get("thought", "")))
        actions.append(a)
        if len(thoughts) >= n:
            break
    if len(thoughts) < n:
        raise SystemExit(f"only {len(thoughts)} parsable responses in {path}, need {n}")
    return thoughts, actions


class _Metrics:
    """Deltas of the server's Prometheus counters over the bench window."""

    KEYS = ("vllm:prompt_tokens_total", "vllm:generation_tokens_total",
            "vllm:prefix_cache_queries_total", "vllm:prefix_cache_hits_total",
            "vllm:spec_decode_num_drafts_total", "vllm:spec_decode_num_draft_tokens_total",
            "vllm:spec_decode_num_accepted_tokens_total",
            "vllm:time_to_first_token_seconds_sum", "vllm:time_to_first_token_seconds_count",
            "vllm:e2e_request_latency_seconds_sum", "vllm:e2e_request_latency_seconds_count",
            "vllm:request_success_total")

    def __init__(self, root: str) -> None:
        self.root = root

    def snapshot(self) -> dict[str, float]:
        out = {k: 0.0 for k in self.KEYS}
        try:
            for line in requests.get(self.root + "/metrics", timeout=10).text.splitlines():
                if line.startswith("#"):
                    continue
                name = line.split("{")[0].split(" ")[0]
                if name in out:
                    out[name] += float(line.rsplit(" ", 1)[1])
        except Exception as e:  # metrics are a bonus, not the measurement
            logger.warning(f"/metrics unavailable: {e}")
        return out


def run_cell(cell_id: int, args, frames_all, thoughts_all, actions_all, results: dict) -> None:
    provider = VLLMProvider(model_name=args.model, base_url=args.base_url, temperature=0.7)
    if args.agent == "default":
        agent = DefaultAgent(MinerRLActionSpace(), provider, DefaultContextBuilder, args.model,
                             prompt_layout=args.layout, response_style=args.style)
    else:
        agent = HypothesisAgent(action_space=MinerRLActionSpace(), provider=provider,
                                context_builder_class=HypothesisContextBuilder, model=args.model,
                                prompt_layout=args.layout, response_style=args.style)
    agent.load_system_prompt(TASK)
    # Each cell starts at a different point of the recording so the requests are not identical
    # across cells (identical requests would share cache blocks and flatter the numbers).
    start = args.start_step + cell_id * 7
    buf: deque = deque() if args.layout == "append-only" else deque(maxlen=FRAME_BUFFER_SIZE)
    for k in range(max(0, start - FRAME_BUFFER_SIZE - 5), start):
        buf.append(frames_all[k])
        if args.layout == "append-only":
            while len(buf) >= FRAME_BUFFER_SIZE + FRAME_WINDOW_REBASE:
                for _ in range(FRAME_WINDOW_REBASE):
                    buf.popleft()
    memory = "" if args.agent == "hypothesis" else "Spawned on a stone path in a forest. Nothing found yet."
    lat, out_chars = [], []
    # What the model chose to re-emit (the compact style sends memory / hypotheses / plan only
    # when they change): per step, did the memory change, did the graph, did the plan.
    mem_changed, graph_changed, plan_changed = [], [], []
    for t in range(args.steps):
        step = start + t  # 1-indexed step number the agent believes it is at
        buf.append(frames_all[step - 1])
        if args.layout == "append-only":
            while len(buf) >= FRAME_BUFFER_SIZE + FRAME_WINDOW_REBASE:
                for _ in range(FRAME_WINDOW_REBASE):
                    buf.popleft()
        move = (f"You are {3.0 + 0.37 * step:.1f} blocks from spawn; your last action moved you "
                f"{0.2 + 0.1 * (step % 4):.1f} blocks.")
        graph_before = json.dumps(agent.graph.to_dict(), sort_keys=True) if hasattr(agent, "graph") else ""
        plan_before = list(getattr(agent, "current_plan", []))
        t0 = time.perf_counter()
        thought, action, memory_update = agent.get_action(
            list(buf), thoughts_all[:step - 1], actions_all[:step - 1], step,
            long_term_memory=memory,
            milestone_hint="The environment has not verified the task as complete yet.",
            camera_hint="pitch 0.0 (level)", movement_hint=move)
        dt = time.perf_counter() - t0
        lat.append(dt)
        out_chars.append(len(memory_update or "") + len(thought or ""))
        new_mem = memory_update.strip() if memory_update and memory_update.strip() else None
        mem_changed.append(new_mem is not None and new_mem != memory)
        if new_mem is not None:
            memory = new_mem
        if hasattr(agent, "graph"):
            graph_changed.append(json.dumps(agent.graph.to_dict(), sort_keys=True) != graph_before)
            plan_changed.append(list(agent.current_plan) != plan_before)
    results[cell_id] = {"latency": lat, "out_chars": out_chars, "mem_changed": mem_changed,
                        "graph_changed": graph_changed, "plan_changed": plan_changed}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True, help="e.g. http://192.168.2.20:8004/v1")
    ap.add_argument("--model", default="Qwen3.8-27B")
    ap.add_argument("--video", required=True, help="episode.mp4 of a recorded cell (frames)")
    ap.add_argument("--log", required=True, help="log-*.txt of a recorded cell (thoughts/actions)")
    ap.add_argument("--agent", choices=("default", "hypothesis"), default="default")
    ap.add_argument("--layout", choices=PROMPT_LAYOUTS, default="legacy")
    ap.add_argument("--style", choices=RESPONSE_STYLES, default="full")
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument("--steps", type=int, default=10)
    ap.add_argument("--start-step", type=int, default=40, help="cell 0 replays from this step")
    ap.add_argument("--warmup", type=int, default=1, help="leading steps per cell excluded from the stats")
    ap.add_argument("--quiet", action="store_true", help="silence the agents' per-step logging")
    args = ap.parse_args()
    if args.quiet:
        logger.remove()
        logger.add(sys.stderr, level="WARNING")

    n_needed = args.start_step + args.concurrency * 7 + args.steps + 2
    frames = [iio.imread(args.video, index=i) for i in range(n_needed)]
    thoughts, actions = _history_from_log(args.log, n_needed)
    metrics = _Metrics(args.base_url.rsplit("/v1", 1)[0])

    m0 = metrics.snapshot()
    t_start = time.perf_counter()
    results: dict = {}
    threads = [threading.Thread(target=run_cell, args=(c, args, frames, thoughts, actions, results))
               for c in range(args.concurrency)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    wall = time.perf_counter() - t_start
    m1 = metrics.snapshot()
    d = {k: m1[k] - m0[k] for k in m0}

    lat = [x for r in results.values() for x in r["latency"][args.warmup:]]
    if not lat:
        print("no steps measured")
        return 1
    lat_s = sorted(lat)
    p90 = lat_s[min(len(lat_s) - 1, int(0.9 * len(lat_s)))]
    n_req = d["vllm:request_success_total"] or float("nan")
    def _rate(key):
        xs = [x for r in results.values() for x in r[key][args.warmup:]]
        return f"{100 * sum(xs) / len(xs):.0f}%" if xs else "-"
    line = (f"{args.agent:10s} {args.layout:12s} {args.style:8s} conc={args.concurrency} steps={args.steps}: "
            f"step latency med={st.median(lat):.1f}s mean={st.mean(lat):.1f}s p90={p90:.1f}s "
            f"(n={len(lat)}, wall {wall:.0f}s); steps with memory/graph/plan change: "
            f"{_rate('mem_changed')}/{_rate('graph_changed')}/{_rate('plan_changed')}")
    if n_req == n_req:  # metrics available
        prompt = d["vllm:prompt_tokens_total"] / n_req
        gen = d["vllm:generation_tokens_total"] / n_req
        ttft = d["vllm:time_to_first_token_seconds_sum"] / max(1, d["vllm:time_to_first_token_seconds_count"])
        e2e = d["vllm:e2e_request_latency_seconds_sum"] / max(1, d["vllm:e2e_request_latency_seconds_count"])
        hit = 100 * d["vllm:prefix_cache_hits_total"] / max(1, d["vllm:prefix_cache_queries_total"])
        acc = d["vllm:spec_decode_num_accepted_tokens_total"] / max(1, d["vllm:spec_decode_num_drafts_total"])
        line += (f"\n{'':10s} server: {n_req:.0f} reqs, prompt {prompt:.0f} tok/req, gen {gen:.0f} tok/req, "
                 f"TTFT {ttft:.2f}s, e2e {e2e:.1f}s -> {gen / max(1e-9, e2e - ttft):.1f} tok/s decode/req, "
                 f"prefix hit {hit:.0f}%, MTP accepted {acc:.2f} tok/draft (+1 = {acc + 1:.2f} tok/iter)")
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
