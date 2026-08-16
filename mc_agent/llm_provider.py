"""LLM provider abstractions for the Minecraft agent.

Four classes are provided:
  - BaseLLMProvider  – abstract interface all providers implement
  - OpenAIProvider   – calls the OpenAI (or compatible) API
  - VLLMProvider     – calls a locally-running vLLM OpenAI-compatible server
  - CodexProvider    – drives a model through the Codex CLI (subscription auth,
                       no API key)
"""
from __future__ import annotations
import abc
import base64
import copy
import json
import os
import re
import shutil
import subprocess
import tempfile
from abc import abstractmethod
from pathlib import Path
from typing import Any

from loguru import logger
from openai import OpenAI

from mc_agent.utils import deco_retry_on_ratelimit
# One definition of what codex is told about a locally served model, so the two codex
# paths -- this provider and PRO-LONG's own turn runner -- cannot drift apart on the
# setting that decides whether the conversation gets compacted underneath them.
from prolong_mc.codex_backend import DEFAULT_CONTEXT_WINDOW, _metadata_args, effort_for


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class BaseLLMProvider(abc.ABC):
    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None
    ) -> None:
        self.api_key = api_key
        self.api_base = api_base

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        max_tokens: int = 10240,
        temperature: float = 0.7,
        response_format: dict | None = None
    ) -> str:
        raise NotImplementedError("BaseLLMProvider is an abstract class, you need to implement subclass")


# ---------------------------------------------------------------------------
# OpenAI / compatible API provider
# ---------------------------------------------------------------------------

class OpenAIProvider(BaseLLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        default_model: str = "gpt-5.2-chat",
        temperature: float = 0.7,
    ) -> None:
        super().__init__(api_key, api_base)
        self.default_model = default_model
        self.temperature = temperature

        if api_base and not api_base.endswith('/'):
            api_base += '/'
        self.api_base = api_base

        self.client = OpenAI(api_key=self.api_key, base_url=self.api_base)

    @deco_retry_on_ratelimit(max_retries=10, wait_seconds=60)
    def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float | None = None,
        timeout: int = 60,
        response_format: dict | None = None
    ) -> str:
        logger.info("Querying LLM directly via OpenAI client...")
        model = model if model else self.default_model
        temperature = temperature if temperature is not None else self.temperature
        # kimi models only accept temperature=1
        if model.startswith("kimi"):
            temperature = 1
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            timeout=timeout,
            temperature=temperature,
            response_format=response_format
        )
        return response.choices[0].message.content


# ---------------------------------------------------------------------------
# vLLM local server provider
# ---------------------------------------------------------------------------

# Models that only accept a single image per request.
_SINGLE_IMAGE_MODELS = (
    "llama-3.2",
    "llama3.2",
)


def _truncate_images(messages: list[dict[str, Any]], max_images: int) -> list[dict[str, Any]]:
    """Return a deep-copied messages list with at most *max_images* image_url
    content blocks retained (keeping the *last* N images so the model sees the
    most recent frames).

    Text blocks and non-image_url blocks are left untouched.
    """
    if max_images <= 0:
        return messages

    total = sum(
        sum(1 for block in msg.get("content", []) if isinstance(block, dict) and block.get("type") == "image_url")
        for msg in messages
        if isinstance(msg.get("content"), list)
    )

    if total <= max_images:
        return messages

    to_skip = total - max_images
    skipped = 0
    result = []
    for msg in messages:
        content = msg.get("content")
        if not isinstance(content, list):
            result.append(msg)
            continue
        new_content = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "image_url":
                if skipped < to_skip:
                    skipped += 1
                    continue
            new_content.append(block)
        new_msg = copy.copy(msg)
        new_msg["content"] = new_content
        result.append(new_msg)

    logger.debug(f"[VLLMProvider] Trimmed images: {total} → {max_images} (dropped {to_skip} earliest frames)")
    return result


