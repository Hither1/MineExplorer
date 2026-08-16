"""Ask a model server whether it can actually do what a run needs of it.

Not "is the port open" -- that question has already been answered wrongly twice here,
once by a stranger's process and once by a server holding a different model. This asks
the server to produce text, to look at a real Minecraft frame, to accept the Responses
API request shape the Codex CLI sends, and then -- because these three change what a
score means rather than whether one exists -- to show its per-request output cap, its
decode rate, and whether thinking is on in the request shape the codex arms send. It
prints what came back so the answers can be judged rather than trusted.

Usage: check_model_server.py <base-url> [--model M] [--frame path.png]
                             [--expect-cap 4096] [--min-decode 30]
Exit code is non-zero if any probe fails.
"""
from __future__ import annotations

import argparse
import base64
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

DEFAULT_FRAME = pathlib.Path(__file__).resolve().parent.parent / "artifacts"


def post(url: str, payload: dict, timeout: int = 300) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer EMPTY"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def find_frame() -> pathlib.Path | None:
    """Any real episode frame beats a synthetic image: a solid-colour square can be
    'described' by a model that never looked at it."""
    hits = sorted(DEFAULT_FRAME.glob("runs/*/results/*/*/*/prolong_workspace/frames/step_*.png"))
    return hits[len(hits) // 2] if hits else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base_url")
    ap.add_argument("--model", default=None)
    ap.add_argument("--frame", default=None)
    ap.add_argument("--expect-cap", type=int, default=4096,
                    help="per-request output cap the server should enforce")
    ap.add_argument("--min-decode", type=float, default=30.0,
                    help="tok/s the serving configuration is expected to reach")
    args = ap.parse_args()
    base = args.base_url.rstrip("/")
    failures = []

    # 1. identity
    try:
        with urllib.request.urlopen(f"{base}/models", timeout=60) as r:
            served = json.load(r)["data"][0]["id"]
        print(f"[ok]   serving: {served}")
        if args.model and served != args.model:
            failures.append(f"serves {served!r}, expected {args.model!r}")
    except Exception as e:
        print(f"[FAIL] /models: {e}")
        return 1
    model = args.model or served

    # 2. text
    try:
        d = post(f"{base}/chat/completions", {
            "model": model, "max_tokens": 400,
            "messages": [{"role": "user", "content": "Reply with the single word OK."}]})
        text = d["choices"][0]["message"]["content"]
        print(f"[ok]   chat/completions: {text.strip()[-80:]!r} "
              f"({d.get('usage', {}).get('completion_tokens')} tokens)")
    except Exception as e:
        print(f"[FAIL] chat/completions: {e}")
        failures.append("text generation")

    # 3. vision, on a frame from a real episode
    frame = pathlib.Path(args.frame) if args.frame else find_frame()
    if frame and frame.exists():
        try:
            b64 = base64.b64encode(frame.read_bytes()).decode()
            d = post(f"{base}/chat/completions", {
                "model": model, "max_tokens": 400,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": "In one short sentence, what is in this image?"},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/png;base64,{b64}"}}]}]})
            text = d["choices"][0]["message"]["content"].strip()
            print(f"[ok]   vision ({frame.name}): {text[-160:]!r}")
        except Exception as e:
            print(f"[FAIL] vision: {e}")
            failures.append("image input")
    else:
        print("[warn] no episode frame found; vision not probed")

    # 4. the Responses shape codex sends: content blocks, not a bare string
    try:
        d = post(f"{base}/responses", {
            "model": model, "max_output_tokens": 400,
            "input": [{"role": "user", "content": [
                {"type": "input_text", "text": "Reply with the single word OK."}]}]})
        out = "".join(c.get("text", "")
                      for item in d.get("output", []) if item.get("type") == "message"
                      for c in item.get("content", []))
        print(f"[ok]   responses: {out.strip()[-80:]!r}")
        # sglang's implementation echoed the content blocks back as literal dicts;
        # that is a pass on status and a failure in substance, so look at the text.
        if "input_text" in out or "'type':" in out:
            marker = "input_text" if "input_text" in out else "'type':"
            i = out.index(marker)
            failures.append(
                f"responses echoed its own input structure back, near: "
                f"{out[max(0, i - 60):i + 60]!r}")
    except Exception as e:
        print(f"[FAIL] responses: {e}")
        failures.append("responses API")

    # 5. the output cap and the decode rate, from one request.
    # Asking for far more than the cap and refusing EOS makes the server show its own
    # ceiling: vLLM takes a min over --override-generation-config, so a correct server
    # stops at exactly the cap with finish_reason "length". The same request times the
    # decode, since the prompt is short enough that prefill is noise. Eager served 12.5
    # tok/s per request here, which is what truncated the one-call-per-step arms at
    # walltime; cudagraphs are the fix and this is the number that says whether they took.
    # Asked in three forms because a server that rejects one field would otherwise look
    # like a server without a cap: a 400 on `ignore_eos` or on an over-long max_tokens is
    # a protocol difference, not an answer about the ceiling.
    attempts = [
        {"max_tokens": 100000, "ignore_eos": True},
        {"max_tokens": args.expect_cap * 2, "ignore_eos": True},
        {"max_tokens": args.expect_cap * 2},
    ]
    try:
        d, elapsed, asked = None, 0.0, attempts[0]["max_tokens"]
        for i, extra in enumerate(attempts):
            try:
                t0 = time.monotonic()
                d = post(f"{base}/chat/completions", dict(
                    extra, model=model, temperature=0.7,
                    messages=[{"role": "user",
                               "content": "Count upward from one, in words."}]))
                elapsed, asked = time.monotonic() - t0, extra["max_tokens"]
                if i:
                    print(f"[warn] cap probe fell back to {extra}; the server refused "
                          f"the stricter form")
                break
            except urllib.error.HTTPError as e:
                if e.code != 400 or i == len(attempts) - 1:
                    raise
        produced = d.get("usage", {}).get("completion_tokens", 0)
        finish = d["choices"][0].get("finish_reason")
        rate = produced / elapsed if elapsed else 0.0
        print(f"[ok]   output cap: stopped at {produced} tokens ({finish}) "
              f"in {elapsed:.1f}s -> {rate:.1f} tok/s decode")
        if produced != args.expect_cap or finish != "length":
            failures.append(
                f"asked for {asked} tokens and got {produced} ({finish}); expected exactly "
                f"{args.expect_cap} with finish_reason 'length' -- the per-request cap is "
                f"not in effect, so one degenerate loop can generate to the context end")
        if rate < args.min_decode:
            failures.append(
                f"decode {rate:.1f} tok/s is below the {args.min_decode} tok/s this "
                f"serving configuration is supposed to deliver (eager measured 12.5)")
    except Exception as e:
        print(f"[FAIL] output cap / decode rate: {e}")
        failures.append("output cap probe")

    # 6. thinking, through the request shape the codex arms actually send.
    # The server-side pin does not survive a Responses request that carries
    # reasoning.effort: vLLM synthesises enable_thinking = (effort != "none") and merges
    # the server default underneath it. So the arms are only pinned if they send "none",
    # and this asks the server, in their shape, whether that holds.
    #
    # It is asked twice and compared, because none of the obvious single-response tells
    # work here. `reasoning_tokens` reads 0 either way (no reasoning parser is
    # configured, and none is wanted); the response's `reasoning` field is the request's
    # own echo and is present whatever the model did; and the `<think>` tag lives in the
    # *prompt*, with its closing tag not surviving into the message content. What does
    # separate them is the prompt itself: enabling thinking makes the template inject
    # "Reasoning effort is set to ..." into the system message, so the same user text
    # bills more input tokens. Measured on the 1-GPU probe: 24 tokens at effort=none
    # against 52 at effort=low, for one identical question.
    counted = {}
    for effort in ("none", "low"):
        try:
            d = post(f"{base}/responses", {
                "model": model, "max_output_tokens": 200,
                "reasoning": {"effort": effort, "summary": "auto"},
                "input": [{"role": "user", "content": [
                    {"type": "input_text", "text": "What is 17 times 3? Answer briefly."}]}]})
            out = "".join(c.get("text", "")
                          for item in d.get("output", []) if item.get("type") == "message"
                          for c in item.get("content", []))
            counted[effort] = d.get("usage", {}).get("input_tokens", 0)
            print(f"[ok]   responses(effort={effort}): prompt {counted[effort]} tok, "
                  f"reply {out.strip()[:60]!r}")
            if effort == "none" and "</think>" in out:
                failures.append("effort=none produced a closing </think>: thinking is on")
        except Exception as e:
            print(f"[FAIL] responses(effort={effort}): {e}")
            failures.append(f"thinking probe at effort={effort}")
    if len(counted) == 2:
        pinned = counted["none"] < counted["low"]
        print(f"[{'ok' if pinned else 'FAIL'}]   thinking pin: effort=none renders "
              f"{counted['low'] - counted['none']} fewer prompt tokens than effort=low")
        if not pinned:
            failures.append(
                f"effort=none and effort=low render the same prompt "
                f"({counted['none']} vs {counted['low']} tokens), so the template switch "
                f"is not reaching the codex arms and the asymmetry with the vLLM arm has "
                f"to be reported rather than fixed here")

    if failures:
        print("\nFAILED: " + "; ".join(failures))
        return 1
    print("\nall probes passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
