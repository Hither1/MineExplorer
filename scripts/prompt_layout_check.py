#!/usr/bin/env python3
"""Check what --prompt-layout / --response-style do to the request, without a Minecraft sandbox.

  .venv/bin/python scripts/prompt_layout_check.py --write-golden golden.json   # before a change
  .venv/bin/python scripts/prompt_layout_check.py --golden golden.json         # after: legacy unchanged?
  .venv/bin/python scripts/prompt_layout_check.py --tokenize-url http://192.168.2.20:8004 [--codex]

For a fixed synthetic episode it builds the default and hypothesis agents' messages at two
consecutive steps under every layout and reports (a) the sha256 of the legacy messages against a
golden file -- neither option may change the campaign arm's (legacy/full) prompt by a byte -- and
(b) with --tokenize-url, how many leading tokens the two steps' text share, i.e. what the
server's prefix cache can reuse (--codex measures the same on the codex channel, whose provider
flattens the message list into one text prompt plus image files, so the layout survives but the
images leave the token stream) (approximate: text parts only, images dropped; the server's own
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
from mc_agent.context import PROMPT_LAYOUTS, RESPONSE_STYLES  # noqa: E402
from mc_agent.hypothesis_agent import HypothesisAgent, HypothesisContextBuilder  # noqa: E402
from mc_agent.llm_provider import CodexProvider  # noqa: E402


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


MODEL = "Qwen3.8-27B"  # a label on the agent object; nothing here calls a server with it


def _messages(kind: str, layout: str, step: int, memory: str, movement: str, style: str = "full"):
    provider = _Capture()
    if kind == "default":
        agent = DefaultAgent(MinerRLActionSpace(), provider, DefaultContextBuilder, MODEL,
                             prompt_layout=layout, response_style=style)
    else:
        agent = HypothesisAgent(action_space=MinerRLActionSpace(), provider=provider,
                                context_builder_class=HypothesisContextBuilder, model=MODEL,
                                prompt_layout=layout, response_style=style)
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


def _server_model(url: str) -> str:
    """Whichever checkpoint this server serves. /tokenize 404s on any other name, and the dev
    slot has served both Qwen3.8-27B and Qwen3.5-27B on the same port."""
    import requests
    cache = getattr(_server_model, "_cache", None)
    if cache is None:
        cache = _server_model._cache = {}
    key = url.rstrip("/")
    if key not in cache:
        r = requests.get(key + "/v1/models", timeout=10)
        r.raise_for_status()
        cache[key] = r.json()["data"][0]["id"]
    return cache[key]


def _text_tokens(url: str, messages) -> list[int]:
    import requests
    text_only = [{"role": "user", "content": [c for c in messages[0]["content"] if c["type"] == "text"]}]
    r = requests.post(url.rstrip("/") + "/tokenize",
                      json={"model": _server_model(url), "messages": text_only, "add_generation_prompt": True},
                      timeout=60)
    r.raise_for_status()
    return r.json()["tokens"]


def _prompt_tokens(url: str, prompt: str) -> list[int]:
    """Tokens of a raw text prompt (the codex channel sends text, not a message list)."""
    import requests
    r = requests.post(url.rstrip("/") + "/tokenize", json={"model": _server_model(url), "prompt": prompt}, timeout=60)
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
    ap.add_argument("--dump-dir", help="write each style's instruction block (default and hypothesis) here, to read")
    ap.add_argument("--codex", action="store_true",
                    help="with --tokenize-url: the same shared-prefix measurement on the codex channel's "
                         "flattened prompt (CodexProvider._flatten), which is what a default/hypothesis "
                         "x codex cell actually sends")
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

    if args.dump_dir:
        Path(args.dump_dir).mkdir(parents=True, exist_ok=True)
        for style in RESPONSE_STYLES:
            for kind in ("default", "hypothesis"):
                m = _messages(kind, "append-only", 25, MEM[0], MOVE[0], style)
                out = Path(args.dump_dir) / f"{kind}-{style}.txt"
                out.write_text("\n".join(c["text"] for c in m[0]["content"] if c["type"] == "text"))
                print(f"dumped {out}")

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
    if args.tokenize_url:
        for style in RESPONSE_STYLES:
            for kind in ("default", "hypothesis"):
                m = _messages(kind, "append-only", 25, MEM[0], MOVE[0], style)
                head = [{"role": "user", "content": [m[0]["content"][0]]}]
                print(f"style {style:8s} {kind:10s}: instruction block {len(_text_tokens(args.tokenize_url, head))} tokens")
    if args.codex and args.tokenize_url:
        import tempfile
        for style in RESPONSE_STYLES:
            for layout in PROMPT_LAYOUTS:
                for kind, step in (("default", 25), ("hypothesis", 25)):
                    m1 = _messages(kind, layout, step, MEM[0], MOVE[0], style)
                    m2 = _messages(kind, layout, step + 1, MEM[1] % (step + 1), MOVE[1], style)
                    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
                        p1, imgs = CodexProvider._flatten(m1, Path(d1))
                        p2, _ = CodexProvider._flatten(m2, Path(d2))
                    t1 = _prompt_tokens(args.tokenize_url, p1)
                    t2 = _prompt_tokens(args.tokenize_url, p2)
                    shared = _lcp(t1, t2)
                    print(f"codex {style:8s} {layout:12s} {kind:10s}: flattened {len(t1)} -> {len(t2)} tok "
                          f"({len(imgs)} images as files), shared prefix {shared} "
                          f"({100 * shared / len(t2):.0f}%, ~{shared // 800} blocks of 800)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
