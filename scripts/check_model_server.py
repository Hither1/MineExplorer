"""Ask a model server whether it can actually do the three things a run needs.

Not "is the port open" -- that question has already been answered wrongly twice here,
once by a stranger's process and once by a server holding a different model. This
asks the server to produce text, to look at a real Minecraft frame, and to accept the
Responses API request shape the Codex CLI sends, and it prints what came back so the
answers can be judged rather than trusted.

Usage: check_model_server.py <base-url> [--model M] [--frame path.png]
Exit code is non-zero if any probe fails.
"""
from __future__ import annotations

import argparse
import base64
import json
import pathlib
import sys
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

    if failures:
        print("\nFAILED: " + "; ".join(failures))
        return 1
    print("\nall probes passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
