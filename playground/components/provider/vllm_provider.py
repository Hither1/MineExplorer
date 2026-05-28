from __future__ import annotations
import copy
from typing import Any

from loguru import logger
from openai import OpenAI
from .base import BaseLLMProvider

# Models that only accept a single image per request.
# Add more model name substrings here as needed.
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

    # Count total images across all messages
    total = sum(
        sum(1 for block in msg.get("content", []) if isinstance(block, dict) and block.get("type") == "image_url")
        for msg in messages
        if isinstance(msg.get("content"), list)
    )

    if total <= max_images:
        return messages  # nothing to trim

    # We need to drop (total - max_images) images, skipping the first ones.
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
                    continue  # drop this image
            new_content.append(block)
        new_msg = copy.copy(msg)
        new_msg["content"] = new_content
        result.append(new_msg)

    logger.debug(f"[VLLMProvider] Trimmed images: {total} → {max_images} (dropped {to_skip} earliest frames)")
    return result


class VLLMProvider(BaseLLMProvider):
    """LLM provider backed by a locally-running vLLM OpenAI-compatible server.

    vLLM exposes an OpenAI-compatible REST API, so we simply point the OpenAI
    client at the local server URL instead of the real OpenAI endpoint.

    Typical usage:
        Start vLLM in one terminal::

            python -m vllm.entrypoints.openai.api_server \\
                --model /path/to/Qwen3-VL-235B-A22B-Instruct \\
                --served-model-name Qwen3-VL-235B-A22B-Instruct \\
                --port 8000 \\
                --tensor-parallel-size 8

        Then pass ``--use-vllm`` to the eval script::

            python playground/examples/eval_minestudio.py run \\
                --model Qwen3-VL-235B-A22B-Instruct \\
                --use-vllm \\
                --num-workers 10 --resume
    """

    def __init__(
        self,
        model_name: str,
        base_url: str = "http://localhost:8000/v1",
        api_key: str = "EMPTY",
        max_images: int | None = None,
    ) -> None:
        super().__init__(api_key=api_key, api_base=base_url)
        self.default_model = model_name

        if not base_url.endswith("/"):
            base_url += "/"
        self.api_base = base_url

        self.client = OpenAI(api_key=api_key, base_url=base_url)

        # Determine the effective image limit:
        # - If the caller passes an explicit max_images, honour it.
        # - Otherwise auto-detect known single-image models and cap at 1.
        # - Otherwise leave unconstrained (None).
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
        temperature: float = 0.7,
        timeout: int = 120,
        response_format: dict | None = None,
        max_tokens: int = 4096,
    ) -> str:
        """Send a chat-completion request to the local vLLM server.

        Parameters are intentionally kept identical to ``OpenAIProvider.chat``
        so the two providers are interchangeable.
        """
        effective_model = model if model else self.default_model

        # Trim images if this model has a per-request image limit
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
        response_content = response.choices[0].message.content
        return response_content
