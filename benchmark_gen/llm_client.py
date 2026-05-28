from __future__ import annotations

import copy
import os
import time
from typing import Dict, List, Optional

import openai

DEFAULT_BASE_URL = "https://aigc.sankuai.com/v1/openai/native"


def _is_claude_model(model: str) -> bool:
    """Check whether the given model name refers to a Claude model."""
    return "claude" in model.lower()


def _apply_prefix_cache(messages: List[Dict]) -> List[Dict]:
    """
    Return a deep-copied message list with prefix cache applied to the last
    user / system / tool message.

    Cache control is injected as per the Anthropic prompt-caching spec:
      https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching

    NOTE: Caching only activates when the prompt is long enough (>= 1024 tokens
    for Claude 3, >= 2048 tokens for Claude 2).  Applying cache_control to
    shorter prompts is harmless – the cache simply won't be used.
    """
    messages_copy = copy.deepcopy(messages)
    # Walk backwards to find the last cacheable message.
    for msg in reversed(messages_copy):
        if msg.get("role") in ("user", "system", "tool"):
            content = msg.get("content", "")
            # Already wrapped – skip.
            if isinstance(content, list):
                # Append cache_control to the last content block.
                if content:
                    last_block = content[-1]
                    if isinstance(last_block, dict) and "cache_control" not in last_block:
                        last_block["cache_control"] = {
                            "type": "ephemeral",
                            "ttl": "5m",
                        }
            else:
                # Plain string content – wrap into a content block.
                msg["content"] = [
                    {
                        "type": "text",
                        "text": content,
                        "cache_control": {
                            "type": "ephemeral",
                            "ttl": "5m",
                        },
                    }
                ]
            break
    return messages_copy


class LLMClient:
    """
    OpenAI-SDK-based LLM client with parallel batch dispatch.

    chat() accepts a list of conversations (each a list of message dicts)
    and returns a list of response strings.

    When the model is a Claude model, prefix cache is automatically applied
    to reduce prompt token costs.
    """

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        batch_size: int = 20,
        timeout: int = 600,
        max_retries: int = 5,
    ):
        self.api_key = (
            api_key
            or os.environ.get("AGENT_API_KEY")
            or os.environ.get("AIGC_APP_KEY")
            or os.environ.get("OPENAI_API_KEY", "")
        )
        self.base_url = (
            base_url
            or os.environ.get("AGENT_API_BASE")
            or os.environ.get("AIGC_BASE_URL")
            or DEFAULT_BASE_URL
        )
        self.model = model
        self.batch_size = max(1, batch_size)
        self.timeout = timeout
        self.max_retries = max(0, max_retries)

        self._client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=0,  # We handle retries ourselves.
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def chat(
        self,
        conversations: List[List[Dict]],
        temperature: float = 0.7,
        max_new_tokens: int = 4096,
    ) -> List[str]:
        """Send multiple conversations in parallel and return responses."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        total = len(conversations)
        results: List[str] = [""] * total
        if total == 0:
            return results

        def process_one(idx: int) -> None:
            messages = [
                {"role": m.get("role", "user"), "content": m.get("content", "")}
                for m in conversations[idx]
            ]
            results[idx] = self._call_one(messages, temperature, max_new_tokens)

        num_chunks = (total + self.batch_size - 1) // self.batch_size
        for chunk_idx in range(num_chunks):
            start = chunk_idx * self.batch_size
            end = min(start + self.batch_size, total)
            with ThreadPoolExecutor(max_workers=end - start) as executor:
                futures = [executor.submit(process_one, i) for i in range(start, end)]
                for future in as_completed(futures):
                    future.result()

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_one(
        self,
        messages: List[Dict],
        temperature: float,
        max_new_tokens: int,
    ) -> str:
        """
        Call the LLM using the openai SDK.

        For Claude models, prefix cache is applied automatically to the last
        cacheable message to reduce input token costs.

        NOTE for Gemini models: Gemini 2.x consumes hidden reasoning_tokens
        that count against max_tokens but are not surfaced in the output.
        If you see truncated responses, increase --max-new-tokens (e.g. 4096).
        """
        use_cache = _is_claude_model(self.model)

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                send_messages = _apply_prefix_cache(messages) if use_cache else messages
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=send_messages,
                    temperature=temperature,
                    max_tokens=max_new_tokens,
                )
                if not response.choices:
                    raise ValueError(
                        f"Empty choices in response (model={self.model}, "
                        f"usage={response.usage})"
                    )
                choice = response.choices[0]

                # Detect truncation: reasoning models (e.g. Gemini 2.5 Pro) can
                # consume all of max_tokens on internal reasoning, leaving
                # completion_tokens=0 and message=None.  Retrying won't help –
                # just warn and bail out so the caller can fall back / retry
                # with a larger token budget.
                if choice.finish_reason == "length" or choice.message is None:
                    usage = getattr(response, "usage", None)
                    reasoning = (
                        getattr(getattr(usage, "completion_tokens_details", None),
                                "reasoning_tokens", None)
                        if usage else None
                    )
                    hint = (
                        f" (reasoning_tokens={reasoning} consumed hidden budget)"
                        if reasoning else ""
                    )
                    print(
                        f"[LLMClient] WARNING: output truncated/empty because "
                        f"max_tokens={max_new_tokens} is too small{hint}. "
                        f"Increase --max-new-tokens and retry.",
                        flush=True,
                    )
                    # No point retrying with the same token budget.
                    return ""
                return choice.message.content or ""
            except Exception as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                sleep_s = min(60, 5 * (attempt + 1))
                print(
                    f"[LLMClient] request failed ({exc}), retry {attempt+1}/{self.max_retries} "
                    f"after {sleep_s}s",
                    flush=True,
                )
                time.sleep(sleep_s)

        if last_error is not None:
            print(f"[LLMClient] request failed after all retries: {last_error}", flush=True)
        return ""
