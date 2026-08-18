#!/usr/bin/env python3
"""Check what --prompt-layout does to the request, without a Minecraft sandbox.

  .venv/bin/python scripts/prompt_layout_check.py --write-golden golden.json   # before a change
  .venv/bin/python scripts/prompt_layout_check.py --golden golden.json         # after: legacy unchanged?
  .venv/bin/python scripts/prompt_layout_check.py --tokenize-url http://192.168.2.20:8004

For a fixed synthetic episode it builds the default and hypothesis agents' messages at two
consecutive steps under every layout and reports (a) the sha256 of the legacy messages against a
golden file -- the layout option must not change the campaign arm's prompt by a byte -- and
(b) with --tokenize-url, how many leading tokens the two steps' text share, i.e. what the
server's prefix cache can reuse (approximate: text parts only, images dropped; the server's own
"Prefix cache hit rate" on a live smoke is the real number). Frame windows follow
eval_benchmark.py's policy for the layout (sliding 20 vs append-only 20-29).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("AGENT_API_KEY", "check")
os.environ.setdefault("AGENT_API_BASE", "check")

import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

logger.remove()  # the agents log the captured provider error at every call; not useful here

from eval_benchmark import FRAME_BUFFER_SIZE, FRAME_WINDOW_REBASE  # noqa: E402
from mc_agent import DefaultAgent, DefaultContextBuilder, MinerRLActionSpace  # noqa: E402
from mc_agent.context import PROMPT_LAYOUTS  # noqa: E402
from mc_agent.hypothesis_agent import HypothesisAgent, HypothesisContextBuilder  # noqa: E402


class _Capture:
    """A provider that records the messages and refuses to answer."""

    def chat(self, messages, **kwargs):
        self.messages = messages
        raise RuntimeError("captured")


def _frame(k: int) -> np.ndarray:
    a = np.zeros((360, 640, 3), dtype=np.uint8)
    a[:, :, 0] = (np.arange(640)[None, :] // 3 + k) % 256
    a[:, :, 1] = (np.arange(360)[:, None] // 2) % 256
    a[:, :, 2] = (k * 7) % 256
    return a


def _window(step: int, layout: str) -> list[np.ndarray]:
    """The frame buffer the runner would hand the agent at `step` (frame k = observation before step k)."""
    buf: deque = deque() if layout == "append-only" else deque(maxlen=FRAME_BUFFER_SIZE)
    for k in range(1, step + 1):
        buf.append(_frame(k))
        if layout == "append-only":
            while len(buf) >= FRAME_BUFFER_SIZE + FRAME_WINDOW_REBASE:
                for _ in range(FRAME_WINDOW_REBASE):
                    buf.popleft()
    return list(buf)


def _messages(kind: str, layout: str, step: int, memory: str, movement: str):
    provider = _Capture()
    if kind == "default":
        agent = DefaultAgent(MinerRLActionSpace(), provider, DefaultContextBuilder, "Qwen3.8-27B",
                             prompt_layout=layout)
    else:
        agent = HypothesisAgent(action_space=MinerRLActionSpace(), provider=provider,
                                context_builder_class=HypothesisContextBuilder, model="Qwen3.8-27B",
                                prompt_layout=layout)
        agent._apply_hypothesis_ops(json.dumps({
            "thought": "t", "action": {}, "memory_update": "m",
            "hypotheses": [{"id": "h1", "statement": "the banner is north of spawn", "confidence": 0.4,
                            "status": "active", "evidence": "saw green through the trees"}],
            "plan": ["go north", "look for the wall"]}), 5)
    agent.load_system_prompt("Find the green banner, then press the dark oak button.")
    thoughts = [f"thought {i + 1}: go {'left' if i % 2 else 'right'}" for i in range(step - 1)]
    actions = [{"forward": 1, "sprint": i % 2, "camera": [0, (i % 5) * 10]} for i in range(step - 1)]
    try:
        agent.get_action(_window(step, layout), thoughts, actions, step,
                         long_term_memory=memory,
                         milestone_hint="The environment has not verified the task as complete yet.",
                         camera_hint="pitch 0.0 (level)", movement_hint=movement)
    except Exception:
        pass
    return provider.messages


def _sha(messages) -> str:
    return hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()


def _text_tokens(url: str, messages) -> list[int]:
    import requests
    text_only = [{"role": "user", "content": [c for c in messages[0]["content"] if c["type"] == "text"]}]
    r = requests.post(url.rstrip("/") + "/tokenize",
                      json={"model": "Qwen3.8-27B", "messages": text_only, "add_generation_prompt": True},
                      timeout=60)
    r.raise_for_status()
    return r.json()["tokens"]


def _lcp(a: list[int], b: list[int]) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


CASES = [  # (kind, step) -- both sides of a rebase for append-only, and a plain mid-episode pair
    ("default", 25), ("hypothesis", 25), ("default", 45),
]
MEM = ("Spawned on a stone path. Green banner confirmed north-east. Button not found yet.",
       "Spawned on a stone path. Green banner confirmed north-east. Button not found yet. Step %d: wall ahead.")
MOVE = ("You are 3.1 blocks from spawn; your last action moved you 0.4 blocks.",
        "You are 3.5 blocks from spawn; your last action moved you 0.4 blocks.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-golden", help="write legacy sha256s + messages here")
    ap.add_argument("--golden", help="compare legacy sha256s against this file")
    ap.add_argument("--tokenize-url", help="server root, e.g. http://192.168.2.20:8004; measures shared prefix")
    args = ap.parse_args()

    legacy = {}
    for kind, step in CASES:
        for s in (step, step + 1):
            legacy[f"{kind}@{s}"] = _messages(kind, "legacy", s, MEM[0], MOVE[0])
    if args.write_golden:
        json.dump({k: {"sha256": _sha(v), "messages": v} for k, v in legacy.items()},
                  open(args.write_golden, "w"))
        print(f"golden written: {args.write_golden} ({len(legacy)} cases)")
    rc = 0
    if args.golden:
        gold = json.load(open(args.golden))
        for k, v in legacy.items():
            same = gold.get(k, {}).get("sha256") == _sha(v)
            print(f"golden {k}: {'IDENTICAL' if same else 'DIFFERENT'}")
            rc |= 0 if same else 1

    for layout in PROMPT_LAYOUTS:
        for kind, step in CASES:
            m1 = _messages(kind, layout, step, MEM[0], MOVE[0])
            m2 = _messages(kind, layout, step + 1, MEM[1] % (step + 1), MOVE[1])
            parts = [c["type"] for c in m2[0]["content"]]
            n_img = parts.count("image_url")
            line = (f"{layout:12s} {kind:10s} step {step}->{step + 1}: parts={len(parts)} images={n_img} "
                    f"first={parts[0]} last={parts[-1]}")
            if args.tokenize_url:
                t1, t2 = _text_tokens(args.tokenize_url, m1), _text_tokens(args.tokenize_url, m2)
                shared = _lcp(t1, t2)
                line += (f" | text tokens {len(t1)}->{len(t2)}, shared prefix {shared} "
                         f"({100 * shared / len(t2):.0f}%, ~{shared // 800} cache blocks of 800)")
            print(line)
    return rc


if __name__ == "__main__":
    sys.exit(main())