class VLLMProvider(BaseLLMProvider):
    """LLM provider backed by a locally-running vLLM OpenAI-compatible server.

    Typical usage – start vLLM in one terminal::

        python -m vllm.entrypoints.openai.api_server \\
            --model /path/to/Qwen3-VL-235B-A22B-Instruct \\
            --served-model-name Qwen3-VL-235B-A22B-Instruct \\
            --port 8000 --tensor-parallel-size 8

    Then pass ``--use-vllm`` to the eval script::

        python eval_benchmark.py run \\
            --model Qwen3-VL-235B-A22B-Instruct \\
            --use-vllm --num-workers 10 --resume
    """

    def __init__(
        self,
        model_name: str,
        base_url: str = "http://localhost:8000/v1",
        api_key: str = "EMPTY",
        max_images: int | None = None,
        temperature: float = 0.7,
    ) -> None:
        super().__init__(api_key=api_key, api_base=base_url)
        self.default_model = model_name
        self.temperature = temperature

        if not base_url.endswith("/"):
            base_url += "/"
        self.api_base = base_url

        self.client = OpenAI(api_key=api_key, base_url=base_url)

        if max_images is not None:
            self.max_images: int | None = max_images
        elif any(s in model_name.lower() for s in _SINGLE_IMAGE_MODELS):
            self.max_images = 1
            logger.info(
                f"[VLLMProvider] Model '{model_name}' only supports 1 image per request. "
                f"Multi-frame buffers will be trimmed to the most recent frame automatically."
            )
        else:
            self.max_images = None

        logger.info(
            f"[VLLMProvider] Connected to vLLM server at {base_url}  "
            f"model={model_name}  max_images={self.max_images}"
        )

    def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float | None = None,
        timeout: int = 120,
        response_format: dict | None = None,
        max_tokens: int = 4096,
    ) -> str:
        effective_model = model if model else self.default_model
        temperature = temperature if temperature is not None else self.temperature

        if self.max_images is not None:
            messages = _truncate_images(messages, self.max_images)

        logger.info(
            f"[VLLMProvider] Querying vLLM  model={effective_model}  "
            f"temp={temperature}  max_tokens={max_tokens}"
        )

        kwargs: dict[str, Any] = dict(
            model=effective_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        if response_format is not None:
            kwargs["response_format"] = response_format

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Codex CLI provider
# ---------------------------------------------------------------------------

_DATA_URI_RE = re.compile(r"^data:image/(\w+);base64,(.*)$", re.DOTALL)


class CodexProvider(BaseLLMProvider):
    """Drive a hosted model through the Codex CLI instead of an HTTP endpoint.

    This exists because a Codex/ChatGPT subscription authenticates with an OAuth
    token, not an API key (``~/.codex/auth.json`` has ``auth_mode="chatgpt"`` and no
    ``OPENAI_API_KEY``), so ``OpenAIProvider`` cannot reach those models at all. The
    CLI can, and it accepts images via ``-i``, which is what this agent needs.

    **Interpretive caveat.** This is not a clean model swap against the vLLM path.
    Codex wraps every call in its own agent scaffolding — system prompt, tool
    definitions, reasoning configuration — so a score obtained here is "model via the
    Codex harness", not the model answering as a plain VLM. Comparisons against
    ``VLLMProvider`` runs carry that difference and should say so.

    Each ``chat`` is a fresh ``codex exec`` with no ``resume``, which matches the
    stateless semantics of the other providers: the caller resends the whole message
    list every turn and nothing is retained between turns.
    """

    def __init__(
        self,
        model_name: str = "gpt-5.6-sol",
        reasoning_effort: str = "xhigh",
        codex_bin: str | None = None,
        max_images: int | None = None,
        timeout: int = 900,
        transcript_dir: str | None = None,
        base_url: str | None = None,
        context_window: int | None = None,
    ) -> None:
        super().__init__(api_key=None, api_base=base_url)
        self.default_model = model_name
        self.reasoning_effort = reasoning_effort
        self.context_window = context_window or DEFAULT_CONTEXT_WINDOW
        self.codex_bin = codex_bin or os.environ.get("CODEX_BIN", "codex")
        self.max_images = max_images
        self.timeout = timeout
        # When set, codex is redirected at a local OpenAI-compatible server instead
        # of the account's hosted models, which is how a local model gets driven
        # through the same harness. The server must tolerate the Responses API's
        # `developer` role and codex's `client_metadata`; see
        # scripts/serve_qwen_for_codex.py.
        self.base_url = base_url
        self.transcript_dir = Path(transcript_dir) if transcript_dir else None
        if self.transcript_dir:
            self.transcript_dir.mkdir(parents=True, exist_ok=True)
        self._calls = 0

        if shutil.which(self.codex_bin) is None and not Path(self.codex_bin).exists():
            raise RuntimeError(f"codex binary not found: {self.codex_bin}")

        logger.info(
            f"[CodexProvider] model={model_name} effort={reasoning_effort} "
            f"max_images={max_images} bin={self.codex_bin} "
            f"endpoint={base_url or 'hosted'}"
        )

    @staticmethod
    def _flatten(messages: list[dict[str, Any]], image_dir: Path) -> tuple[str, list[Path]]:
        """Render the OpenAI message list as one prompt plus image files on disk.

        Frames are numbered in conversation order and referenced by filename in the
        prompt, so "Frame 3" in the text still points at a specific attachment once
        the structure is gone.
        """
        parts: list[str] = []
        images: list[Path] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content")
            if isinstance(content, str):
                parts.append(f"[{role}]\n{content}")
                continue
            chunk: list[str] = []
            for block in content or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    chunk.append(block.get("text", ""))
                elif block.get("type") == "image_url":
                    url = (block.get("image_url") or {}).get("url", "")
                    m = _DATA_URI_RE.match(url)
                    if not m:
                        continue
                    ext, payload = m.group(1), m.group(2)
                    path = image_dir / f"frame_{len(images) + 1:03d}.{ext}"
                    path.write_bytes(base64.b64decode(payload))
                    images.append(path)
                    chunk.append(f"<attached image: {path.name}>")
            parts.append(f"[{role}]\n" + "\n".join(chunk))
        return "\n\n".join(parts), images

    def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float | None = None,
        timeout: int | None = None,
        response_format: dict | None = None,
        max_tokens: int = 4096,
    ) -> str:
        # temperature/max_tokens/response_format have no equivalent on the CLI; they
        # are accepted for interface compatibility and deliberately ignored.
        effective_model = model or self.default_model
        if self.max_images is not None:
            messages = _truncate_images(messages, self.max_images)

        self._calls += 1
        workdir = Path(tempfile.mkdtemp(prefix="codex-provider-"))
        try:
            prompt, images = self._flatten(messages, workdir)
            out_file = workdir / "last_message.txt"
            cmd = [
                self.codex_bin, "exec",
                "--json", "--skip-git-repo-check", "--ignore-user-config", "--ignore-rules",
                "-m", effective_model,
                "-c", f'model_reasoning_effort="{effort_for(self.base_url, self.reasoning_effort)}"',
                "-s", "workspace-write",
                "-o", str(out_file),
            ]
            if self.base_url:
                cmd += [
                    "-c", "model_provider=local",
                    "-c", 'model_providers.local.name="local"',
                    "-c", f'model_providers.local.base_url="{self.base_url}"',
                    "-c", 'model_providers.local.wire_api="responses"',
                    "-c", 'model_providers.local.env_key="LOCAL_API_KEY"',
                ] + _metadata_args(self.context_window)
            for img in images:
                cmd += ["-i", str(img)]
            # `-i/--image` is variadic, so a positional prompt appended after it is
            # swallowed as one more image path and codex silently falls back to
            # stdin. Pass the prompt on stdin explicitly instead: `-` is codex's
            # documented sentinel for that and cannot be captured by --image.
            cmd.append("-")

            logger.info(
                f"[CodexProvider] call {self._calls}: model={effective_model} "
                f"images={len(images)} prompt_chars={len(prompt)}"
            )
            proc = subprocess.run(
                cmd, cwd=workdir, input=prompt,
                capture_output=True, text=True,
                timeout=timeout or self.timeout,
            )

            if self.transcript_dir:
                stem = self.transcript_dir / f"call_{self._calls:04d}"
                stem.with_suffix(".events.jsonl").write_text(proc.stdout)
                stem.with_suffix(".prompt.txt").write_text(prompt)
                if proc.stderr:
                    stem.with_suffix(".stderr.txt").write_text(proc.stderr)

            if out_file.exists():
                reply = out_file.read_text().strip()
                if reply:
                    return reply

            # No -o file means the turn failed; surface the CLI's own reason rather
            # than an empty string the agent would silently mis-parse.
            reasons = []
            for line in proc.stdout.splitlines():
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                if ev.get("type") in ("error", "turn.failed"):
                    reasons.append(str(ev.get("message") or ev.get("error", {}).get("message", "")))
            raise RuntimeError(
                f"codex exec produced no message (rc={proc.returncode}): "
                f"{reasons[-1] if reasons else proc.stderr[:300]}"
            )
        finally:
            # Always remove it: the prompt and events are already copied into
            # transcript_dir, and keeping ~20 frames per call would leave thousands
            # of files in the node's tmpfs over a 300-step episode.
            shutil.rmtree(workdir, ignore_errors=True)
